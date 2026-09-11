// 띵동 firmware - 마이크 링버퍼 2초 스냅샷 → /api/v1/detect 업로드 (2026-09-11, M5-d)
//
// ★ PR 성격 = **배관(plumbing)**. decisions.md 8.5 서문 정의 준용:
//   새 판정 기준·임계값·상태 어휘를 0개 신설하고, 이미 양쪽 끝이 완성된 두 계층을 잇는다.
//     송신 끝 = M5-a/a2 PSRAM 2초 링버퍼 32슬롯 (firmware, 프로즌 mic_common — import만)
//     수신 끝 = PR #24 /detect multipart + int16 PCM 64KB 수신 + PR #43 ToF fail-open
//   그 사이 송신 코드가 **0줄**이었다 (decisions.md 6.2/6.4: "G10 수신측 CLOSE ≠ G10 CLOSE
//   — 송신측(마이크 M5-d …)은 여전히 0줄"). 본 env가 그 0줄을 채운다.
//
// ★ 트리거 = **시리얼 키 's' 수동 입력**이다. RMS 임계값·pre/post 비율은 M5-c 소관이고
//   현관 실측(C-0) 전이라 판정 근거가 없다 → "측정 전 확정"을 하지 않기 위해
//   (decisions.md 카테고리 20 "계측 → 실측 → 판정") 판정 없이 **경로만 먼저** 잇는다.
//   본 파일에는 임계값 비교가 단 한 줄도 없다.
//
// ★ 페이로드 = 링버퍼 최근 2.048초(32슬롯 = 65,536 bytes)를 **오래된→최신 순서 그대로**.
//   pre/post 비율 개념을 도입하지 않는다(도입하면 그 자체가 M5-c 판정이다).
//
// ★ 2026-09-11 PoC-(45) ToF 메타 4필드 송신 (G10 송신측). 역시 **배관**이다:
//   tofTask(tof_common.cpp tofJudgeFrame — tof_dummy 와 같은 판정, 복제 아님)가 매 프레임 최신
//   판정 한 벌을 공유 구조체에 쓰고, 's' 입력 **시점**의 한 벌을 그대로 4필드로 싣는다(D1).
//   2초 창 집계·다수결·신선도 임계 같은 새 판정은 0줄(D1/D4). ToF init 실패 = 4필드 미전송 =
//   PR #52 동작(서버 tof_absent)으로 degrade(D3).

#include <Arduino.h>
#include <WiFi.h>
#include <string.h>

#include "esp_random.h"
#include "mic_common.h"
#include "secrets.h"
#include "tof_common.h"
#include "uplink_common.h"

extern SparkFun_VL53L5CX tofImager;  // tof_common.cpp 소유 (tof_test.cpp 와 동형)

// ── PSRAM 버퍼 (setup에서 1회 할당, 이후 불변) ──────────────────────────────
// 링버퍼 본체(64KB, initMicRingBuffer)는 micUplinkTask 지역변수 = mic_common.h 컨벤션 그대로.
static uint8_t* g_snap = nullptr;  // 64KB 스냅샷 (micUplinkTask가 쓰고 loop가 읽는다)
static uint8_t* g_body = nullptr;  // multipart 조립 버퍼 (loop 전용)

// ── 태스크 ↔ loop 핸드셰이크 ───────────────────────────────────────────────
// ★ 락을 쓰지 않는 근거 (전 상태 열거): 각 플래그는 **쓰는 쪽이 한 곳뿐**이고, 두 플래그가
//   상태를 주고받는 순서가 한 방향으로만 돈다.
//     IDLE  ──loop: req=true──▶  REQUESTED
//     REQUESTED ──task: 복사 후 ready=true, req=false──▶ READY
//     READY ──loop: POST 후 ready=false──▶ IDLE
//   g_snap 은 REQUESTED 구간에서만 task가 쓰고, READY 구간에서만 loop가 읽는다 — 두 구간은
//   ready 플래그 하나로 배타적이라 동시 접근 자체가 발생하지 않는다. req 는 loop만,
//   ready 는 task만 true 로 만든다(각 플래그의 set 주체가 유일 = read-modify-write 경합 없음).
//   ⚠️ 여기에 "여러 스냅샷 큐"나 세 번째 상태를 추가하면 이 논증이 깨진다. 큐가 필요해지면
//      그때 FreeRTOS queue 로 바꿀 것 — 플래그를 하나 더 늘리지 말 것.
static volatile bool g_snapReq   = false;  // loop → task : 다음 슬롯 경계에서 스냅샷 떠라
static volatile bool g_snapReady = false;  // task → loop : 스냅샷 준비됨, 보내라
static volatile bool g_ringFull  = false;  // task → loop : 32슬롯이 한 번 이상 다 찼다

