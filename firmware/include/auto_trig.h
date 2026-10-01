// 띵동 firmware - M5-c ⓑ 자동 트리거 계산·상태 (2026-10-01 PoC-(66), env:enrich_autotrig 전용)
//
// ★ 성격 = **판정** 계층(decisions.md 카테고리 20 「계측 → 실측 → 판정」의 마지막 칸). ⓐ(mic_trigprobe ·
//   trig_line.h)가 계측, 2026-10-01 오프라인 재분석이 실측, 여기가 그 결과를 보드 규칙으로 옮긴 판정이다.
//   규칙 = 사용자 결정 2026-10-01 16:21 결정 1(V1 · N=1 · 불응기 5초 · 한 버퍼 늦게 판정) ·
//          16:38 결정 2(T=450 잠정) · 16:38 결정 4(1차 창 = 앞 8버퍼 + 트리거 버퍼부터 24버퍼, 잠정) ·
//          17:05 불응기 = 발화 기준(권고 수용).
//
// ★ 왜 Arduino 무의존 순수 헤더인가: 호스트 테스트(firmware/tools/auto_trig_test.cpp)와 오프라인 교차 대조
//   하네스가 **같은 파일을 그대로** include 해 검산한다(trig_line.h · enrich_wire.h 선례 = 복사 아님).
//   보드 의존 상수(MIC_DMA_BUF_LEN · MIC_RING_SLOTS · MIC_SAMPLE_RATE_HZ)와의 일치는 호출부
//   enrich_uplink_main.cpp 가 static_assert 로 묶는다(여기서 mic_common.h 를 include 하면 호스트 컴파일 불가).
//
// ★ V1 = 오프라인 trig_wav.py 의 V1 과 **같은 정수식**(교차 대조 (a) 불일치 0 이 증명 범위):
//   ① 클램프 = noiseIsClip(32767 / -32768) — 펌웨어 정의 하나(I10).
//      ⚠️ 원본 slice_direct.py 는 |x| ≥ 32767 이라 -32767 도 클램프로 본다. 차이는 -32767 한 값뿐이고
//      2026-10-01 입력 493파일에서 -32767 샘플 = 0개(trig_wav_analysis/summary.txt). 컨버터
//      (convertMicRawToInt16)는 saturation 가드라 -32767 을 특별히 만들지 않는다 → 보드에서도 드물다는 논증,
//      측정은 아님. 테스트 T4 가 이 차이를 고정한다.
//   ② 마스크 = 길이 ≤ AUTO_TRIG_MAX_RUN 인 클램프 런의 [시작 − HALF, 끝 + HALF). 런 위치·길이는 원본 샘플에서 본다.
//   ③ 제외 = 마스크 위치 ∪ 모든 클램프(런 길이 무관). 분모 = 남은 샘플 수, 0 이면 V1 = 0.
//   ④ 값 = isqrt(Σx² / n_ok) — 정수 나눗셈 후 정수 제곱근(math.isqrt(Σ // n) 과 같음, noiseIsqrt64 재사용).
//   ⑤ 경계 = 스트림 첫 버퍼(prev = nullptr)는 앞을 「클램프 아님」으로 본다 = 오프라인의 파일 첫머리와 같다.
//      다음 버퍼가 없거나 짧으면(next_n < 1024) 그 끝도 같은 방식 = 파일 끝과 같다.
//
// ★ 한 버퍼 늦게 판정하는 이유: 버퍼 k 의 끝 32샘플은 버퍼 k+1 첫머리 클램프의 마스크에 덮일 수 있다
//   (오프라인 실측: 버퍼 경계를 앞으로 넘는 마스크 28 · 뒤로 넘는 마스크 33, trig_wav_analysis/summary.txt).
//   그래서 k+1 이 적재된 뒤 k 를 판정한다 → 발화 순번 = k + AUTO_TRIG_FIRE_LAG.
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "noise_stats.h"   // noiseIsClip · noiseIsqrt64 재사용(복제 0, I10)

// ── 버퍼 단위(보드 값과의 일치는 호출부 static_assert) ──────────────────────
constexpr int32_t  AUTO_TRIG_BUF_SAMPLES = 1024;  // == MIC_DMA_BUF_LEN
constexpr uint32_t AUTO_TRIG_BUF_MS      = 64;    // == 1024 / 16000 s
constexpr uint32_t AUTO_TRIG_WIN_BUFS    = 32;    // == MIC_RING_SLOTS = 1차 wire 65,536 B / 2 B / 1024

