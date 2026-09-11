// noise_modes.h 호스트 검산 — 실제 firmware/include/noise_modes.h 를 그대로 include 한다(복사 아님).
//   c++ -std=c++17 -Wall -I firmware/include -o /tmp/nmt firmware/tools/noise_modes_test.cpp && /tmp/nmt
//
// 이 하네스의 유일한 가치는 「한 번에 한 변수만」이다. 그래서 단언의 중심은 개별 모드 값이 아니라
// **두 모드의 전 필드 비교**다(I1). 필드를 하나라도 빠뜨리고 비교하면 실험이 조용히 무효가 되므로
// 비교는 diffCount() 한 곳에서만 하고, 모든 I1 단언이 그것을 쓴다.
//
// negative control 3종(m5 풀다운 해제 / m5 클럭 오염 / m2 풀다운 오염)은
// MIC_NOISEPROBE_RUNBOOK.md 7절 참조 — 각각 반드시 실패해야 한다.
#include <cassert>
#include <cstdio>

#include "noise_modes.h"

static int checks = 0;
#define CHECK(x) do { assert(x); checks++; } while (0)

constexpr uint32_t FAST = 400000;
constexpr uint32_t SLOW = 100000;

static NoiseModeCfg cfg(int m) { return noiseModeCfg(m, FAST, SLOW); }

// 두 구성이 서로 다른 필드 수. 전 필드를 여기 한 곳에서만 센다.
static int diffCount(const NoiseModeCfg& a, const NoiseModeCfg& b) {
  int d = 0;
  if (a.ranging != b.ranging) d++;
  if (a.poll    != b.poll)    d++;
  if (a.i2c_hz  != b.i2c_hz)  d++;
  if (a.core    != b.core)    d++;
  if (a.sd_pd   != b.sd_pd)   d++;
  return d;
}

int main() {
  // ── 기존 m0~m4 = decisions.md 6.3(n) 5모드 표 (동작 무변경 고정) ──────────────
  CHECK(cfg(0).ranging == false); CHECK(cfg(0).poll == false);
  CHECK(cfg(0).i2c_hz == FAST);   CHECK(cfg(0).core == 0);
  CHECK(cfg(1).ranging == true);  CHECK(cfg(1).poll == false);
  CHECK(cfg(1).i2c_hz == FAST);   CHECK(cfg(1).core == 0);
  CHECK(cfg(2).ranging == true);  CHECK(cfg(2).poll == true);
  CHECK(cfg(2).i2c_hz == FAST);   CHECK(cfg(2).core == 0);
  CHECK(cfg(3).ranging == true);  CHECK(cfg(3).poll == true);
  CHECK(cfg(3).i2c_hz == SLOW);   CHECK(cfg(3).core == 0);
  CHECK(cfg(4).ranging == true);  CHECK(cfg(4).poll == true);
  CHECK(cfg(4).i2c_hz == FAST);   CHECK(cfg(4).core == 1);

  // ── I2: 기존 m0~m4 의 sd_pd 는 전부 OFF ────────────────────────────────────
  // (하나라도 켜지면 그 모드의 과거 실측 6.3(n) 과 비교가 불가능해진다)
  for (int m = 0; m <= 4; ++m) CHECK(cfg(m).sd_pd == false);

  // ── I1: m5 는 m2 와 **정확히 sd_pd 한 필드만** 다르다 ────────────────────────
  CHECK(diffCount(cfg(5), cfg(2)) == 1);
  CHECK(cfg(5).sd_pd == true);
  CHECK(cfg(2).sd_pd == false);
  // 나머지 필드는 개별적으로도 같아야 한다(diffCount 가 무뎌지는 경우 대비 이중 그물)
  CHECK(cfg(5).ranging == cfg(2).ranging);
  CHECK(cfg(5).poll    == cfg(2).poll);
  CHECK(cfg(5).i2c_hz  == cfg(2).i2c_hz);
  CHECK(cfg(5).core    == cfg(2).core);

  // ── I1: m6 는 m0 와 **정확히 sd_pd 한 필드만** 다르다 ────────────────────────
  CHECK(diffCount(cfg(6), cfg(0)) == 1);
  CHECK(cfg(6).sd_pd == true);
  CHECK(cfg(0).sd_pd == false);
  CHECK(cfg(6).ranging == cfg(0).ranging);
  CHECK(cfg(6).poll    == cfg(0).poll);
  CHECK(cfg(6).i2c_hz  == cfg(0).i2c_hz);
  CHECK(cfg(6).core    == cfg(0).core);

  // ── 나머지 모드와의 거리도 정확히 고정 (전부 같아지는 퇴화 / 축 이동 방지) ────
  CHECK(diffCount(cfg(5), cfg(0)) == 3);   // ranging + poll + sd_pd
  CHECK(diffCount(cfg(5), cfg(3)) == 2);   // i2c_hz + sd_pd
  CHECK(diffCount(cfg(5), cfg(4)) == 2);   // core + sd_pd
  CHECK(diffCount(cfg(6), cfg(2)) == 3);   // ranging + poll + sd_pd

  // ── 범위 밖은 m0 와 같은 안전값 ─────────────────────────────────────────────
  CHECK(diffCount(cfg(-1), cfg(0)) == 0);
  CHECK(diffCount(cfg(NOISE_MODE_N), cfg(0)) == 0);
  CHECK(NOISE_MODE_N == 7);

  printf("noise_modes_test: %d checks OK\n", checks);
  return 0;
}
