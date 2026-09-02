// 띵동 PoC firmware - ToF 더미 테스트 (5/11, PoC Day 5)
//
// tofTask 단독: isDataReady 폴링 + 64 zone 거리 추출 + Stage A 사람 존재 판정.
// 2026-08-07 브레드보드 브링업 성공(카테고리 9.1)으로 실측 단계 진입.
// 2026-08-08 ④런타임 실측에서 임계 경계 플리커 확인 → presence에 N=3 대칭 디바운스 도입.
// Stage B-1(Motion Indicator 계측 계층): motion 값을 관측·로그로만 노출(presence 판정 무변경).
// 2026-09-02 Stage B-2(판정 계층) 추가: B-1이 관측하던 ndet를 임계 판정으로 승격하고,
//   motion latch(이벤트 보존)와 Stage A presence를 프레임 단위 AND로 융합한다.
//   ★ B-1 계측 로직·감시창·로그 포맷은 0라인 변경 — B-2는 그 출력을 소비만 한다.
// 5/21 PoC 통합 시 cameraTask(Core 1) + micTask(Core 0, prio 4) + tofTask(Core 0, prio 3)
// 병행 검증 (decisions.md 카테고리 14).

#include "tof_common.h"

extern SparkFun_VL53L5CX tofImager;

// target_status가 valid(5 또는 9)인지 판정 — Stage A near-count/center 공통 술어.
// VL53L5CX datasheet: 5 = range valid, 9 = range valid(large pulse). 그 외는 폐기.
static inline bool tofStatusValid(uint8_t status) {
  return status == TOF_STATUS_VALID || status == TOF_STATUS_VALID_LARGE;
}

// ── Stage B-2 순수 술어/갱신자 ──────────────────────────────────────────────
// 배치 근거(학습 16): 판정 술어는 tof_common.cpp가 아니라 본 파일의 static inline이
//   기존 컨벤션이다(위 tofStatusValid, 아래 Stage A 판정 전부 본 파일). tof_common.cpp는
//   init·진단 전용이며 판정 로직 0건 — 여기에 B-2를 넣으면 계층이 섞인다.
//   상태(latch 카운터)도 Stage A presence_state와 동일하게 tofTask 내 static으로 두어
//   "전역 변수 신설 없이 유지"라는 기존 설계 의도를 그대로 따른다.

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

