// 띵동 firmware - 보드 2차 체인 배관: /detect → enrich_status 게이트 → 캡처 + 5초 녹음 → /enrich
//                 (2026-09-18, env:enrich_uplink, PR-B / decisions.md 6.5(d))
//
// ★ PR 성격 = **배관(plumbing)**. 새 판정 기준·임계값·상태 어휘 **0개**다.
//   판정은 이미 서버에서 끝나 있다 — `/detect` 응답의 `enrich_status`(`pending` / `skipped`)를
//   **읽어서 분기만** 한다(6.5(b) 파생 사실 ②). 보드가 다시 판정하는 것은 하나도 없다.
//     송신 끝 = M5-d `/detect` 1차 업로드(PR #52·#53, 무변경)
//     수신 끝 = `/enrich` 서버 구현(PR #27, 2026-07-31 완성)
//   그 사이 2차 클라이언트가 **0줄**이었다. 본 env 가 그 0줄을 채운다.
//
// ★ 트리거 = **시리얼 키 's' 수동 입력**. 임계값 비교 0줄(RMS 자동 트리거는 M5-c 소관).
//
// ★ 순서 (§2-1 ① S1 직렬 / ② pre 0)
//   's' → **2차 녹음 먼저 시작** → 1차 스냅샷 POST → 응답 파싱 → 게이트 → 녹음 완료 대기
//        → 카메라 init/capture/deinit → `/enrich` POST → 로그.
//   ⚠️ 녹음을 `/detect` 응답 **뒤에** 시작하면 말 앞이 잘린다. 그래서 트리거 시점에 먼저 건다.
//
// ★ 태스크 배치 = **신규 태스크 0**. POST 2회 모두 Arduino loop 태스크에서 돈다
//   (6.3(m): 마이크 태스크 스택 4096 부족 위험 회피. loopTask 8192B 는 프로즌 upload_spike 가
//    이미 실측 완주). 마이크 태스크가 하는 추가 일은 **memcpy 1회**뿐이다.
//
// ★ 재시도 0. 404/409/타임아웃/SOI 불일치/파싱 실패 — 전부 **로그만** 남기고 그 이벤트를 버린다.
//
// ★ tof_presence=false 에서도 촬영한다(§2-1 ⑥) — 보드에서 재판정하지 않는다. ToF 4필드는
//   1차에 그대로 실어 보내고, 촬영 여부는 서버의 enrich_status 만 본다(6.4(b) 거울상 회피).

#include <Arduino.h>
#include <WiFi.h>
#include <string.h>

#include "esp_camera.h"
#include "esp_random.h"

#include "camera_common.h"
#include "enrich_wire.h"
#include "mic_common.h"
#include "probe_stats.h"   // probeIsJpegSoi — SOI 2바이트 검사(6.6 자산 재사용, 복제 0)
#include "secrets.h"
#include "tof_common.h"
#include "uplink_common.h"

extern SparkFun_VL53L5CX tofImager;  // tof_common.cpp 소유 (mic_uplink_main.cpp 와 동형)

// ── PSRAM 버퍼 (setup 에서 1회 할당, 이후 불변) ─────────────────────────────
// 링버퍼 본체(64KB)는 micTask 지역변수 = mic_common.h 컨벤션 그대로.
static uint8_t* g_snap  = nullptr;  // 65,536B  1차 스냅샷 (task 가 쓰고 loop 가 읽는다)
static uint8_t* g_body  = nullptr;  // 66,560B  1차 multipart
static uint8_t* g_rec   = nullptr;  // 163,840B 2차 녹음(별도 버퍼 — 링버퍼 확장은 기각, 6.5(c))
static uint8_t* g_ebody = nullptr;  // 676,864B 2차 multipart

