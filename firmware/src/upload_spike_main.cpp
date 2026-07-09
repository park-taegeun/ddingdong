// 띵동 firmware - ESP32 오디오 업로드 지연 스파이크 (7/9, 카테고리 6.2 wire 갭 실측)
//
// PR #22(6.2): ML 추론 6.74ms → 1차 5초 병목 아님, 후보 = 오디오 업로드+카카오 왕복.
// PR #24(6.2 A안): /detect가 multipart+int16 PCM 수신 배선 완료 (타겟 엔드포인트 준비).
// 본 스케치 = 마이크 없이 합성 사인톤(64KB/2초, PR #24와 동일 파라미터)을 PSRAM에서
// multipart 바디로 조립해 그 엔드포인트로 실어 보내고 왕복 지연을 실측한다.
//
// ★ 측정 = HTTP-LAN 하한값 (핫스팟 LAN, 평문 HTTP, TLS·WAN 미포함).
// 프로덕션(HTTPS→EC2)은 이보다 느림 — PR #22 "M4 하한" 정신과 동일한 성격의 숫자.
//
// 실행: setup() 1회 구간에서 전체 측정을 순차 완료 후 idle (loop()는 대기만).

#include <Arduino.h>
#include <HTTPClient.h>
#include <WiFi.h>

#include "secrets.h"
#include "upload_spike_common.h"

static uint8_t *g_audioBuf = nullptr;  // PSRAM, 스윕 최대(128KB) 사인톤 원본
static uint8_t *g_bodyBuf = nullptr;   // PSRAM, multipart 조립 버퍼(오디오+오버헤드)
static uint32_t g_iterationSeq = 0;

static String nextClientRequestId() {
  g_iterationSeq++;
  return String("spike-") + String(static_cast<unsigned long>(millis())) + "-" + String(g_iterationSeq);
}

// 표본 수(12~15)가 작아 O(n^2) 삽입정렬로 충분 — 별도 정렬 라이브러리 불필요.
static void printStats(const char *label, uint32_t *values, size_t n) {
  for (size_t i = 1; i < n; ++i) {
    const uint32_t key = values[i];
    size_t j = i;
    while (j > 0 && values[j - 1] > key) {
      values[j] = values[j - 1];
      --j;
    }
    values[j] = key;
  }
  const uint32_t minV = values[0];
  const uint32_t maxV = values[n - 1];
  const uint32_t p50 = values[n / 2];
  const size_t p95idx = static_cast<size_t>(static_cast<float>(n - 1) * 0.95f);
  const uint32_t p95 = values[p95idx];
  Serial.printf("[STATS] %s: min=%u p50=%u p95=%u max=%u (n=%u)\n",
                label, static_cast<unsigned>(minV), static_cast<unsigned>(p50),
                static_cast<unsigned>(p95), static_cast<unsigned>(maxV), static_cast<unsigned>(n));
}

static void runLatencySpike() {
  Serial.println("\n[SPIKE] === Phase 1: 왕복 지연 (N회, 64KB 고정) ===");
  uint32_t rtts[SPIKE_ITERATIONS];
  uint8_t okCount = 0;

  for (uint8_t i = 0; i < SPIKE_ITERATIONS; ++i) {
    const String reqId = nextClientRequestId();
    const SpikeResult r = postAudioSpike(SPIKE_SERVER_HOST, SPIKE_SERVER_PORT, reqId.c_str(),
                                          g_audioBuf, AUDIO_BASE_BYTES, g_bodyBuf,
                                          AUDIO_MAX_BYTES + MULTIPART_OVERHEAD_BYTES, false);
    rtts[i] = r.roundTripMs;
    if (r.ok) okCount++;
    Serial.printf("[SPIKE] iter=%u id=%s status=%d rtt_ms=%u %s\n",
                  static_cast<unsigned>(i + 1), reqId.c_str(), r.httpStatus,
                  static_cast<unsigned>(r.roundTripMs), r.ok ? "PASS" : "FAIL");
    if (i + 1 < SPIKE_ITERATIONS) delay(SPIKE_INTERVAL_MS);
  }

  Serial.printf("[SPIKE] 201 성공 %u/%u\n", static_cast<unsigned>(okCount), static_cast<unsigned>(SPIKE_ITERATIONS));
  printStats("round_trip_ms", rtts, SPIKE_ITERATIONS);
}