// 스냅샷 진폭 관측값 (④런타임 대조 실험의 **입력값 축** — 조용함 vs 손뼉을 여기서 가른다).
// 판정에 쓰지 않는다. 임계값 비교 0줄.
static volatile int32_t  g_snapRms  = 0;
static volatile int32_t  g_snapPeak = 0;
static volatile uint32_t g_snapBytes = 0;
static volatile uint32_t g_taskStackFree = 0;
static volatile uint32_t g_ringGaps      = 0;  // task → loop : ring.gaps 누적 사본(스냅샷마다 갱신)

// ── ToF 최신 판정 공유 (tofTask → loop) ───────────────────────────────────
// ★ 보호 방식 = portMUX 크리티컬 섹션(spinlock). 근거:
//   - 쓰기 = tofTask(Core 0) 15Hz, 읽기 = loop(Core 1) 's' 1회당 1번. 양쪽 다 12B 구조체 복사 1회라
//     점유 시간이 수백 ns — 뮤텍스(블로킹·컨텍스트 스위치)는 과하고, volatile 만으로는 4값이
//     **서로 다른 프레임에서 섞이는** torn read 를 막지 못한다(구조체 복사는 원자적이지 않다).
//   - portMUX 는 두 코어 사이에서도 유효하다(taskENTER_CRITICAL 이 spinlock + 로컬 인터럽트 마스크).
//     Core 0 에서 수백 ns 인터럽트 마스크는 I2S DMA ISR 지연으로 무시 가능(DMA 는 8×64ms 버퍼링).
//   ⚠️ 신선도(staleness) 정책은 신설하지 않는다(D4). g_tofLatestMs 는 age_ms 관측 전용이다.
//     [defer] age_ms 임계 도입 여부 판정 방법: Runbook 9절 (b) 에서 age_ms 분포를 수집한다.
//       15Hz 정상이면 상시 < 100ms. 수백 ms 이상이 반복되면 I2C 정체(getRangingData 지연)가
//       실재하는 것이고, 그때 "age_ms > N 이면 4필드 미전송" 규칙을 근거(분포)와 함께 도입한다.
static portMUX_TYPE   g_tofMux      = portMUX_INITIALIZER_UNLOCKED;
static TofFrameResult g_tofLatest   = {};  // g_tofMux 보호
static uint32_t       g_tofLatestMs = 0;   // g_tofMux 보호. 0 = 아직 프레임 없음(millis 0ms 에 프레임 불가)
static bool           g_tofAvailable = false;  // setup 이 1회 쓰고 이후 읽기만 (init 실패 = degrade)
static volatile uint32_t g_tofStackFree = 0;

// 's' 시점 캡처본 (loop 전용 — 이후 sendSnapshot 이 읽는다)
static TofFrameResult g_tofAtS      = {};
static bool           g_tofAtSValid = false;
static uint32_t       g_tofAgeMs    = 0;

// ── client_request_id (decisions.md 6.3(l) ⑤ 처리) ─────────────────────────
// 하네스(upload_spike_main.cpp)는 "spike-<millis()>-<seq>" 를 쓴다. millis()는 **매 부팅
// 0부터 다시 센다** → 재부팅하면 같은 id가 재생산되고, 서버는 그것을 24h TTL 멱등 키로
// 취급해 **캐시 응답을 replay**한다(routes.py: IdempotencyKey 조회 → 200 + Idempotent-Replay).
// 즉 새 소리를 보냈는데 옛 판정이 돌아온다 = 조용한 오작동이다.
// → 부팅마다 esp_random() 32비트 nonce를 뽑아 앞에 붙인다. 서버 계약은 손대지 않는다
//   (client_request_id 는 "비어있지 않은 문자열" 외 형식 제약이 없다 — routes.py 실독).
// ⚠️ 충돌 확률은 0이 아니다(생일 문제). 하지만 24h TTL 안에 같은 nonce를 두 번 뽑을
//   확률은 2^-32 규모라 부스 시연 단위에서 무시 가능하다. 기기 고유값(MAC)을 쓰지 않은
//   이유는 그 반대다 — MAC 은 부팅 간 **동일**해서 재부팅 충돌을 못 막는다.
static char     g_idNonce[9] = {0};
static uint32_t g_idSeq      = 0;

