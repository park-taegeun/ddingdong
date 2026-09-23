// 띵동 firmware - M5-c ⓐ 64ms 버퍼 단위 RMS 계측 하네스 (2026-09-23, env:mic_trigprobe)
//
// ★ 성격 = 관측 계층(decisions.md 카테고리 20 「계측 → 실측 → 판정」). 임계값·디바운스·트리거
//   판정 **0줄**. 마이크 1024 샘플 버퍼(64ms)마다 {순번, raw RMS, 클램프 제외 RMS, 클램프 수}를
//   **버퍼별로** 시리얼에 낸다. 판정(ⓑ)은 이 로그를 오프라인으로 돌려서 한다.
//
// ★ 왜 64ms 단위인가: 오늘까지의 실측은 2.048초 창 집계(mic_noiseprobe)인데, 트리거는 「64ms 버퍼
//   단위」다(decisions.md 6.3). 버퍼 단위 분포는 미실측 → 디바운스(연속 N버퍼) 시뮬레이션의 입력이 없다.
//
// ★ 왜 클램프 제외 RMS 를 같이 내는가: ToF I2C 활동 시 마이크 SD 비트 오류가 고립 32767 샘플을
//   만든다(6.3(n)). 한 샘플이 64ms RMS 를 크게 올리므로 raw 와 제외 값을 나란히 둬야 비교가 된다.
//   계산은 noise_stats.h noiseAnalyzeI16 재사용(6.3(o) 방법론 자산) — 새 계산식 0.
//
// ★ 제품과 같은 조건: 마이크 태스크 = MIC_TASK_PRIORITY 4 / Core 0 / MIC_TASK_STACK_SIZE,
//   ToF 태스크 = TOF_TASK_PRIORITY 3 / Core 0 / TOF_TASK_STACK_SIZE + tofJudgeFrame 호출
//   (mic_uplink_main.cpp tofUplinkTask 와 동형, 판정 결과는 쓰지 않는다). 기동 순서도 같다(마이크 → ToF).
//   다른 점(런북 한계): WiFi off · 링버퍼 없음 · 업링크 없음 · 2차 녹음 없음.
//
// ★ 출력 경로: 마이크 태스크는 시리얼에 **한 줄도 쓰지 않는다**. 버퍼 결과(16B)를 FreeRTOS 큐로 넘기고
//   loop 태스크가 꺼내 출력한다. 큐가 차면 그 버퍼는 버리고 드롭 수를 센다 → health 줄로 출력.
//   순번은 드롭돼도 증가하므로 데이터 줄 사이 순번 틈 = 드롭(조용한 누락 불가).
//
// ★ 줄 섞임: HWCDC::write 는 호출 1회를 tx_lock 뮤텍스로 감싼다(설치 코어 2.0.17 HWCDC.cpp).
//   printf 는 vsnprintf 후 write 1회 → 줄 1개 단위로는 태스크 간 섞이지 않는다(논증, 미실측).
//   ToF 태스크·tofJudgeFrame 의 [tof] 줄은 그대로 섞여 나온다 — 파서는 "[t] " 접두만 본다.

#include <Arduino.h>
#include <ctype.h>
#include <string.h>

#include "mic_common.h"
#include "noise_stats.h"
#include "tof_common.h"
#include "trig_line.h"

extern SparkFun_VL53L5CX tofImager;  // tof_common.cpp 소유 (mic_uplink_main.cpp 와 동형)

// 버퍼 길이 = clip_n 상한 → trig_line.h 필드 폭(4자) 근거가 코드와 어긋나면 빌드를 멈춘다.
static_assert((uint32_t)MIC_DMA_BUF_LEN <= TRIG_CLIP_MAX, "clip_n 이 trig_line 4자 폭을 넘을 수 있다");

// 큐 길이 32 = 32버퍼 = 2.048초. loop 가 시리얼 쓰기로 막혀도(HWCDC 타임아웃 등) 2초까지는 드롭 없이
// 버틴다. 16B × 32 = 512B 내부 heap. 모자라면 health 의 drop·q 가 알려준다(그때 늘린다).
constexpr UBaseType_t TRIG_QUEUE_LEN = 32;

