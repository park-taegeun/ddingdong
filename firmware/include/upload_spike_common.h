// 띵동 firmware - ESP32 오디오 업로드 지연 스파이크 공통 헤더 (7/9, 카테고리 6.2)
//
// 목적: 마이크 없이 합성 int16 PCM(16kHz mono)을 PSRAM에서 조립해 로컬 Flask
// POST /api/v1/detect(PR #24, multipart 수신 배선)에 실어 보내고 왕복 지연을 실측.
// PR #22가 지목한 "1차 5초 병목 = ML 아님, 후보 = 오디오 업로드+카카오 왕복"의
// 업로드 절반을 숫자로 만드는 스파이크(측정 전용, 서버/ML 코드 무관).
//
// ★ 측정 성격 = 하한값: 같은 WiFi(핫스팟, 카테고리 23) LAN 위 평문 HTTP.
// 프로덕션(HTTPS→EC2)은 TLS 핸드셰이크 + 인터넷 왕복이 가산되어 이보다 느림.

#pragma once

#include <Arduino.h>
#include <WiFiClient.h>

// === 오디오 합성 상수 (카테고리 6.2 A안 계약과 동일 포맷: int16 LE, 16kHz mono) ===
// PR #24 검증에 쓰인 합성 사인톤과 동일 파라미터(440Hz / amplitude 0.5, 재현성).
constexpr uint32_t AUDIO_SAMPLE_RATE_HZ  = 16000;
constexpr float     AUDIO_SINE_FREQ_HZ    = 440.0f;
constexpr float     AUDIO_SINE_AMPLITUDE  = 0.5f;   // 풀스케일 대비 -6dB (클리핑 방지)

// [bonus] 크기 스윕 3종 (bytes) — int16 mono @16kHz: 32KB≈1s / 64KB≈2s / 128KB≈4s.
// PSRAM 오디오 버퍼는 스윕 최대치(128KB)로 1회 할당 후 앞부분을 잘라 재사용(복사 없음).
constexpr size_t AUDIO_SWEEP_SIZES_BYTES[] = {32000, 64000, 128000};
constexpr size_t AUDIO_SWEEP_COUNT         = 3;
constexpr size_t AUDIO_MAX_BYTES           = 128000;  // 스윕 최대 = PSRAM 오디오 버퍼 상한
constexpr size_t AUDIO_BASE_BYTES          = 64000;   // 본 지연 측정(Phase 1) 고정 크기 = PR #24와 동일

// === multipart 조립 상수 (카테고리 6.2 A안: client_request_id/device_id form field + audio file part) ===
constexpr const char* MULTIPART_BOUNDARY       = "ddingdongUploadSpikeBoundary7F3A9";
constexpr const char* AUDIO_FIELD_NAME         = "audio";  // 서버 AUDIO_FILE_FIELD(constants.py)와 동일값
constexpr const char* AUDIO_CONTENT_TYPE       = "application/octet-stream";
constexpr const char* SPIKE_DEVICE_ID          = "ddingdong-upload-spike-001";  // env:poc DEVICE_ID와 분리(rate limit 격리)
// head(필드 3개 boilerplate, 실측 최대 ≈392B) + tail("--boundary--\r\n", ≈42B) 여유폭.
constexpr size_t      MULTIPART_OVERHEAD_BYTES = 640;

// === 측정 상수 ===
constexpr uint8_t  SPIKE_ITERATIONS      = 14;    // 권장 12~15
constexpr uint32_t SPIKE_INTERVAL_MS     = 6000;  // device rate limit(카테고리 6.1, 5초/1회) 회피 여유
constexpr uint8_t  SWEEP_REPS_PER_SIZE   = 3;      // [bonus] 크기별 반복 횟수
constexpr uint32_t HTTP_TIMEOUT_MS       = 10000;

// === WiFi 상수 (env:poc main.cpp와 동일 타임아웃/폴링 값 재사용, 카테고리 23) ===
constexpr uint32_t WIFI_PRIMARY_TIMEOUT_MS  = 15000;
constexpr uint32_t WIFI_FALLBACK_TIMEOUT_MS = 15000;
constexpr uint32_t WIFI_POLL_INTERVAL_MS    = 250;
constexpr uint32_t SERIAL_BOOT_DELAY_MS     = 200;

// === API ===
uint8_t *allocPsramBuffer(size_t bytes, const char *tag);
void synthesizeSineInt16(int16_t *out, size_t sampleCount, float freqHz, float amplitude, uint32_t sampleRateHz);
bool connectWifiBlocking();

size_t buildMultipartBody(uint8_t *dest, size_t destCapacity,
                           const char *clientRequestId, const char *deviceId,
                           const uint8_t *audioBytes, size_t audioLen);

struct SpikeResult {
  bool     ok;            // status == 201
  int      httpStatus;    // HTTPClient 반환값 (음수 = 전송 실패, errorToString 참조)
  uint32_t roundTripMs;   // POST 직전(혹은 connect 직전) ~ 응답 수신까지
  uint32_t connectMs;     // measureConnectSeparately=true일 때만 유효, 아니면 0
};

// measureConnectSeparately=true 시 TCP connect를 별도로 미리 수행해 connectMs를 분리 측정
// (HTTPClient::connect()는 이미 connected()인 소켓을 재사용 — 공식 헤더 확인, 학습 15).
SpikeResult postAudioSpike(const char *host, uint16_t port,
                            const char *clientRequestId,
                            const uint8_t *audioBytes, size_t audioLen,
                            uint8_t *bodyBuf, size_t bodyBufCapacity,
                            bool measureConnectSeparately);
