// 띵동 PoC firmware - ToF 공통 구현 (5/11, PoC Day 5)

#include "tof_common.h"
// Stage B-1: SparkFun 래퍼는 motion 전용 메서드 0건 → 번들 ULD 함수를 직접 include하여
//   tofImager.Dev(public VL53L5CX_Configuration*) 핸들로 호출(decisions.md 카테고리 9 판정 B).
#include <vl53l5cx_plugin_motion_indicator.h>

// 외부에서 tofTask가 접근하는 imager 인스턴스. mic_common의 i2s 핸들과 동일 패턴.
SparkFun_VL53L5CX tofImager;

// Stage B-1: Motion Indicator를 센서에 프로그래밍. begin() 성공(=Dev 할당) 이후에만 호출.
//   VL53L5CX_Motion_Configuration(~156B)은 프로그래밍 시점에만 필요하고 set_distance_motion이
//   device로 write하면(motion_indicator.cpp:124) 이후 결과는 ResultsData.motion_indicator로 들어온다.
//   → 영구 BSS로 상주시킬 필요가 없어 함수 로컬(전이 스택)로 둔다. 런타임 RAM 순증 0 목표.
bool initToFMotionIndicator() {
  if (tofImager.Dev == nullptr) {
    Serial.println("[tof][StageB-1] motion init skipped — Dev 미할당(begin 미완)");
    return false;
  }

  VL53L5CX_Motion_Configuration motionConfig;

  // init: 기본 config + 8x8 aggregate map 구성(내부적으로 set_resolution 호출). resolution은 센서와 정합.
  uint8_t status = vl53l5cx_motion_indicator_init(
      tofImager.Dev, &motionConfig, VL53L5CX_RESOLUTION_8X8);

  // set_distance_motion: 감시 거리창을 확정하며 config 전체를 device로 write(=실제 활성화 지점).
  //   400~1500mm = ST ULD 문서화 기본값(판정 임계값 아님, 근거 = tof_common.h TOF_MOTION_DIST_* 주석).
  status |= vl53l5cx_motion_indicator_set_distance_motion(
      tofImager.Dev, &motionConfig, TOF_MOTION_DIST_MIN_MM, TOF_MOTION_DIST_MAX_MM);

  if (status == VL53L5CX_STATUS_OK) {
    Serial.printf("[tof][StageB-1] motion indicator ready (8x8, %u~%umm, %u aggregates)\n",
                  (unsigned)TOF_MOTION_DIST_MIN_MM, (unsigned)TOF_MOTION_DIST_MAX_MM,
                  (unsigned)TOF_MOTION_AGG_COUNT_8X8);
    return true;
  }
  // 실패해도 Stage A는 계속 — 여기서 return false는 로깅용이며 initToF() 반환을 죽이지 않는다.
  Serial.printf("[tof][StageB-1] motion init failed (status=%u) — Stage A는 계속 동작\n",
                (unsigned)status);
  return false;
}

void logToFMemoryDiagnostics(const char* tag) {
  // 5/12 메모리 self-checkpoint 입력 데이터 (decisions.md 카테고리 17.1.1).
  Serial.printf("[MEM:%s] PSRAM total=%u free=%u | Heap free=%u min=%u\n",
                tag,
                (unsigned)ESP.getPsramSize(),
                (unsigned)ESP.getFreePsram(),
                (unsigned)ESP.getFreeHeap(),
                (unsigned)ESP.getMinFreeHeap());
}