// ── 태스크 ↔ loop 핸드셰이크 ───────────────────────────────────────────────
// ★ 락 없음의 근거는 mic_uplink_main.cpp 와 같다 — 각 플래그의 set 주체가 유일하고 상태가
//   한 방향으로만 돈다. 2차 녹음 플래그도 같은 규율을 따른다:
//     IDLE ──loop: filled=0 후 recReq=true──▶ RECORDING
//     RECORDING ──task: 버퍼가 다 차면 recReq=false, recReady=true──▶ DONE
//     DONE ──loop: 소비 후 recReady=false──▶ IDLE
//   g_recFilled 는 RECORDING 구간에서만 task 가 쓴다. loop 가 쓰는 유일한 지점은 recReq 를
//   올리기 **직전**(= task 가 손대지 않는 구간)이다.
//   ⚠️ 여기에 "녹음 중 재트리거"를 허용하면 이 논증이 깨진다. loop 가드가 그것을 막는다.
static volatile bool g_snapReq   = false;
static volatile bool g_snapReady = false;
static volatile bool g_ringFull  = false;
static volatile bool g_recReq    = false;
static volatile bool g_recReady  = false;
static volatile uint32_t g_recFilled = 0;

static volatile int32_t  g_snapRms   = 0;
static volatile int32_t  g_snapPeak  = 0;
static volatile uint32_t g_snapBytes = 0;
static volatile uint32_t g_taskStackFree = 0;
static volatile uint32_t g_ringGaps      = 0;

// ── ToF 최신 판정 공유 (tofTask → loop) — mic_uplink_main.cpp 와 동형 ──────
static portMUX_TYPE   g_tofMux       = portMUX_INITIALIZER_UNLOCKED;
static TofFrameResult g_tofLatest    = {};
static uint32_t       g_tofLatestMs  = 0;
static bool           g_tofAvailable = false;
static volatile uint32_t g_tofStackFree = 0;

static TofFrameResult g_tofAtS      = {};
static bool           g_tofAtSValid = false;

// ── 세션 과금 상한 (§2-1 ⑧) ────────────────────────────────────────────────
// loop 전용. 부팅마다 0 — "세션" = 1회 부팅이다(재부팅으로 리셋되는 것이 의도다: 부스 시연
// 1회분 상한이지 기기 수명 상한이 아니다).
static uint32_t g_enrichSent = 0;

// ── client_request_id (M5-d 와 동일 근거: millis 기반은 재부팅 시 멱등 replay 유발) ──
static char     g_idNonce[9] = {0};
static uint32_t g_idSeq      = 0;

static void makeClientRequestId(char* out, size_t cap) {
  snprintf(out, cap, "e2-%s-%u", g_idNonce, (unsigned)(++g_idSeq));
}

