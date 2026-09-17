// 띵동 firmware - 카메라·마이크·ToF 동시 구동 관측 하네스 (2026-09-17, env:camera_probe)
//
// ★ 무엇을 가르는가
//   보드 2차 체인(카메라 캡처 + 녹음 → /enrich)을 붙이기 전에 답해야 하는 질문 하나:
//   **「카메라(와 WiFi 송신)를 켜면 마이크 클립 미결(6.3(n))이 악화되는가」**
//   악화되면 2차 오디오가 오염돼 STT·ML 입력이 같이 망가진다. 본 env 는 그 판단의 **입력만**
//   만든다 — 악화 여부의 판정도, 6.3(n) 해결책 선택도 여기 0줄이다(사용자 판단 대기).
//
// ★ 성격 = 방법론 자산(decisions.md 8.4(f) 서문 / 6.3(o) mic_noiseprobe · 9.1(e) tof_pinscan 선례).
//   제품 코드(camera_common / mic_common / tof_common / uplink_common) 무수정 — import·호출만.
//   서버 API 호출 0 · 판정 0 · 전송 계약 0.
//
// ★ 모드 (시리얼 '0'~'7', 재플래시 없음 — 인접 모드끼리 **한 변수만** 다르다)
//   사슬의 근거와 전이 의미는 include/probe_modes.h 주석 참조. 불변식은 호스트 테스트가 강제한다.
//     m0 cam OFF      / wifi TX off / QVGA   ← 기준선(마이크 + ToF 만)
//     m1 cam OFF      / wifi TX ON  / QVGA
//     m2 cam IDLE     / wifi TX ON  / QVGA
//     m3 cam PERIODIC / wifi TX ON  / QVGA
//     m4 cam CONT     / wifi TX ON  / QVGA
//     m5 cam CONT     / wifi TX off / QVGA
//     m6 cam PERIODIC / wifi TX off / QVGA   (= m2 축이 아닌 m3 와 같은 구성 — 재현성 확인 지점)
//     m7 cam PERIODIC / wifi TX off / VGA
//
// ★ 코어 배치 (근거유형 = 실측 설치 core 대조 + 실측 상수 대조)
//   Core 0 = micProbeTask(prio 4) · tofProbeTask(prio 3)  — mic_uplink(6.3(m)) 와 동일 배치
//   Core 1 = loopTask(prio 1, stack 8192)                 — 카메라 fb_get / UDP 송신 / 창 출력
//   cores/esp32/main.cpp 의 xTaskCreateUniversal(..., 1, ..., ARDUINO_RUNNING_CORE) +
//   tools/sdk/esp32s3/sdkconfig CONFIG_ARDUINO_RUNNING_CORE=1 ⇒ loopTask 는 Core 1.
//   ⚠️ 같은 sdkconfig 의 CONFIG_CAMERA_CORE0=y 이므로 **esp32-camera 내부 DMA 태스크는 Core 0**,
//      즉 마이크·ToF 와 같은 코어다. 카메라 ON 이 Core 0 경합을 늘리는 경로가 실재한다는 뜻이며
//      이것이 본 하네스가 재는 것 중 하나다(판정은 하지 않는다).
//
// ★ I2C 포트 분리 (근거유형 = 실측 설치 sdkconfig + 실측 core 대조)
//   카메라 SCCB = CONFIG_SCCB_HARDWARE_I2C_PORT1=y → I2C 포트 1
//   ToF Wire    = libraries/Wire/src/Wire.cpp `TwoWire Wire = TwoWire(0)` → I2C 포트 0
//   ⇒ 포트가 다르다. 핀도 교집합이 ∅ 다(카메라 SCCB 40/39, ToF 5/6, 마이크 I2S1 2/3/7).
//
// ★ 조용한 실패 금지(카테고리 20): fb_get NULL · SOI 불일치 · I2S 오류 · ToF 읽기 실패 ·
//   UDP 송신 실패 · WiFi 미연결이 **전부 창 출력의 카운터**로 드러난다.
//
// ★ 시리얼 한 줄 ≤80B (decisions.md 6.3(h)(j) 실측: ≤80B 62줄에서 손상 0건). 각 printf 위에
//   최악값 문자열과 바이트 수를 적어 둔다.

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>

#include "esp_system.h"   // esp_reset_reason

