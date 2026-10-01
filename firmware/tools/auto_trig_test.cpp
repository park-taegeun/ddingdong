// auto_trig.h 호스트 검산 (2026-10-01 PoC-(66) M5-c ⓑ). repo 루트에서:
//   c++ -std=c++17 -Wall -I firmware/include -o /tmp/att firmware/tools/auto_trig_test.cpp && /tmp/att
// (repo 루트에서 실행해야 한다 — T10 이 ml/curation/slice_direct.py 를 상대경로로 읽는다.)
//
// 증명 범위 = 계산 동일성(V1 · 발화 · 창 · 수락 판단). 마이크 태스크 배선 · 스냅샷 시점 · 스택은 보드 ④런타임만 검출.
#include <assert.h>
#include <stdio.h>
#include <string.h>

#include <fstream>
#include <regex>
#include <sstream>
#include <string>
#include <vector>

#include "auto_trig.h"

static int checks = 0;
#define CHECK(x) do { assert(x); checks++; } while (0)

constexpr int32_t N = AUTO_TRIG_BUF_SAMPLES;

// ── 기준 구현: slice_direct.mask_glitch_clamps 를 스트림 **전체**에 한 번 적용(오프라인 trig_wav.py 와 같은 꼴) ──
// 클램프 판정만 noiseIsClip(I10). 버퍼별 isqrt(Σx² // n_ok).
static std::vector<int32_t> refV1(const std::vector<int16_t>& x) {
  const int32_t n = (int32_t)x.size();
  std::vector<bool> ex(n, false);
  for (int32_t i = 0; i < n;) {
    if (!noiseIsClip(x[i])) { ++i; continue; }
    int32_t j = i;
    while (j < n && noiseIsClip(x[j])) ++j;
    for (int32_t t = i; t < j; ++t) ex[t] = true;  // 모든 클램프 제외
    if (j - i <= AUTO_TRIG_MAX_RUN) {
      const int32_t lo = (i - AUTO_TRIG_MASK_HALF > 0) ? i - AUTO_TRIG_MASK_HALF : 0;
      const int32_t hi = (j + AUTO_TRIG_MASK_HALF < n) ? j + AUTO_TRIG_MASK_HALF : n;
      for (int32_t t = lo; t < hi; ++t) ex[t] = true;
    }
    i = j;
  }
  std::vector<int32_t> out;
  for (int32_t b = 0; b + N <= n; b += N) {
    uint64_t sq = 0; uint32_t k = 0;
    for (int32_t t = b; t < b + N; ++t) {
      if (ex[t]) continue;
      sq += (uint64_t)((int64_t)x[t] * x[t]); k++;
    }
    out.push_back(k ? noiseIsqrt64(sq / k) : 0);
  }
  return out;
}

// 보드와 같은 방식으로 흘린다: 버퍼 b 를 이웃 b−1 · b+1(꼬리면 짧게)과 함께.
static int32_t streamV1(const std::vector<int16_t>& x, int32_t b) {
  const int32_t n = (int32_t)x.size();
  const int16_t* prev = (b > 0) ? &x[(b - 1) * N] : nullptr;
  const int32_t  nx   = n - (b + 1) * N;
  const int16_t* next = (nx > 0) ? &x[(b + 1) * N] : nullptr;
  return autoTrigV1(prev, &x[b * N], next, (size_t)(nx > 0 ? (nx < N ? nx : N) : 0));
}

static uint32_t lcg = 12345;
static uint32_t rnd(uint32_t m) { lcg = lcg * 1664525u + 1013904223u; return (lcg >> 8) % m; }