static void makeClientRequestId(char* out, size_t cap) {
  snprintf(out, cap, "m5d-%s-%u", g_idNonce, (unsigned)(++g_idSeq));
}

// ── 응답 JSON 얕은 추출 ────────────────────────────────────────────────────
// 필요한 값이 3개(predicted_class / confidence / tof_check.reason)뿐이라 JSON 파서를
// 끌어오지 않는다(§3 신규 의존성 금지 — ArduinoJson 은 env:poc lib_deps 에만 있다).
// "key": 뒤의 문자열 또는 스칼라를 그대로 복사한다. 못 찾으면 false → 호출부가 "?" 를 찍어
// **조용히 틀린 값을 만들지 않는다**.
// ※ "reason" 패턴은 "skip_reason" 과 겹치지 않는다 — 선행 큰따옴표가 다르다.
static bool jsonPeek(const char* body, const char* key, char* out, size_t cap) {
  char pat[32];
  snprintf(pat, sizeof(pat), "\"%s\":", key);
  const char* p = strstr(body, pat);
  if (p == nullptr) {
    return false;
  }
  p += strlen(pat);
  while (*p == ' ') {
    ++p;
  }
  const bool quoted = (*p == '"');
  if (quoted) {
    ++p;
  }
  size_t i = 0;
  while (*p != '\0' && i + 1 < cap) {
    if (quoted ? (*p == '"') : (*p == ',' || *p == '}' || *p == ' ')) {
      break;
    }
    out[i++] = *p++;
  }
  out[i] = '\0';
  return i > 0;
}

