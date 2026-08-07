// 띵동 firmware - ToF 라인 프로브 진단 하네스 (2026-08-07, PoC-(34) 전원/배선 실측 — 멀티미터 대체)
//
// 목적: VL53L5CX-SATEL 미검출의 잔존 후보 = "센서에 전원이 실제 공급되는가" 단 1건.
//   전압계가 없어 물리 측정을 못 함 → ESP32 GPIO를 전압 판별기로 사용해 이를 대체한다.
//   (PR #32 tof_pinscan은 I2C ACK 순서쌍 전수 스캔 → NONE FOUND. 신호선 배선은 배제됨.
//    본 하네스는 그 하위 계층 = 전원/도통 자체를 실측한다.)
//
// 원리 2가지:
//   (A) 외부 pull-up 검출 — 어떤 GPIO를 INPUT_PULLDOWN(내부 ~45kΩ 풀다운)으로 읽었을 때
//       HIGH면 그 라인에 내부 풀다운을 이기는 외부 pull-up(라이브 레일 기준)이 물려 있다는 뜻.
//       I2C 라인에 2.2k pull-up이 IOVDD로 물려 있고 IOVDD가 급전 중이면 HIGH → 전원+배선 동시 증명.
//       floating(미연결/무급전)이면 내부 풀다운이 이겨 LOW.  → 사실상 전압 측정.
//   (B) 도통 매트릭스 — GPIO A를 OUTPUT HIGH, GPIO B를 INPUT_PULLDOWN으로 읽어 HIGH면 A-B 도통.
//       → 점퍼 단선 / 브레드보드 구멍 접촉 불량을 실측으로 잡아냄. pull-up 유무와 무관하게 유효.
//
// ★ 진단 전용. 실제 플래시/관측/해석은 학부생 로컬 몫(하드웨어 런타임). 컴파일까지가 본 태스크.
// ★ 본 하네스는 SATEL 연결을 전제하지 않음 — 미연결로 돌려도 (B)는 유효(대조군 확보).
//
// 출처(설치 실물 + ST 공식 인용, 학습 13/15):
//   - variants/XIAO_ESP32S3/pins_arduino.h: D0=1 D1=2 D2=3 D3=4 D4=5 D5=6 D6=43(TX) D7=44(RX)
//       D8=7 D9=8 D10=9. (SDA=5, SCL=6 static const 도 동일 = SSoT 카테고리 2 일치.)
//   - cores/esp32/esp32-hal-gpio.h: INPUT_PULLUP=0x05, INPUT_PULLDOWN=0x09 (매크로 실존 확인).
//   - boards/seeed_xiao_esp32s3.json: ARDUINO_USB_CDC_ON_BOOT=1 → Serial=네이티브 USB CDC.
//       따라서 D6/D7(GPIO43/44=UART0 TX/RX)를 GPIO로 구동해도 모니터 로그는 유실 안 됨.
//   - VL53L5CX datasheet(DS13754) I2C 인터페이스 표: SDA/SCL 는 IOVDD 기준 2.2kΩ pull-up 필요,
//       "located on the host". SATEL 새틀라이트 보드는 호스트측 pull-up 전제 = SDA/SCL pull-up이
//       보드에 내장된다고 보장되지 않음(ST 커뮤니티 SATEL 사용자도 외부 2.2k 추가). LPn/I2C_RST/
//       INT/RSVD6 = IOVDD 기준 47kΩ pull-up 필요. → (A) 해석 유의: pull-up 검출은 "그 라인에
//       라이브 레일로의 pull-up이 실제 존재하는가"를 재므로, 학부생이 pull-up을 달아둔 경우 유효.
//       달지 않았으면 (A)는 floating으로 읽히고 (B) 도통 매트릭스가 배선 결함을 계속 격리한다.

#include <Arduino.h>

// === 후보 핀 (pins_arduino.h 실측 인용, 카테고리 1 strapping = D0/D3/D6/D7) ===
// PR #32 tof_pinscan_main.cpp의 PINS[] 구조 계승(학습 16 — 형제 하네스 컨벤션 일치).
struct PinCandidate {
  int         gpio;
  const char* dLabel;      // XIAO 실크 라벨
  bool        strapping;   // decisions.md 카테고리 1: D0/D3/D6/D7 회피 원칙
};