#include "camera_common.h"
#include "mic_common.h"
#include "probe_modes.h"
#include "probe_stats.h"
#include "tof_common.h"
#include "uplink_common.h"   // UPLINK_WIFI_* 타임아웃만 재사용(WiFi 정책 SSoT). 함수 호출 0.
#include "secrets.h"

extern SparkFun_VL53L5CX tofImager;   // tof_common.cpp 소유

// ── 상수 (진단 전용) ──────────────────────────────────────────────────────────
// 창 길이. 10초 = ToF 150프레임 / 마이크 156버퍼 / 주기 캡처 10장 — 어느 축도 표본 한 자릿수가
// 되지 않는 최소 길이. 짧게 잡으면 창마다 값이 튀어 모드 간 비교가 불가능해진다(논증).
constexpr uint32_t PROBE_WINDOW_MS = 10000;

// 주기 캡처 간격. 제품 2차 체인은 **이벤트당 1프레임**이라 1초 1장이 그 부하의 상한 근사다(논증).
constexpr uint32_t PROBE_CAPTURE_PERIOD_MS = 1000;

// ── WiFi 송신 부하 축 ─────────────────────────────────────────────────────────
// 서버 API 를 부르지 않고 **송신 전류만** 만든다. 목적지는 secrets.h 의 노트북 LAN 주소이고
// 포트는 아래 상수 — 프로젝트 어디에서도 바인딩하지 않는 포트다(서버 5000 / tls_probe 5001).
// 수신 프로세스가 없어도 UDP 는 연결 없이 나가므로 보드 쪽 송신 부하는 동일하다.
//   크기 1400 B = 일반 이더넷 MTU 1500 에서 IP/UDP 헤더(28 B)를 뺀 값 아래 → IP 단편화 없이 1프레임.
//   주기 20 ms = 50 pkt/s ≈ 560 kbit/s. 2차 체인의 실 업로드(수백 KB 를 수백 ms 에)보다 낮지만
//   **송신 버스트가 창 내내 규칙적으로 반복**되는 조건을 만든다(전원 흔들림을 보려는 것이지
//   대역폭을 재려는 것이 아니다).
// ⚠️ 값은 관측 편의 상수이며 판정값이 아니다. 근거유형 = 논증(④런타임 미검증).
constexpr uint16_t PROBE_UDP_PORT      = 55555;
constexpr size_t   PROBE_UDP_BYTES     = 1400;
constexpr uint32_t PROBE_UDP_PERIOD_MS = 20;

// 빌드 식별. 커밋 해시 주입은 extra_scripts(신규 빌드 기계)가 필요해 넣지 않았다 —
// env 이름 + 컴파일 시각으로 "어느 바이너리인가"는 가려진다.
#ifndef PROBE_ENV_NAME
#define PROBE_ENV_NAME "camera_probe"
#endif

// ── 모드 상태 (loop 가 쓰고 태스크가 읽는다) ──────────────────────────────────
static volatile int  g_mode    = 0;       // 부팅 = m0 (기준선)
static bool          g_camInit = false;   // loop 전용: esp_camera_init 상태 추적
static uint8_t       g_camRes  = PROBE_RES_QVGA;   // loop 전용

// ── 창 통계 공유 (태스크가 누적 → loop 가 창 끝에 회수) ───────────────────────
// ★ 왜 portMUX 병합인가: 누적 자체를 임계구역에 넣으면 1024 샘플 루프 동안 Core 0 인터럽트가
//   막힌다. Core 0 에는 WiFi 스택도 있으므로 그러면 **재려는 대상을 관측기가 흔든다**.
//   그래서 태스크는 지역 창에 누적하고, 버퍼 1개(64ms)마다 **7필드 덧셈만** 임계구역에서 한다.
static portMUX_TYPE g_winMux = portMUX_INITIALIZER_UNLOCKED;
static ProbeMicWin  g_micShared = {};
static ProbeTofWin  g_tofShared = {};

// 카메라 창은 loop 만 만진다(캡처가 loop 전용) → 락 없음.
static ProbeCamWin  g_camWin = {};

// ── 태스크 핸들 (창 출력의 stack free 용) ─────────────────────────────────────
static TaskHandle_t g_micTask = nullptr;
static TaskHandle_t g_tofTask = nullptr;

