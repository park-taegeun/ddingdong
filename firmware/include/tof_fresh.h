// 띵동 firmware - 트리거 시점 ToF 값 신선도 판정 순수 계층 (env:enrich_uplink · env:enrich_autotrig)
//
// ★ 왜 있나 (감사 AU-01, 2026-10-13)
//   ToF 태스크는 새 프레임이 올 때만 최신 값 · 시각을 갱신한다. 센서가 부팅 뒤 동작 중에 멈추면 보드는
//   마지막 판정값을 계속 싣는다 — 그 값이 「사람 없음」이면 이후 초인종 · 노크가 서버에서 tof_rejected 로
//   조용히 막힌다(화재는 ToF 우회라 무관). 그래서 마지막 프레임 뒤 경과가 임계를 넘으면 「첫 프레임 전」과
//   같은 결과(4필드 미전송 → 서버 tof_absent → fail-open, decisions.md 6.4(c))로 보낸다.
//   보드에서 멈춤을 재현한 적은 없다(논증). 사용자 결정 2026-10-15.
//
// ★ 왜 Arduino 무의존 순수 헤더인가 (heartbeat_wire.h · auto_trig.h 선례)
//   호스트 테스트(firmware/tools/tof_fresh_test.cpp)가 같은 파일을 그대로 컴파일한다(복사 아님).
//   배선(크리티컬 섹션 복사 · 로그)은 enrich_uplink_main.cpp 의 captureTofAtTrigger 에 있다.
//
// ★ 여기에 없는 것
//   - ToF 태스크 재초기화 · 자가 복구 (별도 결정)
//   - 「모르면 보낸다」 기본값 — 판정이 안 되면 미전송 쪽이다(기존 fail-open 과 같은 방향)
#pragma once

#include <stdint.h>

// ── 멈춤 임계 ────────────────────────────────────────────────────────────────
// 마지막 프레임 뒤 경과 1,000ms 초과 = 멈춤. ★ 잠정.
// 근거: 지난 보드 로그 `[tof][e2|M5d] … age_ms=` 882건 · 최소 0 · 중앙 54 · 최대 103ms · 1000ms 초과 0건
//       (2026-10-15 재계산) ⇒ 이 임계였다면 잘못 걸린 건 0. 정상 프레임 간격 TOF_PERIOD_MS ≈ 67ms(15Hz)의 약 15배.
// 재판정 트리거: ① 정상 동작 중 멈춤 로그 관측 ② 센서 · 보드 교체 ③ TOF_RANGING_FREQ_HZ · TOF_PERIOD_MS 변경
//               ④ age_ms 분포 재수집에서 수백 ms 가 반복
constexpr uint32_t TOF_STALE_MS = 1000;

// 보드 배선 확인 전용 시험 임계. platformio.ini 는 건드리지 않고 PLATFORMIO_BUILD_FLAGS 로만 주입한다
// (예: PLATFORMIO_BUILD_FLAGS="-DTOF_STALE_MS_TEST_OVERRIDE=1"). 정의하지 않으면 TOF_STALE_MS 고정 —
// 빌드 시점에 둘 중 하나로 정해진다. 시험 빌드면 부팅 때 [BOOT] 경고 줄이 찍힌다(enrich_uplink_main.cpp).
#ifdef TOF_STALE_MS_TEST_OVERRIDE
constexpr uint32_t TOF_RUN_STALE_MS = (uint32_t)(TOF_STALE_MS_TEST_OVERRIDE);
#else
constexpr uint32_t TOF_RUN_STALE_MS = TOF_STALE_MS;
#endif

enum TofFresh : uint8_t {
  TOF_FRESH_SEND = 0,  // 4필드 전송
  TOF_FRESH_NO_TOF,    // init 실패 — 4필드 미전송
  TOF_FRESH_NO_FRAME,  // 첫 프레임 전(lastMs == 0) — 4필드 미전송
  TOF_FRESH_STALE,     // 마지막 프레임 뒤 경과 > 임계 — 4필드 미전송
};

// 분기 순서 = ToF 없음 → 첫 프레임 전 → 멈춤 → 전송 (로그가 가장 앞선 원인을 가리킨다).
// 경과 = 부호 없는 뺄셈 → millis() 49.7일 wrap 에서도 정확. 경과 == 임계는 정상(전송).
inline TofFresh tofFreshJudge(bool available, uint32_t lastMs, uint32_t nowMs) {
  if (!available) return TOF_FRESH_NO_TOF;
  if (lastMs == 0) return TOF_FRESH_NO_FRAME;
  if ((uint32_t)(nowMs - lastMs) > TOF_RUN_STALE_MS) return TOF_FRESH_STALE;
  return TOF_FRESH_SEND;
}
