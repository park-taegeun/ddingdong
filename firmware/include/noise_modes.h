// 띵동 firmware - mic_noiseprobe 모드 → 구성 매핑 (2026-09-11 PoC-(45), env:mic_noiseprobe 전용)
//
// ★ 성격 = 진단 하네스의 **관측 계층**(noise_stats.h 와 동형, decisions.md 카테고리 20
//   "계측 → 실측 → 판정" 분리). 여기엔 판정·임계값·해결책이 0줄이다. 구성만 낸다.
//
// ★ 왜 헤더로 뺐나 = 「한 번에 한 변수만」이 이 하네스의 전부인데, 그 불변식이 지금까지
//   applyMode() 안의 삼항 연산자에 흩어져 있어 호스트에서 검증할 수 없었다. Arduino 무의존
//   순수 함수로 표현해 firmware/tools/noise_modes_test.cpp 가 **같은 파일을 그대로** include 해
//   전 필드를 비교한다(noise_stats.h / tof_judge_test 선례 = 복사 아님).
//   ※ m0~m4 값은 기존 applyMode 의 want_rng/want_poll/want_hz/want_core 와 1:1 등가 — 동작 무변경.
//
// ★ sd_pd = INMP441 SD 라인(카테고리 2 핀 표: D8 = GPIO7)에 **내부 풀다운**을 거는가.
//   가설(근거유형 = 논증, 미실측): INMP441 은 LSB 출력 직후 SD 를 tri-state 하므로 데이터시트가
//   SD 에 100kΩ 풀다운을 권장한다. 6.3(n) 의 오류 비트가 워드 **앞쪽**(`7F…` MSB / 100k 의
//   `C0000000` 상위 2비트)에 몰리는 것은 "Hi-Z → 재구동 직후 샘플되는 비트" 위치와 일치한다.
//   m5/m6 는 **결선 변경 0**으로 그 가설을 가른다.
//   ⚠️ 6.3(n) 해결책(①펌웨어 필터 ②배선 조치 ③병행)은 **사용자 판단 대기** — 본 헤더는 판별 수단일 뿐이고
//      풀다운을 제품 경로에 넣지 않는다.
#pragma once

#include <stdint.h>

// 진단 모드 개수 (시리얼 '0'~'6')
constexpr int NOISE_MODE_N = 7;

// 한 모드의 전 구성. "한 변수만 다르다"를 필드 단위로 비교하려고 전부 값 필드다.
struct NoiseModeCfg {
  bool     ranging;   // ToF 측정(startRanging) ON/OFF
  bool     poll;      // 호스트 I2C 읽기(isDataReady/getRangingData) ON/OFF
  uint32_t i2c_hz;    // I2C 클럭
  int      core;      // 폴링 태스크 담당 코어
  bool     sd_pd;     // 마이크 SD 핀 내부 풀다운
};

// 모드 번호 → 구성. 범위 밖은 m0 와 같은 안전값(전부 OFF)을 돌려준다.
// fast_hz/slow_hz 를 인자로 받는 이유 = tof_common.h(Arduino 의존)를 호스트로 끌어오지 않기 위해.
inline NoiseModeCfg noiseModeCfg(int m, uint32_t fast_hz, uint32_t slow_hz) {
  NoiseModeCfg c = {false, false, fast_hz, 0, false};
  switch (m) {
    case 0: break;                                                       // 대조군: 측정 OFF / 통신 OFF
    case 1: c.ranging = true; break;                                     // H2 격리: 측정 ON / 통신 OFF
    case 2: c.ranging = true; c.poll = true; break;                      // 현행 재현: ON / ON 400k / core 0
    case 3: c.ranging = true; c.poll = true; c.i2c_hz = slow_hz; break;  // H1 엣지속도: 100k
    case 4: c.ranging = true; c.poll = true; c.core = 1; break;          // H3 코어경합: core 1
    case 5: c.ranging = true; c.poll = true; c.sd_pd = true; break;      // = m2 + SD 풀다운 (실험군)
    case 6: c.sd_pd = true; break;                                       // = m0 + SD 풀다운 (부작용 대조군)
    default: break;
  }
  return c;
}
