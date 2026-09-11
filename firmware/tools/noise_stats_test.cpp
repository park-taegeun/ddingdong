// noise_stats.h 호스트 검산 — 실제 firmware/include/noise_stats.h 를 그대로 include 한다(복사 아님).
//   c++ -std=c++17 -Wall -I firmware/include -o /tmp/nst firmware/tools/noise_stats_test.cpp && /tmp/nst
// 합성 2.048초 스냅샷(32768 샘플)에 클램프 버스트를 **알려진 위치·길이**로 심고 개수·간격·rms 를 단언한다.
// negative control 3종(간격 off-by-one / 경계 32767 vs 32766 / 제외 rms 분모)은
// MIC_NOISEPROBE_RUNBOOK.md 7절 참조 — 각각 반드시 실패해야 한다.
#include <cassert>
#include <cmath>
#include <cstdio>
#include <cstring>

#include "noise_stats.h"

static int checks = 0;
#define CHECK(x) do { assert(x); checks++; } while (0)

constexpr uint32_t SR = 16000;
constexpr size_t   N  = 32768;
static int16_t  snap[N];
static int32_t  raw[N];
static uint32_t bursts[NOISE_MAX_BURSTS];

// 결정론 배경 잡음 ±300 (LCG). 실측 조용한 rms 95~119 와 같은 자릿수.
static void fill_quiet() {
  uint32_t x = 12345u;
  for (size_t i = 0; i < N; ++i) {
    x = x * 1664525u + 1013904223u;
    snap[i] = (int16_t)((int32_t)(x >> 20) % 601 - 300);
    raw[i]  = (int32_t)snap[i] << 14;          // tz ≥ 6 (실제로는 ≥14) 인 "정상" raw
  }
}

// 참조 rms (double) — 분석기의 정수 isqrt 와 ±1 이내 일치해야 한다.
static int32_t ref_rms(bool exclude_clip) {
  double acc = 0; size_t cnt = 0;
  for (size_t i = 0; i < N; ++i) {
    if (exclude_clip && noiseIsClip(snap[i])) continue;
    acc += (double)snap[i] * snap[i]; cnt++;
  }
  return cnt ? (int32_t)std::sqrt(acc / cnt) : 0;
}