// ── T = 450 (잠정, 16:38 결정 2) ────────────────────────────────────────────
// 근거(~/ddingdong-측정결과/2026-10-01/trig_window_analysis/report.md · trig_wav_analysis/report.md):
//   고정 조건 102테이크 최약 최대 V1 = 528(homespk) → ÷450 = 1.173 (home 567 → 1.260)
//   무음 최대 V1 = 417(bgC0928 04 post, 알려진 예외) → ÷450 = 0.927 / 예외 제외 335 → 0.744
//   V1 · N1 · T450 = 자극 트리거 159 / 165 · 무음 오트리거 0 (T400 에선 bgC0928 04 post 1건)
// 재판정 트리거: ① 실보드 ④런타임에서 무음 오트리거 또는 고정 조건 놓침 관측 ② 부스 리허설 ③ 보드 · 마이크 교체.
constexpr int32_t AUTO_TRIG_T = 450;
static_assert(AUTO_TRIG_T > 0 && AUTO_TRIG_T < 32767, "T 는 V1 값 범위 (0, 32767) 안이어야 한다");

// ── 1차 창 앞 버퍼 수 = 8 (잠정, 16:38 결정 4) ─────────────────────────────
// 창 = 슬롯 [k − 8, k + 24) = 6.2 B안 예시 「32슬롯 = 8(0.512s)+24(1.536s)」와 같은 구성.
// 근거(trig_window_analysis/summary_mtp.csv, 모델 J · T450 · P8): 165테이크 중 no_trig 6 · n/a 1 ·
//   분류 158 · 정답 157 · 발송 145 / 고정 조건 102 · 102 · 96.
// 재판정 트리거: T 와 같은 ①②③.
constexpr uint32_t AUTO_TRIG_PRE_BUFS = 8;
// 판정(k + FIRE_LAG) 뒤 loop 수락까지 여유가 있어야 창이 지나가지 않는다 — autoTrigDecide 의 late 참조.
static_assert(AUTO_TRIG_PRE_BUFS >= 1 && AUTO_TRIG_PRE_BUFS + 4 <= AUTO_TRIG_WIN_BUFS,
              "앞 버퍼 수는 [1, WIN−4] — 창 끝이 판정 시점 + 2슬롯보다 뒤여야 한다");

// ── 마스크 상수 (원본 = ml/curation/slice_direct.py, 펌웨어는 복제 — I11) ──────
// CLAMP_MASK_HALF_WIDTH = 32 · GLITCH_MAX_RUN = 2. 6.3(q) · 33.27(d) 글리치(고립 1샘플 + 2샘플 런,
// 클램프 +17/+18샘플 뒤 두 번째 스파이크)를 덮는 폭, #97(eb15c55). 호스트 테스트가 원본 텍스트와 대조한다.
// 재판정 트리거: 원본 slice_direct.py 값이 바뀔 때(테스트가 먼저 깨진다).
constexpr int32_t AUTO_TRIG_MASK_HALF = 32;
constexpr int32_t AUTO_TRIG_MAX_RUN   = 2;
static_assert(AUTO_TRIG_MASK_HALF >= 1 && AUTO_TRIG_MAX_RUN >= 1, "마스크 상수는 양수");
// 이웃 버퍼를 이만큼만 훑으면 충분하다: 이웃 쪽 끝에서 잘린 가짜 짧은 런([−M, −M+l), l ≤ RUN)의
// 마스크 끝 −M + l + HALF ≤ 0 ⇔ M ≥ HALF + RUN. 오른쪽도 대칭. 이보다 안쪽의 런은 길이가 정확하다.
constexpr int32_t AUTO_TRIG_SCAN_MARGIN = AUTO_TRIG_MASK_HALF + AUTO_TRIG_MAX_RUN;
static_assert(AUTO_TRIG_SCAN_MARGIN <= AUTO_TRIG_BUF_SAMPLES, "이웃 훑기 폭은 한 버퍼 이내");