static void tofTask(void* parameter) {
  (void)parameter;
  logToFMemoryDiagnostics("tofTask-entry");

  // ResultsData ~1356B (SparkFun 주석 인용). task 스택(6KiB) 폭주 방지로 static (BSS).
  static VL53L5CX_ResultsData measurementData;
  uint32_t frame_count = 0;
  uint32_t err_count   = 0;

  // presence 디바운스 상태는 tofTask 내 static (BSS) — 전역 변수 신설 없이 유지.
  //   presence_state  = 디바운스 통과한 "확정" 상태 (로그·요약이 참조하는 값)
  //   presence_streak = 확정 상태와 다른 raw 판정이 몇 프레임 연속됐는지 카운터
  // 초기값: NONE(false) / 0. 부팅 직후 물체가 있으면 3프레임 뒤 DETECTED로 전환됨(정상).
  static bool    presence_state  = false;
  static uint8_t presence_streak = 0;

  // Stage B-2 latch 상태 — presence와 동일하게 tofTask 내 static (BSS).
  //   ★ raw vs 확정 네이밍 분리(선례: raw_presence vs presence_state):
  //     raw_motion         = "이번 프레임에 motion 검출됨"      (프레임 지역 변수, 아래 루프 내)
  //     motion_latch       = 남은 유지 프레임 수 (0 = 만료)
  //     motion_latch_active= "최근에 움직여서 온 상태"          (= motion_latch > 0)
  //     fused_state        = presence_state && motion_latch_active 의 직전 프레임 값(전이 감지용)
  //   초기값 0/false: 부팅 직후에는 아직 motion 이력이 없으므로 latch 만료 상태가 정상이다
  //   (정지 사물 앞에서 부팅해도 fused는 false로 시작 — 오탐 없음).
  static uint8_t  motion_latch = 0;
  static bool     fused_state  = false;

  for (;;) {
    if (tofImager.isDataReady()) {
      if (tofImager.getRangingData(&measurementData)) {
        frame_count++;

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
        if (raw_presence != presence_state) {
          if (++presence_streak >= TOF_PRESENCE_DEBOUNCE_FRAMES) {
            presence_state  = raw_presence;   // 확정 상태 전환
            presence_streak = 0;              // 전환 즉시 리셋
            transitioned    = true;
          }
        } else {
          presence_streak = 0;                // 확정 상태 유지 프레임 → 카운터 리셋
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
                        presence_state ? "NONE" : "DETECTED",   // 전환 전 = !presence_state
                        presence_state ? "DETECTED" : "NONE",
                        (unsigned)near_count, (unsigned)TOF_ZONE_COUNT, center_str,
                        (unsigned)TOF_PRESENCE_DEBOUNCE_FRAMES);
        } else if ((frame_count % TOF_LOG_EVERY_N_FRAMES) == 1) {
          Serial.printf("[tof][StageA] frame #%u near=%u/%u presence=%s center=%s\n",
                        (unsigned)frame_count, (unsigned)near_count, (unsigned)TOF_ZONE_COUNT,
                        presence_state ? "DETECTED" : "NONE", center_str);
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
        if ((frame_count % TOF_MOTION_LOG_EVERY_N_FRAMES) == 0) {
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

        motion_latch = tofMotionLatchStep(motion_latch, raw_motion);
        const bool motion_latch_active = (motion_latch > 0);

        // 융합에는 Stage A의 "확정" 상태(presence_state)만 쓴다. raw_presence를 쓰면 A의 디바운스가
        //   무효화된다 — A 판정 함수·임계값·디바운스는 호출만 하고 내부를 건드리지 않는다(회귀 대상).
        const bool fused = tofFusedPresent(presence_state, motion_latch_active);
        const bool fused_transitioned = (fused != fused_state);
        fused_state = fused;

        // 로그 정책: 상태가 실제로 바뀔 때만 1줄(B-1 게이트 패턴과 동일한 도배 방지 취지이나,
        //   여기서는 주기가 아니라 전이 조건이다 — 판정 계층은 곡선이 아니라 사건이 관측 대상).
        // frame# 병기 이유: 진입/만료 두 줄의 frame# 차 ÷ 15 = latch 실지속 초 → ④런타임에서
        //   latch 파라미터(논증값 75)를 실측으로 재조정할 유일한 관측 수단이다.
        // near·center 동반: 측정 조건이 수치와 함께 이동한다(9.2(d) 8→20 교훈).
        if (fused_transitioned) {
          Serial.printf("[tof][StageB-2] fused #%u: %s -> %s "
                        "(presence=%s, latch=%u/%u, ndet=%u, near=%u/%u, center=%s)\n",
                        (unsigned)frame_count,
                        fused ? "NONE" : "PERSON",
                        fused ? "PERSON" : "NONE",
                        presence_state ? "DETECTED" : "NONE",
                        (unsigned)motion_latch, (unsigned)TOF_MOTION_LATCH_FRAMES,
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
      } else {
        if ((++err_count % 10) == 1) {
          Serial.printf("[tof] getRangingData failed #%u\n", (unsigned)err_count);
        }
      }
    }
    // 67ms (15Hz). datasheet 권장 폴링 간격. OnlyFeet은 5ms 폴링이지만 본 작업은 정확한 주기.
    vTaskDelay(pdMS_TO_TICKS(TOF_PERIOD_MS));
  }
}

void setup() {
  Serial.begin(115200);
  delay(TOF_SERIAL_BOOT_DELAY_MS);
  Serial.printf("\n[BOOT] ddingdong tof test (VL53L5CX %ux%u, %uHz, I2C %lukHz)\n",
                (unsigned)TOF_GRID_SIZE, (unsigned)TOF_GRID_SIZE,
                (unsigned)TOF_RANGING_FREQ_HZ,
                (unsigned long)(TOF_I2C_FREQ_HZ / 1000));

  if (!initToF()) {
    Serial.println("[BOOT] tof init failed — task spawn 생략, loop()에서 idle 진단만 출력");
    return;  // graceful: 무한 루프 X. loop()에서 주기적 메모리 로그.
  }

  xTaskCreatePinnedToCore(tofTask, "tofTask",
                          TOF_TASK_STACK_SIZE, nullptr,
                          TOF_TASK_PRIORITY, nullptr,
                          TOF_TASK_CORE);
  Serial.println("[BOOT] tofTask started on Core 0 priority 3");
}

void loop() {
  // 정상 부팅 시 task가 모든 작업 수행 → loop는 idle.
  // init 실패 시 (부품 부재) 메모리 진단만 주기 출력.
  static uint32_t last_log = 0;
  const uint32_t now = millis();
  if ((now - last_log) >= TOF_LOOP_IDLE_LOG_MS) {
    last_log = now;
    logToFMemoryDiagnostics("loop-idle");
  }
  delay(100);
}