// ── WiFi / UDP (loop 전용) ────────────────────────────────────────────────────
static WiFiUDP  g_udp;
static bool     g_wifiUp  = false;
static uint32_t g_txOk    = 0;
static uint32_t g_txErr   = 0;

static const char* modeTag(int m) {
  static const char* t[PROBE_MODE_N] = {"[cp][m0]", "[cp][m1]", "[cp][m2]", "[cp][m3]",
                                        "[cp][m4]", "[cp][m5]", "[cp][m6]", "[cp][m7]"};
  return (m >= 0 && m < PROBE_MODE_N) ? t[m] : "[cp][m?]";
}

static const char* resetReasonName(esp_reset_reason_t r) {
  switch (r) {
    case ESP_RST_POWERON:   return "POWERON";
    case ESP_RST_EXT:       return "EXT";
    case ESP_RST_SW:        return "SW";
    case ESP_RST_PANIC:     return "PANIC";
    case ESP_RST_INT_WDT:   return "INT_WDT";
    case ESP_RST_TASK_WDT:  return "TASK_WDT";
    case ESP_RST_WDT:       return "WDT";
    case ESP_RST_DEEPSLEEP: return "DEEPSLEEP";
    case ESP_RST_BROWNOUT:  return "BROWNOUT";   // ★ 전원 흔들림 재부팅의 식별자
    case ESP_RST_SDIO:      return "SDIO";
    default:                return "UNKNOWN";
  }
}

// ── 마이크 태스크 (Core 0, prio 4 — mic_uplink 와 동일 배치) ──────────────────
// 적재 경로는 제품과 동일하다: i2s_read → convertMicRawToInt16 → 링버퍼 슬롯.
// ★ 링버퍼를 그대로 두는 이유 = 이 하네스가 재려는 것이 "제품 부하에서의 마이크"이기 때문이다.
//   PSRAM 슬롯 쓰기는 카메라 프레임버퍼(PSRAM)와 같은 버스를 쓴다 — 빼면 그 경합이 사라진다.
static void micProbeTask(void* parameter) {
  (void)parameter;
  static union {
    int32_t raw[MIC_DMA_BUF_LEN];
    int16_t i16[MIC_DMA_BUF_LEN];
  } audio_buffer;

  int16_t* const ring_base = initMicRingBuffer();
  MicRingStatus  ring      = {};
  size_t         bytes_read = 0;
  uint32_t       gaps_reported = 0;
  if (ring_base == nullptr) {
    Serial.println("[cp] mic ring alloc 실패 — 적재 없이 통계만 계속");
  }

  for (;;) {
    const esp_err_t err = i2s_read(MIC_I2S_PORT, audio_buffer.raw, sizeof(audio_buffer.raw),
                                   &bytes_read, portMAX_DELAY);
    if (err != ESP_OK) { ring.gaps++; }

    ProbeMicWin local = {};
    if (err == ESP_OK) {
      size_t n = bytes_read / sizeof(int32_t);
      if (n > (size_t)MIC_DMA_BUF_LEN) n = (size_t)MIC_DMA_BUF_LEN;

      int16_t* const slot = micRingSlot(ring_base, ring.write_idx);
      // 링버퍼가 없어도 통계는 낸다 — union 의 int16 뷰에 제자리 변환(mic_common 이 겹침 허용).
      int16_t* const dst = (slot != nullptr) ? slot : audio_buffer.i16;
      convertMicRawToInt16(audio_buffer.raw, dst, n);
      probeMicAccumulate(&local, dst, n);
      if (slot != nullptr) micRingAdvance(&ring);
    }

    // 창 누적 병합 + 새로 생긴 gap 만 이관(창 경계에서 중복 계상하지 않는다).
    const uint32_t new_gaps = ring.gaps - gaps_reported;
    gaps_reported = ring.gaps;
    taskENTER_CRITICAL(&g_winMux);
    g_micShared.n      += local.n;
    g_micShared.n_ok   += local.n_ok;
    g_micShared.clip   += local.clip;
    g_micShared.gaps   += new_gaps;
    g_micShared.sq_all += local.sq_all;
    g_micShared.sq_ok  += local.sq_ok;
    if (local.peak > g_micShared.peak) g_micShared.peak = local.peak;
    taskEXIT_CRITICAL(&g_winMux);
  }
}

