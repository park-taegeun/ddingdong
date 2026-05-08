// ddingdong PoC firmware - WiFi + HTTPS 더미 테스트 (5/8, PoC-(3) Day 2)
//
// 검증 목표:
//   1. WPA2-Personal 통합 환경 (집 WiFi + 모바일 핫스팟 동일 프로토콜)
//   2. 런타임 SSID fallback (PRIMARY 실패 시 FALLBACK 자동 전환)
//   3. HTTPS POST (httpbin.org/post)에 setInsecure 사용 시 정상 동작
//
// 보안 한계: WiFiClientSecure::setInsecure()는 TLS 인증서 검증을 비활성화함.
//   PoC 단계에서만 허용. 11주차에 Let's Encrypt 도입으로 교체 예정.

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "secrets.h"

// === 매직 넘버 const화 ===
constexpr uint32_t WIFI_PRIMARY_TIMEOUT_MS    = 15000;
constexpr uint32_t WIFI_FALLBACK_TIMEOUT_MS   = 15000;
constexpr uint32_t WIFI_RETRY_BASE_MS         = 1000;
constexpr uint8_t  WIFI_RETRY_MAX_COUNT       = 5;
constexpr uint32_t WIFI_RECONNECT_COOLDOWN_MS = 5000;
constexpr uint32_t WIFI_POLL_INTERVAL_MS      = 250;
constexpr uint32_t HTTP_TIMEOUT_MS            = 10000;
constexpr uint32_t POST_INTERVAL_MS           = 30000;
constexpr size_t   HTTP_RESPONSE_PREVIEW_BYTES = 100;
constexpr uint32_t LOOP_YIELD_MS              = 10;
constexpr uint32_t SERIAL_BOOT_DELAY_MS       = 200;
constexpr const char* HTTP_TARGET_URL         = "https://httpbin.org/post";
constexpr const char* DEVICE_ID               = "ddingdong-poc-001";

// === SSID 식별자 (Serial 출력용) ===
enum class WifiSlot : uint8_t { NONE = 0, PRIMARY = 1, FALLBACK = 2 };

// === 상태 변수 ===
// g_reconnect_pending: 이벤트 콜백(별도 스레드)과 메인 루프 양쪽에서 접근하므로 volatile.
// g_last_slot: 메인 루프에서만 변경 (콜백은 flag만 set).
static volatile bool g_reconnect_pending      = false;
static WifiSlot      g_last_slot              = WifiSlot::NONE;
static uint32_t      g_last_post_ms           = 0;
static uint32_t      g_last_reconnect_attempt_ms = 0;
static uint32_t      g_event_seq              = 0;

// === 전방 선언 ===
static const char* slotName(WifiSlot slot);
static void        wifiEventHandler(arduino_event_id_t event, arduino_event_info_t info);
static bool        tryWifiConnect(const char* ssid, const char* password, uint32_t timeout_ms);
static bool        setupWifiWithFallback();
static bool        reconnectLastSlot();
static String      buildJsonPayload(uint32_t event_seq);
static bool        sendHttpsPost(uint32_t event_seq);

static const char* slotName(WifiSlot slot) {
  switch (slot) {
    case WifiSlot::PRIMARY:  return "PRIMARY";
    case WifiSlot::FALLBACK: return "FALLBACK";
    case WifiSlot::NONE:
    default:                 return "NONE";
  }
}

// 이벤트 콜백은 별도 스레드에서 실행되므로 flag만 설정하고 무거운 작업은 loop()에서.
static void wifiEventHandler(arduino_event_id_t event, arduino_event_info_t info) {
  (void)info;
  if (event == ARDUINO_EVENT_WIFI_STA_DISCONNECTED) {
    g_reconnect_pending = true;
  }
}

static bool tryWifiConnect(const char* ssid, const char* password, uint32_t timeout_ms) {
  Serial.printf("[WIFI] Trying SSID=%s (timeout=%ums)\n", ssid, (unsigned)timeout_ms);
  WiFi.disconnect(false, false);  // wifioff=false, eraseap=false (NVS AP 보존)
  WiFi.begin(ssid, password);
  const uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && (millis() - start) < timeout_ms) {
    delay(WIFI_POLL_INTERVAL_MS);
  }
  if (WiFi.status() == WL_CONNECTED) {
    return true;
  }
  Serial.printf("[WIFI] Timeout connecting to SSID=%s\n", ssid);
  return false;
}

static void logConnected(const char* tag, WifiSlot slot) {
  Serial.printf("[WIFI] %s via %s (SSID=%s, RSSI=%d, IP=%s)\n",
                tag, slotName(slot),
                WiFi.SSID().c_str(), (int)WiFi.RSSI(),
                WiFi.localIP().toString().c_str());
}

static bool setupWifiWithFallback() {
  for (uint8_t retry = 0; retry < WIFI_RETRY_MAX_COUNT; ++retry) {
    if (retry > 0) {
      const uint32_t backoff = WIFI_RETRY_BASE_MS * (1u << (retry - 1));
      Serial.printf("[WIFI] Retry #%u after %ums backoff\n", (unsigned)retry, (unsigned)backoff);
      delay(backoff);
    }
    if (tryWifiConnect(WIFI_PRIMARY_SSID, WIFI_PRIMARY_PASSWORD, WIFI_PRIMARY_TIMEOUT_MS)) {
      g_last_slot = WifiSlot::PRIMARY;
      logConnected("Connected", WifiSlot::PRIMARY);
      return true;
    }
    if (tryWifiConnect(WIFI_FALLBACK_SSID, WIFI_FALLBACK_PASSWORD, WIFI_FALLBACK_TIMEOUT_MS)) {
      g_last_slot = WifiSlot::FALLBACK;
      logConnected("Connected", WifiSlot::FALLBACK);
      return true;
    }
  }
  g_last_slot = WifiSlot::NONE;
  Serial.println("[WIFI] All retries failed");
  return false;
}