// ── 마이크 태스크: 적재 + 1차 스냅샷 + 2차 녹음 ────────────────────────────
static void micEnrichTask(void* parameter) {
  (void)parameter;

  static union {
    int32_t raw[MIC_DMA_BUF_LEN];
    int16_t i16[MIC_DMA_BUF_LEN];
  } audio_buffer;

  int16_t* const ring_base  = initMicRingBuffer();
  MicRingStatus  ring       = {};
  size_t         bytes_read = 0;

  if (ring_base == nullptr) {
    Serial.println("[mic][e2] ring alloc 실패 — 스냅샷 불가, 적재만 계속");
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
      n = (size_t)MIC_DMA_BUF_LEN;
    }

    int16_t* const slot = micRingSlot(ring_base, ring.write_idx);
    if (slot == nullptr) {
      continue;
    }
    convertMicRawToInt16(audio_buffer.raw, slot, n);
    micRingAdvance(&ring);

    if (!g_ringFull && ring.slots_filled >= MIC_RING_SLOTS) {
      g_ringFull = true;
      Serial.println("[mic][e2] ring filled — 's' 로 2차 체인 시작");
    }

    // ── 2차 녹음 적재 (pre 0 — 트리거 시점 이후 슬롯만 담는다) ───────────────
    // ★ 링버퍼를 다시 읽지 않고 **방금 변환한 슬롯**을 그대로 흘려 담는다. 링버퍼 길이(2.048초)와
    //   무관하므로 MIC_RING_SLOTS 확장이 필요 없다(6.5(c) 기각 후보 회피 = 1차 wire 계약 무접촉).
    // ★ take 클램프: n 이 MIC_DMA_BUF_LEN 보다 작은 반환이 와도 버퍼 너머를 쓰지 않는다.
    //   샘플 수로 세므로 **실제 길이 = 정확히 ENRICH_AUDIO_SAMPLES** 이고 시간축이 짧아지지 않는다.
    if (g_recReq && g_rec != nullptr) {
      const size_t want = n * sizeof(int16_t);
      const size_t room = ENRICH_AUDIO_BYTES - (size_t)g_recFilled;
      const size_t take = (want < room) ? want : room;
      memcpy(g_rec + g_recFilled, slot, take);
      g_recFilled += (uint32_t)take;
      if ((size_t)g_recFilled >= ENRICH_AUDIO_BYTES) {
        g_recReq = false;
        __sync_synchronize();  // 위 memcpy 가 loop 에 보인 뒤에야 ready 가 보여야 한다
        g_recReady = true;
      }
    }

    // ── 1차 스냅샷 (mic_uplink_main.cpp 와 동일 지점·동일 논증: 여기서만 torn read 불가) ──
    if (g_snapReq && ring.slots_filled >= MIC_RING_SLOTS && g_snap != nullptr) {
      size_t copied = 0;
      for (uint32_t i = 0; i < MIC_RING_SLOTS; ++i) {
        const int16_t* const src = micRingSlot(ring_base, ring.write_idx + i);
        if (src == nullptr) {
          break;
        }
        memcpy(g_snap + copied, src, (size_t)MIC_DMA_BUF_LEN * sizeof(int16_t));
        copied += (size_t)MIC_DMA_BUF_LEN * sizeof(int16_t);
      }

      const int16_t* const s  = reinterpret_cast<const int16_t*>(g_snap);
      const size_t         ns = copied / sizeof(int16_t);
      int64_t              acc = 0;
      int32_t              peak = 0;
      for (size_t i = 0; i < ns; ++i) {
        const int32_t v = (int32_t)s[i];
        const int32_t a = (v >= 0) ? v : -v;
        if (a > peak) {
          peak = a;
        }
        acc += (int64_t)v * (int64_t)v;
      }

      g_snapBytes     = (uint32_t)copied;
      g_snapPeak      = peak;
      g_snapRms       = (ns > 0) ? (int32_t)sqrt((double)acc / (double)ns) : 0;
      g_taskStackFree = (uint32_t)uxTaskGetStackHighWaterMark(nullptr);
      g_ringGaps      = ring.gaps;

      g_snapReq = false;
      __sync_synchronize();
      g_snapReady = true;
    }
  }
}

