// 띵동 firmware - upload_spike 공통 함수 구현 (7/9, 카테고리 6.2)
//
// PSRAM 할당 / 합성 사인톤 / multipart 바디 조립 / WiFi 연결(최소 자체 구현,
// env:poc main.cpp는 §7 제약상 리팩토링 금지 — 재사용은 secrets.h 매크로만) /
// POST + 왕복 지연 측정. 출처(학습 15): 실제 설치된 헤더로 시그니처 확인
// (framework-arduinoespressif32 HTTPClient.h L216 `POST(uint8_t*, size_t)`,
//  esp_heap_caps.h L67 `heap_caps_malloc`, esp_timer.h L198 `esp_timer_get_time`).

#include "upload_spike_common.h"

#include <math.h>
#include <string.h>

#include <HTTPClient.h>
#include <WiFi.h>

#include "esp_heap_caps.h"
#include "esp_timer.h"
#include "secrets.h"

uint8_t *allocPsramBuffer(size_t bytes, const char *tag) {
  uint8_t *buf = static_cast<uint8_t *>(heap_caps_malloc(bytes, MALLOC_CAP_SPIRAM));
  if (buf == nullptr) {
    Serial.printf("[PSRAM] alloc FAILED tag=%s bytes=%u\n", tag, static_cast<unsigned>(bytes));
  } else {
    Serial.printf("[PSRAM] alloc OK tag=%s bytes=%u\n", tag, static_cast<unsigned>(bytes));
  }
  return buf;
}

void synthesizeSineInt16(int16_t *out, size_t sampleCount, float freqHz, float amplitude, uint32_t sampleRateHz) {
  for (size_t i = 0; i < sampleCount; ++i) {
    const float t = static_cast<float>(i) / static_cast<float>(sampleRateHz);
    const float v = amplitude * sinf(TWO_PI * freqHz * t);
    out[i] = static_cast<int16_t>(v * 32767.0f);
  }
}

// env:poc(main.cpp)와 달리 이벤트 기반 재연결/backoff 없음 — 1회 스파이크 측정용
// 최소 블로킹 연결. WiFi 자격증명 매크로(secrets.h)만 재사용, 코드는 자체 작성
// (§7: env:poc 리팩토링 금지 → main.cpp 흡수 대신 최소 재구현, 자체검증 ② 명시).
static bool tryConnect(const char *ssid, const char *password, uint32_t timeoutMs) {
  Serial.printf("[WIFI] Trying SSID=%s (timeout=%ums)\n", ssid, static_cast<unsigned>(timeoutMs));
  WiFi.begin(ssid, password);
  const uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && (millis() - start) < timeoutMs) {
    delay(WIFI_POLL_INTERVAL_MS);
  }
  if (WiFi.status() != WL_CONNECTED) {
    Serial.printf("[WIFI] Timeout connecting to SSID=%s\n", ssid);
    return false;
  }
  return true;
}

bool connectWifiBlocking() {
  WiFi.mode(WIFI_STA);
  if (tryConnect(WIFI_PRIMARY_SSID, WIFI_PRIMARY_PASSWORD, WIFI_PRIMARY_TIMEOUT_MS)) {
    Serial.printf("[WIFI] Connected via PRIMARY (SSID=%s, RSSI=%d, IP=%s)\n",
                  WiFi.SSID().c_str(), static_cast<int>(WiFi.RSSI()), WiFi.localIP().toString().c_str());
    return true;
  }
  if (tryConnect(WIFI_FALLBACK_SSID, WIFI_FALLBACK_PASSWORD, WIFI_FALLBACK_TIMEOUT_MS)) {
    Serial.printf("[WIFI] Connected via FALLBACK (SSID=%s, RSSI=%d, IP=%s)\n",
                  WiFi.SSID().c_str(), static_cast<int>(WiFi.RSSI()), WiFi.localIP().toString().c_str());
    return true;
  }
  Serial.println("[WIFI] Both SSIDs failed (u.FL 외장 안테나 장착 확인, 카테고리 32)");
  return false;
}