// ── 불응기 = 5,000ms → 79버퍼 (16:21 결정 1, 발화 기준 = 17:05 결정) ────────────
// 근거: 6.1 rate limit = 같은 device 5초당 1회(넘으면 429). 오프라인 규칙 = 트리거 버퍼 끝 시각이
//   직전 트리거 끝 + 5000ms 이하이면 차단 → 버퍼 차 d 가 d·64 ≤ 5000 ⇔ d ≤ 78 이면 차단, 79(5,056ms)부터 허용.
// 발화 기준: 무시된(처리 중 · 링 미충전 등) 발화도 불응기를 시작시킨다 = 오프라인 규칙과 같다(교차 대조 (b)).
//   대가 = 이벤트 처리가 끝난 직후 최대 5초 동안 새 사건(노크 · 벨)을 놓칠 수 있다.
// 재판정 트리거: ④런타임 또는 부스 리허설에서 이벤트 직후 노크 · 벨 놓침이 관측될 때.
constexpr uint32_t AUTO_TRIG_REFRACTORY_MS   = 5000;
constexpr uint32_t AUTO_TRIG_REFRACTORY_BUFS = AUTO_TRIG_REFRACTORY_MS / AUTO_TRIG_BUF_MS + 1;
static_assert(AUTO_TRIG_REFRACTORY_BUFS * AUTO_TRIG_BUF_MS > AUTO_TRIG_REFRACTORY_MS &&
              (AUTO_TRIG_REFRACTORY_BUFS - 1) * AUTO_TRIG_BUF_MS <= AUTO_TRIG_REFRACTORY_MS,
              "불응기 버퍼 수 = 5,000ms 를 넘는 최소 버퍼 수(79 = 5,056ms; 78 = 4,992ms 는 5초 미만)");

// 버퍼 k 는 슬롯 k+1 이 적재된 직후(적재 순번 = k + 2) 판정된다.
constexpr uint32_t AUTO_TRIG_FIRE_LAG = 2;

// ── V1 ─────────────────────────────────────────────────────────────────────
// cur = 버퍼 k(1024샘플). prev = 버퍼 k−1(1024샘플, 스트림 첫 버퍼면 nullptr).
// next = 버퍼 k+1(next_n 샘플, 없으면 nullptr / 0). 배열 할당 0 — 스택 증가는 지역 변수 몇 개(I6).
// 런은 왼쪽부터 순서대로 찾으므로 마스크 시작(s − HALF)이 단조 증가한다 → 「지금 위치 p 까지 시작한 마스크의
// 끝 최댓값」 하나로 합집합을 판정한다(masked ⇔ p < mask_end).
inline int32_t autoTrigV1(const int16_t* prev, const int16_t* cur, const int16_t* next,
                          size_t next_n) {
  constexpr int32_t N = AUTO_TRIG_BUF_SAMPLES;
  if (cur == nullptr) return 0;
  if (next == nullptr) next_n = 0;
  const int32_t lo = (prev != nullptr) ? -AUTO_TRIG_SCAN_MARGIN : 0;
  const int32_t hi =
      N + (int32_t)((next_n < (size_t)AUTO_TRIG_SCAN_MARGIN) ? next_n : (size_t)AUTO_TRIG_SCAN_MARGIN);
  auto clipAt = [&](int32_t i) -> bool {
    const int16_t v = (i < 0) ? prev[N + i] : (i < N ? cur[i] : next[i - N]);
    return noiseIsClip(v);
  };

  int32_t q = lo;              // 런 탐색 위치
  int32_t rs = 0, rl = 0;      // 아직 반영 안 한 다음 런
  bool    have = false, done = false;
  int32_t mask_end = lo;       // 시작이 p 이하인 마스크들의 끝 최댓값
  uint64_t sq = 0;             // Σx² ≤ 1024 · 2^30 = 2^40
  uint32_t n_ok = 0;

  for (int32_t p = 0; p < N; ++p) {
    for (;;) {
      if (!have) {
        if (done) break;
        while (q < hi && !clipAt(q)) ++q;
        if (q >= hi) { done = true; break; }
        rs = q;
        while (q < hi && clipAt(q)) ++q;
        rl = q - rs;
        have = true;
      }
      if (rs - AUTO_TRIG_MASK_HALF > p) break;   // 이 런의 마스크는 아직 시작 전
      if (rl <= AUTO_TRIG_MAX_RUN && rs + rl + AUTO_TRIG_MASK_HALF > mask_end) {
        mask_end = rs + rl + AUTO_TRIG_MASK_HALF;
      }
      have = false;
    }
    const int32_t v = (int32_t)cur[p];
    if (p < mask_end || noiseIsClip(v)) continue;
    sq += (uint64_t)((int64_t)v * v);
    n_ok++;
  }
  return (n_ok > 0) ? noiseIsqrt64(sq / n_ok) : 0;
}