static const PinCandidate PINS[] = {
  {  1, "D0",  true  },   // strapping
  {  2, "D1",  false },
  {  3, "D2",  false },
  {  4, "D3",  true  },   // strapping
  {  5, "D4",  false },   // ← SSoT SDA
  {  6, "D5",  false },   // ← SSoT SCL
  { 43, "D6",  true  },   // strapping (UART0 TX, USB CDC라 로그 무영향)
  { 44, "D7",  true  },   // strapping (UART0 RX, USB CDC라 로그 무영향)
  {  7, "D8",  false },
  {  8, "D9",  false },
  {  9, "D10", false },
};
static const int PIN_COUNT = sizeof(PINS) / sizeof(PINS[0]);

// === 프로브 설정 (매직넘버 금지 — 전부 상수화) ===
static const int      PROBE_SAMPLES       = 5;    // floating 노이즈 오판 방지용 다수결 표본 수
static const uint32_t PROBE_SETTLE_US     = 200;  // pinMode 후 라인 안정화 (RC 정착)
static const uint32_t PROBE_INTERSAMPLE_US = 50;  // 표본 간 간격 (동일 순간 중복 표집 회피)
static const uint32_t PROBE_PHASE_GAP_MS  = 20;   // 단계/항목 사이 워치독 급양 + flush 여유
static const uint32_t PROBE_BOOT_DELAY_MS = 200;  // Serial.begin 후 (기존 컨벤션)
static const uint32_t PROBE_LOOP_IDLE_MS  = 5000; // loop() heartbeat 주기 (tof_test 일치)

// === PHASE 1 판정 결과 ===
enum LineState {
  LS_EXT_PULLUP,       // INPUT_PULLDOWN에서 HIGH = 외부 pull-up(라이브 레일) 존재 ★ 핵심 신호
  LS_FLOATING,         // pd LOW + pu HIGH = 미연결 또는 무급전 (내부 저항만 관여)
  LS_EXT_PULLDOWN_GND, // pd LOW + pu LOW = 외부 pull-down 또는 GND 단락
  LS_UNSTABLE,         // 표본 불일치 = floating 강한 후보 (오판 방지로 별도 분류)
};

// 한 GPIO를 특정 모드로 설정 후 PROBE_SAMPLES회 읽어 다수결/안정성 산출.
struct SampleResult {
  bool level;   // 다수결 논리값 (HIGH 우세)
  bool stable;  // 전 표본 동일 여부 (false = 노이즈로 튐 = floating 후보)
  int  highCnt; // HIGH 표본 수 (진단 로그용)
};

static SampleResult sampleGpio(int gpio, uint8_t mode) {
  pinMode(gpio, mode);
  delayMicroseconds(PROBE_SETTLE_US);
  int high = 0;
  for (int k = 0; k < PROBE_SAMPLES; k++) {
    if (digitalRead(gpio)) high++;
    delayMicroseconds(PROBE_INTERSAMPLE_US);
  }
  SampleResult r;
  r.highCnt = high;
  r.level   = (high * 2 > PROBE_SAMPLES);          // 과반 = HIGH
  r.stable  = (high == 0 || high == PROBE_SAMPLES); // 전부 동일해야 stable
  return r;
}

static const char* lineStateStr(LineState s) {
  switch (s) {
    case LS_EXT_PULLUP:       return "EXT_PULLUP  *** (라이브 레일 pull-up = 전원+배선 증명) ***";
    case LS_FLOATING:         return "floating (미연결 또는 무급전)";
    case LS_EXT_PULLDOWN_GND: return "EXT_PULLDOWN/GND (외부 풀다운 또는 GND 단락)";
    case LS_UNSTABLE:         return "UNSTABLE (표본 불일치 = floating 후보)";
  }
  return "?";
}

// PHASE 1에서 검출된 EXT_PULLUP 핀 인덱스 기록.
static int g_pullupIdx[PIN_COUNT];
static int g_pullupCount = 0;

// 도통 hit 기록 (최대 PIN_COUNT*(PIN_COUNT-1)). (srcIdx<<8)|dstIdx.
static uint16_t g_contPairs[PIN_COUNT * (PIN_COUNT - 1)];
static int      g_contCount = 0;