int main() {
  // ── T0 빈 입력 / 클램프 없음 ──
  {
    NoiseSnapStats z = noiseAnalyzeI16(nullptr, 0, SR, bursts, NOISE_MAX_BURSTS);
    CHECK(z.n == 0 && z.clip_n == 0 && z.burst_n == 0 && z.rms_all == 0 && z.rms_excl == 0);

    fill_quiet();
    NoiseSnapStats q = noiseAnalyzeI16(snap, N, SR, bursts, NOISE_MAX_BURSTS);
    CHECK(q.n == N && q.clip_n == 0 && q.burst_n == 0 && q.gap_n == 0 && q.first_clip_idx == 0);
    CHECK(q.peak == 300 || q.peak == 299);            // LCG 범위 상한 근처
    CHECK(std::abs(q.rms_all - ref_rms(false)) <= 1);
    CHECK(q.rms_excl == q.rms_all);                   // 제외할 것이 없으면 동일
  }

  // ── T1 경계: 32766 / -32767 은 클램프가 아니다 (NC-2 표적) + 버스트 경계 정확히 16 샘플 (NC-1b 표적) ──
  {
    fill_quiet();
    snap[100] = 32766; snap[200] = -32767; snap[300] = 32767; snap[316] = -32768;
    NoiseSnapStats st = noiseAnalyzeI16(snap, N, SR, bursts, NOISE_MAX_BURSTS);
    CHECK(st.clip_n == 2 && st.clip_pos == 1 && st.clip_neg == 1);
    CHECK(st.first_clip_idx == 300);
    CHECK(st.peak == 32768);
    CHECK(st.burst_n == 2 && st.gap_n == 1);          // 거리 16 = NOISE_BURST_GAP_SAMPLES → 새 버스트
    CHECK(st.burst_len_max == 1);
    CHECK(st.gap_min_ms == 1 && st.gap_max_ms == 1);  // 16 샘플 = 1.0ms
  }

  // ── T2 알려진 버스트: ToF 주기 배수 3개 + 비배수 1개 ──
  //   시작 인덱스: 1000 / +1067(66.7ms) / +1067 / +500(31.25ms 비배수) / +2134(133.4ms = 2배)
  //   각 버스트 = 연속 5 샘플 클램프(+, -, +, -, +) = 25개 + 버스트1 꼬리 1개(아래) → clip_n = 26
  {
    fill_quiet();
    const uint32_t starts[5] = {1000, 2067, 3134, 3634, 5768};
    for (uint32_t s : starts) {
      for (uint32_t k = 0; k < 5; ++k) snap[s + k] = (k % 2 == 0) ? 32767 : -32768;
    }
    // 같은 버스트 안 15 샘플 간격(< 16) 은 새 버스트가 아니어야 한다
    snap[1000 + 4 + 15] = 32767;   // 인덱스 1019 → 버스트 1 에 흡수, len = 20
    NoiseSnapStats st = noiseAnalyzeI16(snap, N, SR, bursts, NOISE_MAX_BURSTS);
    CHECK(st.clip_n == 26 && st.clip_pos == 16 && st.clip_neg == 10);
    CHECK(st.burst_n == 5);
    CHECK(st.burst_len_max == 20);
    CHECK(st.first_clip_idx == 1000);
    for (int i = 0; i < 5; ++i) CHECK(bursts[i] == starts[i]);
    CHECK(st.gap_n == 4);
    // 간격 ms: 1067→67, 1067→67, 500→31, 2134→133
    CHECK(st.gap_min_ms == 31);
    CHECK(st.gap_max_ms == 133);
    CHECK(st.gap_mode_ms == 67);
    CHECK(st.gap_tof_mult_n == 3);                    // 67, 67, 133 (31 은 아님)
    CHECK(std::abs(st.rms_all  - ref_rms(false)) <= 1);
    CHECK(std::abs(st.rms_excl - ref_rms(true))  <= 1);
    CHECK(st.rms_excl < 400 && st.rms_all > 500);     // 클램프 26개가 전체 rms 를 크게 끌어올린다
  }

  // ── T3 전부 클램프 → rms_excl = 0 (분모 0 회피) ──
  {
    for (size_t i = 0; i < N; ++i) snap[i] = 32767;
    NoiseSnapStats st = noiseAnalyzeI16(snap, N, SR, bursts, NOISE_MAX_BURSTS);
    CHECK(st.clip_n == N && st.burst_n == 1 && st.burst_len_max == N);
    CHECK(st.rms_all == 32767 && st.rms_excl == 0);
  }

  // ── T3b 절반 클램프 / 절반 상수 1000 → rms_excl 은 정확히 1000 (NC-3 제외 rms 분모 표적) ──
  //   ★ T2 의 ±1 허용 비교는 클램프 26/32768(0.08%)이라 분모를 n 으로 바꿔도 rms 가 0.08% 만 움직여
  //     통과한다(2026-09-11 NC-3 1차 미검출 = 판별력 부족, 카테고리 20 「미검출의 판정」). 분모 오류가
  //     √2 배로 드러나는 50% 클램프 케이스를 두어 **구조로** 잡는다.
  {
    for (size_t i = 0; i < N; ++i) snap[i] = (i < N / 2) ? (int16_t)-32768 : (int16_t)1000;
    NoiseSnapStats st = noiseAnalyzeI16(snap, N, SR, bursts, NOISE_MAX_BURSTS);
    CHECK(st.clip_n == N / 2 && st.clip_neg == N / 2 && st.burst_n == 1 && st.burst_len_max == N / 2);
    CHECK(st.rms_excl == 1000);                       // 분모 n 이면 707
    CHECK(st.rms_all > 23000 && st.rms_all < 23200);  // sqrt((2^15)²/2 + 1000²/2) ≈ 23181
  }

  // ── T4 버스트 상한(cap) 초과: burst_n 은 계속 세고, gap 은 기록분만 ──
  {
    fill_quiet();
    for (uint32_t b = 0; b < 300; ++b) snap[b * 100] = 32767;   // 300 버스트, 간격 100 샘플
    NoiseSnapStats st = noiseAnalyzeI16(snap, N, SR, bursts, NOISE_MAX_BURSTS);
    CHECK(st.burst_n == 300 && st.clip_n == 300);
    CHECK(st.gap_n == NOISE_MAX_BURSTS - 1);
    CHECK(st.gap_min_ms == 6 && st.gap_max_ms == 6 && st.gap_mode_ms == 6);
    // burst_idx 없이 호출해도 개수는 같고 간격만 0
    NoiseSnapStats nb = noiseAnalyzeI16(snap, N, SR, nullptr, 0);
    CHECK(nb.burst_n == 300 && nb.gap_n == 0 && nb.gap_min_ms == 0);
  }

  // ── T5 주기 배수 판정 도우미 ──
  {
    CHECK(noiseIsPeriodMultiple(67, 667, 10));
    CHECK(noiseIsPeriodMultiple(133, 667, 10));
    CHECK(noiseIsPeriodMultiple(200, 667, 10));
    CHECK(!noiseIsPeriodMultiple(31, 667, 10));
    CHECK(!noiseIsPeriodMultiple(100, 667, 10));      // 1.5배
    CHECK(!noiseIsPeriodMultiple(0, 667, 10));        // k=0
    CHECK(noiseSamplesToMs(1067, SR) == 67 && noiseSamplesToMs(16, SR) == 1 && noiseSamplesToMs(7, SR) == 0);
  }

  // ── T6 raw 비트 패턴 ──
  {
    fill_quiet();
    // bad 아님: 정상 큰 값이지만 int16 범위 안 (32767<<14 = 536854528)
    raw[10] = 32767 << 14;
    // bad 4 종:
    raw[20] = 0x40000F40;          // 상위 비트 1개 뒤집힘, low6 = 0 → iso_hi
    raw[30] = 0x40000F41;          // + low6 ≠ 0
    raw[40] = (int32_t)0xBFFF0F00; // 음수 쪽 뒤집힘(부호 1, 30비트 0 뒤 1 8개) → iso_hi, low6 = 0
    raw[50] = 0x7FFFFFC0;          // 진짜 큰 값(포화 음향) → iso 아님, low6 = 0
    NoiseRawPattern p = noiseAnalyzeRaw(raw, N, 14);
    CHECK(p.n == N && p.bad_n == 4);
    CHECK(p.low6_nz_n == 1);
    CHECK(p.iso_hi_n == 3);                       // 0x40000F40 / 0x40000F41 / 0xBFFF0F00
    CHECK(p.example[0] == 0x40000F40u && p.example[1] == 0x40000F41u &&
          p.example[2] == 0xBFFF0F00u && p.example[3] == 0x7FFFFFC0u);
    CHECK(p.tz_all == 0);          // 0x...41 이 하위 비트를 세웠다
    raw[30] = 0x40000F40;
    CHECK(noiseAnalyzeRaw(raw, N, 14).tz_all == 6);   // 이제 전부 6비트 정렬 = 6.3 실측값
    CHECK(noiseIsolatedHighBit(0x40000000u) && !noiseIsolatedHighBit(0x00000F40u) &&
          !noiseIsolatedHighBit(0x7FFFFFC0u) && noiseIsolatedHighBit(0xBFFF0000u));
  }

  // ── T7 시각 상관: ToF 읽기 창 [start,end] 까지 거리 (랩어라운드 포함) ──
  {
    const uint32_t st[2] = {1000u, 5000u};
    const uint32_t en[2] = {3000u, 5500u};
    CHECK(noiseUsToWindow(2000u, st, en, 2) == 0u);        // 창 안
    CHECK(noiseUsToWindow(1000u, st, en, 2) == 0u);        // 경계 = 안
    CHECK(noiseUsToWindow(5500u, st, en, 2) == 0u);
    CHECK(noiseUsToWindow(4000u, st, en, 2) == 1000u);     // 두 창 사이 정중앙
    CHECK(noiseUsToWindow(4990u, st, en, 2) == 10u);
    CHECK(noiseUsToWindow(5600u, st, en, 2) == 100u);
    CHECK(noiseUsToWindow(500u,  st, en, 2) == 500u);
    CHECK(noiseUsToWindow(0xFFFFFFF0u, st, en, 2) == 1016u); // 랩어라운드 건너 첫 창 시작까지
    CHECK(noiseUsToWindow(0u, nullptr, nullptr, 0) == UINT32_MAX);
    CHECK(noiseAbsDiffUs(5u, 0xFFFFFFFFu) == 6u && noiseAbsDiffUs(0xFFFFFFFFu, 5u) == 6u);
  }

  std::printf("noise_stats_test: %d checks OK\n", checks);
  return 0;
}