// 마지막 성공 슬롯부터 한 번씩만 시도 (ping-pong 방지).
// 실패 시 g_last_slot=NONE으로 두고 다음 disconnect 이벤트에서 재시도.
static bool reconnectLastSlot() {
  const bool tryPrimaryFirst = (g_last_slot != WifiSlot::FALLBACK);
  const char* firstSsid  = tryPrimaryFirst ? WIFI_PRIMARY_SSID  : WIFI_FALLBACK_SSID;
  const char* firstPass  = tryPrimaryFirst ? WIFI_PRIMARY_PASSWORD  : WIFI_FALLBACK_PASSWORD;
  const char* secondSsid = tryPrimaryFirst ? WIFI_FALLBACK_SSID : WIFI_PRIMARY_SSID;
  const char* secondPass = tryPrimaryFirst ? WIFI_FALLBACK_PASSWORD : WIFI_PRIMARY_PASSWORD;
  const WifiSlot firstSlot  = tryPrimaryFirst ? WifiSlot::PRIMARY  : WifiSlot::FALLBACK;
  const WifiSlot secondSlot = tryPrimaryFirst ? WifiSlot::FALLBACK : WifiSlot::PRIMARY;

  if (tryWifiConnect(firstSsid, firstPass, WIFI_PRIMARY_TIMEOUT_MS)) {
    g_last_slot = firstSlot;
    logConnected("Reconnected", firstSlot);
    return true;
  }
  if (tryWifiConnect(secondSsid, secondPass, WIFI_FALLBACK_TIMEOUT_MS)) {
    g_last_slot = secondSlot;
    logConnected("Reconnected", secondSlot);
    return true;
  }
  g_last_slot = WifiSlot::NONE;
  Serial.println("[WIFI] Reconnect failed (will retry on next disconnect event)");
  return false;
}

static String buildJsonPayload(uint32_t event_seq) {
  // ArduinoJson 7: JsonDocument는 heap 할당 + elastic capacity.
  JsonDocument doc;
  doc["device_id"] = DEVICE_ID;
  doc["event_id"]  = event_seq;
  doc["uptime_ms"] = millis();
  doc["rssi"]      = (int)WiFi.RSSI();
  doc["slot"]      = slotName(g_last_slot);
  doc["ssid"]      = WiFi.SSID();
  String out;
  serializeJson(doc, out);
  return out;
}

static bool sendHttpsPost(uint32_t event_seq) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[HTTP] Skip POST (WiFi not connected)");
    return false;
  }
  WiFiClientSecure client;
  client.setInsecure();  // PoC 한정: TLS 인증서 검증 OFF. 11주차 Let's Encrypt로 교체 예정.

  HTTPClient https;
  https.setTimeout(HTTP_TIMEOUT_MS);
  if (!https.begin(client, HTTP_TARGET_URL)) {
    Serial.println("[HTTP] begin() failed");
    return false;
  }
  https.addHeader("Content-Type", "application/json");

  const String payload = buildJsonPayload(event_seq);
  Serial.printf("[JSON] Payload: %s\n", payload.c_str());

  bool ok = false;
  const int status = https.POST(payload);
  if (status > 0) {
    const String body = https.getString();
    const size_t preview_len = body.length() > HTTP_RESPONSE_PREVIEW_BYTES
                                 ? HTTP_RESPONSE_PREVIEW_BYTES
                                 : body.length();
    const String preview = body.substring(0, preview_len);
    Serial.printf("[HTTP] status=%d body[0..%u]=%s\n",
                  status, (unsigned)preview_len, preview.c_str());
    ok = (status >= 200 && status < 300);
  } else {
    Serial.printf("[HTTP] POST failed: %s\n",
                  HTTPClient::errorToString(status).c_str());
  }
  https.end();  // 메모리 누수 방지 (HTTPClient 내부 리소스 해제)
  return ok;
}

void setup() {
  Serial.begin(115200);
  delay(SERIAL_BOOT_DELAY_MS);
  Serial.println("\n[BOOT] ddingdong PoC firmware (WiFi + HTTPS dummy test)");

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(false);  // core 자동 재연결 OFF, 우리가 직접 슬롯 관리
  WiFi.onEvent(wifiEventHandler, ARDUINO_EVENT_WIFI_STA_DISCONNECTED);

  if (!setupWifiWithFallback()) {
    Serial.println("[BOOT] WiFi setup failed at boot — loop will retry on disconnect events");
  }

  // 첫 POST를 즉시 트리거하기 위해 last_post_ms를 과거로 설정
  g_last_post_ms = millis() - POST_INTERVAL_MS;
}

void loop() {
  const uint32_t now = millis();

  // 재연결: 이벤트 핸들러가 flag set, 메인 루프에서 처리 (스레드 안전).
  // cooldown으로 disconnect 폭주 시 재시도 폭주 차단.
  if (g_reconnect_pending && (now - g_last_reconnect_attempt_ms) >= WIFI_RECONNECT_COOLDOWN_MS) {
    g_reconnect_pending = false;
    g_last_reconnect_attempt_ms = now;
    reconnectLastSlot();
  }

  // 30초 간격 POST (비블로킹: millis() 비교)
  if ((now - g_last_post_ms) >= POST_INTERVAL_MS) {
    g_last_post_ms = now;
    g_event_seq++;
    sendHttpsPost(g_event_seq);
  }

  delay(LOOP_YIELD_MS);  // CPU 양보 (FreeRTOS task 스케줄링)
}