// ── 마이크 태스크: 적재 + (요청 시) 스냅샷 ─────────────────────────────────
static void micUplinkTask(void* parameter) {
  (void)parameter;

  // mic_test.cpp 와 동일 구조 — DMA 수신 버퍼는 4KiB라 스택(4KiB)이 아닌 BSS에 둔다.
  static union {
    int32_t raw[MIC_DMA_BUF_LEN];
    int16_t i16[MIC_DMA_BUF_LEN];
  } audio_buffer;

  int16_t* const ring_base = initMicRingBuffer();
  MicRingStatus  ring      = {};
  size_t         bytes_read = 0;

  if (ring_base == nullptr) {
    Serial.println("[mic][M5d] ring alloc 실패 — 스냅샷 불가, 적재만 계속");
  }

  for (;;) {
    const esp_err_t err = i2s_read(MIC_I2S_PORT, audio_buffer.raw, sizeof(audio_buffer.raw),
                                   &bytes_read, portMAX_DELAY);
    if (err != ESP_OK) {
      ring.gaps++;
      continue;
    }

    size_t n = bytes_read / sizeof(int32_t);
    if (n > (size_t)MIC_DMA_BUF_LEN) {
      n = (size_t)MIC_DMA_BUF_LEN;  // 슬롯 경계 초과 쓰기 방어 (mic_test.cpp 동형)
    }

    int16_t* const slot = micRingSlot(ring_base, ring.write_idx);
    if (slot == nullptr) {
      continue;  // 링버퍼 미가용 — 적재할 곳이 없다
    }
    convertMicRawToInt16(audio_buffer.raw, slot, n);
    micRingAdvance(&ring);

    if (!g_ringFull && ring.slots_filled >= MIC_RING_SLOTS) {
      g_ringFull = true;
      Serial.println("[mic][M5d] ring filled — 's' 키로 스냅샷 전송 가능");
    }

    // ── 스냅샷: **torn read 가 구조적으로 불가능한 지점**에서만 뜬다 ──────────
    // ★ 설계 결정 (§6 기록 대상)
    //   후보 A) loop 태스크가 링버퍼를 직접 복사한다 → 복사 64KB 도중 micUplinkTask 가
    //           슬롯을 계속 덮어써서 **찢어진 프레임**(앞부분 새 소리 / 뒷부분 옛 소리)이
    //           섞인다. 막으려면 뮤텍스가 필요하고, 뮤텍스는 i2s_read 폴링 루프를 막아
    //           DMA 오버런 위험을 새로 만든다.
    //   후보 B) 채택 — **복사를 micUplinkTask 안에서, micRingAdvance 직후에** 한다.
    //           그 순간 이 태스크는 링버퍼에 쓰고 있지 않고(방금 쓰기를 끝냈다), 링버퍼에
    //           쓰는 주체는 이 태스크가 유일하다 → 복사 중 쓰기가 **존재할 수 없다**.
    //           락이 필요 없는 게 아니라 **경합 자체가 없다**.
    //   ★ 비용: 복사 동안 i2s_read 가 지연된다. PSRAM→PSRAM 64KB memcpy 는 ms 단위이고,
    //           DMA 는 MIC_DMA_BUF_COUNT(8) × 64ms = 512ms 를 버퍼링하므로 잠식은 미미하다.
    //           그래도 실제로 구멍이 생기면 ring.gaps 가 오르거나 다음 i2s_read 가 즉시
    //           반환된다 → ④런타임에서 관측 가능하다.
    //
    // ★ 순서: 오래된→최신. 링버퍼가 꽉 찬 상태에서 write_idx 는 "다음에 덮어쓸 칸"
    //   = 현재 살아 있는 데이터 중 **가장 오래된 칸**이다. 거기서 32칸을 돌면 시간순이다.
    if (g_snapReq && ring.slots_filled >= MIC_RING_SLOTS) {
      size_t copied = 0;
      for (uint32_t i = 0; i < MIC_RING_SLOTS; ++i) {
        const int16_t* const src = micRingSlot(ring_base, ring.write_idx + i);
        if (src == nullptr) {
          break;  // 도달 불가(ring_base 널이면 위에서 이미 continue) — 방어적
        }
        memcpy(g_snap + copied, src, (size_t)MIC_DMA_BUF_LEN * sizeof(int16_t));
        copied += (size_t)MIC_DMA_BUF_LEN * sizeof(int16_t);
      }

      // 진폭 관측 (관측 전용 — 비교·판정 0줄). Σv² ≤ 32768 × 32767² ≈ 3.5e13 → int64 필수.
      const int16_t* const s = reinterpret_cast<const int16_t*>(g_snap);
      const size_t         ns = copied / sizeof(int16_t);
      int64_t              acc = 0;
      int32_t              peak = 0;
      for (size_t i = 0; i < ns; ++i) {
        const int32_t v = (int32_t)s[i];             // int16 중간 변수 금지: |INT16_MIN| 부호 반전
        const int32_t a = (v >= 0) ? v : -v;          // → int32 에서만 절댓값 (mic_test.cpp 동형)
        if (a > peak) {
          peak = a;
        }
        acc += (int64_t)v * (int64_t)v;
      }

      g_snapBytes = (uint32_t)copied;
      g_snapPeak  = peak;
      g_snapRms   = (ns > 0) ? (int32_t)sqrt((double)acc / (double)ns) : 0;
      g_taskStackFree = (uint32_t)uxTaskGetStackHighWaterMark(nullptr);
      g_ringGaps      = ring.gaps;

      g_snapReq = false;

      // ★ volatile 만으로는 부족하다: volatile 저장은 **비**volatile 접근(위 memcpy 64KB)의
      //   재배치를 막지 않는다(C++ 메모리 모델). g_snapReady 가 먼저 보이면 loop 는 아직
      //   덜 채워진 g_snap 을 전송한다 = 조용히 잘린 페이로드. 전체 배리어 1회로 봉인한다.
      //   (비용 = 스냅샷당 1회. 적재 루프에는 닿지 않는다.)
      __sync_synchronize();
      g_snapReady = true;  // ★ 반드시 마지막 — 이 줄 앞의 모든 쓰기가 loop 에 보여야 한다
    }
  }
}

