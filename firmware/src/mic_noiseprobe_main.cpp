// 띵동 firmware - 마이크 잡음 근본원인 진단 하네스 (2026-09-11 PoC-(45), env:mic_noiseprobe)
//
// ★ 무엇을 가르는가 (배경 = PR #53 댓글 A/B 실측, ToF_meta_uplink_runtime.log)
//   ToF 측정 ON(mic_uplink) 조용한 2초 스냅샷 6회 peak 32767~32768 / rms 455~636
//   ToF 측정 OFF(main b3414a4)  3회 peak 412~464 / rms 95~96
//   → "ToF 측정 동작"이 원인인 것은 실측. 그 **안의 기전**(H1 I2C 누화 / H2 센서 전원 / H3 태스크
//   경합)은 미분리. 본 env 는 한 번에 한 변수만 바꾸는 모드 5개와 보드 내 스냅샷 통계로 기전을 가른다.
//
// ★ 성격 = 방법론 자산(decisions.md 8.4(f) / 9.1(e) tof_pinscan·tof_lineprobe 선례). 제품 코드
//   (mic_common / tof_common / mic_uplink) 무수정 — import 만. 해결책 0줄. 판정표는 Runbook.
//
// ★ 모드 (시리얼 '0'~'4', 재플래시 없음 — 한 번에 한 변수)
//   m0 측정 정지(stopRanging, init·전원·버스 결선 동일)      → 대조군
//   m1 측정 ON + 읽기 OFF(발광만, 호스트 I2C 트래픽 0)       → H2 격리 (센서 동작 전원)
//   m2 측정 ON + 읽기 ON @400kHz, tofTask Core 0            → 현행 재현 (mic_uplink 와 동일 조건)
//   m3 = m2, I2C 100kHz                                      → 엣지 수/속도 의존 (H1)
//   m4 = m2, tofTask Core 1                                  → 코어 경합 (H3)
//   m5 = m2, 마이크 SD 핀 내부 풀다운 ON                      → SD tri-state 부유 (H1 하위, 2026-09-11 추가)
//   m6 = m0, 마이크 SD 핀 내부 풀다운 ON                      → 풀다운 자체의 부작용 대조군
//   's' = 2초 스냅샷 + 보드 내 분석 (noise_stats.h)
//
// ★ m1 의 전제(근거유형 = 문서인용 + 코드 논증, 실측 미확인 → Runbook 에서 sc 로 확인):
//   ULD vl53l5cx_check_data_ready 는 호스트가 0x0 4바이트를 읽어 streamcount 변화를 보는 **호스트측
//   폴링**일 뿐(vl53l5cx_api.cpp:591~608)이고 ack/handshake 쓰기가 없다 → 호스트가 읽지 않아도
//   센서는 autonomous 모드로 계속 측정(발광)한다. m1→m2 전환 첫 프레임에서 streamcount 가 m1 진입
//   시점보다 전진했으면 그 사실의 실측 증거다(로그 sc= 두 값).
//
// ★ ToF 버스 접근 직렬화 = FreeRTOS 뮤텍스 1개(g_busMux).
//   SparkFun readMultipleBytes 는 32B 청크마다 별도 Wire 트랜잭션을 연다(SparkFun_VL53L5CX_IO.cpp:77~).
//   Wire 자체 HAL 락은 트랜잭션 1개만 지키므로 "폴링 태스크의 ULD 호출"과 "loop 의 stop/start/setClock"
//   이 겹치면 ULD 시퀀스 중간에 다른 트랜잭션이 끼어든다. 뮤텍스로 ULD 호출 단위 전체를 감싼다.
//   폴링 태스크는 뮤텍스 획득 **후** 모드 플래그를 재확인한다(획득 대기 중 모드가 바뀐 경우 1회 폴링 방지).
//
// ★ tofTask 코어 전환(m4) = 태스크 재생성 없이 **Core 0/1 에 하나씩 미리 띄우고** 활성 코어만 바꾼다.
//   vTaskDelete 를 I2C 도중에 때리는 위험·재생성 핸드셰이크를 통째로 피한다. 비활성 쪽은 vTaskDelay 만.

#include <Arduino.h>
#include <Wire.h>
#include <string.h>

#include "mic_common.h"
#include "noise_modes.h"
#include "noise_stats.h"
#include "tof_common.h"

