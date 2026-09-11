// tofJudgeFrame 호스트 검증 — 실제 firmware/src/tof_common.cpp 를 그대로 링크한다(복사 아님).
//   c++ -std=c++17 -Wall -I firmware/include -I firmware/tools/host_stubs \
//       -o /tmp/tjt firmware/tools/tof_judge_test.cpp firmware/src/tof_common.cpp && /tmp/tjt
// 합성 프레임 시퀀스로 Stage A 디바운스(N=3) / center zone / 임계 8·1000mm / B-2 latch(75) /
// ndet≥1 / 프레임 단위 AND / 로그 포맷(전이 줄 verbatim)을 단언한다.
// negative control(헤더·cpp 변형 → 반드시 실패해야 함) 4종은 MIC_UPLINK_RUNBOOK.md 9절 참조.
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <cstring>

#include "tof_common.h"

HostSerial Serial;
HostEsp    ESP;
TwoWire    Wire;

// ── 합성 프레임 도우미 ───────────────────────────────────────────────────────
static VL53L5CX_ResultsData frame_all_invalid() {
  VL53L5CX_ResultsData d;
  memset(&d, 0, sizeof(d));
  for (int i = 0; i < 64; i++) { d.target_status[i] = 0; d.distance_mm[i] = 0; }
  return d;
}
// zone 0..(n-1) 을 valid(status 5) + mm 로 채운다. 나머지는 invalid.
static VL53L5CX_ResultsData frame_near(uint8_t n, int16_t mm, uint8_t ndet = 0, uint8_t status = 5) {
  VL53L5CX_ResultsData d = frame_all_invalid();
  for (uint8_t i = 0; i < n; i++) { d.target_status[i] = status; d.distance_mm[i] = mm; }
  d.motion_indicator.nb_of_detected_aggregates = ndet;
  d.motion_indicator.nb_of_aggregates = 16;
  return d;
}

static int checks = 0;
#define CHECK(x) do { assert(x); checks++; } while (0)