static QueueHandle_t   g_q          = nullptr;
static TaskHandle_t    g_micTask    = nullptr;
static TaskHandle_t    g_tofTask    = nullptr;
static bool            g_ready      = false;  // setup 이 1회 쓰고 이후 읽기만
// 아래 4개는 마이크 태스크만 쓴다(쓰기 주체 유일 · 32비트 정렬 = 읽기 원자적). loop 는 읽기만.
static volatile uint32_t g_seqLast  = 0;      // 마지막으로 만든 버퍼 순번 (마커 줄 기준)
static volatile uint32_t g_drops    = 0;      // 큐 가득 → 버린 버퍼 수
static volatile uint32_t g_gaps     = 0;      // i2s_read 실패 누적 (순번 증가 없음)
static volatile uint32_t g_qMax     = 0;      // 전송 직후 큐 수위 최고치

// ── 마이크 태스크: 읽기 → int16 변환 → 분석 → 큐 (시리얼 0줄) ────────────────
static void micTrigTask(void* parameter) {
  (void)parameter;

  // mic_uplink_main.cpp 와 동일 — DMA 수신 버퍼 4KiB 는 스택이 아닌 BSS, int16 은 in-place 변환.
  static union {
    int32_t raw[MIC_DMA_BUF_LEN];
    int16_t i16[MIC_DMA_BUF_LEN];
  } audio_buffer;
  size_t   bytes_read = 0;
  uint32_t seq        = 0;

  for (;;) {
    const esp_err_t err = i2s_read(MIC_I2S_PORT, audio_buffer.raw, sizeof(audio_buffer.raw),
                                   &bytes_read, portMAX_DELAY);
    if (err != ESP_OK) {
      g_gaps = g_gaps + 1;
      continue;
    }

    size_t n = bytes_read / sizeof(int32_t);
    if (n > (size_t)MIC_DMA_BUF_LEN) {
      n = (size_t)MIC_DMA_BUF_LEN;  // mic_uplink_main.cpp 동형 방어
    }
    convertMicRawToInt16(audio_buffer.raw, audio_buffer.i16, n);
    const NoiseSnapStats st = noiseAnalyzeI16(audio_buffer.i16, n, MIC_SAMPLE_RATE_HZ, nullptr, 0);

    const TrigBuf item = {++seq, st.rms_all, st.rms_excl, st.clip_n};
    g_seqLast = seq;
    if (xQueueSend(g_q, &item, 0) != pdTRUE) {
      g_drops = g_drops + 1;
    } else {
      const uint32_t w = (uint32_t)uxQueueMessagesWaiting(g_q);
      if (w > g_qMax) g_qMax = w;
    }
  }
}

// ── ToF 태스크: mic_uplink_main.cpp tofUplinkTask 와 동형(폴링·에러 카운트·주기·판정 호출) ──
// 판정 결과는 공유하지 않는다(계측 전용). CPU·I2C 부하를 제품과 같게 두는 것이 목적이다.
static void tofTrigTask(void* parameter) {
  (void)parameter;
  logToFMemoryDiagnostics("tofTask-entry");
  static VL53L5CX_ResultsData measurementData;  // ~1356B → BSS (tof_test.cpp 동형)
  static TofJudgeState        judge;
  uint32_t err_count = 0;

  for (;;) {
    if (tofImager.isDataReady()) {
      if (tofImager.getRangingData(&measurementData)) {
        (void)tofJudgeFrame(&judge, measurementData);
      } else {
        if ((++err_count % 10) == 1) {
          Serial.printf("[tof] getRangingData failed #%u\n", (unsigned)err_count);
        }
      }
    }
    vTaskDelay(pdMS_TO_TICKS(TOF_PERIOD_MS));
  }
}