bool initToF() {
  logToFMemoryDiagnostics("pre-init");

  // ESP32-S3 GPIO 매핑 + I2C 클럭(TOF_I2C_FREQ_HZ = 400kHz, 2026-08-07 실측 정식 채택).
  // 정정: 구 "1MHz 워크어라운드" 주석은 8/07 브링업 실측(카테고리 9.1)으로 무효 — 상수 단일 출처 참조.
  Wire.begin(TOF_SDA_PIN, TOF_SCL_PIN);
  Wire.setClock(TOF_I2C_FREQ_HZ);
  Serial.printf("[tof] I2C ready (SDA=GPIO%d/SCL=GPIO%d, clock=%uHz)\n",
                TOF_SDA_PIN, TOF_SCL_PIN, (unsigned)TOF_I2C_FREQ_HZ);

  // OnlyFeet 패턴: 2회 retry. SparkFun begin()이 내부적으로 ~86KB FW upload 수행 (수 초 소요).
  // SparkFun begin()은 8-bit 주소(0x52) → 7-bit shift (DEFAULT_I2C_ADDR >> 1 = 0x29) 기본값.
  for (int attempt = 0; attempt < TOF_INIT_RETRY_MAX; attempt++) {
    if (attempt > 0) {
      Serial.printf("[tof] retry init (%d/%d)...\n", attempt + 1, TOF_INIT_RETRY_MAX);
    }
    if (tofImager.begin()) {
      // 8x8 mode (datasheet RESOLUTION_8X8 = 64).
      tofImager.setResolution(TOF_ZONE_COUNT);
      // 15Hz @ 8x8 (datasheet limit, SparkFun Example3 패턴).
      tofImager.setRangingFrequency(TOF_RANGING_FREQ_HZ);
      // Stage B-1: motion 설정은 startRanging 이전에(ST 시퀀스). best-effort — 실패해도 아래로 계속.
      initToFMotionIndicator();
      tofImager.startRanging();
      Serial.printf("[tof] VL53L5CX ready (%dx%d, %uHz, continuous)\n",
                    TOF_GRID_SIZE, TOF_GRID_SIZE, TOF_RANGING_FREQ_HZ);
      logToFMemoryDiagnostics("post-init");
      return true;
    }
    Serial.printf("[tof] init failed (attempt %d/%d)\n", attempt + 1, TOF_INIT_RETRY_MAX);
  }

  // OnlyFeet 진단 패턴: 실패 시 I2C scan으로 부품 부재/배선 오류 구분.
  Serial.println("[tof] I2C bus scan:");
  bool anyDevice = false;
  for (uint8_t addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.printf("[tof]   device at 0x%02X\n", addr);
      anyDevice = true;
    }
  }
  if (!anyDevice) {
    Serial.println("[tof]   no devices on bus (부품 부재 상태 추정)");
  }
  return false;
}

// ============================================================================
// === Stage A/B-2 판정 (2026-09-11 PoC-(45) 승격 — tof_test.cpp 에서 순수 이동) ===
// ============================================================================
// 아래 술어 4개 + tofJudgeFrame 본문은 종전 tof_test.cpp(HEAD b3414a4) 17~52행 / 84~240행을
// 식별자 접두()·들여쓰기 외 0변경으로 옮긴 것이다. 배치 정정 근거 = tof_common.h 동명 블록.

// target_status가 valid(5 또는 9)인지 판정 — Stage A near-count/center 공통 술어.
// VL53L5CX datasheet: 5 = range valid, 9 = range valid(large pulse). 그 외는 폐기.
static inline bool tofStatusValid(uint8_t status) {
  return status == TOF_STATUS_VALID || status == TOF_STATUS_VALID_LARGE;
}

// ── Stage B-2 순수 술어/갱신자 ──────────────────────────────────────────────
// 배치: 종전(PR #39)에는 "판정 술어 = tof_test.cpp static inline / tof_common.cpp = init·진단
//   전용"이 컨벤션이었으나 2026-09-11 사용자 확정(D2)으로 본 파일로 순수 이동했다 — 근거는
//   tof_common.h "Stage A/B-2 판정 상태·출력" 블록. 상태(latch 카운터·presence)는 종전 tofTask
//   내 static 을 TofJudgeState 로 묶어 호출부(tofTask)가 static 으로 소유한다(전역 신설 없음).

