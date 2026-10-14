// tof_fresh.h 호스트 검산 — 실제 firmware/include/tof_fresh.h 를 그대로 include 한다(복사 아님).
//   c++ -std=c++17 -Wall -I firmware/include -o /tmp/tft firmware/tools/tof_fresh_test.cpp && /tmp/tft
// (TOF_STALE_MS_TEST_OVERRIDE 없이 컴파일한다 — 기본 빌드 임계를 단언한다.)
//
// 이 하네스가 지켜야 할 불변식:
//   I1 경과 > 임계면 미전송(멈춤) · 경과 == 임계면 전송
//   I2 분기 순서 = ToF 없음 → 첫 프레임 전 → 멈춤 → 전송 (분류값으로 단언 — 셋 다 미전송이라 전송 여부만 보면 같다)
//   I3 millis() 49.7일 wrap 에서도 경과가 정확하다
//   I4 기본 빌드 임계 = 1,000ms
//
// ⚠️ 단언 무딤 함정:
//   - I1 은 경계 한 점만 보면 「멈춤 분기 제거」 와 「> → >=」 중 하나를 놓친다 → 임계 · 임계+1 둘 다 본다.
//   - I2 는 lastMs == 0 + 큰 now 케이스가 없으면 「멈춤 검사를 앞으로」 변형을 통과시킨다.
//   - I3 는 wrap 케이스가 없으면 부호 있는 비교 변형을 통과시킨다 → wrap 을 넘긴 멈춤 케이스를 둔다.
//
// 증명 범위 · 한계: 판정 함수만 본다. captureTofAtTrigger 가 이 함수를 부르는가 · 멈춤 로그 줄이 찍히는가
// (호출부 배선)는 호스트 사정권 밖 → 도달 불가, ENRICH_AUTOTRIG_RUNBOOK.md 12절 보드 확인 (b) 가 유일한 검출자.
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <initializer_list>

#include "tof_fresh.h"

static int checks = 0;
#define CHECK(x) do { assert(x); checks++; } while (0)

int main() {
  // T1 (I4) 기본 빌드 임계
  CHECK(TOF_STALE_MS == 1000);
  CHECK(TOF_RUN_STALE_MS == 1000);

  // T2 (I2) ToF 없음 — ms · now 가 무엇이든 ToF 없음
  for (uint32_t ms : {0u, 1u, 500u, UINT32_MAX}) {
    for (uint32_t now : {0u, 1u, 1000u, 1001u, 100000u, UINT32_MAX}) {
      CHECK(tofFreshJudge(false, ms, now) == TOF_FRESH_NO_TOF);
    }
  }

  // T3 (I2) 첫 프레임 전 — now 가 커서 「경과」 가 임계를 넘어도 멈춤이 아니다
  for (uint32_t now : {0u, 5u, 1000u, 1001u, 100000u, UINT32_MAX}) {
    CHECK(tofFreshJudge(true, 0, now) == TOF_FRESH_NO_FRAME);
  }

  // T4 (I1) 정상 — 관측 분포(0 · 54 · 103) · 정상 간격 67 · 경계 == 임계
  for (uint32_t age : {0u, 1u, 54u, 67u, 103u, 999u, 1000u}) {
    CHECK(tofFreshJudge(true, 5000, 5000 + age) == TOF_FRESH_SEND);
  }

  // T5 (I1) 멈춤 — 경계 + 1 · 큰 경과
  for (uint32_t age : {1001u, 1002u, 5000u, 3600000u}) {
    CHECK(tofFreshJudge(true, 5000, 5000 + age) == TOF_FRESH_STALE);
  }
  CHECK(tofFreshJudge(true, 1, UINT32_MAX) == TOF_FRESH_STALE);

  // T6 (I3) wrap — 마지막 프레임이 UINT32_MAX 근처 · 지금이 작은 값
  CHECK(tofFreshJudge(true, UINT32_MAX - 100, 50) == TOF_FRESH_SEND);    // 경과 151
  CHECK(tofFreshJudge(true, UINT32_MAX, 999) == TOF_FRESH_SEND);         // 경과 1000 (경계)
  CHECK(tofFreshJudge(true, UINT32_MAX, 1000) == TOF_FRESH_STALE);       // 경과 1001
  CHECK(tofFreshJudge(true, UINT32_MAX - 100, 900) == TOF_FRESH_STALE);  // 경과 1001
  CHECK(tofFreshJudge(true, UINT32_MAX - 2000, 5000) == TOF_FRESH_STALE);

  // T7 (I2) 분류 4종이 서로 다르다(로그 구분)
  CHECK(TOF_FRESH_SEND != TOF_FRESH_NO_TOF && TOF_FRESH_SEND != TOF_FRESH_NO_FRAME &&
        TOF_FRESH_SEND != TOF_FRESH_STALE && TOF_FRESH_NO_TOF != TOF_FRESH_NO_FRAME &&
        TOF_FRESH_NO_TOF != TOF_FRESH_STALE && TOF_FRESH_NO_FRAME != TOF_FRESH_STALE);

  printf("tof_fresh_test: %d checks OK\n", checks);
  return 0;
}
