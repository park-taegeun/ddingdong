// 띵동 firmware - 마이크 스냅샷 잡음 분석기 (2026-09-11 PoC-(45), env:mic_noiseprobe 전용)
//
// ★ 성격 = 진단 하네스의 **관측 계층**(decisions.md 카테고리 20 "계측 → 실측 → 판정" 분리).
//   여기엔 판정(어느 가설이 맞는가)·임계값·해결책이 0줄이다. 숫자만 낸다. 판정표는
//   MIC_NOISEPROBE_RUNBOOK.md 에 있고, 판정 주체는 사람이다.
//
// ★ 왜 Arduino 무의존 순수 헤더인가: 호스트 테스트(firmware/tools/noise_stats_test.cpp)가
//   **같은 파일을 그대로** 컴파일해 합성 스냅샷으로 검산한다(tof_judge_test.cpp 선례 = 복사 아님).
//
// ★ 클램프 판정값 32767 / -32768 의 출처 = mic_common.cpp convertMicRawToInt16 의
//   saturation 가드(`v > INT16_MAX → INT16_MAX`, `v < INT16_MIN → INT16_MIN`). 2026-09-11 실측
//   peak 32767~32768 은 정확히 이 두 값의 절댓값이다(PR #53 댓글, ToF_meta_uplink_runtime.log).
//   ⚠️ 32766 은 클램프가 아니다 — 경계 판정은 등호 2개(==)로만 한다(NC-2 대상).
#pragma once

#include <stddef.h>
#include <stdint.h>

// 클램프 샘플 사이가 이 샘플 수 미만이면 같은 "버스트"로 묶는다(16 샘플 = 1ms @16kHz).
// 근거 = 논증: I2C 1바이트(9클럭) @400kHz ≈ 22.5µs, 한 트랜잭션(수십 B) ≈ 1ms 이내 → 한 I2C
// 트랜잭션이 유발한 클램프 무리를 1개 사건으로 세기 위한 묶음 폭. 관측 편의 상수이며 판정값 아님.
constexpr uint32_t NOISE_BURST_GAP_SAMPLES = 16;

// 버스트 시작 인덱스 기록 상한. ponytail: 256 초과분은 세기만 하고 위치는 버린다(burst_n 은 계속 증가).
constexpr size_t NOISE_MAX_BURSTS = 256;

// ToF 프레임 주기 배수 판정용 기본값: 1000/15Hz = 66.67ms → 0.1ms 단위 667, 허용 ±10%.
// (tof_common.h TOF_PERIOD_MS 는 정수 나눗셈으로 66 이라 배수 검사에는 0.1ms 해상도가 필요하다)
constexpr uint32_t NOISE_TOF_PERIOD_X10_MS = 667;
constexpr uint32_t NOISE_TOF_TOL_PCT       = 10;

struct NoiseSnapStats {
  uint32_t n;              // 샘플 수
  int32_t  peak;           // max |v|                       ∈ [0, 32768]
  int32_t  rms_all;        // 전체 RMS                      ∈ [0, 32768]
  int32_t  rms_excl;       // 클램프 샘플 제외 RMS (제외 후 0개면 0)
  uint32_t clip_n;         // v == 32767 || v == -32768
  uint32_t clip_pos;       // v == 32767
  uint32_t clip_neg;       // v == -32768
  uint32_t burst_n;        // 클램프 버스트 수(간격 < NOISE_BURST_GAP_SAMPLES 이면 같은 버스트)
  uint32_t burst_len_max;  // 가장 긴 버스트의 샘플 수(첫 클램프~마지막 클램프 포함 폭)
  uint32_t first_clip_idx; // 첫 클램프 샘플 인덱스 (clip_n==0 이면 0)
  uint32_t gap_n;          // 버스트 시작→다음 버스트 시작 간격 개수 = min(burst_n, cap)-1
  uint32_t gap_min_ms;     // 간격 최소 (반올림 ms)   gap_n==0 이면 0
  uint32_t gap_mode_ms;    // 간격 최빈 (반올림 ms, 동률이면 작은 값)
  uint32_t gap_max_ms;     // 간격 최대
  uint32_t gap_tof_mult_n; // 간격이 NOISE_TOF_PERIOD_X10_MS 의 정수배(±tol) 인 개수
};