// SD 풀다운 재독용 — IO_MUX 레지스터 직독 (경로 판정 근거는 아래 applySdPulldown 주석)
#include "driver/gpio.h"
#include "soc/gpio_periph.h"
#include "soc/io_mux_reg.h"
#include "soc/soc.h"

extern SparkFun_VL53L5CX tofImager;  // tof_common.cpp 소유

// ── 상수 (진단 전용) ──────────────────────────────────────────────────────────
constexpr size_t   SNAP_SAMPLES   = (size_t)MIC_RING_SLOTS * MIC_DMA_BUF_LEN;   // 32768
constexpr size_t   SNAP_I16_BYTES = SNAP_SAMPLES * sizeof(int16_t);             // 65,536
constexpr size_t   SNAP_RAW_BYTES = SNAP_SAMPLES * sizeof(int32_t);             // 131,072
constexpr size_t   TOF_STAMP_N    = 64;        // 최근 ToF 읽기 시각 64건(15Hz × ≈4.3초 > 2.048초 창)
constexpr uint32_t I2C_FAST_HZ    = TOF_I2C_FREQ_HZ;   // 400k (tof_common.h, 현행)
constexpr uint32_t I2C_SLOW_HZ    = 100000;            // m3

// ── 모드 상태 (loop 가 쓰고 tof 태스크가 읽는다) ─────────────────────────────
static volatile int  g_mode      = 2;      // 부팅 = m2(현행 재현)
static volatile bool g_tofPoll   = true;   // isDataReady/getRangingData 수행 여부 (m2~m4)
static volatile int  g_tofCore   = 0;      // 폴링 담당 코어
static bool          g_tofRanging = false; // loop 전용: startRanging 상태 추적
static bool          g_tofAvail   = false;
static SemaphoreHandle_t g_busMux = nullptr;

// ── ToF 읽기 시각 링 (tof 태스크가 쓰고, 스냅샷 시 mic 태스크가 복사) ──────────
static portMUX_TYPE g_stampMux = portMUX_INITIALIZER_UNLOCKED;
static uint32_t     g_tofStart[TOF_STAMP_N];   // isDataReady 직전 (I2C 트래픽 시작)
static uint32_t     g_tofEnd[TOF_STAMP_N];     // getRangingData 직후 (I2C 트래픽 끝)
static uint32_t     g_tofStampIdx = 0;     // 다음 기록 위치
static uint32_t     g_tofReads    = 0;     // 부팅 후 getRangingData 성공 누계
static volatile uint8_t g_scLast  = 0;     // 마지막 성공 프레임의 streamcount
static volatile bool    g_scLogReq = false;  // 모드 전환 후 첫 프레임 sc 로그 1회

// ── PSRAM 버퍼 ────────────────────────────────────────────────────────────────
static int32_t*  g_rawRing = nullptr;      // 32 슬롯 × 1024 × int32 (진단 전용, 가드 이전 raw)
static int16_t*  g_snap16  = nullptr;      // 스냅샷 int16 (mic_common 변환 경로 = 제품과 동일)
static int32_t*  g_snapRaw = nullptr;      // 스냅샷 raw

// ── 태스크 ↔ loop 핸드셰이크 (mic_uplink_main.cpp 와 동일 2플래그 논증) ────────
static volatile bool g_snapReq   = false;
static volatile bool g_snapReady = false;
static volatile bool g_ringFull  = false;
static uint32_t g_snapSlotUs[MIC_RING_SLOTS];   // 슬롯별 i2s_read 반환 시각 (오래된→최신)
static uint32_t g_snapTofStart[TOF_STAMP_N];    // 스냅샷 시점 ToF 읽기 창 사본
static uint32_t g_snapTofEnd[TOF_STAMP_N];
static uint32_t g_snapTofN   = 0;
static uint32_t g_snapGaps   = 0;
static uint32_t g_snapNo     = 0;
static uint32_t g_snapStackFree = 0;
static uint32_t g_bursts[NOISE_MAX_BURSTS];

static const char* modeTag(int m) {
  static const char* t[NOISE_MODE_N] = {"[noise][m0]", "[noise][m1]", "[noise][m2]", "[noise][m3]",
                                        "[noise][m4]", "[noise][m5]", "[noise][m6]"};
  return (m >= 0 && m < NOISE_MODE_N) ? t[m] : "[noise][m?]";
}

