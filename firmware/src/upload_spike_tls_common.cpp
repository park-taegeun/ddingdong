// 띵동 firmware - upload_spike_tls 공통 함수 구현 (7/29, 카테고리 6.2)
//
// 7/28 upload_spike_common.cpp(frozen)의 PSRAM 할당/사인톤/multipart/WiFi 헬퍼를
// 복제(§3 — frozen은 참조·복제만, env whitelist가 upload_spike_tls_*만 포함하므로
// 링크 공유 불가). 신규 = runTlsColdIteration: 평문 TCP 프로브 + WiFiClientSecure
// 풀 연결 + Δ_TLS 분해 + heap 워터마크 + cipher/버전 로깅.
//
// 출처(학습 15, 설치 헤더 실측):
// - WiFiClientSecure.h L31 `sslclient_context *sslclient` — protected. 버전/cipher용
//   공개 introspection API 부재 → 최소 파생(IntrospectableSecureClient)으로 ssl_ctx 노출
// - WiFiClientSecure.h L68 `lastError(char*, size_t)` / L69 `setInsecure()` /
//   L79 `setHandshakeTimeout(unsigned long)` (WiFiClientSecure.cpp L371: 단위=초, ×1000)
// - HTTPClient.h L182 `begin(WiFiClient&, String url)` — https URL + 외부 client 지원
//   (HTTPClient.cpp beginInternal: protocol=="https" 허용, _client 그대로 사용)
// - mbedtls/ssl.h `mbedtls_ssl_get_version` / `mbedtls_ssl_get_ciphersuite`

#include "upload_spike_tls_common.h"

#include <math.h>
#include <string.h>

#include <HTTPClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <mbedtls/ssl.h>

#include "esp_heap_caps.h"
#include "esp_timer.h"
#include "secrets.h"

// WiFiClientSecure의 sslclient(설치 헤더 L31)는 protected — F4(협상 버전/cipher) 로깅에
// 필요한 읽기 접근만 최소 파생으로 노출 (getPeerCertificate 같은 공개 API가 버전/cipher엔 없음).
class IntrospectableSecureClient : public WiFiClientSecure {
 public:
  const mbedtls_ssl_context *sslCtx() const { return &sslclient->ssl_ctx; }
};

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

// 7/28과 동일한 최소 블로킹 연결 (env:poc main.cpp 리팩토링 금지 → 자체 구현 복제).
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

TlsIterResult runTlsColdIteration(const char *host, uint16_t port,
                                   const char *clientRequestId,
                                   const uint8_t *audioBytes, size_t audioLen,
                                   uint8_t *bodyBuf, size_t bodyBufCapacity,
                                   bool doPost) {
  TlsIterResult r;
  memset(&r, 0, sizeof(r));
  r.httpStatus = -1;
  r.tlsVersion = "-";
  r.cipher = "-";

  // 바디는 타이밍 시작 전에 조립 (memcpy 64KB를 네트워크 구간에서 배제).
  size_t bodyLen = 0;
  if (doPost) {
    bodyLen = buildMultipartBody(bodyBuf, bodyBufCapacity, clientRequestId,
                                 SPIKE_DEVICE_ID, audioBytes, audioLen);
    if (bodyLen == 0) return r;
  }

  r.heapBefore = ESP.getFreeHeap();

  // (F2-①) 평문 TCP 프로브: 같은 5001 포트에 접속만 하고 즉시 close.
  // 서버(python ssl)는 무데이터 접속을 조용히 drop — 별도 HTTP 엔드포인트 불필요.
  {
    WiFiClient plain;
    const int64_t t0 = esp_timer_get_time();
    if (!plain.connect(host, port)) {
      Serial.println("[TLS] 평문 TCP 프로브 connect 실패");
      return r;
    }
    r.tcpConnectMs = static_cast<uint32_t>((esp_timer_get_time() - t0) / 1000);
    plain.stop();
  }
  r.tcpOk = true;

  // (F2-②/F3) 신규 WiFiClientSecure 풀 연결 — 지역 객체 = 이터마다 콜드 보장.
  // core 2.x ssl_client는 세션 save/restore API 부재(헤더 실측) → 재개 원천 불가.
  IntrospectableSecureClient secure;
  secure.setInsecure();  // 프로덕션(6.1) 동일 설정 — cert 체인 검증 skip, 핸드셰이크 자체는 풀 수행
  secure.setHandshakeTimeout(TLS_HANDSHAKE_TIMEOUT_S);

  const int64_t t1 = esp_timer_get_time();
  const int connected = secure.connect(host, port);
  r.secureConnectMs = static_cast<uint32_t>((esp_timer_get_time() - t1) / 1000);

  if (connected == 0) {
    r.sslError = secure.lastError(r.sslErrBuf, sizeof(r.sslErrBuf));
    r.heapMinWatermark = ESP.getMinFreeHeap();
    r.heapAfter = ESP.getFreeHeap();
    r.psramFree = ESP.getFreePsram();
    return r;
  }
  r.tlsOk = true;
  r.tlsHandshakeMs = (r.secureConnectMs > r.tcpConnectMs) ? (r.secureConnectMs - r.tcpConnectMs) : 0;

  // (F4) 협상 결과 — cert 타입(ECDSA P-256)이 핸드셰이크에 실반영됐는지 위상 못 박기.
  // mbedTLS 내부 정적 문자열 반환이라 연결 종료 후에도 포인터 유효.
  r.tlsVersion = mbedtls_ssl_get_version(secure.sslCtx());
  r.cipher = mbedtls_ssl_get_ciphersuite(secure.sslCtx());

  // 핸드셰이크 피크 heap 근사 = since-boot 최저 워터마크 (핸드셰이크 직후 샘플).
  r.heapMinWatermark = ESP.getMinFreeHeap();

  if (doPost) {
    HTTPClient https;
    https.setTimeout(HTTP_TIMEOUT_MS);
    const String url = String("https://") + host + ":" + String(port) + "/api/v1/detect";
    if (!https.begin(secure, url)) {
      Serial.println("[TLS] HTTPClient begin() failed");
      secure.stop();
      r.heapAfter = ESP.getFreeHeap();
      r.psramFree = ESP.getFreePsram();
      return r;
    }
    https.addHeader("Content-Type", String("multipart/form-data; boundary=") + MULTIPART_BOUNDARY);

    const int64_t t2 = esp_timer_get_time();
    const int status = https.POST(bodyBuf, bodyLen);
    r.postMs = static_cast<uint32_t>((esp_timer_get_time() - t2) / 1000);

    r.httpStatus = status;
    r.httpOk = (status == 200);  // tls_probe_server는 200 고정 (실 /detect 201과 구분 — F9 transport 전용)
    if (status > 0) {
      https.getString();  // 응답 바디 drain
    } else {
      Serial.printf("[TLS] POST failed: %s\n", HTTPClient::errorToString(status).c_str());
    }
    https.end();
  }
  secure.stop();

  r.totalMs = r.secureConnectMs + r.postMs;
  r.heapAfter = ESP.getFreeHeap();
  r.psramFree = ESP.getFreePsram();
  return r;
}