// ── PHASE 1: 외부 pull-up 검출 (전원 실측 대체) ──
static void phasePullup() {
  Serial.println("\n=== PHASE 1: 외부 pull-up 검출 (전원/배선 동시 실측) ===");
  Serial.printf("[probe] 각 핀 INPUT_PULLDOWN/INPUT_PULLUP %d회 다수결.\n", PROBE_SAMPLES);
  g_pullupCount = 0;

  for (int i = 0; i < PIN_COUNT; i++) {
    const PinCandidate& p = PINS[i];
    Serial.flush();

    SampleResult pd = sampleGpio(p.gpio, INPUT_PULLDOWN);  // 내부 풀다운 기준
    SampleResult pu = sampleGpio(p.gpio, INPUT_PULLUP);    // 내부 풀업 기준

    LineState st;
    if (!pd.stable || !pu.stable) {
      st = LS_UNSTABLE;
    } else if (pd.level) {                 // 내부 풀다운을 이기고 HIGH → 강한 외부 pull-up
      st = LS_EXT_PULLUP;
    } else if (pu.level) {                 // pd LOW + pu HIGH → 내부 저항만 관여 = floating
      st = LS_FLOATING;
    } else {                               // pd LOW + pu LOW → 외부가 LOW로 고정
      st = LS_EXT_PULLDOWN_GND;
    }

    Serial.printf("[probe] GPIO%d(%s)%s pd=%s(%d/%d) pu=%s(%d/%d) -> %s\n",
                  p.gpio, p.dLabel, p.strapping ? "[strapping]" : "",
                  pd.level ? "H" : "L", pd.highCnt, PROBE_SAMPLES,
                  pu.level ? "H" : "L", pu.highCnt, PROBE_SAMPLES,
                  lineStateStr(st));

    if (st == LS_EXT_PULLUP && g_pullupCount < PIN_COUNT) {
      g_pullupIdx[g_pullupCount++] = i;
    }

    pinMode(p.gpio, INPUT);   // 다음 항목 전 floating 복귀 (내부 저항 해제)
    Serial.flush();
    delay(PROBE_PHASE_GAP_MS);
    yield();
  }
}

// ── PHASE 2: 도통 매트릭스 (점퍼/브레드보드 실측) ──
// 안전: 항상 단 하나의 핀만 OUTPUT. 측정 직후 즉시 INPUT 복귀 → 두 OUTPUT 충돌(단락) 구조적 불가.
// strapping 핀(GPIO 1/4/43/44) OUTPUT 구동은 부팅 완료 후라 부트 스트랩에 무영향(리셋 직후 실행 금지).
static void phaseContinuity() {
  Serial.println("\n=== PHASE 2: 도통 매트릭스 (OUTPUT HIGH -> INPUT_PULLDOWN 읽기) ===");
  g_contCount = 0;
  int attempts = 0;

  // 시작 전 전 핀 INPUT 보장 (직전 PHASE 1 잔여 모드 제거, 다중 OUTPUT 원천 차단).
  for (int i = 0; i < PIN_COUNT; i++) pinMode(PINS[i].gpio, INPUT);

  for (int a = 0; a < PIN_COUNT; a++) {
    for (int b = 0; b < PIN_COUNT; b++) {
      if (a == b) continue;
      const PinCandidate& src = PINS[a];
      const PinCandidate& dst = PINS[b];

      pinMode(src.gpio, OUTPUT);
      digitalWrite(src.gpio, HIGH);
      SampleResult r = sampleGpio(dst.gpio, INPUT_PULLDOWN);  // dst를 풀다운으로 읽음
      pinMode(src.gpio, INPUT);   // ★ 측정 직후 즉시 OUTPUT 해제 (단락/접촉 스트레스 최소화)
      pinMode(dst.gpio, INPUT);
      attempts++;

      if (r.level && r.stable) {   // 안정적으로 HIGH만이 도통 (노이즈 HIGH 배제)
        if (g_contCount < (int)(sizeof(g_contPairs) / sizeof(g_contPairs[0]))) {
          g_contPairs[g_contCount++] = (uint16_t)((a << 8) | b);
        }
        Serial.printf("[cont] GPIO%d(%s) -> GPIO%d(%s)  CONTINUOUS (%d/%d)\n",
                      src.gpio, src.dLabel, dst.gpio, dst.dLabel, r.highCnt, PROBE_SAMPLES);
        Serial.flush();
      }
      // hit이 아니면 라인 노이즈 → 출력 생략(110줄 노이즈 억제). 요약에서 재집계.
      delay(PROBE_PHASE_GAP_MS);
      yield();
    }
  }
  Serial.printf("[cont] 매트릭스 완료 — 시도 %d, 도통 %d쌍.\n", attempts, g_contCount);
}

