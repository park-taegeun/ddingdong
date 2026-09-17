// 띵동 firmware - camera_probe 창(window) 통계 집계 + JPEG SOI 검사 (2026-09-17, env:camera_probe)
//
// ★ 성격 = 관측 계층(decisions.md 카테고리 20). 판정·임계값 0줄 — 숫자만 낸다.
//
// ★ 왜 Arduino 무의존 순수 헤더인가: 호스트 테스트(firmware/tools/camera_probe_test.cpp)가
//   **같은 파일을 그대로** 컴파일해 검산한다(noise_stats.h / noise_modes.h / tof_judge_test 선례
//   = 복사 아님). 그리고 probeIsJpegSoi 는 PR-B(/enrich 전송)가 전송 직전 가드로 **그대로**
//   재사용할 수 있게 전송 코드와 무관한 헤더에 둔다.
//
// ★ 센티넬 금지 (mic_common 의 「센티넬 없는 win_rms_min」 선례)
//   최소값을 UINT32_MAX 나 0 으로 초기화해 두면, 표본이 0건인 창이 "0ms 에 성공" 처럼 읽힌다
//   (= 조용한 실패). 여기서는 **표본 수 필드가 0인지**로 유효성을 가르고, 유효할 때만 첫 표본으로
//   min/max 를 동시에 세운다. 출력부는 probeCamHasSample() 이 false 면 "n/a" 를 찍는다(NC-3 대상).
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "noise_stats.h"   // noiseIsClip(클램프 정의 SSoT) / noiseIsqrt64(정수 RMS)

// ── JPEG SOI(Start Of Image) 검사 ────────────────────────────────────────────
// JPEG 는 반드시 0xFF 0xD8 로 시작한다(JFIF/Exif 공통). esp_camera 가 PIXFORMAT_JPEG 로 돌려준
// 버퍼가 이 두 바이트로 시작하지 않으면 그 프레임은 이미지가 아니다 — 보드가 여기서 세지 않으면
// 서버가 400 을 내야 알 수 있다(조용한 실패 금지, 카테고리 20).
// ⚠️ 길이 가드가 **비교보다 먼저** 와야 한다. len < 2 인 버퍼에서 buf[1] 을 읽으면 버퍼 너머다(NC-2).
inline bool probeIsJpegSoi(const uint8_t* buf, size_t len) {
  if (buf == nullptr || len < 2) return false;
  return buf[0] == 0xFF && buf[1] == 0xD8;   // 두 바이트 모두 확인 (NC-1)
}

// ── 카메라 창 통계 ────────────────────────────────────────────────────────────
// attempt = fb_get 호출 수. ok = SOI 까지 통과한 프레임 수.
// attempt = ok + fb_null + soi_bad 가 항상 성립한다(모든 실패 경로가 카운터로 드러난다).
struct ProbeCamWin {
  uint32_t attempt;
  uint32_t ok;
  uint32_t fb_null;   // esp_camera_fb_get() == nullptr (카테고리 17 #620 fb_get fail)
  uint32_t soi_bad;   // fb 는 왔으나 선두 2바이트가 JPEG 이 아님
  uint32_t len_min;   // ok == 0 이면 무의미 — probeCamHasSample() 로 가른다
  uint32_t len_max;
  uint32_t ms_min;
  uint32_t ms_max;
  uint64_t ms_sum;    // 평균 산출용. 10초 창 × 최악 1000ms = 10,000 → uint64 과잉이지만 합산 안전
};

inline void probeCamReset(ProbeCamWin* w) { *w = ProbeCamWin{}; }

// 표본이 있는가. 출력부는 이 함수가 false 면 최소/최대/평균을 찍지 않는다.
inline bool probeCamHasSample(const ProbeCamWin* w) { return w != nullptr && w->ok != 0; }

// fb_get 성공 + SOI 통과 1건. len = fb->len, ms = fb_get 소요 시간.
inline void probeCamRecordOk(ProbeCamWin* w, uint32_t len, uint32_t ms) {
  if (w == nullptr) return;
  w->attempt++;
  if (w->ok == 0) {                       // 첫 표본 = min·max 를 동시에 세운다(센티넬 없음)
    w->len_min = len; w->len_max = len;
    w->ms_min  = ms;  w->ms_max  = ms;
  } else {
    if (len < w->len_min) w->len_min = len;
    if (len > w->len_max) w->len_max = len;
    if (ms  < w->ms_min)  w->ms_min  = ms;
    if (ms  > w->ms_max)  w->ms_max  = ms;
  }
  w->ok++;
  w->ms_sum += ms;
}