// 이번 프레임에 motion이 검출됐는가 = "raw" 판정. latch 활성 여부와 다른 개념이다.
//   ndet(nb_of_detected_aggregates, uint8_t)는 device가 자체 산출한 공간 검출 수 → 0..16.
static inline bool tofMotionRawDetected(uint8_t ndet) {
  return ndet >= TOF_MOTION_NDET_MIN;
}

// latch 갱신: 검출되면 만충 재충전, 아니면 1프레임 감쇠(0에서 멈춤).
//   ★ Stage A 디바운스와 반대 방향 — A는 "연속 충족"을 세고, 여기는 "최근 검출"을 태운다.
//   값 도메인: 입출력 모두 [0, TOF_MOTION_LATCH_FRAMES]. 재충전은 대입(산술 없음)이라 오버플로 불가,
//              감쇠는 >0 가드 뒤에서만 수행하므로 언더플로 불가.
static inline uint8_t tofMotionLatchStep(uint8_t latch, bool raw_motion) {
  if (raw_motion) return TOF_MOTION_LATCH_FRAMES;
  return (latch > 0) ? (uint8_t)(latch - 1) : (uint8_t)0;
}

// 융합 판정: 프레임 단위 AND. ★ zone 인덱스 매칭이 아니다.
//   근거 = Stage A는 8x8 zone(64) 단위인데 motion은 4x4 aggregate(16, 각 2x2 super-zone) 단위라
//          "near로 잡힌 그 zone이 움직이는가"를 1:1로 물을 수 없다(decisions.md 카테고리 9 설계 파급).
//          사람과 정지 사물이 같은 super-zone에 겹치면 분리가 원리적으로 불가하므로,
//          해상도를 억지로 맞추는 대신 프레임 전체에 대한 두 명제의 논리곱으로만 판정한다.
static inline bool tofFusedPresent(bool presence_state, bool latch_active) {
  return presence_state && latch_active;
}