// ── N=1 · 불응기 ───────────────────────────────────────────────────────────
struct AutoTrigState {
  bool     fired;    // 한 번이라도 발화했는가
  uint32_t last_k;   // 마지막 발화 버퍼 번호
};

// 버퍼 k 의 V1 로 발화 여부. 발화하면 불응기를 시작한다(이후 처리 결과와 무관 = 발화 기준).
// 「v1 > T」(등호 불포함 — 오프라인 `v > T` 와 같다). k 는 매 호출 1씩 증가한다고 가정(uint32 모듈러 차).
inline bool autoTrigStep(AutoTrigState* st, uint32_t k, int32_t v1) {
  if (v1 <= AUTO_TRIG_T) return false;
  if (st->fired && k - st->last_k < AUTO_TRIG_REFRACTORY_BUFS) return false;
  st->fired  = true;
  st->last_k = k;
  return true;
}

// 1차 스냅샷을 찍을 적재 순번 = 슬롯 k+23 이 적재된 직후. 그때 링의 최근 32슬롯 = [k−8, k+24) (I1).
inline uint32_t autoTrigSnapSeq(uint32_t k) {
  return k - AUTO_TRIG_PRE_BUFS + AUTO_TRIG_WIN_BUFS;
}

// ── 수락 판단 (loop 가 부른다) ───────────────────────────────────────────────
// 판정 순서가 규칙의 일부다:
//   psram 먼저 = 버퍼가 없으면 나머지 판단이 무의미.
//   busy 를 ring · late 보다 먼저 = 처리 중에 발화해 runEvent 가 끝난 뒤에야 읽힌 요청은 late 로도 보이는데,
//     그 원인은 「처리 중」이므로 busy 로 센다(7.7(l) 재판정 트리거 (1)의 관측값이 정확해지도록).
enum AutoTrigVerdict : uint8_t {
  AUTO_TRIG_OK = 0,
  AUTO_TRIG_IGN_PSRAM,   // 버퍼 할당 실패
  AUTO_TRIG_IGN_BUSY,    // 이전 이벤트 처리 중(1차 · 2차 진행) 또는 처리 중에 발화한 요청 — 수동 's' 와 같은 규칙
  AUTO_TRIG_IGN_RING,    // k < 앞 버퍼 수: 창 시작이 부팅 후 첫 슬롯보다 앞
  AUTO_TRIG_IGN_LATE,    // 스냅샷 시점까지 여유 부족(정상 경로에선 도달 불가 — 가드)
  AUTO_TRIG_VERDICT_N
};

inline const char* autoTrigVerdictName(AutoTrigVerdict v) {
  switch (v) {
    case AUTO_TRIG_OK:        return "ok";
    case AUTO_TRIG_IGN_PSRAM: return "psram";
    case AUTO_TRIG_IGN_BUSY:  return "busy";
    case AUTO_TRIG_IGN_RING:  return "ring";
    case AUTO_TRIG_IGN_LATE:  return "late";
    default:                  return "?";
  }
}

// buffers_ok = PSRAM 버퍼 4개 모두 있음. event_busy = 기존 4플래그(snapReq · snapReady · recReq · recReady) 중 하나.
// idle_since = 직전 이벤트 처리가 끝났을 때의 적재 순번(loop 기록). seq_now = 지금 적재 순번.
// late: loop 가 seq_now 를 읽은 뒤 스냅샷 요청이 태스크에 보이기까지 최대 1슬롯 경계를 넘을 수 있으므로
//   seq_now + 2 ≤ 스냅샷 순번이어야 첫 「보이는」 검사가 스냅샷 순번 이전이다.
inline AutoTrigVerdict autoTrigDecide(bool buffers_ok, bool event_busy, uint32_t k,
                                      uint32_t idle_since, uint32_t seq_now) {
  if (!buffers_ok) return AUTO_TRIG_IGN_PSRAM;
  if (event_busy || k + AUTO_TRIG_FIRE_LAG <= idle_since) return AUTO_TRIG_IGN_BUSY;
  if (k < AUTO_TRIG_PRE_BUFS) return AUTO_TRIG_IGN_RING;
  if (seq_now + 2 > autoTrigSnapSeq(k)) return AUTO_TRIG_IGN_LATE;
  return AUTO_TRIG_OK;
}