struct NoiseRawPattern {
  uint32_t n;            // 검사 샘플 수
  uint32_t bad_n;        // (raw >> shift) 가 int16 범위를 벗어나는 샘플 수 (= 가드가 클램프할 샘플)
  uint32_t low6_nz_n;    // bad 중 하위 6비트 ≠ 0 인 수. 정상 INMP441 데이터는 tz=6(하위 6비트 항상 0,
                         //   6.3 실측) → 여기가 0 이 아니면 "음향이 아닌 비트 오류" 정황
  uint32_t iso_hi_n;     // bad 중 "부호 비트 아래 첫 상이 비트 1개 뒤에 부호 비트가 8개 연속" 인 수
                         //   = 큰 값이 아니라 상위 비트 1개만 뒤집힌 모양(예 0x40000F40)
  int      tz_all;       // 전체 샘플 OR 누적의 trailing zeros ∈ [0, 32] (6.3 실측 6 과 대조)
  uint32_t example[4];   // bad 샘플 앞 4개의 raw hex (육안 확인용)
};

// ── 내부 도우미 ──────────────────────────────────────────────────────────────
inline bool noiseIsClip(int32_t v) { return v == 32767 || v == -32768; }

// 정수 제곱근 (double 미사용: 호스트/보드 동일 결과 보장). x ≤ 2^63-1.
inline int32_t noiseIsqrt64(uint64_t x) {
  if (x == 0) return 0;
  uint64_t r = 0, bit = (uint64_t)1 << 62;
  while (bit > x) bit >>= 2;
  while (bit != 0) {
    if (x >= r + bit) { x -= r + bit; r = (r >> 1) + bit; }
    else              { r >>= 1; }
    bit >>= 2;
  }
  return (int32_t)r;
}

// 샘플 간격 → 반올림 ms.  Σ 최대 = n/sr*1000 ≤ 2048ms → uint32 안전.
inline uint32_t noiseSamplesToMs(uint32_t samples, uint32_t sr_hz) {
  return (uint32_t)(((uint64_t)samples * 1000u + sr_hz / 2) / sr_hz);
}

// 간격(ms)이 주기(0.1ms 단위)의 정수배 ±tol% 인가. k = round(gap/period), k ≥ 1.
inline bool noiseIsPeriodMultiple(uint32_t gap_ms, uint32_t period_x10, uint32_t tol_pct) {
  const uint32_t g10 = gap_ms * 10u;
  const uint32_t k   = (g10 + period_x10 / 2) / period_x10;
  if (k == 0) return false;
  const uint32_t target = k * period_x10;
  const uint32_t tol    = target * tol_pct / 100u;
  return (g10 + tol >= target) && (g10 <= target + tol);
}

// ── int16 스냅샷 분석 ─────────────────────────────────────────────────────────
// burst_idx(cap 개)에 버스트 시작 샘플 인덱스를 기록한다(호출부가 ToF 읽기 시각과 상관을 볼 때 사용).
// ★ 오버플로 가드: Σv² ≤ n·32768² = 32768·2^30 = 2^45 < 2^64 → uint64 안전. gap 개수 ≤ cap-1.
inline NoiseSnapStats noiseAnalyzeI16(const int16_t* s, size_t n, uint32_t sr_hz,
                                      uint32_t* burst_idx, size_t cap) {
  NoiseSnapStats st = {};
  st.n = (uint32_t)n;
  if (n == 0 || s == nullptr) return st;

  uint64_t sq_all = 0, sq_ok = 0;
  uint32_t n_ok = 0;
  int32_t  peak = 0;
  bool     in_burst = false;
  uint32_t last_clip = 0, burst_start = 0;

  for (size_t i = 0; i < n; ++i) {
    const int32_t v = (int32_t)s[i];
    const int32_t a = (v >= 0) ? v : -v;   // int32 에서 절댓값 (|INT16_MIN| 부호 반전 회피)
    if (a > peak) peak = a;
    sq_all += (uint64_t)((int64_t)v * v);

    if (noiseIsClip(v)) {
      if (v > 0) st.clip_pos++; else st.clip_neg++;
      if (st.clip_n == 0) st.first_clip_idx = (uint32_t)i;
      st.clip_n++;
      // 버스트 경계: 직전 클램프와의 거리 ≥ GAP 이면 새 버스트
      if (!in_burst || (uint32_t)i - last_clip >= NOISE_BURST_GAP_SAMPLES) {
        if (in_burst) {
          const uint32_t len = last_clip - burst_start + 1;
          if (len > st.burst_len_max) st.burst_len_max = len;
        }
        if (burst_idx != nullptr && st.burst_n < cap) burst_idx[st.burst_n] = (uint32_t)i;
        st.burst_n++;
        burst_start = (uint32_t)i;
        in_burst    = true;
      }
      last_clip = (uint32_t)i;
    } else {
      sq_ok += (uint64_t)((int64_t)v * v);
      n_ok++;
    }
  }
  if (in_burst) {
    const uint32_t len = last_clip - burst_start + 1;
    if (len > st.burst_len_max) st.burst_len_max = len;
  }

  st.peak     = peak;
  st.rms_all  = noiseIsqrt64(sq_all / (uint64_t)n);
  st.rms_excl = (n_ok > 0) ? noiseIsqrt64(sq_ok / (uint64_t)n_ok) : 0;   // 분모 = 제외 후 개수(NC-3)

  // 간격 통계 (기록된 버스트 시작 인덱스만 대상)
  const uint32_t recorded = (burst_idx == nullptr) ? 0
                          : (st.burst_n < cap ? st.burst_n : (uint32_t)cap);
  if (recorded >= 2) {
    st.gap_n      = recorded - 1;
    st.gap_min_ms = UINT32_MAX;
    uint32_t best_cnt = 0;
    for (uint32_t g = 0; g < st.gap_n; ++g) {
      const uint32_t ms = noiseSamplesToMs(burst_idx[g + 1] - burst_idx[g], sr_hz);
      if (ms < st.gap_min_ms) st.gap_min_ms = ms;
      if (ms > st.gap_max_ms) st.gap_max_ms = ms;
      if (noiseIsPeriodMultiple(ms, NOISE_TOF_PERIOD_X10_MS, NOISE_TOF_TOL_PCT)) st.gap_tof_mult_n++;
      // 최빈값: O(gap_n²) 단순 계수. ponytail: gap_n ≤ 255 라 최대 65k 비교 = 무시 가능.
      uint32_t cnt = 0;
      for (uint32_t h = 0; h < st.gap_n; ++h) {
        if (noiseSamplesToMs(burst_idx[h + 1] - burst_idx[h], sr_hz) == ms) cnt++;
      }
      if (cnt > best_cnt || (cnt == best_cnt && ms < st.gap_mode_ms)) {
        best_cnt = cnt;
        st.gap_mode_ms = ms;
      }
    }
  }
  return st;
}