// ── PHASE 3: 요약 ──
static void phaseSummary(uint32_t elapsedMs) {
  Serial.println("\n=== SUMMARY ===");

  Serial.print("PULLUP_DETECTED: ");
  if (g_pullupCount == 0) {
    Serial.println("(none)");
    Serial.println("  힌트: 어떤 라인에도 라이브 레일 pull-up이 없음. 다음 중 하나 —");
    Serial.println("        (1) 센서 무급전(IOVDD 미공급), (2) SDA/SCL 신호선 미연결,");
    Serial.println("        (3) SATEL 호스트측 2.2k pull-up 미장착(IOVDD로 pull-up 추가 필요).");
  } else {
    for (int k = 0; k < g_pullupCount; k++) {
      const PinCandidate& p = PINS[g_pullupIdx[k]];
      Serial.printf("GPIO%d(%s)%s ", p.gpio, p.dLabel, p.strapping ? "[strapping]" : "");
    }
    Serial.println();
    Serial.println("  해석: 위 핀들이 라이브 레일 pull-up을 실측 검출 = 전원+배선 증명.");
    Serial.println("        정확히 2개면 그게 실제 SDA/SCL 후보 (SSoT: SDA=GPIO5/D4, SCL=GPIO6/D5).");
  }

  Serial.print("CONTINUITY_PAIRS: ");
  if (g_contCount == 0) {
    Serial.println("(none — 점퍼 단선 또는 브레드보드 접촉 불량 의심)");
  } else {
    Serial.println();
    for (int k = 0; k < g_contCount; k++) {
      const PinCandidate& s = PINS[(g_contPairs[k] >> 8) & 0xFF];
      const PinCandidate& d = PINS[g_contPairs[k] & 0xFF];
      Serial.printf("  GPIO%d(%s) -> GPIO%d(%s)\n", s.gpio, s.dLabel, d.gpio, d.dLabel);
    }
  }

  Serial.printf("총 시도: PHASE1 %d핀 / PHASE2 %d쌍, 소요 %lums\n",
                PIN_COUNT, PIN_COUNT * (PIN_COUNT - 1), (unsigned long)elapsedMs);
  Serial.flush();
}

void setup() {
  Serial.begin(115200);
  delay(PROBE_BOOT_DELAY_MS);

  // 학부생이 모니터 접속 타이밍을 반복적으로 놓친 실측 이력 → 3초 카운트다운 (PR #32 동일).
  Serial.println("\n[BOOT] ddingdong ToF 라인 프로브 (PoC-(34) 전원/배선 실측, 멀티미터 대체)");
  for (int s = 3; s >= 1; s--) {
    Serial.printf("[probe] starting in %d..\n", s);
    Serial.flush();
    delay(1000);
  }

  const uint32_t t0 = millis();
  phasePullup();
  Serial.flush();
  delay(PROBE_PHASE_GAP_MS);

  phaseContinuity();
  Serial.flush();
  delay(PROBE_PHASE_GAP_MS);

  phaseSummary(millis() - t0);

  Serial.println("[probe] 진단 완료 — loop() idle (5s heartbeat). reset+flash로 재실행.");
}

void loop() {
  // 진단은 setup()에서 1회. loop()는 idle heartbeat (tof_test 컨벤션 일치).
  static uint32_t last_log = 0;
  const uint32_t now = millis();
  if ((now - last_log) >= PROBE_LOOP_IDLE_MS) {
    last_log = now;
    Serial.printf("[probe] idle — pullup %d, continuity %d. reset+flash to re-run.\n",
                  g_pullupCount, g_contCount);
  }
  delay(100);
}