void setup() {
  Serial.begin(115200);
  delay(MIC_SERIAL_BOOT_DELAY_MS);
  Serial.println("\n[BOOT] ddingdong mic trigprobe (M5-c a 계측, 판정 0줄)");

  if (!initMicI2S()) {
    Serial.println("[BOOT] mic init 실패 — 계측 불가");
    return;
  }
  discardMicWarmup();

  g_q = xQueueCreate(TRIG_QUEUE_LEN, sizeof(TrigBuf));
  if (g_q == nullptr) {
    Serial.println("[BOOT] 큐 생성 실패 — 계측 불가");
    return;
  }
  if (xTaskCreatePinnedToCore(micTrigTask, "micTrigTask", MIC_TASK_STACK_SIZE, nullptr,
                              MIC_TASK_PRIORITY, &g_micTask, MIC_TASK_CORE) != pdPASS) {
    Serial.println("[BOOT] micTrigTask 생성 실패 — 계측 불가");
    return;
  }
  g_ready = true;

  // mic_uplink_main.cpp 와 같은 순서: 마이크 기동 뒤 ToF. 실패하면 제품 조건이 아니다 → 부팅 줄 tof=FAIL,
  // health 줄 tstk=na 로 계속 알린다(조용히 ToF 없는 측정으로 넘어가지 않는다).
  bool tof_ok = false;
  if (initToF()) {
    tof_ok = xTaskCreatePinnedToCore(tofTrigTask, "tofTask", TOF_TASK_STACK_SIZE, nullptr,
                                     TOF_TASK_PRIORITY, &g_tofTask, TOF_TASK_CORE) == pdPASS;
  }

  // 최악 "[t] boot sr=16000 buf=1024 k=3 q=32 tof=FAIL 계측전용 판정0줄" = 68B + '\n'
  Serial.printf("[t] boot sr=%u buf=%u k=%u q=%u tof=%s 계측전용 판정0줄\n",
                (unsigned)MIC_SAMPLE_RATE_HZ, (unsigned)MIC_DMA_BUF_LEN,
                (unsigned)TRIG_BUFS_PER_LINE, (unsigned)TRIG_QUEUE_LEN, tof_ok ? "ok" : "FAIL");
}

void loop() {
  static TrigBuf  pend[TRIG_BUFS_PER_LINE];
  static size_t   npend      = 0;
  static uint32_t lastHealth = 0;
  char            line[TRIG_LINE_BUF];

  if (!g_ready) {
    // setup 실패 경로. 모니터를 늦게 열어도 보이도록 주기 반복.
    if (millis() - lastHealth >= MIC_LOOP_IDLE_LOG_MS) {
      lastHealth = millis();
      Serial.println("[t] FAIL setup 실패 — 계측 불가 (부팅 로그 확인)");
    }
    delay(10);
    return;
  }

  // 데이터 줄: k개가 모이면 순번 연속 앞부분을 한 줄로. 틈(드롭)이 있으면 거기서 줄을 끊는다.
  TrigBuf item;
  while (xQueueReceive(g_q, &item, 0) == pdTRUE) {
    pend[npend++] = item;
    while (npend == TRIG_BUFS_PER_LINE) {
      size_t len = 0;
      size_t used = trigFormatLine(pend, npend, line, sizeof(line), &len);
      if (used == 0) {
        // 도메인 밖(도달 불가 — noiseAnalyzeI16 값역). 조용히 넘기지 않는다.
        // 최악 "[t] fmt_err seq=4294967295" = 26B + '\n'
        Serial.printf("[t] fmt_err seq=%u\n", (unsigned)pend[0].seq);
        used = 1;
      } else {
        Serial.write((const uint8_t*)line, len);  // write 1회 = 줄 1개 원자적(머리 주석)
      }
      memmove(pend, pend + used, (npend - used) * sizeof(TrigBuf));
      npend -= used;
    }
  }

  // 마커: 출력 가능 문자 1개 = 1줄. 문자별 분기 없음. 최악 "[t] mark=~ seq=4294967295" = 25B + '\n'
  for (int c = Serial.read(); c >= 0; c = Serial.read()) {
    if (isprint(c)) {
      Serial.printf("[t] mark=%c seq=%u\n", (char)c, (unsigned)g_seqLast);
    }
  }

  // health: MIC_LOOP_IDLE_LOG_MS(5초) 주기. 스택 최저 여유는 bytes(ESP-IDF) ≤ 스택 크기(4096/6144).
  // 최악 "[t] hp drop=4294967295 gaps=4294967295 mstk=4096 tstk=6144 q=32/32" = 66B + '\n'
  //   (스택 두 필드가 10자여도 78B + '\n' = 79B ≤ 80)
  if (millis() - lastHealth >= MIC_LOOP_IDLE_LOG_MS) {
    lastHealth = millis();
    char tstk[12] = "na";
    if (g_tofTask != nullptr) {
      snprintf(tstk, sizeof(tstk), "%u", (unsigned)uxTaskGetStackHighWaterMark(g_tofTask));
    }
    Serial.printf("[t] hp drop=%u gaps=%u mstk=%u tstk=%s q=%u/%u\n", (unsigned)g_drops,
                  (unsigned)g_gaps, (unsigned)uxTaskGetStackHighWaterMark(g_micTask), tstk,
                  (unsigned)g_qMax, (unsigned)TRIG_QUEUE_LEN);
  }

  delay(10);
}