// ── raw int32 비트 패턴 요약 ─────────────────────────────────────────────────
// shift = mic_common.h MIC_RAW_TO_INT16_SHIFT(14). bad = 가드가 클램프하는 샘플(|raw>>14| > 32767).
inline bool noiseIsolatedHighBit(uint32_t u) {
  const uint32_t sign = u >> 31;
  int p = 30;
  while (p >= 0 && ((u >> p) & 1u) == sign) --p;   // 첫 상이 비트
  if (p < 8) return false;                          // 상이 비트가 너무 낮거나 없음(= 작은 값)
  for (int b = p - 1; b >= p - 8; --b) {           // 그 아래 8비트가 전부 부호 비트인가
    if (((u >> b) & 1u) != sign) return false;
  }
  return true;
}

inline NoiseRawPattern noiseAnalyzeRaw(const int32_t* raw, size_t n, int shift) {
  NoiseRawPattern p = {};
  p.n = (uint32_t)n;
  uint32_t oracc = 0;
  for (size_t i = 0; i < n; ++i) {
    const int32_t r = raw[i];
    oracc |= (uint32_t)r;
    const int32_t v = r >> shift;                      // 산술 시프트 (mic_common 동일)
    if (v > 32767 || v < -32768) {
      if (p.bad_n < 4) p.example[p.bad_n] = (uint32_t)r;
      p.bad_n++;
      if (((uint32_t)r & 0x3Fu) != 0) p.low6_nz_n++;
      if (noiseIsolatedHighBit((uint32_t)r)) p.iso_hi_n++;
    }
  }
  p.tz_all = (oracc == 0) ? 32 : __builtin_ctz(oracc);
  return p;
}

// ── 시각 상관: t_us 와 가장 가까운 ToF 읽기 창 [start, end] 까지 거리(µs) ───────
// 창 안이면 0. 밖이면 창 양끝 중 가까운 쪽까지의 거리. uint32 micros 랩어라운드 안전
// ((a-b) < 2^31 이면 a 가 뒤). n == 0 이면 UINT32_MAX(= 비교 대상 없음).
inline uint32_t noiseAbsDiffUs(uint32_t a, uint32_t b) {
  const uint32_t d = a - b;
  return (d < 0x80000000u) ? d : (b - a);
}
inline uint32_t noiseUsToWindow(uint32_t t_us, const uint32_t* start, const uint32_t* end, size_t n) {
  uint32_t best = UINT32_MAX;
  for (size_t i = 0; i < n; ++i) {
    if ((t_us - start[i]) < 0x80000000u && (end[i] - t_us) < 0x80000000u) return 0;   // 창 안
    const uint32_t d1 = noiseAbsDiffUs(t_us, start[i]);
    const uint32_t d2 = noiseAbsDiffUs(t_us, end[i]);
    const uint32_t d  = (d1 < d2) ? d1 : d2;
    if (d < best) best = d;
  }
  return best;
}