int main() {
  // T1 클램프 없음 = 평범한 정수 RMS(상수 300 → 300)
  {
    std::vector<int16_t> b(N, 300);
    CHECK(autoTrigV1(nullptr, b.data(), nullptr, 0) == 300);
    std::vector<int16_t> z(N, 0);
    CHECK(autoTrigV1(nullptr, z.data(), nullptr, 0) == 0);
  }

  // T2 (NC-a 대상) 고립 클램프 + 17샘플 뒤 큰 값 28,000 — 6.3(q) 글리치 모양.
  //   V0(클램프만 제외) > T 로 오트리거, V1(±32 마스크) ≤ T.
  {
    std::vector<int16_t> b(N, 100);
    b[500] = 32767;
    b[517] = 28000;
    b[518] = -28000;
    const NoiseSnapStats v0 = noiseAnalyzeI16(b.data(), N, 16000, nullptr, 0);
    CHECK(v0.rms_excl > AUTO_TRIG_T);
    CHECK(autoTrigV1(nullptr, b.data(), nullptr, 0) == 100);
    AutoTrigState st = {};
    CHECK(!autoTrigStep(&st, 20, autoTrigV1(nullptr, b.data(), nullptr, 0)));
    CHECK(autoTrigStep(&st, 21, v0.rms_excl));   // V0 로 판정했다면 발화했을 것
  }

  // T3 (NC-c 대상) 다음 버퍼 첫 샘플의 고립 클램프 → 마스크가 현재 버퍼 끝 32샘플에 닿는다.
  {
    std::vector<int16_t> cur(N, 100), next(N, 100);
    for (int32_t i = N - 30; i < N; ++i) cur[i] = 20000;
    next[0] = -32768;
    const int32_t seen   = autoTrigV1(nullptr, cur.data(), next.data(), N);
    const int32_t unseen = autoTrigV1(nullptr, cur.data(), nullptr, 0);
    CHECK(seen == 100);
    CHECK(unseen > AUTO_TRIG_T);
    // 앞 버퍼 끝의 2샘플 런도 대칭으로 현재 버퍼 앞 30샘플을 덮는다
    std::vector<int16_t> prev(N, 100), c2(N, 100);
    prev[N - 2] = 32767; prev[N - 1] = 32767;
    for (int32_t i = 0; i < 30; ++i) c2[i] = 20000;
    CHECK(autoTrigV1(prev.data(), c2.data(), nullptr, 0) == 100);
    CHECK(autoTrigV1(nullptr, c2.data(), nullptr, 0) > AUTO_TRIG_T);
  }

  // T4 (I10) -32767 은 펌웨어 클램프가 아니다 — slice_direct(|x| ≥ 32767)와 다른 유일한 값.
  {
    CHECK(!noiseIsClip(-32767) && noiseIsClip(-32768) && noiseIsClip(32767) && !noiseIsClip(32766));
    std::vector<int16_t> b(N, 0);
    b[100] = -32767;   // 마스크도 제외도 없음 → Σ = 32767², n = 1024
    CHECK(autoTrigV1(nullptr, b.data(), nullptr, 0) == noiseIsqrt64((uint64_t)32767 * 32767 / N));
  }

  // T5 3샘플 런 = 마스크 없음(클램프 자체만 제외) / 2샘플 런 = 마스크
  {
    std::vector<int16_t> b(N, 100);
    b[200] = b[201] = b[202] = 32767;
    b[210] = 5000;
    CHECK(autoTrigV1(nullptr, b.data(), nullptr, 0) ==
          noiseIsqrt64(((uint64_t)100 * 100 * (N - 4) + (uint64_t)5000 * 5000) / (N - 3)));
    b[202] = 100;
    CHECK(autoTrigV1(nullptr, b.data(), nullptr, 0) == 100);
  }

  // T6 무작위 대조: 스트림 전체 마스크(기준) == 이웃 3버퍼만 본 V1(보드 방식). 클램프를 버퍼 경계 ±40 에 몰아 넣는다.
  {
    int cases = 0;
    for (int it = 0; it < 3000; ++it) {
      const int32_t nb = 2 + (int32_t)rnd(5);
      const int32_t tail = (it % 3 == 0) ? (int32_t)rnd(N) : 0;
      std::vector<int16_t> x(nb * N + tail);
      for (auto& v : x) v = (int16_t)((int32_t)rnd(1201) - 600);
      const int32_t nclip = (int32_t)rnd(12);
      for (int32_t c = 0; c < nclip; ++c) {
        const int32_t edge = (int32_t)(rnd(nb + 1) * N);
        int32_t pos = edge + (int32_t)rnd(81) - 40;
        if (rnd(4) == 0) pos = (int32_t)rnd((uint32_t)x.size());
        const int32_t len = 1 + (int32_t)rnd(4);
        for (int32_t t = pos; t < pos + len; ++t)
          if (t >= 0 && t < (int32_t)x.size()) x[t] = rnd(2) ? 32767 : -32768;
        if (rnd(2)) {
          const int32_t sp = pos + 17;
          if (sp >= 0 && sp < (int32_t)x.size()) x[sp] = 28000;
        }
      }
      const std::vector<int32_t> ref = refV1(x);
      for (int32_t b = 0; b < nb; ++b) {
        CHECK(streamV1(x, b) == ref[b]);
        cases++;
      }
    }
    printf("T6 무작위 버퍼 %d 개 일치\n", cases);
  }

  // T7 (NC-b 대상) N=1: 단일 버퍼만 > T 인 노크형 입력이 그 버퍼에서 발화. 등호는 발화 아님.
  {
    const int32_t v[] = {100, 100, AUTO_TRIG_T, AUTO_TRIG_T + 1, 100, 100};
    AutoTrigState st = {};
    uint32_t fired_k = 999, n = 0;
    for (uint32_t k = 0; k < 6; ++k)
      if (autoTrigStep(&st, k, v[k])) { fired_k = k; n++; }
    CHECK(n == 1 && fired_k == 3);
  }

  // T8 (NC-e 대상) 불응기 = 79버퍼(5,056ms). 78(4,992ms)은 차단. 무시된 발화도 불응기를 시작(발화 기준).
  {
    CHECK(AUTO_TRIG_REFRACTORY_BUFS == 79);
    CHECK(AUTO_TRIG_REFRACTORY_BUFS * AUTO_TRIG_BUF_MS == 5056);
    AutoTrigState st = {};
    CHECK(autoTrigStep(&st, 10, 1000));
    CHECK(!autoTrigStep(&st, 10 + 78, 1000));
    CHECK(autoTrigStep(&st, 10 + 79, 1000));
    // uint32 순번이 감겨도 차로 센다
    AutoTrigState w = {};
    CHECK(autoTrigStep(&w, 0xFFFFFFF0u, 1000));
    CHECK(!autoTrigStep(&w, 0xFFFFFFF0u + 78, 1000));
    CHECK(autoTrigStep(&w, 0xFFFFFFF0u + 79, 1000));
  }

  // T9 (I1 · NC-d 대상) 창: 링(32슬롯, 인덱스 = 순번 % 32)에서 순번 k+24 시점에 write_idx 부터 32슬롯을 복사하면
  //   슬롯 [k−8, k+24). 펌웨어 스냅샷 루프(micRingSlot(base, write_idx + i))를 같은 산술로 흉내 낸다.
  {
    for (uint32_t k = AUTO_TRIG_PRE_BUFS; k < 200; ++k) {
      const uint32_t snap = autoTrigSnapSeq(k);
      CHECK(snap == k + 24);
      uint32_t ring[AUTO_TRIG_WIN_BUFS];
      for (uint32_t s = 0; s < snap; ++s) ring[s % AUTO_TRIG_WIN_BUFS] = s;   // 슬롯에 순번을 적재
      const uint32_t write_idx = snap % AUTO_TRIG_WIN_BUFS;
      CHECK(ring[write_idx % AUTO_TRIG_WIN_BUFS] == k - 8);
      CHECK(ring[(write_idx + AUTO_TRIG_WIN_BUFS - 1) % AUTO_TRIG_WIN_BUFS] == k + 23);
      // 판정 순번(k+2)부터 스냅샷까지 = 22슬롯 = 1,408ms, 트리거 버퍼 끝부터 = 23슬롯 = 1,472ms
      CHECK((snap - (k + AUTO_TRIG_FIRE_LAG)) * AUTO_TRIG_BUF_MS == 1408);
    }
  }

  // T10 (I11 · NC-f 대상) 마스크 상수 원본 = ml/curation/slice_direct.py 텍스트 대조
  {
    std::ifstream f("ml/curation/slice_direct.py");
    if (!f) {
      fprintf(stderr, "ml/curation/slice_direct.py 를 못 읽음 — repo 루트에서 실행할 것\n");
      return 1;
    }
    std::stringstream ss;
    ss << f.rdbuf();
    const std::string src = ss.str();
    auto val = [&](const char* name) -> long {
      std::smatch m;
      const std::regex re(std::string("(^|\\n)") + name + "\\s*=\\s*(\\d+)");
      if (!std::regex_search(src, m, re)) return -1;
      return std::stol(m[2]);
    };
    CHECK(val("CLAMP_MASK_HALF_WIDTH") == AUTO_TRIG_MASK_HALF);
    CHECK(val("GLITCH_MAX_RUN") == AUTO_TRIG_MAX_RUN);
    CHECK(val("CLAMP") == 32767 && noiseIsClip(32767));   // 양의 클램프 값은 같다(음수 쪽 차이 = T4)
  }

  // T11 (I3 · I4 · NC-g 대상) 수락 판단과 사유 순서
  {
    // 정상: 판정 직후(seq = k+2) 수락
    CHECK(autoTrigDecide(true, false, 20, 0, 22) == AUTO_TRIG_OK);
    CHECK(autoTrigDecide(false, true, 3, 100, 999) == AUTO_TRIG_IGN_PSRAM);
    // 처리 중(4플래그) → busy. 수동 's' 와 같은 규칙
    CHECK(autoTrigDecide(true, true, 20, 0, 22) == AUTO_TRIG_IGN_BUSY);
    // 처리 중에 발화(k+2 ≤ idle_since) → 처리가 끝난 뒤 읽어도 busy (late 보다 먼저)
    CHECK(autoTrigDecide(true, false, 100, 102, 180) == AUTO_TRIG_IGN_BUSY);
    CHECK(autoTrigDecide(true, false, 100, 102, 102) == AUTO_TRIG_IGN_BUSY);   // 경계: 발화 순번 == idle_since
    // 처리 종료 뒤 발화(발화 순번 k+2 > idle_since) → 수락
    CHECK(autoTrigDecide(true, false, 100, 101, 102) == AUTO_TRIG_OK);
    // 링: k < 8
    CHECK(autoTrigDecide(true, false, 7, 0, 9) == AUTO_TRIG_IGN_RING);
    CHECK(autoTrigDecide(true, false, 8, 0, 10) == AUTO_TRIG_OK);
    // late 경계: seq_now + 2 ≤ k + 24
    CHECK(autoTrigDecide(true, false, 20, 0, 42) == AUTO_TRIG_OK);
    CHECK(autoTrigDecide(true, false, 20, 0, 43) == AUTO_TRIG_IGN_LATE);
    CHECK(strcmp(autoTrigVerdictName(AUTO_TRIG_IGN_BUSY), "busy") == 0);
    CHECK(strcmp(autoTrigVerdictName(AUTO_TRIG_OK), "ok") == 0);
  }

  printf("auto_trig_test: %d checks OK\n", checks);
  return 0;
}