// ── ToF 태스크 (Core 0, prio 3 — tof_common 판정 본체를 그대로 호출) ──────────
static void tofProbeTask(void* parameter) {
  (void)parameter;
  static VL53L5CX_ResultsData measurementData;
  static TofJudgeState        judge;
  bool last_presence = false;
  bool have_last     = false;

  for (;;) {
    bool ok = false, edge = false;
    if (tofImager.isDataReady() && tofImager.getRangingData(&measurementData)) {
      const TofFrameResult r = tofJudgeFrame(&judge, measurementData);   // 판정값은 세지 않는다
      ok = true;
      if (have_last && r.presence_state != last_presence) edge = true;
      last_presence = r.presence_state;
      have_last     = true;
    }
    taskENTER_CRITICAL(&g_winMux);
    if (ok) { g_tofShared.frames++; if (edge) g_tofShared.pres_edge++; }
    else    { g_tofShared.read_fail++; }
    taskEXIT_CRITICAL(&g_winMux);
    vTaskDelay(pdMS_TO_TICKS(TOF_PERIOD_MS));
  }
}

// ── 카메라 (loop 전용) ────────────────────────────────────────────────────────
// 해상도는 esp_camera_init 을 다시 하지 않고 sensor->set_framesize 로 바꾼다 —
// camera_common 의 buildCameraConfig(QVGA 고정)를 복제하지 않기 위함(무변경 대상 유지).
static bool applyResolution(uint8_t res) {
  sensor_t* s = esp_camera_sensor_get();
  if (s == nullptr) { Serial.println("[cp] sensor_get NULL — 해상도 변경 불가"); return false; }
  const framesize_t fs = (res == PROBE_RES_VGA) ? FRAMESIZE_VGA : FRAMESIZE_QVGA;
  const int rc = s->set_framesize(s, fs);
  // "[cp] framesize res=1 rc=-2147483648" = 34B
  Serial.printf("[cp] framesize res=%d rc=%d\n", (int)res, rc);
  return rc == 0;
}

static void cameraStart(uint8_t res) {
  const uint32_t t0 = millis();
  const uint32_t psram_before = (uint32_t)ESP.getFreePsram();
  const bool ok = initCameraWithDiagnostics();   // 내부에서 [MEM:pre-init]/[MEM:post-init] 출력
  const uint32_t dt = millis() - t0;
  g_camInit = ok;
  // "[cp] cam init ok=0 ms=4294967295 psram_used=4294967295" = 54B
  Serial.printf("[cp] cam init ok=%d ms=%u psram_used=%u\n", (int)ok, (unsigned)dt,
                (unsigned)(psram_before - (uint32_t)ESP.getFreePsram()));
  if (ok) {
    g_camRes = PROBE_RES_QVGA;                   // init 은 언제나 QVGA 로 선다
    if (res != PROBE_RES_QVGA && applyResolution(res)) g_camRes = res;
  }
}

static void cameraStop() {
  const uint32_t t0 = millis();
  const uint32_t psram_before = (uint32_t)ESP.getFreePsram();
  logMemoryDiagnostics("pre-deinit");
  const esp_err_t err = esp_camera_deinit();
  const uint32_t dt = millis() - t0;
  logMemoryDiagnostics("post-deinit");
  g_camInit = false;
  // "[cp] cam deinit err=0x105 ms=4294967295 psram_back=4294967295" = 60B
  Serial.printf("[cp] cam deinit err=0x%x ms=%u psram_back=%u\n", err, (unsigned)dt,
                (unsigned)((uint32_t)ESP.getFreePsram() - psram_before));
}

// fb_get → SOI 검사 → 길이·시간 기록 → **즉시** fb_return.
// ★ fb 를 쥔 채 다른 일을 하지 않는다(fb_count=2 라 반환이 늦으면 다음 프레임이 고갈된다).
static void captureOnce() {
  const uint32_t t0 = millis();
  camera_fb_t* fb = esp_camera_fb_get();
  const uint32_t dt = millis() - t0;
  if (fb == nullptr) { probeCamRecordNull(&g_camWin); return; }
  const bool soi = probeIsJpegSoi(fb->buf, fb->len);
  const uint32_t len = (uint32_t)fb->len;
  esp_camera_fb_return(fb);
  if (soi) probeCamRecordOk(&g_camWin, len, dt);
  else     probeCamRecordSoiBad(&g_camWin);
}