// ── ToF 태스크: 폴링 + 판정 + 최신 한 벌 공유 ─────────────────────────────
// tof_test.cpp tofTask 와 동형(폴링·에러 카운트·주기). 판정 본문은 tofJudgeFrame 공유(복제 0).
static void tofUplinkTask(void* parameter) {
  (void)parameter;
  logToFMemoryDiagnostics("tofTask-entry");
  static VL53L5CX_ResultsData measurementData;  // ~1356B → BSS (tof_test.cpp 동형)
  static TofJudgeState        judge;
  uint32_t err_count = 0;

  for (;;) {
    if (tofImager.isDataReady()) {
      if (tofImager.getRangingData(&measurementData)) {
        const TofFrameResult r   = tofJudgeFrame(&judge, measurementData);
        const uint32_t       now = millis();
        taskENTER_CRITICAL(&g_tofMux);
        g_tofLatest   = r;    // 4값 + 시각을 한 벌로 — 섞임 불가
        g_tofLatestMs = now;
        taskEXIT_CRITICAL(&g_tofMux);
        g_tofStackFree = (uint32_t)uxTaskGetStackHighWaterMark(nullptr);
      } else {
        if ((++err_count % 10) == 1) {
          Serial.printf("[tof] getRangingData failed #%u\n", (unsigned)err_count);
        }
      }
    }
    vTaskDelay(pdMS_TO_TICKS(TOF_PERIOD_MS));
  }
}

// 's' 입력 시점의 ToF 최신 판정 한 벌을 캡처 + 로그 1줄(≤80B). D1: 집계 없이 그대로.
static void captureTofAtTrigger() {
  g_tofAtSValid = false;
  if (!g_tofAvailable) {
    Serial.println("[tof][M5d] tof 없음 — 4필드 미전송(서버 tof_absent)");
    return;
  }
  uint32_t ms;
  taskENTER_CRITICAL(&g_tofMux);
  g_tofAtS = g_tofLatest;
  ms       = g_tofLatestMs;
  taskEXIT_CRITICAL(&g_tofMux);
  if (ms == 0) {
    Serial.println("[tof][M5d] 첫 프레임 전 — 4필드 미전송(서버 tof_absent)");
    return;
  }
  g_tofAtSValid = true;
  g_tofAgeMs    = millis() - ms;

  char center[8];
  if (g_tofAtS.center_valid) {
    snprintf(center, sizeof(center), "%umm", (unsigned)g_tofAtS.center_mm);
  } else {
    snprintf(center, sizeof(center), "n/a");
  }
  // 최악 "[tof][M5d] presence=false near=64/64 center=4000mm ndet=16/16 age_ms=4294967295" = 79B.
  Serial.printf("[tof][M5d] presence=%s near=%u/%u center=%s ndet=%u/%u age_ms=%u\n",
                g_tofAtS.fused ? "true" : "false", (unsigned)g_tofAtS.near_count,
                (unsigned)TOF_ZONE_COUNT, center, (unsigned)g_tofAtS.motion_ndet,
                (unsigned)TOF_MOTION_AGG_COUNT_8X8, (unsigned)g_tofAgeMs);
}

