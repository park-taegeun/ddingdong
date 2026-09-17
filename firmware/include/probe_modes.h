// 띵동 firmware - camera_probe 모드 → 구성 매핑 (2026-09-17, env:camera_probe 전용)
//
// ★ 성격 = 관측 계층(decisions.md 카테고리 20 "계측 → 실측 → 판정" 분리). 판정·임계값·해결책 0줄.
//   구성만 낸다. 어느 창이 "악화"인지는 사람이 CAMERA_PROBE_RUNBOOK.md 를 보고 판단한다.
//
// ★ 왜 헤더로 빼는가 = noise_modes.h 선례 그대로. 이 하네스의 전부는 「한 번에 한 변수만」인데,
//   그 불변식이 applyMode() 안의 분기에 흩어지면 호스트에서 검증할 수 없다. Arduino 무의존
//   순수 함수로 표현해 firmware/tools/camera_probe_test.cpp 가 **같은 파일을 그대로** include 해
//   인접 모드 전 쌍을 비교한다(noise_modes.h / tof_judge_test 선례 = 복사 아님).
//
// ★ 모드 사슬 설계 (왜 조합 전부가 아니라 사슬인가)
//   축 3개(카메라 4상태 × WiFi 2 × 해상도 2)를 전부 돌면 16 모드지만, 악화의 원인을 한 변수에
//   귀속하려면 필요한 것은 **인접 쌍의 차이가 1개인 경로**뿐이다. 아래 m0~m7 은 그 경로이며
//   probeModeAdjacentOk() 가 전 쌍에 대해 그 불변식을 강제한다(NC-4 대상).
//     m0 → m1  WiFi 송신만 켠다        (카메라 무관 = 전원·RF 단독 기여)
//     m1 → m2  카메라 init 만 (캡처 0) (init 자체 = XCLK·SCCB·PSRAM 점유의 기여)
//     m2 → m3  주기 캡처 (이벤트형)    (제품 2차 체인이 실제로 할 일)
//     m3 → m4  연속 캡처 (스트레스)    (상한 부하)
//     m4 → m5  WiFi 송신을 끈다        (역방향 재확인 — m0→m1 의 기여가 카메라 최대부하에서도 같은가)
//     m5 → m6  주기 캡처로 되돌린다    (캡처 방식 축의 역방향 — 연속에서 주기로 내려온다)
//     m6 → m7  해상도 VGA             (설계 U2 해상도 판단 입력)
//   ★ m6 = m3 에서 WiFi 송신만 뺀 구성(cam=PERIODIC/wifi=off/res=QVGA). m0~m5 에 같은 구성은 없다.
//      그래서 m6 은 두 역할을 겸한다 — 인접쌍 m5↔m6(캡처 방식) 과 **비인접쌍 m3↔m6(WiFi 송신)**.
//      비인접쌍은 probeModeChainOk() 가 보지 못하므로 PROBE_NONADJ_PAIRS 가 따로 고정한다.
//   ★ 재현성(관측이 돌아오는가) 확인 지점은 이 사슬 안이 아니라 CAMERA_PROBE_RUNBOOK.md 5절의
//      **마지막 m0 복귀**다 — 첫 m0 와 끝 m0 가 같은 자릿수로 돌아오지 않으면 그 세션의
//      모드 간 비교는 전부 무효다.
#pragma once

#include <stdint.h>

// 진단 모드 개수 (시리얼 '0'~'7')
constexpr int PROBE_MODE_N = 8;

// 카메라 상태. 값은 "부하 순서"대로 오름차순 — 사슬을 읽을 때 방향이 보이게.
enum ProbeCam : uint8_t {
  PROBE_CAM_OFF        = 0,  // esp_camera_deinit 상태 (드라이버 미기동)
  PROBE_CAM_IDLE       = 1,  // init 만. fb_get 0회
  PROBE_CAM_PERIODIC   = 2,  // PROBE_CAPTURE_PERIOD_MS 마다 1장
  PROBE_CAM_CONTINUOUS = 3,  // loop 가 도는 대로 계속
};

// 해상도. framesize_t(esp_camera) 를 그대로 쓰지 않는 이유 = 호스트 테스트가 Arduino/IDF 헤더를
// 끌어오지 않게 하기 위함(noise_modes.h 가 tof_common.h 를 피한 것과 같은 논증).
enum ProbeRes : uint8_t {
  PROBE_RES_QVGA = 0,  // 320x240 — camera_common.h CAMERA_DEFAULT_FRAMESIZE 와 동일
  PROBE_RES_VGA  = 1,  // 640x480
};

// 한 모드의 전 구성. "한 변수만 다르다"를 필드 단위로 비교하려고 전부 값 필드다.
struct ProbeModeCfg {
  uint8_t cam;      // ProbeCam
  bool    wifi_tx;  // UDP 더미 송신 부하 ON/OFF (WiFi 연결 자체는 부팅 시 1회, 모드와 무관)
  uint8_t res;      // ProbeRes
};

