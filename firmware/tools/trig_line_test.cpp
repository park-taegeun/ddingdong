// trig_line.h 호스트 검산 — 실제 firmware/include/trig_line.h · noise_stats.h 를 그대로 include 한다(복사 아님).
//   c++ -std=c++17 -Wall -I firmware/include -o /tmp/tlt firmware/tools/trig_line_test.cpp && /tmp/tlt
//
// 이 하네스가 지켜야 할 불변식 3개에 단언을 건다.
//   I1 데이터 줄 최악 길이 = 헤더 산술(TRIG_LINE_WORST)과 정확히 같고 ≤ 80B        (NC-2)
//   I2 버퍼별 값이 **제자리에** 실린다 — 되읽은 rms_all / rms_excl / clip_n 이 원값과 같다 (NC-1)
//   I3 입력 버퍼가 하나도 빠지지 않고, 순번이 줄 안·줄 사이에서 연속이다             (NC-3)
//
// ⚠️ 단언 무딤 함정 (negative control 설계와 짝지어 둔다):
//   - I2 는 클램프가 없는 입력이면 rms_all == rms_excl 이라 두 필드를 뒤바꿔도 통과한다
//     → T2 는 고립 32767 1개를 심어 rms_all > rms_excl 을 만든 뒤 대조한다.
//   - I1 은 「≤ 80」만 보면 폭을 2자 늘려도(66 → 68) 통과한다 → 헤더 산술과 **정확히 같음**을 본다.
//   - I3 은 k 개를 꽉 채운 줄만 보면 마지막 묶음 누락을 줄 개수로는 못 잡는다 → 되읽은 버퍼 수·순번 전수 대조.
//
// negative control 3종은 MIC_TRIGPROBE_RUNBOOK.md 7절 참조 — 각각 반드시 실패해야 한다.
#include <cassert>
#include <cstdio>
#include <cstring>
#include <vector>

#include "noise_stats.h"
#include "trig_line.h"

static int checks = 0;
#define CHECK(x) do { assert(x); checks++; } while (0)

constexpr uint32_t SR = 16000;
constexpr size_t   N  = 1024;   // 버퍼 1개 = 64ms (MIC_DMA_BUF_LEN)

// 테스트 내 파서: 데이터 줄 1개 → TrigBuf 목록 (seq = 첫 순번 + i). 형식이 어긋나면 false.
static bool parseLine(const char* s, std::vector<TrigBuf>* out) {
  unsigned seq = 0;
  int used = 0;
  if (std::sscanf(s, "[t] %u%n", &seq, &used) != 1) return false;
  s += used;
  for (uint32_t i = 0; *s == ' '; ++i) {
    int a = 0, x = 0;
    unsigned c = 0;
    if (std::sscanf(s, " %d,%d,%u%n", &a, &x, &c, &used) != 3) return false;
    out->push_back(TrigBuf{seq + i, a, x, c});
    s += used;
  }
  return std::strcmp(s, "\n") == 0;
}

// 결정론 배경 잡음 ±300 (LCG, noise_stats_test 와 같은 자릿수) + 선택적 고립 클램프 1개.
static NoiseSnapStats analyzeSynthetic(uint32_t seed, int clip_at) {
  static int16_t buf[N];
  uint32_t x = seed;
  for (size_t i = 0; i < N; ++i) {
    x = x * 1664525u + 1013904223u;
    buf[i] = (int16_t)((int32_t)(x >> 20) % 601 - 300);
  }
  if (clip_at >= 0) buf[clip_at] = 32767;   // 6.3(n) 실측 형태 = 고립 단일 샘플
  return noiseAnalyzeI16(buf, N, SR, nullptr, 0);
}

static TrigBuf toBuf(uint32_t seq, const NoiseSnapStats& st) {
  return TrigBuf{seq, st.rms_all, st.rms_excl, st.clip_n};
}

// 스트림 전체를 호출부(loop)와 같은 방식으로 줄로 바꿔 되읽는다. 줄 수를 반환.
static size_t roundTrip(const std::vector<TrigBuf>& in, std::vector<TrigBuf>* back) {
  char line[TRIG_LINE_BUF];
  size_t len = 0, pos = 0, lines = 0;
  while (pos < in.size()) {
    const size_t used = trigFormatLine(&in[pos], in.size() - pos, line, sizeof(line), &len);
    CHECK(used >= 1 && used <= TRIG_BUFS_PER_LINE);
    CHECK(len == std::strlen(line) && len <= TRIG_LINE_MAX);
    CHECK(parseLine(line, back));
    pos += used;
    ++lines;
  }
  return lines;
}

