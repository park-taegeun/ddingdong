// 띵동 firmware - 기기 heartbeat(`POST /api/v1/heartbeat`) 순수 계층 (env:enrich_uplink · env:enrich_autotrig)
//
// ★ 성격 = **배관(plumbing)**. 「켜짐 / 꺼짐」 판정은 서버가 한다(마지막 연락 후 DEVICE_OFFLINE_AFTER 초과 = 꺼짐).
//   보드는 「지금 알림을 낼 수 있다」는 사실이 있을 때만 보고하고, 모르면 보내지 않는다(기본값 폴백 금지).
//   대시보드 켜짐 문구 = 「현관 기기가 소리를 듣고 있어요.」 ⇒ 보고 조건에 **마이크 진행**을 넣는다.
//
// ★ 왜 Arduino 무의존 순수 헤더인가 (enrich_wire.h · trig_line.h 선례)
//   호스트 테스트(firmware/tools/heartbeat_wire_test.cpp)가 **같은 파일을 그대로** 컴파일한다(복사 아님).
//   전송(HTTPClient · WiFi · secrets)은 uplink_common.cpp 의 uplinkPostHeartbeat, 태스크 배선은
//   enrich_uplink_main.cpp 에 있다. 여기엔 상수 · 본문 조립 · 보고 여부 판정만 둔다.
//
// ★ 여기에 없는 것
//   - 재시도 (주기마다 새로 보고할 뿐 실패분을 다시 보내지 않는다)
//   - WiFi 재연결 · 끊김 알림 (범위 밖 — 별도 결정)
//   - 문자열 이스케이프 (우리 값엔 `"` · `\` · 제어문자가 없다 → 있으면 조립 실패로 드러낸다)
#pragma once

#include <inttypes.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

// ── 주기 ─────────────────────────────────────────────────────────────────────
// 보고 주기 30초. ★ 잠정.
// 근거: 사용자 결정(2026-10-06) · 서버 꺼짐 판정 DEVICE_OFFLINE_AFTER 90초 = 보고 3회분
//       (연속 2회 유실까지 켜짐 유지 — 서버 constants.py 주석과 같은 산술. 호스트 테스트가 텍스트로 대조).
// 재판정 트리거: 서버 DEVICE_OFFLINE_AFTER 변경 / 부스 리허설에서 헛 「꺼짐」 관측.
constexpr uint32_t HB_PERIOD_MS = 30000;

// 런타임 대조 실험 전용 짧은 주기 훅. platformio.ini 는 건드리지 않고 PLATFORMIO_BUILD_FLAGS 로만 주입한다
// (예: PLATFORMIO_BUILD_FLAGS="-DHB_PERIOD_MS_TEST=2000"). 정의하지 않으면 HB_PERIOD_MS 고정 —
// 「값이 없을 때 고르는」 폴백이 아니라 빌드 시점에 둘 중 하나로 정해진다. 어느 쪽인지는 [BOOT] 줄이 찍는다.
#ifdef HB_PERIOD_MS_TEST
constexpr uint32_t HB_RUN_PERIOD_MS = (uint32_t)(HB_PERIOD_MS_TEST);
static_assert(HB_RUN_PERIOD_MS >= 1000, "테스트 주기는 1초 이상");
#else
constexpr uint32_t HB_RUN_PERIOD_MS = HB_PERIOD_MS;
#endif

// 부팅(태스크 시작) 뒤 첫 보고까지 3초. ★ 잠정.
// 근거: 첫 보고 판정은 「태스크 시작 시점 계수 → 첫 대기 뒤 계수」가 늘었는지를 본다. 마이크 슬롯은 64ms 마다
//       적재되고, 1차 스냅샷은 링 32슬롯(2.048초)이 찬 뒤에야 가능하다 → 링이 다 찰 시간(2.048초)보다 길게 잡아
//       「켜짐」이 스냅샷 가능 시점보다 앞서지 않게 한다. 태스크는 setup 끝(마이크 태스크 · ToF init 뒤)에 생기므로
//       실제로는 그보다 여유가 더 있다.
// 재판정 트리거: 링 슬롯 수(MIC_RING_SLOTS) 변경 / 태스크 생성 위치 변경.
constexpr uint32_t HB_FIRST_DELAY_MS = 3000;

