// 띵동 firmware - ESP32 HTTPS(TLS) 업로드 지연 재실측 공통 헤더 (7/29, 카테고리 6.2)
//
// 7/28 upload_spike(평문 HTTP, p95 1043ms, TCP connect가 지연 절반)는 frozen —
// 본 하네스는 그 구조를 복제해 WiFiClientSecure(TLS)로 재실측한다. 체인의 92%인
// 업로드 구간에 프로덕션(HTTPS, 카테고리 6.1)이 얹는 TLS 핸드셰이크 가산분이 목적.
//
// ★ Step 1 설치 core 실측 근거 (2026-07-29, 학습 15 — 헤더 4단계 grep):
//   - Arduino-ESP32 core 2.0.17 (esp_arduino_version.h MAJOR=2/MINOR=0/PATCH=17.
//     PIO 패키지 버전 "3.20017.241212"의 "3." 접두는 PIO 규약 — core 3.x 아님)
//   - mbedTLS 2.28.7 (tools/sdk/esp32s3/include/mbedtls/.../version.h)
//   - TLS 1.3 미지원 확정: sdkconfig TLS1_2=y까지만, config.h의 1.3은
//     "//#define MBEDTLS_SSL_PROTO_TLS1_3_EXPERIMENTAL" 주석 처리(미컴파일)
//   → 측정 = TLS 1.2 / 2-RTT 핸드셰이크. 프로덕션 클라이언트도 동일 core이므로
//     실전(nginx+Let's Encrypt)도 1.2/2-RTT 협상 = 본 측정이 프로덕션 대표.
//   - setBufferSizes() 없음(ESP8266 전용 API) — TLS I/O 버퍼는 sdkconfig
//     MBEDTLS_SSL_MAX_CONTENT_LEN=16384 빌드 고정. heap 부족 시 축소 튜닝 불가 →
//     본 하네스는 heap 워터마크 로깅으로 관찰만 (F8 대체).
//
// ★ 콜드 핸드셰이크 = 헤드라인 (F3): 실이벤트 cadence(수분~수시간)라 프로덕션은
// 매번 콜드 → 이터마다 WiFiClientSecure 지역 객체 신규 생성(세션 재개 원천 차단.
// core 2.x ssl_client는 세션 save/restore API 자체가 부재 — 헤더 실측).

#pragma once

#include <Arduino.h>

// === 오디오 합성 상수 (7/28과 동일 — A안 계약: int16 LE, 16kHz mono, 440Hz/-6dB) ===
constexpr uint32_t AUDIO_SAMPLE_RATE_HZ  = 16000;
constexpr float     AUDIO_SINE_FREQ_HZ    = 440.0f;
constexpr float     AUDIO_SINE_AMPLITUDE  = 0.5f;

// 크기 스윕 없음(7/28에서 크기 무관 확인) — 대표 64KB/2초 고정.
constexpr size_t AUDIO_BYTES = 64000;

// === multipart 조립 상수 (A안 프레이밍 동일 — 실전과 같은 바디 구조로 POST) ===
constexpr const char* MULTIPART_BOUNDARY       = "ddingdongUploadTlsBoundary9C4E1";
constexpr const char* AUDIO_FIELD_NAME         = "audio";
constexpr const char* AUDIO_CONTENT_TYPE       = "application/octet-stream";
constexpr const char* SPIKE_DEVICE_ID          = "ddingdong-upload-tls-001";
constexpr size_t      MULTIPART_OVERHEAD_BYTES = 640;

// === 측정 상수 ===
constexpr uint8_t  TLS_SPIKE_ITERATIONS  = 14;     // 7/28과 동일 N
constexpr uint32_t TLS_SPIKE_INTERVAL_MS = 6000;   // ≥6초 간격 (7/28 컨벤션 유지)
constexpr uint8_t  RESUME_PROBE_REPS     = 3;      // [부기록] back-to-back 세션 재개 관찰
constexpr uint32_t TLS_HANDSHAKE_TIMEOUT_S = 15;   // setHandshakeTimeout 단위 = 초 (기본 120s)
constexpr uint32_t HTTP_TIMEOUT_MS       = 10000;

// === WiFi 상수 (7/28 upload_spike_common.h와 동일값, 카테고리 23) ===
constexpr uint32_t WIFI_PRIMARY_TIMEOUT_MS  = 15000;
constexpr uint32_t WIFI_FALLBACK_TIMEOUT_MS = 15000;
constexpr uint32_t WIFI_POLL_INTERVAL_MS    = 250;
constexpr uint32_t SERIAL_BOOT_DELAY_MS     = 200;

// === 이터레이션 결과 (F1 분해: tcp_connect / tls_handshake / post) ===
struct TlsIterResult {
  bool     tcpOk;            // 평문 TCP 프로브 성공 (F2 — 같은 5001 포트에 접속만)
  bool     tlsOk;            // WiFiClientSecure 풀 연결(TCP+TLS) 성공
  bool     httpOk;           // HTTP 200 수신 (F7 2층)
  int      httpStatus;       // HTTPClient 반환값 (음수 = 전송 실패)
  int      sslError;         // 핸드셰이크 실패 시 mbedTLS 리턴코드 (성공 시 0)
  char     sslErrBuf[96];    // mbedtls_strerror 문자열 (lastError)
  uint32_t tcpConnectMs;     // 평문 TCP connect (프로브)
  uint32_t secureConnectMs;  // secure connect 전체 (자체 TCP + TLS 핸드셰이크)
  uint32_t tlsHandshakeMs;   // Δ_TLS = secureConnectMs - tcpConnectMs (동일 순간 RF 조건)
  uint32_t postMs;           // multipart POST + 응답 수신
  uint32_t totalMs;          // secureConnectMs + postMs (실체인 1회분. 프로브 TCP는 계측용이라 미포함)
  uint32_t heapBefore;       // free heap, 이터 시작 시점
  uint32_t heapMinWatermark; // 핸드셰이크 직후 since-boot 최저 free heap (피크 사용 근사)
  uint32_t heapAfter;        // free heap, 이터 종료 시점
  uint32_t psramFree;        // PSRAM 잔량, 이터 종료 시점
  const char *tlsVersion;    // 협상 TLS 버전 (mbedtls_ssl_get_version, F4)
  const char *cipher;        // 협상 cipher suite (mbedtls_ssl_get_ciphersuite, F4)
};

// === API (7/28 upload_spike_common와 동형 분리: 헬퍼=common / 페이즈·통계=main) ===
uint8_t *allocPsramBuffer(size_t bytes, const char *tag);
void synthesizeSineInt16(int16_t *out, size_t sampleCount, float freqHz, float amplitude, uint32_t sampleRateHz);
bool connectWifiBlocking();

size_t buildMultipartBody(uint8_t *dest, size_t destCapacity,
                           const char *clientRequestId, const char *deviceId,
                           const uint8_t *audioBytes, size_t audioLen);

// 콜드 1이터 실행: [평문 TCP 프로브 → close] → [신규 WiFiClientSecure 풀 연결 → POST].
// doPost=false면 핸드셰이크까지만 (RESUME-PROBE 부기록용).
TlsIterResult runTlsColdIteration(const char *host, uint16_t port,
                                   const char *clientRequestId,
                                   const uint8_t *audioBytes, size_t audioLen,
                                   uint8_t *bodyBuf, size_t bodyBufCapacity,
                                   bool doPost);