// ── 마이크 SD 핀 내부 풀다운 (진단 전용 — mic_common 초기화 함수는 건드리지 않는다) ─────
//
// ★ 적용 경로 판정 (설치 헤더 실물 근거, 학습 15 2단계):
//   - GPIO7 은 ESP32-S3 의 RTC IO 겸용이다(soc_caps.h `SOC_RTCIO_PIN_COUNT 22` = GPIO0~21).
//   - 그러나 같은 파일에 `SOC_GPIO_SUPPORT_RTC_INDEPENDENT (1)` 이 있다 → S3 는 디지털 IO_MUX 와
//     RTC 의 pull 설정이 독립이고, `gpio_pulldown_en`(driver/gpio.h:267)은 **IO_MUX 경로**를 탄다.
//   - 그 경로의 실체 = hal/esp32s3/include/hal/gpio_ll.h:74 `gpio_ll_pulldown_en` →
//     `REG_SET_BIT(GPIO_PIN_MUX_REG[gpio_num], FUN_PD)`, FUN_PD = BIT(7)(io_mux_reg.h:50).
//   → 재독도 **같은 레지스터의 같은 비트**를 읽는다. 아래 sdPulldownReg().
//   ⚠️ gpio.c 본문은 Arduino-ESP32 가 IDF 를 사전 컴파일해 배포하므로 읽을 수 없다(논증까지).
//      만에 하나 RTC 경로를 탔다면 IO_MUX 비트가 서지 않으므로 로그가 `req=1 reg=0` 으로 드러난다
//      — 판별은 런타임 증거에 맡긴다.
static bool sdPulldownReg() {
  return REG_GET_BIT(GPIO_PIN_MUX_REG[MIC_SD_PIN], FUN_PD) != 0;
}

// ★ 반드시 I2S 핀 설정(initMicI2S 의 i2s_set_pin) **이후**에 부른다 — i2s_set_pin 이 핀을
//   재구성하면 먼저 건 풀다운이 날아간다. 모드 전환마다 재적용 + 재독한다.
static void applySdPulldown(bool on) {
  if (on) gpio_pulldown_en((gpio_num_t)MIC_SD_PIN);
  else    gpio_pulldown_dis((gpio_num_t)MIC_SD_PIN);
}

// "[noise][m5] sd_pd req=1 reg=1 gpio=7" = 36B (80B 상한 여유)
static void logSdPulldown(int m, bool req) {
  Serial.printf("%s sd_pd req=%d reg=%d gpio=%d\n", modeTag(m), (int)req, (int)sdPulldownReg(),
                MIC_SD_PIN);
}