// ── ToF 태스크 (tof_test.cpp / mic_uplink_main.cpp 와 동형, 판정 본문 공유) ──
static void tofEnrichTask(void* parameter) {
  (void)parameter;
  static VL53L5CX_ResultsData measurementData;
  static TofJudgeState        judge;
  uint32_t err_count = 0;

  for (;;) {
    if (tofImager.isDataReady()) {
      if (tofImager.getRangingData(&measurementData)) {
        const TofFrameResult r   = tofJudgeFrame(&judge, measurementData);
        const uint32_t       now = millis();
        taskENTER_CRITICAL(&g_tofMux);
        g_tofLatest   = r;
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

// 's' 시점 ToF 한 벌 캡처. 집계·재판정 없음(D1) — 1차에 그대로 싣는다.
static void captureTofAtTrigger() {
  g_tofAtSValid = false;
  if (!g_tofAvailable) {
    Serial.println("[tof][e2] tof 없음 — 4필드 미전송(서버 tof_absent)");
    return;
  }
  uint32_t ms;
  taskENTER_CRITICAL(&g_tofMux);
  g_tofAtS = g_tofLatest;
  ms       = g_tofLatestMs;
  taskEXIT_CRITICAL(&g_tofMux);
  if (ms == 0) {
    Serial.println("[tof][e2] 첫 프레임 전 — 4필드 미전송(서버 tof_absent)");
    return;
  }
  g_tofAtSValid = true;
  // "[tof][e2] presence=false near=64/64 ndet=16/16 age_ms=4294967295" = 62B
  Serial.printf("[tof][e2] presence=%s near=%u/%u ndet=%u/%u age_ms=%u\n",
                g_tofAtS.fused ? "true" : "false", (unsigned)g_tofAtS.near_count,
                (unsigned)TOF_ZONE_COUNT, (unsigned)g_tofAtS.motion_ndet,
                (unsigned)TOF_MOTION_AGG_COUNT_8X8, (unsigned)(millis() - ms));
}

// ── 2차 녹음 완료 대기 (loop 태스크 — 블로킹) ──────────────────────────────
// 녹음은 트리거 시점에 이미 시작됐고 5.120초 뒤에 끝난다. 1차 왕복(p95 ≈ 1~2초)이 그 안에
// 끝나므로 여기서 남은 시간만 기다린다. 상한은 **넉넉한 실패 탈출구**일 뿐 판정 기준이 아니다
// (i2s_read 가 죽으면 영영 차지 않는다 → 그 경우를 로그로 드러낸다).
static bool waitRecording() {
  const uint32_t deadline = millis() + ENRICH_AUDIO_MS * 3;
  while (!g_recReady && (int32_t)(millis() - deadline) < 0) {
    delay(10);
  }
  if (!g_recReady) {
    Serial.printf("[e2] rec 미완 filled=%u/%u — 2차 미발송\n", (unsigned)g_recFilled,
                  (unsigned)ENRICH_AUDIO_BYTES);
    return false;
  }
  return true;
}

// 이번 이벤트의 녹음분을 버린다(게이트 skip·상한 도달·파싱 실패 경로 공통).
static void discardRecording() {
  g_recReq   = false;
  g_recReady = false;
}

// ── 2차 발송 (loop 태스크) ─────────────────────────────────────────────────
// 카메라는 **이벤트마다** init → capture → deinit 한다(6.6(c): init 383ms / fb 30,952B /
// deinit 이 동일 바이트 반환 = 누수 0). 상시 init 를 택하지 않은 이유 = 부스 대기 중 fb 30KB 를
// 계속 물고 있을 이유가 없고, 6.6 이 누수 0 을 실측해 뒀기 때문이다.
static bool sendEnrich(const char* id) {
  logMemoryDiagnostics("e2-pre-init");
  const uint32_t t0     = millis();
  const bool     camOk  = initCameraWithDiagnostics();
  const uint32_t initMs = millis() - t0;
  if (!camOk) {
    Serial.printf("[e2] cam init 실패 ms=%u — 2차 미발송\n", (unsigned)initMs);
    return false;
  }

  const uint32_t t1  = millis();
  camera_fb_t*   fb  = esp_camera_fb_get();
  const uint32_t capMs = millis() - t1;

  size_t   bodyLen = 0;
  uint32_t jpgLen  = 0;
  bool     soi     = false;
  if (fb != nullptr) {
    soi    = probeIsJpegSoi(fb->buf, fb->len);
    jpgLen = (uint32_t)fb->len;
    if (soi) {
      // ★ fb 를 쥔 구간을 memcpy 로만 채운다 — POST(수 초)는 fb 반환 뒤에 돈다(fb_count=2).
      bodyLen = enrichBuildMultipart(g_ebody, UPLINK_ENRICH_BODY_BYTES, id, fb->buf, fb->len,
                                     g_rec, ENRICH_AUDIO_BYTES);
    }
    esp_camera_fb_return(fb);
  }

  esp_camera_deinit();
  logMemoryDiagnostics("e2-post-deinit");

  // "[e2] cam ms=4294967295/4294967295 len=4294967295 soi=0" = 53B
  Serial.printf("[e2] cam ms=%u/%u len=%u soi=%d\n", (unsigned)initMs, (unsigned)capMs,
                (unsigned)jpgLen, (int)soi);

  if (fb == nullptr) {
    Serial.println("[e2] fb_get NULL — 2차 미발송(재시도 없음)");
    return false;
  }
  if (!soi) {
    Serial.println("[e2] SOI 불일치 — 2차 미발송(서버 400 회피)");
    return false;
  }
  if (bodyLen == 0) {
    Serial.println("[e2] multipart 조립 실패 — 2차 미발송");
    return false;
  }
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[e2] WiFi 끊김 — 2차 생략(재시도 없음)");
    return false;
  }

  const UplinkResult r = uplinkPostEnrichBody(SPIKE_SERVER_HOST, SPIKE_SERVER_PORT, g_ebody,
                                              bodyLen);
  // "[e2] e http=-9999 rtt=4294967295ms body=4294967295" = 49B
  Serial.printf("[e2] e http=%d rtt=%ums body=%u\n", r.httpStatus, (unsigned)r.roundTripMs,
                (unsigned)bodyLen);
  // 201/200 판정을 보드에서 하지 않는다 — 상태 코드를 그대로 흘린다(1차와 동형).
  return r.httpStatus > 0;
}

// ── 이벤트 1회 전체 (loop 태스크) ──────────────────────────────────────────
static void runEvent() {
  char id[32];
  makeClientRequestId(id, sizeof(id));

  const uint32_t bytes = g_snapBytes;
  if (bytes != UPLINK_AUDIO_BYTES) {
    Serial.printf("[e2] snapshot bytes=%u != %u — 중단\n", (unsigned)bytes,
                  (unsigned)UPLINK_AUDIO_BYTES);
    discardRecording();
    return;
  }

  // "[e2] id=e2-89abcdef-4294967295 rms=32767 peak=32767" = 50B
  Serial.printf("[e2] id=%s rms=%d peak=%d\n", id, (int)g_snapRms, (int)g_snapPeak);
  Serial.printf("[e2] stk=%u psram=%u gaps=%u tof_stk=%u\n", (unsigned)g_taskStackFree,
                (unsigned)ESP.getFreePsram(), (unsigned)g_ringGaps, (unsigned)g_tofStackFree);

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[e2] WiFi 끊김 — 1차 생략(재시도 없음)");
    discardRecording();
    return;
  }

  char resp[UPLINK_RESP_BUF_BYTES];
  const UplinkResult r =
      uplinkPostAudio(SPIKE_SERVER_HOST, SPIKE_SERVER_PORT, id, g_snap, UPLINK_AUDIO_BYTES,
                      g_body, UPLINK_AUDIO_BYTES + UPLINK_MULTIPART_OVERHEAD_BYTES, resp,
                      sizeof(resp), g_tofAtSValid ? &g_tofAtS : nullptr);

  if (r.httpStatus <= 0) {
    Serial.printf("[e2] d http=%d rtt=%ums 전송실패 — 2차 미발송\n", r.httpStatus,
                  (unsigned)r.roundTripMs);
    discardRecording();
    return;
  }

  char cls[16] = "?";
  char conf[8] = "?";
  enrichPeekJson(resp, "predicted_class", cls, sizeof(cls));
  enrichPeekJson(resp, "confidence", conf, sizeof(conf));
  // "[e2] d http=-9999 rtt=4294967295ms cls=fire_alarm__ conf=0.9999" = 62B
  Serial.printf("[e2] d http=%d rtt=%ums cls=%.12s conf=%.6s\n", r.httpStatus,
                (unsigned)r.roundTripMs, cls, conf);

  // ── 게이트 (§2-1 ① / ⑤ / 덤) ──────────────────────────────────────────
  const EnrichGate gate = enrichGateFromDetectBody(resp);
  // "[e2] gate=parsefail sent=4294967295/12" = 38B
  Serial.printf("[e2] gate=%s sent=%u/%u\n", enrichGateName(gate), (unsigned)g_enrichSent,
                (unsigned)ENRICH_SESSION_MAX_EVENTS);
  if (gate != ENRICH_GATE_PENDING) {
    // skip = 서버가 이미 "2차 안 함"으로 판정한 건(409·404 생산 회피).
    // parsefail = 모른다. **기본값으로 고르지 않는다** — 보내지 않고 로그만 남긴다.
    discardRecording();
    return;
  }

  if (!enrichSessionAllows(g_enrichSent)) {
    Serial.println("[e2] 세션 상한 도달 — 2차 중단(과금 상한)");
    discardRecording();
    return;
  }

  if (!waitRecording()) {
    discardRecording();
    return;
  }

  const bool sent = sendEnrich(id);
  if (sent) {
    g_enrichSent++;
  }
  discardRecording();
}

void setup() {
  Serial.begin(115200);
  delay(MIC_SERIAL_BOOT_DELAY_MS);
  Serial.println("\n[BOOT] ddingdong enrich uplink (PR-B, 수동 's' 트리거)");

  // ★ 버퍼를 먼저 잡는다 — WiFi/I2S/카메라가 PSRAM 을 갉기 전에 실패를 드러내기 위함.
  g_snap  = uplinkAllocPsram(UPLINK_AUDIO_BYTES, "snapshot");
  g_body  = uplinkAllocPsram(UPLINK_AUDIO_BYTES + UPLINK_MULTIPART_OVERHEAD_BYTES, "multipart");
  g_rec   = uplinkAllocPsram(ENRICH_AUDIO_BYTES, "enrich-rec");
  g_ebody = uplinkAllocPsram(UPLINK_ENRICH_BODY_BYTES, "enrich-body");
  if (g_snap == nullptr || g_body == nullptr || g_rec == nullptr || g_ebody == nullptr) {
    Serial.println("[BOOT] PSRAM 버퍼 실패 — 전송 비활성(적재만 수행)");
  }
  // "[BOOT] rec=163840B 5120ms ebody=676864B" = 40B
  Serial.printf("[BOOT] rec=%uB %ums ebody=%uB\n", (unsigned)ENRICH_AUDIO_BYTES,
                (unsigned)ENRICH_AUDIO_MS, (unsigned)UPLINK_ENRICH_BODY_BYTES);

  if (!uplinkConnectWifi()) {
    Serial.println("[BOOT] WiFi 실패 — 전송은 매번 생략된다(적재는 계속)");
  }

  snprintf(g_idNonce, sizeof(g_idNonce), "%08x", (unsigned)esp_random());
  Serial.printf("[BOOT] client_request_id nonce=%s\n", g_idNonce);

  if (!initMicI2S()) {
    Serial.println("[BOOT] mic init 실패 — task 미기동");
    return;
  }
  discardMicWarmup();

  xTaskCreatePinnedToCore(micEnrichTask, "micEnrichTask", MIC_TASK_STACK_SIZE, nullptr,
                          MIC_TASK_PRIORITY, nullptr, MIC_TASK_CORE);
  Serial.println("[BOOT] micEnrichTask started (Core 0) — POST 는 loop 태스크");

  if (initToF()) {
    g_tofAvailable = true;
    xTaskCreatePinnedToCore(tofEnrichTask, "tofTask", TOF_TASK_STACK_SIZE, nullptr,
                            TOF_TASK_PRIORITY, nullptr, TOF_TASK_CORE);
    Serial.println("[BOOT] tofTask started (Core 0, prio 3) — ToF 4필드 송신 활성");
  } else {
    Serial.println("[BOOT] tof init 실패 — 4필드 미전송(서버 tof_absent 로 degrade)");
  }
}

void loop() {
  const int c = Serial.read();
  if (c == 's' || c == 'S') {
    if (g_snap == nullptr || g_body == nullptr || g_rec == nullptr || g_ebody == nullptr) {
      Serial.println("[e2] PSRAM 버퍼 없음 — 전송 불가");
    } else if (!g_ringFull) {
      Serial.println("[e2] ring 미충전 — 2초 이상 기다린 뒤 다시 's'");
    } else if (g_snapReq || g_snapReady || g_recReq || g_recReady) {
      Serial.println("[e2] 이전 이벤트 처리 중 — 무시");
    } else {
      captureTofAtTrigger();  // 's' 시점 한 벌 (D1)
      // ★ 2차 녹음을 **1차 요청보다 먼저** 건다(§2-1 ② pre 0 — 트리거 시점부터 담는다).
      g_recFilled = 0;
      __sync_synchronize();
      g_recReq  = true;
      g_snapReq = true;
      Serial.println("[e2] trigger — 2차 녹음 시작 + 1차 스냅샷 요청");
    }
  }

  if (g_snapReady) {
    runEvent();
    g_snapReady = false;  // ★ 전송이 끝난 뒤에 내린다 — 그래야 g_snap 재기록이 막힌다
  }

  delay(10);
}