// ── HTTP 타임아웃 ────────────────────────────────────────────────────────────
// connect 3초 · 무응답 3초. ★ 잠정.
// 근거: 주기(30초)보다 충분히 작다. 이 태스크는 loop 와 별개라 값이 1차 · 2차 발송 판정에 영향을 주지 않는다 —
//       바뀌는 것은 「망이 나쁠 때 보고 1회가 얼마나 늦게 실패하는가」뿐이다.
// 재판정 트리거: 보드 실측에서 정상 망인데 http<0 이 반복될 때.
//
// 설치된 코어(Arduino-ESP32 2.0.17) 실물:
//   - setConnectTimeout(int32_t ms) → WiFiClient::connect 의 select() 대기(ms 그대로). DNS 는 포함 안 됨
//     (SPIKE_SERVER_HOST 는 IP 리터럴 형식 — secrets.h.template).
//   - setTimeout(uint16_t ms) → 헤더 대기 루프는 ms 그대로 비교하지만, 소켓 SO_SNDTIMEO/SO_RCVTIMEO 와
//     Stream 읽기 타임아웃엔 (ms + 500) / 1000 초로 **반올림**돼 들어간다 → 1000 의 배수만 쓴다(아래 assert).
// ⚠️ 상수 전달됨 ≠ 총 경과 제한: connect · 쓰기 · 읽기가 **각자** 이 값을 받는다. 헤더 대기 루프는 줄을 받을
//    때마다 시계를 다시 잰다(서버가 한 줄씩 흘리면 무한정 늘 수 있다 — 우리 서버는 한 번에 보낸다).
constexpr uint32_t HB_CONNECT_TIMEOUT_MS = 3000;
constexpr uint32_t HB_HTTP_TIMEOUT_MS    = 3000;
static_assert(HB_HTTP_TIMEOUT_MS % 1000 == 0 && HB_HTTP_TIMEOUT_MS <= 65535,
              "setTimeout 은 uint16_t ms 이고 소켓엔 초 단위 반올림으로 들어간다");

// 최악 총 경과(산술 — HTTPClient::sendRequest 실물 경로):
//   connect 1회 + 쓰기 2회(헤더 · 본문, 각 「쓰기 0바이트 → delay(100) → 1회 더」 = 2 × SNDTIMEO + 100)
//   + 첫 응답 줄까지 무응답 1회.  = 3,000 + 2 × (2 × 3,000 + 100) + 3,000 = 18,200ms
// 이 산술이 결정 주기보다 짧아야 보고가 밀려 겹치지 않는다(테스트 훅 주기에는 걸지 않는다 — 대조 실험용).
constexpr uint32_t HB_WORST_CASE_MS =
    HB_CONNECT_TIMEOUT_MS + 2u * (2u * HB_HTTP_TIMEOUT_MS + 100u) + HB_HTTP_TIMEOUT_MS;
static_assert(HB_WORST_CASE_MS < HB_PERIOD_MS, "보고 1회 최악 경과가 주기보다 길다");

// ── fw 이름 (서버 규칙 = 영숫자 · 밑줄 1 ~ 32자, routes.py _FW_PATTERN) ───────────
// env 이름 그대로 — 대시보드 · DB 에서 어느 빌드가 보고했는지 가린다.
constexpr const char* HB_FW_ENRICH_UPLINK   = "enrich_uplink";
constexpr const char* HB_FW_ENRICH_AUTOTRIG = "enrich_autotrig";