// ── 마이크 태스크: 적재(int16 링 = mic_common, raw 링 = 진단) + 요청 시 스냅샷 ──
static void micProbeTask(void* parameter) {
  (void)parameter;
  static union {
    int32_t raw[MIC_DMA_BUF_LEN];
    int16_t i16[MIC_DMA_BUF_LEN];
  } audio_buffer;
  static uint32_t slot_us[MIC_RING_SLOTS];   // 슬롯별 i2s_read 반환 시각 (링 인덱스와 동일 위치)

  int16_t* const ring_base = initMicRingBuffer();
  MicRingStatus  ring      = {};
  size_t         bytes_read = 0;
  if (ring_base == nullptr || g_rawRing == nullptr) {
    Serial.println("[noise] ring alloc 실패 — 스냅샷 불가, 적재만 계속");
  }

  for (;;) {
    const esp_err_t err = i2s_read(MIC_I2S_PORT, audio_buffer.raw, sizeof(audio_buffer.raw),
                                   &bytes_read, portMAX_DELAY);
    const uint32_t now_us = micros();
    if (err != ESP_OK) { ring.gaps++; continue; }

    size_t n = bytes_read / sizeof(int32_t);
    if (n > (size_t)MIC_DMA_BUF_LEN) n = (size_t)MIC_DMA_BUF_LEN;

    int16_t* const slot = micRingSlot(ring_base, ring.write_idx);
    if (slot == nullptr || g_rawRing == nullptr) continue;

    // raw 먼저 보존(가드 이전) → 그 다음 제품과 동일한 변환 경로로 int16 슬롯 적재
    memcpy(g_rawRing + (size_t)ring.write_idx * MIC_DMA_BUF_LEN, audio_buffer.raw, n * sizeof(int32_t));
    convertMicRawToInt16(audio_buffer.raw, slot, n);
    slot_us[ring.write_idx] = now_us;
    micRingAdvance(&ring);

    if (!g_ringFull && ring.slots_filled >= MIC_RING_SLOTS) {
      g_ringFull = true;
      Serial.println("[noise] ring filled — 's' 스냅샷 / '0'~'6' 모드");
    }

    // 스냅샷 = micRingAdvance 직후(이 태스크가 유일한 쓰기 주체 → 복사 중 쓰기 부재. mic_uplink 동형)
    if (g_snapReq && ring.slots_filled >= MIC_RING_SLOTS) {
      for (uint32_t i = 0; i < MIC_RING_SLOTS; ++i) {
        const uint32_t idx = (ring.write_idx + i) % MIC_RING_SLOTS;   // 오래된→최신
        memcpy(g_snap16 + (size_t)i * MIC_DMA_BUF_LEN, micRingSlot(ring_base, idx),
               (size_t)MIC_DMA_BUF_LEN * sizeof(int16_t));
        memcpy(g_snapRaw + (size_t)i * MIC_DMA_BUF_LEN, g_rawRing + (size_t)idx * MIC_DMA_BUF_LEN,
               (size_t)MIC_DMA_BUF_LEN * sizeof(int32_t));
        g_snapSlotUs[i] = slot_us[idx];
      }
      taskENTER_CRITICAL(&g_stampMux);
      memcpy(g_snapTofStart, g_tofStart, sizeof(g_tofStart));
      memcpy(g_snapTofEnd,   g_tofEnd,   sizeof(g_tofEnd));
      g_snapTofN = (g_tofReads < TOF_STAMP_N) ? g_tofReads : (uint32_t)TOF_STAMP_N;
      taskEXIT_CRITICAL(&g_stampMux);
      g_snapGaps      = ring.gaps;
      g_snapStackFree = (uint32_t)uxTaskGetStackHighWaterMark(nullptr);
      g_snapReq = false;
      __sync_synchronize();   // 위 비volatile 복사가 ready 보다 먼저 보이도록 (mic_uplink 동형)
      g_snapReady = true;
    }
  }
}

// ── ToF 폴링 태스크 ×2 (parameter = 담당 코어). 활성 코어만 버스를 만진다 ─────
static void tofProbeTask(void* parameter) {
  const int my_core = (int)(intptr_t)parameter;
  static VL53L5CX_ResultsData measurementData[2];   // 코어별 BSS (~1356B × 2)
  static TofJudgeState        judge[2];
  for (;;) {
    if (g_tofPoll && g_tofCore == my_core &&
        xSemaphoreTake(g_busMux, pdMS_TO_TICKS(20)) == pdTRUE) {
      if (g_tofPoll && g_tofCore == my_core) {        // 획득 대기 중 모드 변경 → 이번 회차 건너뜀
        const uint32_t t0 = micros();
        if (tofImager.isDataReady() && tofImager.getRangingData(&measurementData[my_core])) {
          const uint32_t t1 = micros();               // I2C 트래픽 끝(판정 CPU 부하는 창 밖)
          (void)tofJudgeFrame(&judge[my_core], measurementData[my_core]);  // 제품과 같은 CPU 부하(판정값 미사용)
          taskENTER_CRITICAL(&g_stampMux);
          g_tofStart[g_tofStampIdx] = t0;
          g_tofEnd[g_tofStampIdx]   = t1;
          g_tofStampIdx = (g_tofStampIdx + 1) % TOF_STAMP_N;
          g_tofReads++;
          taskEXIT_CRITICAL(&g_stampMux);
          const uint8_t sc = (tofImager.Dev != nullptr) ? tofImager.Dev->streamcount : 0;
          if (g_scLogReq) {
            g_scLogReq = false;
            // "[noise][m2] first frame core=1 sc 255->12" ≤ 45B
            Serial.printf("%s first frame core=%d sc %u->%u\n", modeTag(g_mode), my_core,
                          (unsigned)g_scLast, (unsigned)sc);
          }
          g_scLast = sc;
        }
      }
      xSemaphoreGive(g_busMux);
    }
    vTaskDelay(pdMS_TO_TICKS(TOF_PERIOD_MS));
  }
}