// ── WiFi (loop 전용) ──────────────────────────────────────────────────────────
// ★ uplinkConnectWifi() 를 부르지 않는 이유: 그 함수는 연결 성공 시 SSID 를 시리얼에 찍는다
//   (uplink_common.cpp). 본 하네스의 로그는 측정 기록으로 repo 밖에 남지만, 시리얼에
//   자격증명을 흘리지 않는다는 제약이 더 강하다. 타임아웃 상수는 그 헤더에서 그대로 재사용한다.
static bool probeTryConnect(const char* ssid, const char* password, uint32_t timeoutMs) {
  WiFi.begin(ssid, password);
  const uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && (millis() - start) < timeoutMs) {
    delay(UPLINK_WIFI_POLL_INTERVAL_MS);
  }
  return WiFi.status() == WL_CONNECTED;
}

static bool probeConnectWifi() {
  WiFi.mode(WIFI_STA);
  return probeTryConnect(WIFI_PRIMARY_SSID, WIFI_PRIMARY_PASSWORD,
                         UPLINK_WIFI_PRIMARY_TIMEOUT_MS) ||
         probeTryConnect(WIFI_FALLBACK_SSID, WIFI_FALLBACK_PASSWORD,
                         UPLINK_WIFI_FALLBACK_TIMEOUT_MS);
}

static void sendDummyPacket() {
  static uint8_t payload[PROBE_UDP_BYTES];   // 내용 무의미(0 채움) — 재는 것은 송신 동작이다
  if (!g_wifiUp || WiFi.status() != WL_CONNECTED) { g_txErr++; return; }
  if (g_udp.beginPacket(SPIKE_SERVER_HOST, PROBE_UDP_PORT) != 1) { g_txErr++; return; }
  g_udp.write(payload, sizeof(payload));
  if (g_udp.endPacket() == 1) g_txOk++; else g_txErr++;
}

// ── 모드 전환 (loop 전용) ─────────────────────────────────────────────────────
static void applyMode(int m) {
  if (m < 0 || m >= PROBE_MODE_N) return;
  const ProbeModeCfg cfg = probeModeCfg(m);   // probe_modes.h (호스트 검증 대상)

  if (cfg.cam == PROBE_CAM_OFF) {
    if (g_camInit) cameraStop();
  } else {
    if (!g_camInit) cameraStart(cfg.res);
    else if (cfg.res != g_camRes && applyResolution(cfg.res)) g_camRes = cfg.res;
  }

  g_mode = m;
  // "[cp][m7] set cam=3 wifi=1 res=1 init=0 camres=1" = 46B
  Serial.printf("%s set cam=%d wifi=%d res=%d init=%d camres=%d\n", modeTag(m), (int)cfg.cam,
                (int)cfg.wifi_tx, (int)cfg.res, (int)g_camInit, (int)g_camRes);
}