int main() {
  // ── T1 최악 입력: 모든 필드 최댓값 × k → 길이 = 헤더 산술 = 66, ≤ 80 ──
  {
    static_assert(TRIG_BUFS_PER_LINE == 3, "k 가 바뀌면 아래 최악 입력·기대 문자열도 갱신");
    // 첫 순번 = 10자 최대. 이후 묶음은 uint32 모듈러로 연속(0, 1)
    const TrigBuf w[3] = {{4294967295u, 32768, 32768, TRIG_CLIP_MAX},
                          {0u, 32768, 32768, TRIG_CLIP_MAX},
                          {1u, 32768, 32768, TRIG_CLIP_MAX}};
    char line[TRIG_LINE_BUF];
    size_t len = 0;
    CHECK(trigFormatLine(w, TRIG_BUFS_PER_LINE, line, sizeof(line), &len) == TRIG_BUFS_PER_LINE);
    CHECK(len == std::strlen(line));
    CHECK(len == TRIG_LINE_WORST);
    CHECK(len <= TRIG_LINE_MAX);
    CHECK(std::strcmp(line, "[t] 4294967295 32768,32768,9999 32768,32768,9999 32768,32768,9999\n") == 0);

    // 가드: 도메인 밖 첫 버퍼 / 작은 버퍼 / 빈 입력 → 0 (아무것도 쓰지 않음)
    TrigBuf bad = {7u, 32769, 0, 0};
    CHECK(trigFormatLine(&bad, 1, line, sizeof(line), &len) == 0 && len == 0);
    bad = TrigBuf{7u, 0, -1, 0};
    CHECK(trigFormatLine(&bad, 1, line, sizeof(line), &len) == 0 && len == 0);
    bad = TrigBuf{7u, 0, 0, TRIG_CLIP_MAX + 1};
    CHECK(trigFormatLine(&bad, 1, line, sizeof(line), &len) == 0 && len == 0);
    char tiny[TRIG_LINE_BUF - 1];
    CHECK(trigFormatLine(w, 1, tiny, sizeof(tiny), &len) == 0 && len == 0);
    CHECK(trigFormatLine(w, 0, line, sizeof(line), &len) == 0 && len == 0);
    // 도메인 밖 버퍼는 줄을 거기서 끊는다(앞부분은 정상 출력)
    TrigBuf mix[2] = {{10u, 100, 90, 1}, {11u, 40000, 90, 1}};
    CHECK(trigFormatLine(mix, 2, line, sizeof(line), &len) == 1);
  }

  // ── T2 왕복: 합성 버퍼(고립 32767 1개 + 조용한 배경) → noiseAnalyzeI16 → 포맷 → 되읽기 ──
  {
    std::vector<TrigBuf> in;
    const int clip_pos[TRIG_BUFS_PER_LINE] = {5, 512, 1023};
    for (size_t i = 0; i < TRIG_BUFS_PER_LINE; ++i) {
      const NoiseSnapStats st = analyzeSynthetic(100u + (uint32_t)i, clip_pos[i]);
      CHECK(st.clip_n == 1 && st.rms_all > st.rms_excl);   // 전제: 두 값이 갈라져야 NC-1 이 보인다
      in.push_back(toBuf(4000u + (uint32_t)i, st));
    }
    std::vector<TrigBuf> back;
    CHECK(roundTrip(in, &back) == 1);
    CHECK(back.size() == in.size());
    for (size_t i = 0; i < in.size(); ++i) {
      CHECK(back[i].seq == in[i].seq);
      CHECK(back[i].rms_all == in[i].rms_all);
      CHECK(back[i].rms_excl == in[i].rms_excl);
      CHECK(back[i].clip_n == 1u);
      CHECK(back[i].rms_all > back[i].rms_excl);
    }
    // 클램프 없는 버퍼는 두 값이 같다 (대조)
    const NoiseSnapStats q = analyzeSynthetic(7u, -1);
    CHECK(q.clip_n == 0 && q.rms_all == q.rms_excl);
  }

  // ── T3 순번 연속: 줄 안·줄 사이 연속 / 드롭 틈에서 줄을 끊음 / uint32 랩 ──
  {
    // (a) 연속 10개 → 3+3+3+1 = 4줄, 되읽은 순번 = 100..109 전수
    std::vector<TrigBuf> in;
    for (uint32_t s = 100; s < 110; ++s) in.push_back(TrigBuf{s, (int32_t)s, (int32_t)s - 1, s % 3});
    std::vector<TrigBuf> back;
    CHECK(roundTrip(in, &back) == 4);
    CHECK(back.size() == in.size());
    for (size_t i = 0; i < in.size(); ++i) {
      CHECK(back[i].seq == 100u + (uint32_t)i);
      CHECK(back[i].rms_all == in[i].rms_all && back[i].rms_excl == in[i].rms_excl &&
            back[i].clip_n == in[i].clip_n);
    }

    // (b) 드롭 틈 5,6,[7 드롭],8,9 → 줄 = {5,6} {8,9}. 틈이 줄 안에 숨지 않는다
    const TrigBuf gap[4] = {{5u, 1, 1, 0}, {6u, 2, 2, 0}, {8u, 3, 3, 0}, {9u, 4, 4, 0}};
    char line[TRIG_LINE_BUF];
    size_t len = 0;
    CHECK(trigFormatLine(gap, 4, line, sizeof(line), &len) == 2);
    CHECK(std::strcmp(line, "[t] 5 1,1,0 2,2,0\n") == 0);
    CHECK(trigFormatLine(gap + 2, 2, line, sizeof(line), &len) == 2);
    CHECK(std::strcmp(line, "[t] 8 3,3,0 4,4,0\n") == 0);

    // (c) uint32 랩: 4294967294, 4294967295, 0 은 연속 → 한 줄
    const TrigBuf wrap[3] = {{4294967294u, 1, 1, 0}, {4294967295u, 1, 1, 0}, {0u, 1, 1, 0}};
    CHECK(trigFormatLine(wrap, 3, line, sizeof(line), &len) == 3);
  }

  std::printf("trig_line_test: %d checks OK\n", checks);
  return 0;
}