// ── 모드 전환 (loop 전용). 뮤텍스 안에서만 stop/start/setClock ────────────────
static void applyMode(int m) {
  if (!g_tofAvail) { Serial.println("[noise] tof 없음 — 모드 전환 불가(m0 상태로 간주)"); return; }
  if (m < 0 || m >= NOISE_MODE_N) return;

  const NoiseModeCfg cfg = noiseModeCfg(m, I2C_FAST_HZ, I2C_SLOW_HZ);   // noise_modes.h (호스트 검증 대상)
  const bool want_rng  = cfg.ranging;
  const bool want_poll = cfg.poll;
  const uint32_t want_hz = cfg.i2c_hz;
  const int  want_core = cfg.core;

  static uint32_t cur_hz = I2C_FAST_HZ;                  // initToF 가 400k 로 시작 (tof_common.cpp)

  g_tofPoll = false;                                     // 폴링 먼저 멈추고
  xSemaphoreTake(g_busMux, portMAX_DELAY);               // 진행 중 ULD 호출이 끝나길 기다린다
  bool ok = true;
  if (want_hz != cur_hz) {                               // 변경 필요 시만 (esp32-hal-i2c i2cSetClock = 라이브 재설정)
    if (Wire.setClock(want_hz)) cur_hz = want_hz; else ok = false;
  }
  if (want_rng && !g_tofRanging) {
    if (tofImager.startRanging()) g_tofRanging = true; else ok = false;
  }
  if (!want_rng && g_tofRanging) {
    if (tofImager.stopRanging()) g_tofRanging = false; else ok = false;
  }
  g_mode    = m;
  g_tofCore = want_core;
  g_scLogReq = true;
  __sync_synchronize();
  g_tofPoll = want_poll;
  xSemaphoreGive(g_busMux);

  // 풀다운은 OFF 모드에서도 **명시적으로** 끈다 — m5→m2 교대 측정 시 이전 상태가 남으면 대조군 오염.
  applySdPulldown(cfg.sd_pd);

  // "[noise][m3] rng=1 poll=1 i2c=100k core=0 ok=1 sc=255" ≤ 55B
  Serial.printf("%s rng=%d poll=%d i2c=%uk core=%d ok=%d sc=%u\n", modeTag(m), (int)g_tofRanging,
                (int)want_poll, (unsigned)(cur_hz / 1000), want_core, (int)ok, (unsigned)g_scLast);
  logSdPulldown(m, cfg.sd_pd);
}

