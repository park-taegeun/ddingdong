// 띵동 firmware - ESP32 HTTPS(TLS) 업로드 지연 재실측 (7/29, 카테고리 6.2)
//
// 7/28 PoC-(27) 평문 HTTP 실측(p95 1043ms, TCP connect가 지연 절반) 위에 프로덕션
// (HTTPS, 카테고리 6.1: Let's Encrypt ECDSA P-256 + setInsecure())이 얹는 TLS
// 핸드셰이크 가산분을 실측한다. 타겟 = 로컬 tls_probe_server.py(ECDSA P-256, :5001,
// transport 전용 — 실 /detect auth/파싱 미복제).
//
// ★ 헤드라인 = 진짜 콜드 핸드셰이크: 이터마다 WiFiClientSecure 신규 생성 (F3).
//   실이벤트 cadence(수분~수시간)라 프로덕션은 매번 콜드가 정상 경로.
// ★ 측정 = TLS 1.2 / 2-RTT (Step 1 설치 core 실측 — upload_spike_tls_common.h 주석).
//   1순위 가치 = 신뢰성(핸드셰이크 성공률·HTTP 200률 2층) + 메모리(heap 워터마크).
//   지연은 예산 여유(≈3.87초)라 2순위.
//
// 실행: setup() 1회 구간에서 전체 측정을 순차 완료 후 idle (loop()는 대기만).

#include <Arduino.h>
#include <WiFi.h>

#include "secrets.h"
#include "upload_spike_tls_common.h"

static uint8_t *g_audioBuf = nullptr;  // PSRAM, 64KB 사인톤 원본
static uint8_t *g_bodyBuf = nullptr;   // PSRAM, multipart 조립 버퍼(오디오+오버헤드)
static uint32_t g_iterationSeq = 0;

static String nextClientRequestId() {
  g_iterationSeq++;
  return String("tls-") + String(static_cast<unsigned long>(millis())) + "-" + String(g_iterationSeq);
}