// ── 창 출력 (loop 전용, 각 줄 ≤80B) ──────────────────────────────────────────
static void reportWindow(uint32_t win_no) {
  ProbeMicWin mic;
  ProbeTofWin tof;
  taskENTER_CRITICAL(&g_winMux);
  mic = g_micShared; tof = g_tofShared;
  probeMicReset(&g_micShared); probeTofReset(&g_tofShared);
  taskEXIT_CRITICAL(&g_winMux);

  const ProbeModeCfg cfg = probeModeCfg(g_mode);

  // L1 "[cp][m7] win#4294967295 t=4294967295s cam=3 wifi=1 res=1" = 56B
  Serial.printf("%s win#%u t=%us cam=%d wifi=%d res=%d\n", modeTag(g_mode), (unsigned)win_no,
                (unsigned)(millis() / 1000u), (int)cfg.cam, (int)cfg.wifi_tx, (int)cfg.res);

  // L2 "[cp] mic n=4294967295 pk=32768 rms=32768 rmsx=32768 clip=4294967295 gap=65535" = 77B
  //    n == 0 은 "무음"이 아니라 **표본 없음**이다(I2S 가 한 번도 안 돌았다는 뜻).
  if (mic.n == 0) {
    Serial.printf("[cp] mic n=0 (표본 없음 — i2s_read 미도달) gap=%u\n", (unsigned)mic.gaps);
  } else {
    Serial.printf("[cp] mic n=%u pk=%d rms=%d rmsx=%d clip=%u gap=%u\n", (unsigned)mic.n,
                  (int)mic.peak, (int)probeMicRmsAll(&mic), (int)probeMicRmsExcl(&mic),
                  (unsigned)mic.clip, (unsigned)mic.gaps);
  }

  // L3 "[cp] cam try=4294967295 ok=4294967295 nul=4294967295 soi=4294967295" = 68B
  Serial.printf("[cp] cam try=%u ok=%u nul=%u soi=%u\n", (unsigned)g_camWin.attempt,
                (unsigned)g_camWin.ok, (unsigned)g_camWin.fb_null, (unsigned)g_camWin.soi_bad);

  // L4 "[cp] cap len=4294967295..4294967295 ms=65535/65535/65535" = 56B
  //    ★ ok == 0 창은 최소값을 찍지 않는다 — 0 을 찍으면 "0ms 에 성공"으로 읽힌다(NC-3).
  if (probeCamHasSample(&g_camWin)) {
    Serial.printf("[cp] cap len=%u..%u ms=%u/%u/%u\n", (unsigned)g_camWin.len_min,
                  (unsigned)g_camWin.len_max, (unsigned)g_camWin.ms_min,
                  (unsigned)probeCamAvgMs(&g_camWin), (unsigned)g_camWin.ms_max);
  } else {
    Serial.println("[cp] cap len=n/a ms=n/a (ok=0)");
  }
  probeCamReset(&g_camWin);

  // L5 "[cp] tof fr=4294967295 edge=4294967295 err=4294967295" = 54B
  Serial.printf("[cp] tof fr=%u edge=%u err=%u\n", (unsigned)tof.frames,
                (unsigned)tof.pres_edge, (unsigned)tof.read_fail);

  // L6 "[cp] net st=255 rssi=-128 tx=4294967295 txerr=4294967295" = 57B
  //    st = WiFi.status() 원값. 3(WL_CONNECTED) 이 아니면 그 창의 WiFi 축은 무효다.
  Serial.printf("[cp] net st=%d rssi=%d tx=%u txerr=%u\n", (int)WiFi.status(),
                (int)WiFi.RSSI(), (unsigned)g_txOk, (unsigned)g_txErr);
  g_txOk = 0; g_txErr = 0;

  // L7 "[cp] mem psram=4294967295 heap=4294967295 stk m=65535 t=65535 l=65535" = 68B
  Serial.printf("[cp] mem psram=%u heap=%u stk m=%u t=%u l=%u\n", (unsigned)ESP.getFreePsram(),
                (unsigned)ESP.getFreeHeap(),
                (unsigned)(g_micTask ? uxTaskGetStackHighWaterMark(g_micTask) : 0),
                (unsigned)(g_tofTask ? uxTaskGetStackHighWaterMark(g_tofTask) : 0),
                (unsigned)uxTaskGetStackHighWaterMark(nullptr));
}