// ── 스냅샷 분석 + 로그 (loop 전용, 한 줄 ≤80B — decisions.md 6.3(j) 실측 상한) ──
static void reportSnapshot() {
  const int m = g_mode;
  const NoiseSnapStats st = noiseAnalyzeI16(g_snap16, SNAP_SAMPLES, MIC_SAMPLE_RATE_HZ,
                                            g_bursts, NOISE_MAX_BURSTS);
  const NoiseRawPattern rp = noiseAnalyzeRaw(g_snapRaw, SNAP_SAMPLES, MIC_RAW_TO_INT16_SHIFT);

  // 슬롯 간격 sanity: 64000µs 가 정상. 벗어나면 슬롯 시각(=DMA 큐 대기 포함)을 시각 상관에 쓸 수 없다.
  uint32_t dt_min = UINT32_MAX, dt_max = 0;
  for (uint32_t i = 1; i < MIC_RING_SLOTS; ++i) {
    const uint32_t dt = g_snapSlotUs[i] - g_snapSlotUs[i - 1];
    if (dt < dt_min) dt_min = dt;
    if (dt > dt_max) dt_max = dt;
  }

  // 시각 상관: 각 버스트 시작 샘플의 시각 → 가장 가까운 ToF I2C 읽기 창 [start,end] 까지 거리.
  //   sample_us = slot_end_us − (1024 − k) × 62.5µs   (k = 슬롯 내 인덱스)
  //   ⚠️ slot_end_us 는 i2s_read **반환** 시각 = DMA 완료 + 큐 대기 포함(상한). slot_dt_us 가
  //      64000 근처가 아니면 이 상관은 신뢰 불가 — L7 로 함께 판단한다. in = 창 안(거리 0) 개수.
  const uint32_t nb = (st.burst_n < NOISE_MAX_BURSTS) ? st.burst_n : (uint32_t)NOISE_MAX_BURSTS;
  uint32_t d_min = UINT32_MAX, d_max = 0, d_in = 0;
  uint64_t d_sum = 0; uint32_t d_cnt = 0;
  for (uint32_t b = 0; b < nb && g_snapTofN > 0; ++b) {
    const uint32_t slot = g_bursts[b] / MIC_DMA_BUF_LEN;
    const uint32_t k    = g_bursts[b] % MIC_DMA_BUF_LEN;
    const uint32_t t_us = g_snapSlotUs[slot] - (uint32_t)((uint64_t)(MIC_DMA_BUF_LEN - k) * 1000000u / MIC_SAMPLE_RATE_HZ);
    const uint32_t d    = noiseUsToWindow(t_us, g_snapTofStart, g_snapTofEnd, g_snapTofN);
    if (d == 0) d_in++;
    if (d < d_min) d_min = d;
    if (d > d_max) d_max = d;
    d_sum += d; d_cnt++;
  }

  ++g_snapNo;
  // L1 최악 "[noise][m2] snap#4294967295 n=32768 peak=32768 rms=32768 rms_x=32768" = 71B
  Serial.printf("%s snap#%u n=%u peak=%d rms=%d rms_x=%d\n", modeTag(m), (unsigned)g_snapNo,
                (unsigned)st.n, (int)st.peak, (int)st.rms_all, (int)st.rms_excl);
  // L2 최악 "[noise][m2] clip=32768(+32768/-32768) burst=32768 len_max=32768 first=32767" = 76B
  Serial.printf("%s clip=%u(+%u/-%u) burst=%u len_max=%u first=%u\n", modeTag(m),
                (unsigned)st.clip_n, (unsigned)st.clip_pos, (unsigned)st.clip_neg,
                (unsigned)st.burst_n, (unsigned)st.burst_len_max, (unsigned)st.first_clip_idx);
  // L3 최악 "[noise][m2] gap_ms n=255 min=2048 mode=2048 max=2048 tof_mult=255/255" = 71B
  Serial.printf("%s gap_ms n=%u min=%u mode=%u max=%u tof_mult=%u/%u\n", modeTag(m),
                (unsigned)st.gap_n, (unsigned)(st.gap_n ? st.gap_min_ms : 0), (unsigned)st.gap_mode_ms,
                (unsigned)st.gap_max_ms, (unsigned)st.gap_tof_mult_n, (unsigned)st.gap_n);
  // L4 최악 "[noise][m2] raw bad=32768 low6nz=32768 iso_hi=32768 tz=32" = 57B
  Serial.printf("%s raw bad=%u low6nz=%u iso_hi=%u tz=%d\n", modeTag(m), (unsigned)rp.bad_n,
                (unsigned)rp.low6_nz_n, (unsigned)rp.iso_hi_n, rp.tz_all);
  // L5 "[noise][m2] raw ex 40000F40 40000F41 BFFF0F00 7FFFFFC0" = 53B
  Serial.printf("%s raw ex %08X %08X %08X %08X\n", modeTag(m), (unsigned)rp.example[0],
                (unsigned)rp.example[1], (unsigned)rp.example[2], (unsigned)rp.example[3]);
  // L6 최악 "[noise][m2] tof_rd=64 dt_ms min=4294967.2 avg=4294967.2 max=4294967.2 in=255/255" = 79B
  const uint32_t d_avg = d_cnt ? (uint32_t)(d_sum / d_cnt) : 0;
  Serial.printf("%s tof_rd=%u dt_ms min=%u.%u avg=%u.%u max=%u.%u in=%u/%u\n", modeTag(m),
                (unsigned)g_snapTofN,
                (unsigned)(d_cnt ? d_min / 1000 : 0), (unsigned)(d_cnt ? (d_min % 1000) / 100 : 0),
                (unsigned)(d_avg / 1000), (unsigned)((d_avg % 1000) / 100),
                (unsigned)(d_cnt ? d_max / 1000 : 0), (unsigned)(d_cnt ? (d_max % 1000) / 100 : 0),
                (unsigned)d_in, (unsigned)d_cnt);
  // L7 최악 "[noise][m2] slot_dt_us min=4294967295 max=4294967295 gaps=4294967295 stk=65535" = 79B
  Serial.printf("%s slot_dt_us min=%u max=%u gaps=%u stk=%u\n", modeTag(m), (unsigned)dt_min,
                (unsigned)dt_max, (unsigned)g_snapGaps, (unsigned)g_snapStackFree);
  // L8 = 측정 조건 동반 기록. req≠reg 면 그 스냅샷은 무효(Runbook 1절).
  logSdPulldown(m, noiseModeCfg(m, I2C_FAST_HZ, I2C_SLOW_HZ).sd_pd);
}