// 보드 빌드는 gnu++11 이라 constexpr 루프를 못 쓴다 → 두 상수 검사는 호스트 테스트가 한다.
inline bool hbFwValid(const char* s) {
  if (s == nullptr) return false;
  size_t n = 0;
  for (; s[n] != '\0'; ++n) {
    const char c = s[n];
    const bool ok = (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_';
    if (!ok || n >= 32) return false;
  }
  return n >= 1;
}

// ── RSSI 유효 범위 ──────────────────────────────────────────────────────────
// 서버는 −127 ~ 0 을 받는다. 0 은 빼고 −127 ~ −1 만 보낸다:
//   WiFi.RSSI()(2.0.17 실물)는 모드 NULL 이거나 esp_wifi_sta_get_ap_info 가 실패하면 **0** 을 돌려준다 —
//   「연결 확인」과 「RSSI 읽기」 사이에 끊기면 0 이 나올 수 있고, 서버는 0 ≥ −70 이라 「강함」으로 보인다.
constexpr int32_t HB_RSSI_MIN = -127;
constexpr int32_t HB_RSSI_MAX = -1;

// ── 보고 여부 판정 ──────────────────────────────────────────────────────────
enum HbVerdict : uint8_t {
  HB_SEND = 0,
  HB_SKIP_WIFI,
  HB_SKIP_RSSI,
  HB_SKIP_MIC,
};

inline const char* hbVerdictName(HbVerdict v) {
  switch (v) {
    case HB_SEND:      return "send";
    case HB_SKIP_WIFI: return "wifi";
    case HB_SKIP_RSSI: return "rssi";
    case HB_SKIP_MIC:  return "mic";
  }
  return "?";
}

// 판정 순서 = WiFi → RSSI → 마이크. 사유 로그가 「가장 앞선 원인」을 가리키게 한다
// (WiFi 가 끊겼는데 skip=mic 로 찍히면 원인을 잘못 읽는다).
// 마이크 「늘었다」 = micNow != micLast. uint32 슬롯 계수 랩어라운드 = 2^32 × 64ms ≈ 8.7년 → 무시.
inline HbVerdict hbDecide(bool wifiUp, int32_t rssi, uint32_t micNow, uint32_t micLast) {
  if (!wifiUp) return HB_SKIP_WIFI;
  if (rssi < HB_RSSI_MIN || rssi > HB_RSSI_MAX) return HB_SKIP_RSSI;
  if (micNow == micLast) return HB_SKIP_MIC;
  return HB_SEND;
}

// ── JSON 본문 조립 ──────────────────────────────────────────────────────────
// 필드 순서 = 서버 계약 표기 순(device_id · rssi · uptime_s · fw · enrich_sent), 공백 없는 압축 JSON.
// 반환 = 쓴 길이. 잘리거나 문자열에 `"` · `\` · 제어문자(< 0x20)가 있으면 **0** + out[0] = '\0'
// (부분 본문을 내보내지 않는다). cap 너머는 쓰지 않는다(snprintf).
inline bool hbJsonSafe(const char* s) {
  if (s == nullptr) return false;
  for (; *s != '\0'; ++s) {
    const unsigned char c = (unsigned char)*s;
    if (c == '"' || c == '\\' || c < 0x20) return false;
  }
  return true;
}

inline size_t hbBuildJson(char* out, size_t cap, const char* deviceId, int32_t rssi, uint32_t uptimeS,
                          const char* fw, uint32_t enrichSent) {
  if (out == nullptr || cap == 0) return 0;
  out[0] = '\0';
  if (!hbJsonSafe(deviceId) || !hbJsonSafe(fw)) return 0;
  const int n = snprintf(out, cap,
                         "{\"device_id\":\"%s\",\"rssi\":%" PRId32 ",\"uptime_s\":%" PRIu32
                         ",\"fw\":\"%s\",\"enrich_sent\":%" PRIu32 "}",
                         deviceId, rssi, uptimeS, fw, enrichSent);
  if (n < 0 || (size_t)n >= cap) {
    out[0] = '\0';
    return 0;
  }
  return (size_t)n;
}

// 본문 버퍼 크기. 최악 = 고정 59B + device_id + fw(32) + rssi(4) + uptime(10) + enrich_sent(10).
// UPLINK_DEVICE_ID 24자 기준 139B → 192B. 넘치면 조립 실패(0)로 드러난다.
constexpr size_t HB_JSON_BUF_BYTES = 192;