inline void probeCamRecordNull(ProbeCamWin* w) { if (w) { w->attempt++; w->fb_null++; } }
inline void probeCamRecordSoiBad(ProbeCamWin* w) { if (w) { w->attempt++; w->soi_bad++; } }

// 평균 캡처 ms. 표본 0건이면 0 을 돌려주지만, 출력부는 애초에 부르지 않는다
// (probeCamHasSample 로 먼저 가른다 — 여기서 0 을 "0ms 성공"으로 읽히게 하지 않는 것이 요지).
inline uint32_t probeCamAvgMs(const ProbeCamWin* w) {
  if (!probeCamHasSample(w)) return 0;
  return (uint32_t)(w->ms_sum / w->ok);
}

// ── 마이크 창 통계 ────────────────────────────────────────────────────────────
// noise_stats.h 의 스냅샷 분석(noiseAnalyzeI16)은 연속 버퍼가 필요하다. 창은 10초라 버퍼를
// 들 이유가 없으므로 **증분 누적**으로 창 전체를 덮는다(2초 표본이 아니라 전 구간).
// 클램프 판정은 noiseIsClip 을 그대로 쓴다 = 6.3(n) 실측과 같은 정의.
//
// ★ 오버플로 (근거유형 = 산술): 10초 창 = 160,000 샘플. Σv² ≤ 160,000 × 32768² ≈ 2^47.3 < 2^64.
//   창 길이를 크게 늘려도 uint64 는 2^64/2^30 = 2^34 샘플 ≈ 12일치까지 안전하다.
struct ProbeMicWin {
  uint32_t n;        // 누적 샘플 수
  uint32_t n_ok;     // 클램프가 아닌 샘플 수
  int32_t  peak;     // max |v| ∈ [0, 32768]
  uint32_t clip;     // noiseIsClip 인 샘플 수
  uint32_t gaps;     // i2s_read 실패로 건너뛴 버퍼 수(창 기준 증분)
  uint64_t sq_all;
  uint64_t sq_ok;
};

inline void probeMicReset(ProbeMicWin* w) { *w = ProbeMicWin{}; }

inline void probeMicAccumulate(ProbeMicWin* w, const int16_t* s, size_t n) {
  if (w == nullptr || s == nullptr) return;
  for (size_t i = 0; i < n; ++i) {
    const int32_t v = (int32_t)s[i];
    const int32_t a = (v >= 0) ? v : -v;          // int32 절댓값 (|INT16_MIN| 부호 반전 회피)
    if (a > w->peak) w->peak = a;
    w->sq_all += (uint64_t)((int64_t)v * v);
    if (noiseIsClip(v)) {
      w->clip++;
    } else {
      w->sq_ok += (uint64_t)((int64_t)v * v);
      w->n_ok++;
    }
    w->n++;
  }
}

// 창 전체 RMS. 표본 0건이면 0 — 단 호출부는 n == 0 창을 "무음"이 아니라 "표본 없음"으로 찍는다.
inline int32_t probeMicRmsAll(const ProbeMicWin* w) {
  if (w == nullptr || w->n == 0) return 0;
  return noiseIsqrt64(w->sq_all / (uint64_t)w->n);
}

// 클램프 제외 RMS. 분모는 **제외 후 개수**(noise_stats 의 rms_excl 와 같은 정의).
inline int32_t probeMicRmsExcl(const ProbeMicWin* w) {
  if (w == nullptr || w->n_ok == 0) return 0;
  return noiseIsqrt64(w->sq_ok / (uint64_t)w->n_ok);
}

// ── ToF 창 통계 ───────────────────────────────────────────────────────────────
// 판정 본체(tofJudgeFrame)는 tof_common 이 소유한다. 여기는 그 결과를 **세기만** 한다.
struct ProbeTofWin {
  uint32_t frames;     // getRangingData 성공 수
  uint32_t pres_edge;  // presence_state 가 바뀐 횟수(상승·하강 모두)
  uint32_t read_fail;  // isDataReady/getRangingData 가 false 를 돌려준 회차
};

inline void probeTofReset(ProbeTofWin* w) { *w = ProbeTofWin{}; }