int main() {
  Serial.echo = (getenv("TOF_HOST_ECHO") != nullptr);

  // ── 상수 고정 (SSoT 9.2~9.4 값 — 변형되면 컴파일 단계에서 먼저 걸린다) ──
  // negative control 은 -DTOF_TEST_NO_CONST_PIN 으로 이 블록을 끄고 **행동 단언**이 잡는지를 본다.
#ifndef TOF_TEST_NO_CONST_PIN
  static_assert(TOF_PRESENCE_MIN_ZONES == 8, "9.2 임계 8");
  static_assert(TOF_PRESENCE_DIST_MM == 1000, "9.2 1m");
  static_assert(TOF_PRESENCE_DEBOUNCE_FRAMES == 3, "9.2 디바운스 N=3");
  static_assert(TOF_MOTION_NDET_MIN == 1, "9.4(a) ndet>=1");
  static_assert(TOF_MOTION_LATCH_FRAMES == 75, "9.4(b) latch 75");
  static_assert(TOF_MOTION_DIST_MIN_MM == 400 && TOF_MOTION_DIST_MAX_MM == 1500,
                "9.3 감시창 400~1500 — 센서 설정값(initToFMotionIndicator)이라 판정 함수 도달 불가, 상수만 고정");
  static_assert(TOF_CENTER_ZONES[0] == 27 && TOF_CENTER_ZONES[1] == 28 &&
                TOF_CENTER_ZONES[2] == 35 && TOF_CENTER_ZONES[3] == 36, "center zone 27/28/35/36");
#endif

  // ── T1 baseline: 전부 무효 프레임 ──
  {
    TofJudgeState st;
    const TofFrameResult r = tofJudgeFrame(&st, frame_all_invalid());
    CHECK(r.near_count == 0 && !r.center_valid && r.center_mm == 0);
    CHECK(!r.presence_state && !r.fused && r.motion_ndet == 0);
    CHECK(st.frame_count == 1);
    // frame #1 은 30프레임 주기 요약(%30==1) 대상 → 요약 줄 verbatim
    CHECK(strcmp(Serial.last, "[tof][StageA] frame #1 near=0/64 presence=NONE center=n/a\n") == 0);
  }

  // ── T2 디바운스 N=3 진입/이탈 대칭 + 전이 로그 verbatim ──
  {
    TofJudgeState st;
    TofFrameResult r{};
    r = tofJudgeFrame(&st, frame_near(10, 500)); CHECK(!r.presence_state);  // streak 1
    r = tofJudgeFrame(&st, frame_near(10, 500)); CHECK(!r.presence_state);  // streak 2
    r = tofJudgeFrame(&st, frame_near(10, 500)); CHECK(r.presence_state);   // streak 3 → 전환
    CHECK(strcmp(Serial.last,
                 "[tof][StageA] presence: NONE -> DETECTED (near=10/64, center=n/a, streak=3)\n") == 0);
    CHECK(st.presence_streak == 0);
    r = tofJudgeFrame(&st, frame_near(0, 0)); CHECK(r.presence_state);
    r = tofJudgeFrame(&st, frame_near(0, 0)); CHECK(r.presence_state);
    r = tofJudgeFrame(&st, frame_near(0, 0)); CHECK(!r.presence_state);    // 이탈도 3프레임
    CHECK(strcmp(Serial.last,
                 "[tof][StageA] presence: DETECTED -> NONE (near=0/64, center=n/a, streak=3)\n") == 0);
  }

  // ── T3 streak 리셋: 2 + 끊김 + 2 는 전환 없음, 3연속이어야 전환 ──
  {
    TofJudgeState st;
    TofFrameResult r{};
    tofJudgeFrame(&st, frame_near(10, 500));
    tofJudgeFrame(&st, frame_near(10, 500));
    r = tofJudgeFrame(&st, frame_near(0, 0));    CHECK(!r.presence_state && st.presence_streak == 0);
    tofJudgeFrame(&st, frame_near(10, 500));
    r = tofJudgeFrame(&st, frame_near(10, 500)); CHECK(!r.presence_state);
    r = tofJudgeFrame(&st, frame_near(10, 500)); CHECK(r.presence_state);
  }

  // ── T4 raw 임계 경계: near 7 vs 8 / 1000 vs 1001mm / 0mm / status 5·9 valid, 4 invalid ──
  {
    auto raw_after3 = [](VL53L5CX_ResultsData d) {
      TofJudgeState st;
      tofJudgeFrame(&st, d); tofJudgeFrame(&st, d);
      return tofJudgeFrame(&st, d);
    };
    TofFrameResult r{};
    r = raw_after3(frame_near(7, 500));       CHECK(r.near_count == 7 && !r.presence_state);
    r = raw_after3(frame_near(8, 500));       CHECK(r.near_count == 8 && r.presence_state);
    r = raw_after3(frame_near(8, 1000));      CHECK(r.near_count == 8 && r.presence_state);
    r = raw_after3(frame_near(8, 1001));      CHECK(r.near_count == 0 && !r.presence_state);
    r = raw_after3(frame_near(8, 0));         CHECK(r.near_count == 0);
    r = raw_after3(frame_near(8, 500, 0, 9)); CHECK(r.near_count == 8 && r.presence_state);
    r = raw_after3(frame_near(8, 500, 0, 4)); CHECK(r.near_count == 0 && !r.presence_state);
    r = raw_after3(frame_near(64, 999));      CHECK(r.near_count == 64);
  }

  // ── T5 center 4 zone(27/28/35/36) 평균 · 무효 제외 · 비 center zone 무영향 ──
  {
    TofJudgeState st;
    VL53L5CX_ResultsData d = frame_all_invalid();
    d.target_status[27] = 5; d.distance_mm[27] = 400;
    d.target_status[28] = 5; d.distance_mm[28] = 600;
    d.target_status[26] = 5; d.distance_mm[26] = 5000;  // 이웃 zone — center 에 섞이면 안 됨
    TofFrameResult r = tofJudgeFrame(&st, d);
    CHECK(r.center_valid && r.center_mm == 500);
    d.target_status[27] = 4;                             // 27 무효 → 28 단독
    r = tofJudgeFrame(&st, d);
    CHECK(r.center_valid && r.center_mm == 600);
    d.target_status[35] = 9; d.distance_mm[35] = 0;      // 0mm 는 valid 여도 제외
    r = tofJudgeFrame(&st, d);
    CHECK(r.center_valid && r.center_mm == 600);
    d.target_status[36] = 5; d.distance_mm[36] = 1200;
    r = tofJudgeFrame(&st, d);
    CHECK(r.center_valid && r.center_mm == 900);
    d.target_status[28] = 0; d.target_status[36] = 0;
    r = tofJudgeFrame(&st, d);
    CHECK(!r.center_valid && r.center_mm == 0);
    // 4개 zone 각각이 기여하는지: 하나만 valid 로 두고 값이 그대로 나와야 한다(zone 교체 NC 앵커)
    for (int k = 0; k < 4; k++) {
      VL53L5CX_ResultsData e = frame_all_invalid();
      e.target_status[TOF_CENTER_ZONES[k]] = 5; e.distance_mm[TOF_CENTER_ZONES[k]] = 700 + k;
      TofJudgeState s2;
      r = tofJudgeFrame(&s2, e);
      CHECK(r.center_valid && r.center_mm == (uint16_t)(700 + k));
    }
    {
      VL53L5CX_ResultsData e = frame_all_invalid();
      e.target_status[27] = 5; e.distance_mm[27] = 700;   // zone 27 이 center 에 속해야 한다
      TofJudgeState s3;
      r = tofJudgeFrame(&s3, e);
      CHECK(r.center_valid && r.center_mm == 700);
      e.target_status[27] = 0; e.target_status[26] = 5; e.distance_mm[26] = 700;  // 26 은 아니다
      TofJudgeState s4;
      r = tofJudgeFrame(&s4, e);
      CHECK(!r.center_valid);
    }
  }

  // ── T6 latch 75: 검출 1회 후 74프레임 유지, 75번째에 만료 (presence 는 계속 DETECTED) ──
  {
    TofJudgeState st;
    TofFrameResult r{};
    for (int i = 0; i < 3; i++) r = tofJudgeFrame(&st, frame_near(10, 500));
    CHECK(r.presence_state && !r.fused);                       // motion 이력 없음 → fused false
    r = tofJudgeFrame(&st, frame_near(10, 500, 1));             // ndet=1 → latch 만충
    CHECK(r.fused && st.motion_latch == TOF_MOTION_LATCH_FRAMES);
    CHECK(strncmp(Serial.last, "[tof][StageB-2] fused #4: NONE -> PERSON (presence=DETECTED, latch=75/75, ndet=1, near=10/64, center=n/a)", 60) == 0);
    for (int i = 1; i <= 74; i++) {
      r = tofJudgeFrame(&st, frame_near(10, 500, 0));
      CHECK(r.fused);
      CHECK(st.motion_latch == TOF_MOTION_LATCH_FRAMES - i);
    }
    r = tofJudgeFrame(&st, frame_near(10, 500, 0));             // 75번째 → latch 0
    CHECK(!r.fused && st.motion_latch == 0 && r.presence_state);
    CHECK(strstr(Serial.last, "[tof][StageB-2] fused #79: PERSON -> NONE (presence=DETECTED, latch=0/75") != nullptr);
    r = tofJudgeFrame(&st, frame_near(10, 500, 0));
    CHECK(!r.fused && st.motion_latch == 0);                    // 0 에서 멈춤(언더플로 없음)
  }

  // ── T7 프레임 단위 AND: presence 없이 motion 만 / motion 없이 presence 만 → 둘 다 false ──
  {
    TofJudgeState st;
    TofFrameResult r{};
    r = tofJudgeFrame(&st, frame_near(0, 0, 5));                // motion 만
    CHECK(!r.presence_state && st.motion_latch == 75 && !r.fused);
    for (int i = 0; i < 3; i++) r = tofJudgeFrame(&st, frame_near(10, 500, 0));
    CHECK(r.presence_state && st.motion_latch == 72 && r.fused); // 둘 다 → true
    for (int i = 0; i < 3; i++) r = tofJudgeFrame(&st, frame_near(0, 0, 0));
    CHECK(!r.presence_state && st.motion_latch == 69 && !r.fused);// presence 가 먼저 끊김(9.4(d) 사례)
  }

  // ── T8 ndet 임계 = 1 (0 은 비검출) + 출력 echo ──
  {
    TofJudgeState st;
    TofFrameResult r = tofJudgeFrame(&st, frame_near(3, 500, 0));
    CHECK(st.motion_latch == 0 && r.motion_ndet == 0 && r.near_count == 3);
    r = tofJudgeFrame(&st, frame_near(3, 500, 16));
    CHECK(st.motion_latch == 75 && r.motion_ndet == 16);
  }

  // ── T9 로그 cadence: B-1 줄은 15프레임마다(verbatim 1회) ──
  {
    TofJudgeState st;
    Serial.lines = 0;
    for (int i = 0; i < 14; i++) tofJudgeFrame(&st, frame_near(0, 0));
    const unsigned before = Serial.lines;
    tofJudgeFrame(&st, frame_near(0, 0));                       // #15 (nb_of_aggregates=16)
    CHECK(Serial.lines == before + 1);
    CHECK(strcmp(Serial.last, "[tof][StageB-1] mi: g1=0 ndet=0/16 st=0 aggmax=0 | near=0/64 center=n/a\n") == 0);
  }

  printf("tofJudgeFrame: %d checks OK (9 groups)\n", checks);
  return 0;
}