void setup() {
  Serial.begin(115200);
  delay(MIC_SERIAL_BOOT_DELAY_MS);

  const esp_reset_reason_t rr = esp_reset_reason();
  Serial.println("\n[BOOT] ddingdong camera probe — keys 0~7 mode / h help");
  // "[BOOT] reset=9 (BROWNOUT) env=camera_probe built=Sep 17 2026 21:00:00" = 69B
  Serial.printf("[BOOT] reset=%d (%s) env=%s built=%s %s\n", (int)rr, resetReasonName(rr),
                PROBE_ENV_NAME, __DATE__, __TIME__);
  logMemoryDiagnostics("boot");

  if (!initMicI2S()) {
    Serial.println("[BOOT] mic init 실패 — 마이크 축 무효(나머지는 계속)");
  } else {
    discardMicWarmup();
    xTaskCreatePinnedToCore(micProbeTask, "micProbeTask", MIC_TASK_STACK_SIZE, nullptr,
                            MIC_TASK_PRIORITY, &g_micTask, MIC_TASK_CORE);
    Serial.println("[BOOT] micProbeTask started (Core 0, prio 4)");
  }

  // initToF = Wire.begin + setClock(400k) + begin + 8x8/15Hz + startRanging (tof_common.cpp)
  // (motion indicator 프로그래밍은 initToF() 가 begin 직후 내부에서 한다 — 중복 호출 없음)
  if (initToF()) {
    xTaskCreatePinnedToCore(tofProbeTask, "tofProbeTask", TOF_TASK_STACK_SIZE, nullptr,
                            TOF_TASK_PRIORITY, &g_tofTask, TOF_TASK_CORE);
    Serial.println("[BOOT] tofProbeTask started (Core 0, prio 3)");
  } else {
    Serial.println("[BOOT] tof init 실패 — ToF 축 무효(나머지는 계속)");
  }

  // WiFi 연결은 모드와 무관하게 부팅 1회다. 모드가 바꾸는 것은 **송신 부하**뿐 —
  // 연결 자체를 모드로 묶으면 한 전이에서 두 변수가 움직인다.
  g_wifiUp = probeConnectWifi();
  if (g_wifiUp) {
    // SSID 는 찍지 않는다(제약). 사설 LAN IP 와 RSSI 만.
    // "[BOOT] wifi up ip=192.168.137.123 rssi=-100" = 43B
    Serial.printf("[BOOT] wifi up ip=%s rssi=%d\n", WiFi.localIP().toString().c_str(),
                  (int)WiFi.RSSI());
  } else {
    Serial.println("[BOOT] wifi 연결 실패 — WiFi 축 무효(창 출력 st/txerr 로 드러남)");
  }

  // ★ UDP 대상 주소를 찍는 이유 = WiFi 부하 축이 **조용히** 죽는 것을 막기 위함이다.
  //   핫스팟에서 노트북 IP 가 바뀌어 이 주소에 아무도 없으면 ARP 가 풀리지 않는데, lwIP 는
  //   그 패킷을 큐에 넣고 sendto() 에 성공을 돌려준다(설치 lwipopts.h: ARP_QUEUEING=1) →
  //   WiFiUDP::endPacket() == 1 → txerr=0. 무선으로 실제로 나가는 것은 1400B/20ms 가 아니라
  //   가끔의 ARP 요청뿐인데 로그는 정상으로 보인다 = 「WiFi 켰는데 마이크 무변화」라는 거짓 결론.
  //   그래서 측정 전에 이 줄과 노트북 IP 를 눈으로 맞춘다(RUNBOOK 2-1). 연결 실패 때도 찍는다 —
  //   주소가 틀렸는지 WiFi 가 죽었는지를 가르는 것이 이 줄이다.
  //   사설 LAN IP 라 출력 허용(SSID·비밀번호·토큰 출력은 여전히 0).
  // "[BOOT] udp dst=192.168.137.123:55555" = 36B
  Serial.printf("[BOOT] udp dst=%s:%u\n", SPIKE_SERVER_HOST, (unsigned)PROBE_UDP_PORT);

  applyMode(0);   // 기준선에서 시작
  Serial.println("[BOOT] ready — m0 기준선. 모드 전이는 RUNBOOK 순서표대로.");
}

void loop() {
  static uint32_t win_start   = 0;
  static uint32_t win_no      = 0;
  static uint32_t last_cap_ms = 0;
  static uint32_t last_tx_ms  = 0;

  const int c = Serial.read();
  if (c >= '0' && c <= '7') {
    applyMode(c - '0');
  } else if (c == 'h' || c == '?') {
    Serial.println("[cp] 0 base|1 +wifi|2 +init|3 +periodic|4 +cont|5 -wifi|6 periodic|7 vga");
  }

  const ProbeModeCfg cfg = probeModeCfg(g_mode);
  const uint32_t now = millis();

  if (g_camInit) {
    if (cfg.cam == PROBE_CAM_CONTINUOUS) {
      captureOnce();
    } else if (cfg.cam == PROBE_CAM_PERIODIC && (now - last_cap_ms) >= PROBE_CAPTURE_PERIOD_MS) {
      last_cap_ms = now;
      captureOnce();
    }
  }

  if (cfg.wifi_tx && (now - last_tx_ms) >= PROBE_UDP_PERIOD_MS) {
    last_tx_ms = now;
    sendDummyPacket();
  }

  if ((now - win_start) >= PROBE_WINDOW_MS) {
    win_start = now;
    reportWindow(++win_no);
  }

  delay(1);   // 연속 캡처 모드에서 loop 를 막지 않는 최소 양보
}