// [bonus] 32/64/128KB 스윕 — A안(int16 64KB) vs base64(85KB) 등 트레이드오프 정량화용 ms/KB.
static void runSizeSweep() {
  Serial.println("\n[SPIKE] === Phase 2 (bonus): 크기 스윕 32/64/128KB ===");
  for (size_t s = 0; s < AUDIO_SWEEP_COUNT; ++s) {
    const size_t sizeBytes = AUDIO_SWEEP_SIZES_BYTES[s];
    uint32_t reps[SWEEP_REPS_PER_SIZE];
    for (uint8_t r = 0; r < SWEEP_REPS_PER_SIZE; ++r) {
      const String reqId = nextClientRequestId();
      const SpikeResult res = postAudioSpike(SPIKE_SERVER_HOST, SPIKE_SERVER_PORT, reqId.c_str(),
                                              g_audioBuf, sizeBytes, g_bodyBuf,
                                              AUDIO_MAX_BYTES + MULTIPART_OVERHEAD_BYTES, false);
      reps[r] = res.roundTripMs;
      Serial.printf("[SWEEP] size=%uB rep=%u status=%d rtt_ms=%u %s\n",
                    static_cast<unsigned>(sizeBytes), static_cast<unsigned>(r + 1), res.httpStatus,
                    static_cast<unsigned>(res.roundTripMs), res.ok ? "PASS" : "FAIL");
      delay(SPIKE_INTERVAL_MS);
    }
    uint32_t sum = 0;
    for (uint8_t r = 0; r < SWEEP_REPS_PER_SIZE; ++r) sum += reps[r];
    const float avgMs = static_cast<float>(sum) / SWEEP_REPS_PER_SIZE;
    const float msPerKb = avgMs / (static_cast<float>(sizeBytes) / 1024.0f);
    Serial.printf("[SWEEP] size=%uB avg_ms=%.1f ms_per_kb=%.2f\n", static_cast<unsigned>(sizeBytes), avgMs, msPerKb);
  }
}

// [bonus] TCP connect vs (body upload + 응답 대기) 분해.
// HTTPClient::connect()는 이미 connected()인 소켓이면 재연결을 skip(공식 헤더 확인,
// HTTPClient.cpp L1126) → WiFiClient를 미리 connect()해 넘기면 그 구간만 분리 측정 가능.
// esp_http_client 이벤트 훅 전환은 안정성 우선 원칙(§5 Step6)상 미채택 — 사유는 리포트에 명시.
static void runConnectDecomposition() {
  Serial.println("\n[SPIKE] === Phase 3 (bonus): TCP connect vs POST 왕복 분해 ===");
  const String reqId = nextClientRequestId();
  const SpikeResult r = postAudioSpike(SPIKE_SERVER_HOST, SPIKE_SERVER_PORT, reqId.c_str(),
                                        g_audioBuf, AUDIO_BASE_BYTES, g_bodyBuf,
                                        AUDIO_MAX_BYTES + MULTIPART_OVERHEAD_BYTES, true);
  const uint32_t postOnlyMs = r.roundTripMs - r.connectMs;
  Serial.printf("[SPIKE] connect_ms=%u post_incl_wait_ms=%u total_ms=%u status=%d %s\n",
                static_cast<unsigned>(r.connectMs), static_cast<unsigned>(postOnlyMs),
                static_cast<unsigned>(r.roundTripMs), r.httpStatus, r.ok ? "PASS" : "FAIL");
}

void setup() {
  Serial.begin(115200);
  delay(SERIAL_BOOT_DELAY_MS);
  Serial.println("\n[BOOT] ddingdong upload_spike firmware (합성 PCM multipart POST 지연 실측)");
  Serial.println("[BOOT] \xe2\x98\x85 측정=HTTP-LAN 하한값. 프로덕션(HTTPS/WAN)은 TLS+인터넷 지연이 가산되어 더 느림.");

  g_audioBuf = allocPsramBuffer(AUDIO_MAX_BYTES, "audio_sine");
  g_bodyBuf = allocPsramBuffer(AUDIO_MAX_BYTES + MULTIPART_OVERHEAD_BYTES, "multipart_body");
  if (g_audioBuf == nullptr || g_bodyBuf == nullptr) {
    Serial.println("[BOOT] PSRAM 할당 실패 — 측정 중단");
    return;
  }

  synthesizeSineInt16(reinterpret_cast<int16_t *>(g_audioBuf), AUDIO_MAX_BYTES / sizeof(int16_t),
                       AUDIO_SINE_FREQ_HZ, AUDIO_SINE_AMPLITUDE, AUDIO_SAMPLE_RATE_HZ);
  Serial.printf("[BOOT] 사인톤 합성 완료: samples=%u bytes=%u (스윕 최대, 하위 크기는 앞부분 슬라이스 재사용)\n",
                static_cast<unsigned>(AUDIO_MAX_BYTES / sizeof(int16_t)), static_cast<unsigned>(AUDIO_MAX_BYTES));

  if (!connectWifiBlocking()) {
    Serial.println("[BOOT] WiFi 연결 실패 — 측정 중단 (prereq: 외장 안테나/핫스팟 확인)");
    return;
  }

  Serial.printf("[BOOT] 타겟: http://%s:%u/api/v1/detect\n", SPIKE_SERVER_HOST, static_cast<unsigned>(SPIKE_SERVER_PORT));

  runLatencySpike();
  runSizeSweep();
  runConnectDecomposition();

  Serial.println("\n[SPIKE] === 측정 종료 (loop()는 idle) ===");
}

void loop() {
  delay(1000);
}