// ── 전송 (loop 태스크에서 수행) ────────────────────────────────────────────
// ★ 태스크 배치 근거 (decisions.md 6.3(l) ① 처리)
//   ①은 "업로드 코드가 같은 태스크에 붙는 구조가 되면 MIC_TASK_STACK_SIZE=4096 스택 부족
//   위험"을 경고한다. → 붙이지 않는다. POST 는 Arduino loop 태스크에서 돈다.
//   근거: 프로즌 upload_spike_main.cpp 가 **setup() 안에서** 같은 POST 를 수행하고
//   2026-07-28 ④런타임을 완주했다 — setup()/loop() 는 같은 loopTask 이므로 그 스택
//   (CONFIG_ARDUINO_LOOP_STACK_SIZE, 기본 8192B)에서 HTTPClient+WiFiClient+String 이
//   동작한다는 것이 **이미 실측된 사실**이다. 새 태스크를 만들지 않는 이유이기도 하다.
//   micUplinkTask 는 4096 그대로 두되 여유를 uxTaskGetStackHighWaterMark 로 매 스냅샷
//   출력해 ④런타임에서 숫자로 확인한다(아래 stk_free).
static void sendSnapshot() {
  char id[32];
  makeClientRequestId(id, sizeof(id));

  const uint32_t bytes = g_snapBytes;

  // ★ 가드: 페이로드 바이트 수. 65,536 이 아니면 서버 계약(2초 int16 PCM)이 깨진 것이고,
  //   홀수 바이트면 audio_decode.decode_pcm16 이 400 으로 거절한다. 보내기 전에 잡는다.
  if (bytes != UPLINK_AUDIO_BYTES) {
    Serial.printf("[mic][M5d] snapshot bytes=%u != %u — 전송 중단\n", (unsigned)bytes,
                  (unsigned)UPLINK_AUDIO_BYTES);
    return;
  }

  Serial.printf("[mic][M5d] id=%s bytes=%u rms=%d peak=%d\n", id, (unsigned)bytes,
                (int)g_snapRms, (int)g_snapPeak);
  // gaps = i2s_read 실패 누적(④ (b) 동시 구동 부하에서 증가 0 이어야 함) / tof_stk = tofTask 스택 최저 여유.
  Serial.printf("[mic][M5d] stk_free=%u psram_free=%u gaps=%u tof_stk=%u\n",
                (unsigned)g_taskStackFree, (unsigned)ESP.getFreePsram(), (unsigned)g_ringGaps,
                (unsigned)g_tofStackFree);

  // WiFi 끊김: 재시도하지 않는다(1차 재시도 없음 정책). 로그만 남기고 이번 건은 버린다.
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[mic][M5d] WiFi 끊김 — 전송 생략(재시도 없음)");
    return;
  }

  char resp[UPLINK_RESP_BUF_BYTES];
  const UplinkResult r =
      uplinkPostAudio(SPIKE_SERVER_HOST, SPIKE_SERVER_PORT, id, g_snap, UPLINK_AUDIO_BYTES,
                      g_body, UPLINK_AUDIO_BYTES + UPLINK_MULTIPART_OVERHEAD_BYTES, resp,
                      sizeof(resp), g_tofAtSValid ? &g_tofAtS : nullptr);

  if (r.httpStatus <= 0) {
    // 타임아웃·소켓 실패. 재시도 없음 — 429/401 과 동일하게 로그만 남긴다.
    Serial.printf("[mic][M5d] http=%d rtt=%ums 전송실패(재시도 없음)\n", r.httpStatus,
                  (unsigned)r.roundTripMs);
    return;
  }

  char cls[16] = "?";
  char conf[8] = "?";
  char tof[72] = "?";
  jsonPeek(resp, "predicted_class", cls, sizeof(cls));
  jsonPeek(resp, "confidence", conf, sizeof(conf));
  jsonPeek(resp, "reason", tof, sizeof(tof));

  // 줄 길이 상한 80B (decisions.md 6.3: ≤80B 구간에서 시리얼 줄 손상 0건 실측).
  // PoC-(45): tof reason 이 "presence=true near=13/64 center=1015mm ndet=1/16"(≈45자)로 길어져
  // 한 줄 80B 를 넘으므로 **줄 분리** — 1줄째는 PR #52 와 동일 필드에서 tof 만 뺀 것, 2줄째가 tof.
  // 최악값(http=-9999 rtt=4294967295ms cls 12자 conf 6자)에서도 1줄째 80B 이내.
  Serial.printf("[mic][M5d] http=%d rtt=%ums cls=%.12s conf=%.6s\n", r.httpStatus,
                (unsigned)r.roundTripMs, cls, conf);
  Serial.printf("[mic][M5d] tof=%.64s\n", tof);  // "[mic][M5d] tof=" 15B + 64B = 79B
}