TofFrameResult tofJudgeFrame(TofJudgeState* st, const VL53L5CX_ResultsData& measurementData) {
  st->frame_count++;

  // ── Stage A 사람 존재 판정 (decisions.md 카테고리 9 Stage A: "1m 이내 ≥8 zone") ──
  // 64 zone을 프레임당 단일 패스로 순회. NB_TARGET_PER_ZONE=1이라 zone i = 배열 인덱스 i.
  uint8_t  near_count   = 0;   // 최대 64 → uint8_t(255)로 오버플로 불가
  uint32_t center_sum   = 0;   // 최대 4 × ~4000mm = 16000 → uint32_t 여유
  uint8_t  center_valid = 0;

  for (uint16_t i = 0; i < TOF_ZONE_COUNT; i++) {
    if (!tofStatusValid(measurementData.target_status[i])) continue;
    const int16_t mm = measurementData.distance_mm[i];  // 라이브러리가 음수 0 클램프 완료
    // 1m(1000mm) 이내 且 0 초과만 근접 zone으로 채택.
    if (mm > 0 && mm <= TOF_PRESENCE_DIST_MM) {
      near_count++;
    }
  }
  // valid zone 0개 프레임(센서 시야 전체 무효)이어도 near_count=0 → raw=false로 정상 처리.
  // ★ raw 판정 로직은 PR #34 원형 그대로(변경 금지). 아래 디바운스는 그 위에 얹는 안정화 계층.
  const bool raw_presence = (near_count >= TOF_PRESENCE_MIN_ZONES);

  // ── 디바운스: raw가 확정 상태와 "다른" 프레임이 N회 연속돼야 확정 상태를 전환(진입/이탈 대칭) ──
  // 오버플로 안전: presence_streak는 이 if 분기에서만 +1 되고, N에 "도달"하는 즉시 0으로 리셋.
  //   → 프레임 종료 시 값은 항상 {0,1,2} 중 하나(N=3). else 분기도 0으로 리셋. uint8_t 상한과 무관.
  bool transitioned = false;
  if (raw_presence != st->presence_state) {
    if (++st->presence_streak >= TOF_PRESENCE_DEBOUNCE_FRAMES) {
      st->presence_state  = raw_presence;   // 확정 상태 전환
      st->presence_streak = 0;              // 전환 즉시 리셋
      transitioned    = true;
    }
  } else {
    st->presence_streak = 0;                // 확정 상태 유지 프레임 → 카운터 리셋
  }

  // center 4 zones: valid(status 5/9) 且 거리 유효(>0)한 것만 평균 → 침입자 거리 메트릭.
  for (uint8_t k = 0; k < 4; k++) {
    const uint16_t z = TOF_CENTER_ZONES[k];
    if (!tofStatusValid(measurementData.target_status[z])) continue;
    const int16_t mm = measurementData.distance_mm[z];
    if (mm > 0) {
      center_sum += (uint32_t)mm;
      center_valid++;
    }
  }
  // ★ division by zero 가드: valid center zone 0개면 평균 생략하고 "n/a" 표기.
  char center_str[12];
  if (center_valid > 0) {
    snprintf(center_str, sizeof(center_str), "%umm",
             (unsigned)(center_sum / center_valid));
  } else {
    snprintf(center_str, sizeof(center_str), "n/a");
  }

  // 로그 정책: 확정 상태가 "실제로 전환"될 때만 1줄(raw 변동으로는 출력 안 함),
  //            그 외엔 30프레임 주기 요약(확정 상태 표시, 매 프레임 출력 금지).
  // streak=N은 전환을 성립시킨 연속 프레임 수(전환 직후 카운터는 0으로 리셋됨).
  if (transitioned) {
    Serial.printf("[tof][StageA] presence: %s -> %s (near=%u/%u, center=%s, streak=%u)\n",
                  st->presence_state ? "NONE" : "DETECTED",   // 전환 전 = !presence_state
                  st->presence_state ? "DETECTED" : "NONE",
                  (unsigned)near_count, (unsigned)TOF_ZONE_COUNT, center_str,
                  (unsigned)TOF_PRESENCE_DEBOUNCE_FRAMES);
  } else if ((st->frame_count % TOF_LOG_EVERY_N_FRAMES) == 1) {
    Serial.printf("[tof][StageA] frame #%u near=%u/%u presence=%s center=%s\n",
                  (unsigned)st->frame_count, (unsigned)near_count, (unsigned)TOF_ZONE_COUNT,
                  st->presence_state ? "DETECTED" : "NONE", center_str);
  }

  // ── Stage B-1 계측 계층: Motion Indicator 관측 (★ presence 판정 무변경, 관측 전용) ──
  // motion 초기화 = tof_common.cpp initToFMotionIndicator()가 begin 직후 프로그래밍.
  //   VL53L5CX_DISABLE_MOTION_INDICATOR 매크로는 platform.h에서 주석 상태(=활성)로 배포되어
  //   .motion_indicator 필드가 상주한다(2026-08-12 sha256 확인, 매크로 패치 불필요).
  // ★ 관측 통계 선정 근거: device-native 전역값(global_indicator_1 = 전역 motion 크기,
  //   nb_of_detected_aggregates = device 자체 공간 검출 수, status = 결과 유효성)이 B-2 임계값의
  //   1차 후보이고, 여기에 활성 aggregate 16개의 피크(aggmax)를 더해 공간 국소성을 본다.
  //   로그에 near_count·center를 반드시 동반시켜 측정 조건이 수치와 함께 이동한다(9.2(d) 8→20 교훈).
  // serial flood 방지: 매 프레임이 아니라 TOF_MOTION_LOG_EVERY_N_FRAMES 주기로만 출력.
  if ((st->frame_count % TOF_MOTION_LOG_EVERY_N_FRAMES) == 0) {
    const auto& mi = measurementData.motion_indicator;
    // motion[]은 aggregate 단위(8x8 = 16개, motion[16..31] 미사용). max는 합이 아니라 피크라 오버플로 불가.
    uint32_t agg_motion_max = 0;
    for (uint8_t a = 0; a < TOF_MOTION_AGG_COUNT_8X8; a++) {
      if (mi.motion[a] > agg_motion_max) agg_motion_max = mi.motion[a];
    }
    Serial.printf("[tof][StageB-1] mi: g1=%lu ndet=%u/%u st=%u aggmax=%lu | near=%u/%u center=%s\n",
                  (unsigned long)mi.global_indicator_1,
                  (unsigned)mi.nb_of_detected_aggregates, (unsigned)mi.nb_of_aggregates,
                  (unsigned)mi.status, (unsigned long)agg_motion_max,
                  (unsigned)near_count, (unsigned)TOF_ZONE_COUNT, center_str);
  }

  // ── Stage B-2 판정 계층: motion latch + presence 융합 (2026-09-02) ──
  // ✅ [해소] 구 defer("임계값 확정 + presence 융합은 본 PR 범위 밖")는 본 블록으로 해소.
  //   당시 defer가 지정한 4종 대조 실험은 2026-08-12에 5종으로 수행됐고(decisions.md 9.3(c)),
  //   그 실측표로 임계값을 확정했다 — 판정 근거표는 tof_common.h TOF_MOTION_NDET_MIN 주석에 각인.
  //   당시 "③에서 motion ≈ ② 이면 Stage C(NanoEdge AI) 승격 검토" 조건은 ③이 실제로 ndet=0으로
  //   ②와 동일하게 나왔으나, 원인이 "Stage B 무효"가 아니라 "motion은 속도 의존"(9.3(d)-2)임이
  //   밝혀져 Stage C 승격이 아니라 본 latch 구조로 대응한다.
  //
  // ★ 매 프레임 갱신한다 — 위 B-1 로그 게이트(15프레임 주기) 안이 아니다.
  //   latch는 "최근 N프레임 중 1회라도"를 세므로 15프레임 중 14프레임을 건너뛰면 검출을 놓친다.
  //   그래서 B-1 블록을 옮기지 않고 여기서 motion_indicator를 독립적으로 다시 참조한다
  //   (const 참조라 주소 계산이 컴파일 타임 상수 오프셋 → 런타임 비용 0, B-1 코드 0라인 변경).
  const bool raw_motion = tofMotionRawDetected(
      measurementData.motion_indicator.nb_of_detected_aggregates);

  st->motion_latch = tofMotionLatchStep(st->motion_latch, raw_motion);
  const bool motion_latch_active = (st->motion_latch > 0);

  // 융합에는 Stage A의 "확정" 상태(presence_state)만 쓴다. raw_presence를 쓰면 A의 디바운스가
  //   무효화된다 — A 판정 함수·임계값·디바운스는 호출만 하고 내부를 건드리지 않는다(회귀 대상).
  const bool fused = tofFusedPresent(st->presence_state, motion_latch_active);
  const bool fused_transitioned = (fused != st->fused_state);
  st->fused_state = fused;

  // 로그 정책: 상태가 실제로 바뀔 때만 1줄(B-1 게이트 패턴과 동일한 도배 방지 취지이나,
  //   여기서는 주기가 아니라 전이 조건이다 — 판정 계층은 곡선이 아니라 사건이 관측 대상).
  // frame# 병기 이유: 진입/만료 두 줄의 frame# 차 ÷ 15 = latch 실지속 초 → ④런타임에서
  //   latch 파라미터(논증값 75)를 실측으로 재조정할 유일한 관측 수단이다.
  // near·center 동반: 측정 조건이 수치와 함께 이동한다(9.2(d) 8→20 교훈).
  if (fused_transitioned) {
    Serial.printf("[tof][StageB-2] fused #%u: %s -> %s "
                  "(presence=%s, latch=%u/%u, ndet=%u, near=%u/%u, center=%s)\n",
                  (unsigned)st->frame_count,
                  fused ? "NONE" : "PERSON",
                  fused ? "PERSON" : "NONE",
                  st->presence_state ? "DETECTED" : "NONE",
                  (unsigned)st->motion_latch, (unsigned)TOF_MOTION_LATCH_FRAMES,
                  (unsigned)measurementData.motion_indicator.nb_of_detected_aggregates,
                  (unsigned)near_count, (unsigned)TOF_ZONE_COUNT, center_str);
  }

  // ── Stage B-2 잔여 defer (미구현으로 남기는 것 + 각 판정 방법) ──
  // (1) ⚠️ 문 앞에 오래 서 있는 경우 latch 만료 후 거동 — 미검증.
  //     현상 예측: 접근 시 fused=PERSON → 75프레임(5초) 정지 후 latch 만료 → fused=NONE으로
  //       내려앉는다. presence는 DETECTED로 남으므로 "사람이 있는데 없다고 판정"하는 미탐이다.
  //     ★ 판정 방법: ④런타임 프로토콜 ③④를 수행해 (i) fused 만료 전이 로그의 frame#와
  //       (ii) 학부생이 초시계로 잰 "도착 → 초인종 누름" 소요를 대조한다.
  //       (ii) < (i)이면 실사용상 무해(누름이 만료보다 빠름) → 현행 유지.
  //       (ii) > (i)이면 미탐이 실재 → TOF_MOTION_LATCH_FRAMES 상향 또는
  //       "presence 유지 중에는 latch 감쇠를 멈춘다"(hold-while-present) 규칙 도입을 검토.
  //       후자는 정지 사물 오탐을 되살릴 수 있으므로 ②정지 사물 프로토콜 재실행이 전제다.
  // (2) ⚠️ 벽면 실사용 환경 정확도 — 미측정 (decisions.md 9.3(G) 미결 그대로 상속).
  //     9.2 거리-near 곡선도 9.3(c) motion 실측도 전부 실내 책상/바닥 환경이라,
  //       현관 부착 시 벽·문틀 반사가 near_count와 ndet에 주는 영향은 알려진 바 없다.
  //     ★ 판정 방법: 센서를 실제 현관 높이·각도로 고정한 뒤 ④런타임 프로토콜 ①②를
  //       그대로 재실행한다. ①무자극에서 near>0 또는 ndet>0이 상시로 나오면 벽 반사 오염이
  //       확정이므로, 임계값이 아니라 설치 각도/TOF_PRESENCE_DIST_MM를 먼저 조정한다
  //       (임계값부터 손대면 9.2(d) 8→20 오판의 재판이 된다).
  // (3) ⚠️ motion_indicator.status 게이트 미도입 — 의도적 보류.
  //     B-1 로그는 st(status)를 찍지만 9.3(c) 실측표에 st 열이 없어 "어떤 값일 때 ndet를
  //       신뢰하는가"의 근거가 없다. 근거 없는 게이트는 §7-3 위반이라 넣지 않았다.
  //     정황 근거로는 ①②③=0 / ④⑤=1~6이라는 물리 정합이 나온 것 자체가 status 유효를
  //       간접 실증한다(무효였다면 그런 분리가 나올 수 없다).
  //     ★ 판정 방법: ④런타임에서 B-1 로그의 st 값 분포를 수집한다. 전 구간 동일 상수면
  //       게이트는 영구 불요. 특정 상황에서만 다른 값이 뜨고 그때 ndet가 물리와 어긋나면
  //       그 값을 invalid로 확정하고 게이트를 도입한다.

  // ── 출력 조립 (승격으로 추가된 부분 — 판정에 되먹이지 않는 읽기 전용 사본) ──
  TofFrameResult out;
  out.fused          = fused;
  out.presence_state = st->presence_state;
  out.near_count     = near_count;
  out.center_valid   = (center_valid > 0);
  out.center_mm      = (center_valid > 0) ? (uint16_t)(center_sum / center_valid) : (uint16_t)0;
  out.motion_ndet    = measurementData.motion_indicator.nb_of_detected_aggregates;
  return out;
}