void setup() {
  Serial.begin(115200);
  delay(MIC_SERIAL_BOOT_DELAY_MS);
  Serial.println("\n[BOOT] ddingdong mic noiseprobe (PoC-45 진단, 키: 0~6 모드 / s 스냅샷)");

  g_rawRing = (int32_t*)ps_malloc(SNAP_RAW_BYTES);
  g_snap16  = (int16_t*)ps_malloc(SNAP_I16_BYTES);
  g_snapRaw = (int32_t*)ps_malloc(SNAP_RAW_BYTES);
  if (g_rawRing == nullptr || g_snap16 == nullptr || g_snapRaw == nullptr) {
    Serial.println("[BOOT] PSRAM 진단 버퍼 확보 실패 — 스냅샷 비활성");
  } else {
    memset(g_rawRing, 0, SNAP_RAW_BYTES);
    Serial.printf("[BOOT] diag buffers %u+%u+%u B PSRAM free=%u\n", (unsigned)SNAP_RAW_BYTES,
                  (unsigned)SNAP_I16_BYTES, (unsigned)SNAP_RAW_BYTES, (unsigned)ESP.getFreePsram());
  }

  g_busMux = xSemaphoreCreateMutex();

  if (!initMicI2S()) { Serial.println("[BOOT] mic init 실패 — 중단"); return; }
  // i2s_set_pin 이후에 건다(순서 보장). 부팅 모드 = m2 → 풀다운 OFF 를 명시적으로 박고 재독한다.
  const bool boot_pd = noiseModeCfg(g_mode, I2C_FAST_HZ, I2C_SLOW_HZ).sd_pd;
  applySdPulldown(boot_pd);
  logSdPulldown(g_mode, boot_pd);
  discardMicWarmup();
  xTaskCreatePinnedToCore(micProbeTask, "micProbeTask", MIC_TASK_STACK_SIZE, nullptr,
                          MIC_TASK_PRIORITY, nullptr, MIC_TASK_CORE);
  Serial.println("[BOOT] micProbeTask started (Core 0, prio 4) — mic_uplink 와 동일 배치");

  // initToF = Wire.begin + setClock(400k) + begin + 8x8/15Hz + startRanging (tof_common.cpp)
  if (initToF()) {
    g_tofAvail   = true;
    g_tofRanging = true;
    xTaskCreatePinnedToCore(tofProbeTask, "tofProbe0", TOF_TASK_STACK_SIZE, (void*)0,
                            TOF_TASK_PRIORITY, nullptr, 0);
    xTaskCreatePinnedToCore(tofProbeTask, "tofProbe1", TOF_TASK_STACK_SIZE, (void*)1,
                            TOF_TASK_PRIORITY, nullptr, 1);
    Serial.println("[BOOT] tofProbe0/1 started (prio 3) — 활성 = m2 Core 0 @400k (현행 재현)");
  } else {
    Serial.println("[BOOT] tof init 실패 — 모드 전환 불가, 마이크 기준선만 측정 가능");
  }
}

void loop() {
  const int c = Serial.read();
  if (c >= '0' && c <= '6') {
    applyMode(c - '0');
  } else if (c == 's' || c == 'S') {
    if (g_snap16 == nullptr || g_snapRaw == nullptr) Serial.println("[noise] 버퍼 없음");
    else if (!g_ringFull)                             Serial.println("[noise] ring 미충전 — 2초 후 다시");
    else if (g_snapReq || g_snapReady)                Serial.println("[noise] 이전 스냅샷 처리 중");
    else { g_snapReq = true; Serial.printf("%s snapshot 요청\n", modeTag(g_mode)); }
  } else if (c == 'h' || c == '?') {
    Serial.println("[noise] 0 stop|1 rng|2 rd400k c0|3 100k|4 core1|5 m2+sdpd|6 m0+sdpd|s snap");
  }

  if (g_snapReady) {
    reportSnapshot();
    g_snapReady = false;
  }
  delay(10);
}