void setup() {
  Serial.begin(115200);
  delay(MIC_SERIAL_BOOT_DELAY_MS);
  Serial.println("\n[BOOT] ddingdong mic uplink (M5-d, 수동 's' 트리거)");

  // ★ 버퍼를 먼저 잡는다 — WiFi/I2S 가 PSRAM 여유를 갉기 전에 실패를 드러내기 위함.
  g_snap = uplinkAllocPsram(UPLINK_AUDIO_BYTES, "snapshot");
  g_body = uplinkAllocPsram(UPLINK_AUDIO_BYTES + UPLINK_MULTIPART_OVERHEAD_BYTES, "multipart");
  if (g_snap == nullptr || g_body == nullptr) {
    // graceful: 부팅을 멈추지 않는다(mic_test.cpp 의 init 실패 처리와 동형).
    // 전송만 불가하고 loop 는 계속 돈다 — 아래 loop 가드가 's' 를 거절한다.
    Serial.println("[BOOT] PSRAM 버퍼 확보 실패 — 전송 비활성(적재만 수행)");
  }

  if (!uplinkConnectWifi()) {
    Serial.println("[BOOT] WiFi 실패 — 전송은 매번 생략된다(적재는 계속)");
  }

  // WiFi 기동 후에 시드를 뽑는다: RF 가 켜져 있어야 esp_random() 이 하드웨어 엔트로피를
  // 쓴다(그 전엔 의사난수). 재부팅 간 id 충돌 방지가 목적이므로 품질이 중요하다.
  snprintf(g_idNonce, sizeof(g_idNonce), "%08x", (unsigned)esp_random());
  Serial.printf("[BOOT] client_request_id nonce=%s\n", g_idNonce);

  if (!initMicI2S()) {
    Serial.println("[BOOT] mic init 실패 — task 미기동");
    return;
  }
  discardMicWarmup();

  xTaskCreatePinnedToCore(micUplinkTask, "micUplinkTask", MIC_TASK_STACK_SIZE, nullptr,
                          MIC_TASK_PRIORITY, nullptr, MIC_TASK_CORE);
  Serial.println("[BOOT] micUplinkTask started (Core 0) — POST 는 loop 태스크");

  // ── ToF (PoC-(45)) — 마지막에 기동한다: begin() 이 I2C 로 ~86KB FW 를 수 초간 올리는 동안
  //   위 마이크 태스크는 이미 Core 0 에서 적재 중이고(prio 4 > tofTask 3), 실패해도 앞선 부팅
  //   단계에 영향이 없다. 실패 = 4필드 미전송(서버 tof_absent = PR #52 동작)으로 degrade.
  //   메모리: SparkFun begin() = new VL53L5CX_Configuration(≈5.4KB, 내부 heap). PSRAM 버퍼
  //   (snapshot/multipart/ring)와 풀이 달라 상호 영향 없음 — post-init [MEM] 로그로 확인 가능.
  if (initToF()) {
    g_tofAvailable = true;
    xTaskCreatePinnedToCore(tofUplinkTask, "tofTask", TOF_TASK_STACK_SIZE, nullptr,
                            TOF_TASK_PRIORITY, nullptr, TOF_TASK_CORE);
    Serial.println("[BOOT] tofTask started (Core 0, prio 3) — ToF 4필드 송신 활성");
  } else {
    Serial.println("[BOOT] tof init 실패 — 4필드 미전송(서버 tof_absent 로 degrade)");
  }
}

void loop() {
  const int c = Serial.read();
  if (c == 's' || c == 'S') {
    if (g_snap == nullptr || g_body == nullptr) {
      Serial.println("[mic][M5d] PSRAM 버퍼 없음 — 전송 불가");
    } else if (!g_ringFull) {
      Serial.println("[mic][M5d] ring 미충전 — 2초 이상 기다린 뒤 다시 's'");
    } else if (g_snapReq || g_snapReady) {
      Serial.println("[mic][M5d] 이전 스냅샷 처리 중 — 무시");
    } else {
      captureTofAtTrigger();  // 's' 시점 ToF 한 벌 (D1) — 오디오 스냅샷 요청보다 먼저 확정
      g_snapReq = true;
      Serial.println("[mic][M5d] snapshot 요청");
    }
  }

  if (g_snapReady) {
    sendSnapshot();
    g_snapReady = false;  // ★ 전송이 끝난 뒤에 내린다 — 그래야 g_snap 재기록이 막힌다
  }

  delay(10);
}