// 모드 번호 → 구성. 범위 밖은 m0 와 같은 안전값(전부 OFF)을 돌려준다.
inline ProbeModeCfg probeModeCfg(int m) {
  switch (m) {
    case 0: return {PROBE_CAM_OFF,        false, PROBE_RES_QVGA};
    case 1: return {PROBE_CAM_OFF,        true,  PROBE_RES_QVGA};
    case 2: return {PROBE_CAM_IDLE,       true,  PROBE_RES_QVGA};
    case 3: return {PROBE_CAM_PERIODIC,   true,  PROBE_RES_QVGA};
    case 4: return {PROBE_CAM_CONTINUOUS, true,  PROBE_RES_QVGA};
    case 5: return {PROBE_CAM_CONTINUOUS, false, PROBE_RES_QVGA};
    case 6: return {PROBE_CAM_PERIODIC,   false, PROBE_RES_QVGA};
    case 7: return {PROBE_CAM_PERIODIC,   false, PROBE_RES_VGA};
    default: return {PROBE_CAM_OFF, false, PROBE_RES_QVGA};
  }
}

// 두 구성의 상이 필드 수. ★ 비교는 여기 한 곳에서만 한다 — 필드를 하나라도 빠뜨리고 비교하면
//   실험이 조용히 무효가 되므로(noise_modes_test 의 diffCount 선례와 동일 논증).
inline int probeModeDiffCount(const ProbeModeCfg& a, const ProbeModeCfg& b) {
  return (a.cam != b.cam ? 1 : 0) + (a.wifi_tx != b.wifi_tx ? 1 : 0) + (a.res != b.res ? 1 : 0);
}

// 인접 쌍 (m, m+1) 이 정확히 한 변수만 다른가. m 은 [0, PROBE_MODE_N-1) 이어야 한다.
inline bool probeModeAdjacentOk(int m) {
  if (m < 0 || m + 1 >= PROBE_MODE_N) return false;
  return probeModeDiffCount(probeModeCfg(m), probeModeCfg(m + 1)) == 1;
}

// 전 인접 쌍 순회. ⚠️ 순회를 빠뜨린 쌍이 있으면 사슬이 조용히 깨지므로 호출부는 이 함수만 쓴다.
inline bool probeModeChainOk() {
  for (int m = 0; m + 1 < PROBE_MODE_N; ++m) {
    if (!probeModeAdjacentOk(m)) return false;
  }
  return true;
}

// ── 비인접 비교쌍 ────────────────────────────────────────────────────────────
// CAMERA_PROBE_RUNBOOK.md 6-1 비교표에는 사슬의 인접 쌍이 아닌 쌍이 섞여 있다(m3↔m6).
// 인접 쌍은 probeModeChainOk() 가 강제하지만 비인접 쌍은 아무도 안 본다 — 모드 테이블의 값을
// 누가 한 번 고치면 런북 표만 조용히 거짓이 된다(문서-코드 드리프트).
// ★ 단일 원천 = 이 배열. 런북 표에 비인접 쌍을 추가하면 여기에도 추가해야 호스트 테스트가 통과한다.
struct ProbeModePair { uint8_t a; uint8_t b; };

constexpr ProbeModePair PROBE_NONADJ_PAIRS[] = {
  {3, 6},   // WiFi 송신만 다름 — m0↔m1 · m4↔m5 에 이은 세 번째 대조
};
constexpr int PROBE_NONADJ_PAIR_N =
    (int)(sizeof(PROBE_NONADJ_PAIRS) / sizeof(PROBE_NONADJ_PAIRS[0]));

// i 번째 비인접 쌍이 정확히 한 변수만 다른가.
inline bool probeModeNonAdjOk(int i) {
  if (i < 0 || i >= PROBE_NONADJ_PAIR_N) return false;
  const ProbeModePair& p = PROBE_NONADJ_PAIRS[i];
  return probeModeDiffCount(probeModeCfg(p.a), probeModeCfg(p.b)) == 1;
}

// 전 비인접 쌍 순회. 인접 쌍과 겹치는 쌍이 들어오면(= 사슬이 이미 보는 쌍) 그것도 거짓으로 본다 —
// 표에 중복이 생기면 "세 번째 대조"라는 근거가 거짓이 되기 때문이다.
inline bool probeModeNonAdjPairsOk() {
  for (int i = 0; i < PROBE_NONADJ_PAIR_N; ++i) {
    const ProbeModePair& p = PROBE_NONADJ_PAIRS[i];
    if (p.a + 1 == p.b || p.b + 1 == p.a) return false;
    if (!probeModeNonAdjOk(i)) return false;
  }
  return true;
}