// 표본 수(≤14)가 작아 O(n^2) 삽입정렬로 충분 (7/28 컨벤션 동일).
static void printStats(const char *label, uint32_t *values, size_t n) {
  if (n == 0) {
    Serial.printf("[STATS] %s: 표본 0건 (전건 실패)\n", label);
    return;
  }
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

static void printIterLine(const char *tag, uint8_t iterNo, const TlsIterResult &r) {
  Serial.printf("[%s] iter=%02u tcp=%u tls_hs=%u conn=%u post=%u total=%u http=%d ver=%s cipher=%s "
                "heap(before/min/after)=%u/%u/%u psram=%u %s\n",
                tag, static_cast<unsigned>(iterNo),
                static_cast<unsigned>(r.tcpConnectMs), static_cast<unsigned>(r.tlsHandshakeMs),
                static_cast<unsigned>(r.secureConnectMs), static_cast<unsigned>(r.postMs),
                static_cast<unsigned>(r.totalMs), r.httpStatus, r.tlsVersion, r.cipher,
                static_cast<unsigned>(r.heapBefore), static_cast<unsigned>(r.heapMinWatermark),
                static_cast<unsigned>(r.heapAfter), static_cast<unsigned>(r.psramFree),
                (r.tlsOk && (!r.httpOk ? r.postMs == 0 : true)) ? (r.httpOk ? "PASS" : "TLS-ONLY") : "FAIL");
  if (!r.tlsOk && r.tcpOk) {
    Serial.printf("[%s]   └ mbedTLS err=%d (-0x%04X) %s\n", tag, r.sslError,
                  static_cast<unsigned>(-r.sslError), r.sslErrBuf);
  }
}

// Phase 1: 콜드 핸드셰이크 N회 — 이터마다 [평문 TCP 프로브] + [신규 secure 풀 연결 + POST].
static void runTlsColdSpike() {
  Serial.println("\n[TLS] === Phase 1: 콜드 TLS 핸드셰이크 + 64KB multipart POST (N회) ===");
  uint32_t tcpMs[TLS_SPIKE_ITERATIONS];
  uint32_t hsMs[TLS_SPIKE_ITERATIONS];
  uint32_t connMs[TLS_SPIKE_ITERATIONS];
  uint32_t postMs[TLS_SPIKE_ITERATIONS];
  uint32_t totalMs[TLS_SPIKE_ITERATIONS];
  size_t okN = 0;
  uint8_t tlsOkCount = 0;
  uint8_t httpOkCount = 0;
  uint32_t heapMinSeen = UINT32_MAX;

  for (uint8_t i = 0; i < TLS_SPIKE_ITERATIONS; ++i) {
    const String reqId = nextClientRequestId();
    const TlsIterResult r = runTlsColdIteration(SPIKE_TLS_SERVER_HOST, SPIKE_TLS_SERVER_PORT,
                                                 reqId.c_str(), g_audioBuf, AUDIO_BYTES,
                                                 g_bodyBuf, AUDIO_BYTES + MULTIPART_OVERHEAD_BYTES,
                                                 true);
    printIterLine("TLS", i + 1, r);
    if (r.tlsOk) tlsOkCount++;
    if (r.httpOk) httpOkCount++;
    if (r.heapMinWatermark != 0 && r.heapMinWatermark < heapMinSeen) heapMinSeen = r.heapMinWatermark;
    // 통계는 풀 성공(핸드셰이크+HTTP 200) 이터만 — 타임아웃 값 오염 방지, 실패는 성공률에 반영.
    if (r.tlsOk && r.httpOk) {
      tcpMs[okN] = r.tcpConnectMs;
      hsMs[okN] = r.tlsHandshakeMs;
      connMs[okN] = r.secureConnectMs;
      postMs[okN] = r.postMs;
      totalMs[okN] = r.totalMs;
      okN++;
    }
    if (i + 1 < TLS_SPIKE_ITERATIONS) delay(TLS_SPIKE_INTERVAL_MS);
  }

  Serial.println("\n[TLS] === Phase 1 요약 ===");
  Serial.printf("[TLS] 핸드셰이크 성공 %u/%u | HTTP 200 %u/%u (F7 2층)\n",
                static_cast<unsigned>(tlsOkCount), static_cast<unsigned>(TLS_SPIKE_ITERATIONS),
                static_cast<unsigned>(httpOkCount), static_cast<unsigned>(TLS_SPIKE_ITERATIONS));
  printStats("tcp_connect_ms(평문 프로브)", tcpMs, okN);
  printStats("tls_handshake_ms(Δ_TLS)", hsMs, okN);
  printStats("secure_connect_ms(TCP+TLS)", connMs, okN);
  printStats("post_ms(64KB multipart)", postMs, okN);
  printStats("total_ms(conn+post)", totalMs, okN);
  Serial.printf("[TLS] heap 최저 워터마크(전 이터): %u bytes\n",
                heapMinSeen == UINT32_MAX ? 0 : static_cast<unsigned>(heapMinSeen));
}

// Phase 2 [부기록]: back-to-back 연속 핸드셰이크 — 세션 재개 여부 관찰 (헤드라인 아님).
// core 2.x ssl_client는 세션 save/restore API 부재(헤더 실측) → 기대 = 재개 없음
// (시간 콜드와 유사). 이봉성(뚜렷한 고속군 출현) 발견 시에만 flag.
static void runResumeProbe() {
  Serial.println("\n[TLS] === Phase 2 (부기록): back-to-back 핸드셰이크 — 세션 재개 관찰 ===");
  for (uint8_t i = 0; i < RESUME_PROBE_REPS; ++i) {
    const TlsIterResult r = runTlsColdIteration(SPIKE_TLS_SERVER_HOST, SPIKE_TLS_SERVER_PORT,
                                                 "resume-probe", nullptr, 0, nullptr, 0,
                                                 false);
    printIterLine("RESUME-PROBE", i + 1, r);
  }
  Serial.println("[TLS] 판독: 위 tls_hs가 Phase 1 콜드 대비 뚜렷이 짧으면 세션 재개 의심(이봉성 flag),");
  Serial.println("[TLS]        유사하면 기대대로 재개 없음 — 콜드 헤드라인과 분리 기록할 것.");
}

void setup() {
  Serial.begin(115200);
  delay(SERIAL_BOOT_DELAY_MS);
  Serial.println("\n[BOOT] ddingdong upload_spike_tls firmware (HTTPS/TLS 업로드 재실측)");
  Serial.println("[BOOT] 측정 = TLS 1.2 / 2-RTT (설치 core 2.0.17 + mbedTLS 2.28.7 실측 — 1.3 미지원).");
  Serial.println("[BOOT] 프로덕션 클라이언트도 동일 core → 실전도 1.2/2-RTT 협상 = 본 측정이 대표값.");
  Serial.println("[BOOT] ★ 판정 기준 (F5 — flash 후 이 3개로 즉시 판정):");
  Serial.println("[BOOT]   ① TLS 핸드셰이크 성공률 >= 13/14 (마지막 요약의 '핸드셰이크 성공')");
  Serial.println("[BOOT]   ② heap OOM 없음: 최저 워터마크 > 40KB + 측정 중 리셋/재부팅 0회");
  Serial.println("[BOOT]   ③ total p95 + 프로덕션 가산(2-RTT×EC2_RTT+DNS 1회) 기준,");
  Serial.println("[BOOT]      7/28 HTTP p95 1043ms 대비 Δ_TLS 가산 후에도 5초 예산 여유(≈3.87s) 내");
  Serial.println("[BOOT] ※ cipher가 TLS-ECDHE-ECDSA-* 인지 확인 (F4 — ECDSA P-256 cert 실반영 검증)");

  g_audioBuf = allocPsramBuffer(AUDIO_BYTES, "audio_sine");
  g_bodyBuf = allocPsramBuffer(AUDIO_BYTES + MULTIPART_OVERHEAD_BYTES, "multipart_body");
  if (g_audioBuf == nullptr || g_bodyBuf == nullptr) {
    Serial.println("[BOOT] PSRAM 할당 실패 — 측정 중단");
    return;
  }

  synthesizeSineInt16(reinterpret_cast<int16_t *>(g_audioBuf), AUDIO_BYTES / sizeof(int16_t),
                       AUDIO_SINE_FREQ_HZ, AUDIO_SINE_AMPLITUDE, AUDIO_SAMPLE_RATE_HZ);
  Serial.printf("[BOOT] 사인톤 합성 완료: samples=%u bytes=%u\n",
                static_cast<unsigned>(AUDIO_BYTES / sizeof(int16_t)), static_cast<unsigned>(AUDIO_BYTES));

  if (!connectWifiBlocking()) {
    Serial.println("[BOOT] WiFi 연결 실패 — 측정 중단 (prereq: UPLOAD_TEST_RUNBOOK.md 배선/핫스팟 확인)");
    return;
  }

  Serial.printf("[BOOT] 타겟: https://%s:%u (tls_probe_server.py — firmware/tools, ECDSA P-256)\n",
                SPIKE_TLS_SERVER_HOST, static_cast<unsigned>(SPIKE_TLS_SERVER_PORT));

  runTlsColdSpike();
  runResumeProbe();

  Serial.println("\n[TLS] === 측정 종료 (loop()는 idle) ===");
}

void loop() {
  delay(1000);
}