size_t buildMultipartBody(uint8_t *dest, size_t destCapacity,
                           const char *clientRequestId, const char *deviceId,
                           const uint8_t *audioBytes, size_t audioLen) {
  char head[512];
  const int headLen = snprintf(
      head, sizeof(head),
      "--%s\r\n"
      "Content-Disposition: form-data; name=\"client_request_id\"\r\n\r\n"
      "%s\r\n"
      "--%s\r\n"
      "Content-Disposition: form-data; name=\"device_id\"\r\n\r\n"
      "%s\r\n"
      "--%s\r\n"
      "Content-Disposition: form-data; name=\"%s\"; filename=\"audio.pcm\"\r\n"
      "Content-Type: %s\r\n\r\n",
      MULTIPART_BOUNDARY, clientRequestId, MULTIPART_BOUNDARY, deviceId,
      MULTIPART_BOUNDARY, AUDIO_FIELD_NAME, AUDIO_CONTENT_TYPE);

  char tail[64];
  const int tailLen = snprintf(tail, sizeof(tail), "\r\n--%s--\r\n", MULTIPART_BOUNDARY);

  if (headLen < 0 || static_cast<size_t>(headLen) >= sizeof(head) || tailLen < 0 ||
      static_cast<size_t>(tailLen) >= sizeof(tail)) {
    Serial.println("[MULTIPART] head/tail snprintf 잘림 — 버퍼 크기 재검토 필요");
    return 0;
  }

  const size_t total = static_cast<size_t>(headLen) + audioLen + static_cast<size_t>(tailLen);
  if (total > destCapacity) {
    Serial.printf("[MULTIPART] body build FAILED (need=%u cap=%u)\n",
                  static_cast<unsigned>(total), static_cast<unsigned>(destCapacity));
    return 0;
  }

  size_t cursor = 0;
  memcpy(dest + cursor, head, headLen);
  cursor += headLen;
  memcpy(dest + cursor, audioBytes, audioLen);
  cursor += audioLen;
  memcpy(dest + cursor, tail, tailLen);
  cursor += tailLen;
  return cursor;
}

SpikeResult postAudioSpike(const char *host, uint16_t port,
                            const char *clientRequestId,
                            const uint8_t *audioBytes, size_t audioLen,
                            uint8_t *bodyBuf, size_t bodyBufCapacity,
                            bool measureConnectSeparately) {
  SpikeResult result{false, -1, 0, 0};

  const size_t bodyLen = buildMultipartBody(bodyBuf, bodyBufCapacity, clientRequestId,
                                             SPIKE_DEVICE_ID, audioBytes, audioLen);
  if (bodyLen == 0) {
    return result;
  }

  WiFiClient client;
  const int64_t t0 = esp_timer_get_time();

  if (measureConnectSeparately) {
    if (!client.connect(host, port)) {
      Serial.println("[SPIKE] TCP connect failed");
      return result;
    }
    result.connectMs = static_cast<uint32_t>((esp_timer_get_time() - t0) / 1000);
  }

  HTTPClient https;
  https.setTimeout(HTTP_TIMEOUT_MS);
  const String url = String("http://") + host + ":" + String(port) + "/api/v1/detect";
  if (!https.begin(client, url)) {
    Serial.println("[SPIKE] HTTPClient begin() failed");
    return result;
  }
  https.addHeader("Content-Type", String("multipart/form-data; boundary=") + MULTIPART_BOUNDARY);
  https.addHeader("Authorization", String("Bearer ") + SPIKE_DEVICE_TOKEN);

  const int status = https.POST(bodyBuf, bodyLen);
  const int64_t tEnd = esp_timer_get_time();

  result.httpStatus = status;
  result.roundTripMs = static_cast<uint32_t>((tEnd - t0) / 1000);
  result.ok = (status == 201);

  if (status > 0) {
    https.getString();  // 응답 바디 drain (커넥션 정리)
  } else {
    Serial.printf("[SPIKE] POST failed: %s\n", HTTPClient::errorToString(status).c_str());
  }
  https.end();
  return result;
}
