// 띵동 firmware - M5-c ⓐ 64ms 버퍼 단위 RMS 로그 줄 포맷터 (2026-09-23, env:mic_trigprobe 전용)
//
// ★ 성격 = 관측 계층(decisions.md 카테고리 20 「계측 → 실측 → 판정」). 임계값·디바운스·트리거
//   판정 0줄. 버퍼 하나(1024 샘플 = 64ms)의 noiseAnalyzeI16 결과 3값을 **버퍼별로 그대로** 줄에 싣는다.
//   집계·평균 금지 — 판정 PR(ⓑ)이 오프라인에서 「연속 N버퍼」 디바운스를 시뮬레이션할 입력이다.
//
// ★ 왜 Arduino 무의존 순수 헤더인가: 호스트 테스트(firmware/tools/trig_line_test.cpp)가 **같은 파일을
//   그대로** include 해 검산한다(noise_stats_test 선례 = 복사 아님).
//
// ★ 줄 형식 (데이터 줄 1개 = 순번이 연속인 버퍼 1~TRIG_BUFS_PER_LINE 개)
//     [t] <seq> <rms_all>,<rms_excl>,<clip_n> <rms_all>,<rms_excl>,<clip_n> ...
//   seq = 줄 첫 버퍼의 순번. i 번째 묶음의 순번 = seq + i (uint32 모듈러 — 줄 안에서 연속만 허용).
//   순번이 끊기면(큐 드롭) 줄을 거기서 끊는다 → 한 줄 안의 순번은 항상 연속, 줄 사이 틈 = 드롭.
//
// ★ 필드 폭 근거 (값 도메인 — 호출부 mic_trigprobe_main.cpp 가 n = MIC_DMA_BUF_LEN(1024) 로 부른다)
//   seq      uint32              → 최대 4294967295 = 10자
//   rms_all  noiseAnalyzeI16    → ∈ [0, 32768]   = 5자 (|INT16_MIN| 의 RMS 가 상한)
//   rms_excl noiseAnalyzeI16    → ∈ [0, 32767]   = 5자 (클램프 제외라 32768 불가, 폭은 같게 잡는다)
//   clip_n   noiseAnalyzeI16    → ∈ [0, n=1024]  = 4자 (호출부가 static_assert 로 n ≤ 9999 강제)
//   peak 는 싣지 않는다: 클램프가 1개라도 있으면 32767/32768 로 고정돼(6.3(n)) 정보가 없고,
//   클램프 제외 peak 는 noiseAnalyzeI16 에 없다(새 계산식 금지).
//
// ★ 줄 길이 상한 80B = decisions.md 6.3(j) 실측(「≤80B 62줄에서 손상 0건」). 여기서 80B 는 '\n' 포함.
#pragma once

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

struct TrigBuf {
  uint32_t seq;       // 버퍼 순번 (마이크 태스크가 i2s_read 성공마다 +1, 드롭돼도 증가)
  int32_t  rms_all;   // NoiseSnapStats.rms_all
  int32_t  rms_excl;  // NoiseSnapStats.rms_excl
  uint32_t clip_n;    // NoiseSnapStats.clip_n
};

constexpr size_t TRIG_BUFS_PER_LINE = 3;    // k
constexpr size_t TRIG_LINE_MAX      = 80;   // '\n' 포함 상한 (6.3(j))
constexpr uint32_t TRIG_CLIP_MAX    = 9999; // clip_n 4자 상한 — 호출부 버퍼 길이가 이 이하여야 한다

// 최악 길이 산술 (T1 이 실제 snprintf 결과와 **정확히 같음**을 단언 → 폭이 바뀌면 여기와 어긋나 실패)
//   "[t] "(4) + seq(10)                               = 14
//   묶음 " 32768,32768,9999" = 1 + 5 + 1 + 5 + 1 + 4  = 17  × k(3) = 51
//   '\n'                                              =  1
//   합계                                              = 66  ≤ 80  (k=4 면 83 → 초과)
constexpr size_t TRIG_PREFIX_WORST = 4 + 10;
constexpr size_t TRIG_ENTRY_WORST  = 1 + 5 + 1 + 5 + 1 + 4;
constexpr size_t TRIG_LINE_WORST   = TRIG_PREFIX_WORST + TRIG_BUFS_PER_LINE * TRIG_ENTRY_WORST + 1;
static_assert(TRIG_LINE_WORST <= TRIG_LINE_MAX, "trig 데이터 줄 최악 길이가 80B(6.3(j))를 넘는다");
constexpr size_t TRIG_LINE_BUF = TRIG_LINE_MAX + 1;   // NUL 포함 버퍼 크기

// 값이 필드 폭 근거의 도메인 안인가. 밖이면 줄이 80B 를 넘을 수 있으므로 포맷하지 않는다.
inline bool trigInDomain(const TrigBuf& b) {
  return b.rms_all >= 0 && b.rms_all <= 32768 && b.rms_excl >= 0 && b.rms_excl <= 32768 &&
         b.clip_n <= TRIG_CLIP_MAX;
}

// b[0..n) 중 **순번이 연속이고 도메인 안인 앞부분**(최대 TRIG_BUFS_PER_LINE 개)을 한 줄로 쓴다.
// 반환 = 소비한 버퍼 수. *len = '\n' 포함 바이트 수(NUL 제외).
// 0 반환 = 아무것도 쓰지 않음: n == 0 / cap < TRIG_LINE_BUF / b[0] 이 도메인 밖.
//   ⚠️ 호출부는 0 을 조용히 넘기지 말고 b[0] 을 버린 사실을 출력해야 한다(조용한 누락 금지).
inline size_t trigFormatLine(const TrigBuf* b, size_t n, char* out, size_t cap, size_t* len) {
  *len = 0;
  if (b == nullptr || n == 0 || out == nullptr || cap < TRIG_LINE_BUF || !trigInDomain(b[0])) {
    return 0;
  }

  size_t take = 1;
  while (take < n && take < TRIG_BUFS_PER_LINE && b[take].seq == b[take - 1].seq + 1u &&
         trigInDomain(b[take])) {
    ++take;
  }

  // 도메인 안이면 합계 ≤ TRIG_LINE_WORST(66) < cap 이라 잘림·음수 반환이 없다(T1 이 정확값 단언).
  int w = snprintf(out, cap, "[t] %u", (unsigned)b[0].seq);
  for (size_t i = 0; i < take; ++i) {
    w += snprintf(out + w, cap - (size_t)w, " %d,%d,%u", (int)b[i].rms_all, (int)b[i].rms_excl,
                  (unsigned)b[i].clip_n);
  }
  w += snprintf(out + w, cap - (size_t)w, "\n");
  *len = (size_t)w;
  return take;
}
