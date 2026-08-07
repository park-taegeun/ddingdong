// 띵동 firmware - ToF I2C 핀 스캔 진단 하네스 (2026-08-07, PoC-(34) 하드웨어 브링업 블로커)
//
// 목적: VL53L5CX-SATEL이 I2C 버스에 나타나지 않는 브레드보드 브링업 블로커 해소.
//   2026-08-06~07 수동 배선 순회(신호 12조합 + 전원 6조합)로 전부 미검출.
//   전원축 × 신호축 조합 폭발(~168)에서 한 축 고정 탐색은 고정축이 틀리면 원리적으로
//   해를 못 찾음 → 소프트웨어로 탐색 공간(핀 순서쌍)을 전수 순회하는 진단 도구.
//
// 동작: XIAO ESP32-S3의 D0~D10 GPIO 전체를 (SDA, SCL) 순서쌍으로 순회하며 각 쌍에서
//   I2C 스캔 → VL53L5CX 기본 주소 0x29(7-bit)가 ACK하는 쌍을 찾아 보고.
//   배선을 한 번 고정한 뒤 플래시 1회로 전 조합 자동 탐색(수동 순회 대체).
//
// ★ 본 하네스는 진단 전용. 실제 스캔 실행/결과 해석은 학부생 로컬 몫(하드웨어 런타임).
// ★ SSoT(decisions.md 카테고리 2)는 SDA=D4(GPIO5)/SCL=D5(GPIO6). 본 도구는 SSoT를
//   의심하는 게 아니라, "실물 배선이 SSoT와 일치하는지"를 실측으로 판별(배선 오류 배제)한다.
//
// 출처(설치 실물 인용, 학습 13/15):
//   - variants/XIAO_ESP32S3/pins_arduino.h (framework-arduinoespressif32):
//       D0=GPIO1 D1=GPIO2 D2=GPIO3 D3=GPIO4 D4=GPIO5 D5=GPIO6
//       D6=GPIO43(TX) D7=GPIO44(RX) D8=GPIO7 D9=GPIO8 D10=GPIO9
//   - libraries/Wire/src/Wire.h: bool begin(int sda,int scl,uint32_t freq=0) / bool end()
//       / bool setClock(uint32_t) / beginTransmission(uint8_t) / uint8_t endTransmission(void)
//   - boards/seeed_xiao_esp32s3.json: ARDUINO_USB_CDC_ON_BOOT=1 → Serial=네이티브 USB CDC.
//       따라서 D6/D7(GPIO43/44=UART0 TX/RX)를 I2C로 재구성해도 모니터 로그는 유실 안 됨.
//   - VL53L5CX datasheet: I2C 7-bit default 0x29 (8-bit 0x52).

#include <Arduino.h>
#include <Wire.h>

// === 후보 핀 (pins_arduino.h 실측 인용, 카테고리 1 strapping = D0/D3/D6/D7) ===
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

// === I2C 진단 설정 ===
// 100kHz 채택: 브레드보드 + 20cm 점퍼는 정전용량이 커서 400kHz도 마진이 얇음.
// 진단 단계에선 가장 관대한 속도로 검출 가능성을 최대화(400kHz도 미검출 이력).
static const uint32_t PINSCAN_I2C_FREQ_HZ    = 100000;
static const uint8_t  PINSCAN_TARGET_ADDR    = 0x29;   // VL53L5CX 7-bit default
static const uint32_t PINSCAN_SETTLE_MS      = 20;     // 워치독 급양 + 버스 안정
static const uint32_t PINSCAN_BOOT_DELAY_MS  = 200;    // 기존 컨벤션 (Serial.begin 후)
static const uint32_t PINSCAN_LOOP_IDLE_MS   = 5000;   // tof_test loop() idle 로그 주기

// FOUND 요약을 위한 순서쌍 기록 버퍼 (최대 = PIN_COUNT*(PIN_COUNT-1)).
static int      g_foundCount = 0;
static uint16_t g_foundPairs[PIN_COUNT * (PIN_COUNT - 1)];   // (sdaIdx<<8)|sclIdx

// 단일 (sda, scl) 쌍에서 0x29 ACK 여부 판정.
static bool probePair(int sdaGpio, int sclGpio) {
  Wire.end();                                   // 이전 버스 상태 정리
  if (!Wire.begin(sdaGpio, sclGpio)) {
    return false;                               // 핀 구성 실패 = 미검출로 간주
  }
  Wire.setClock(PINSCAN_I2C_FREQ_HZ);
  Wire.beginTransmission(PINSCAN_TARGET_ADDR);
  uint8_t err = Wire.endTransmission();         // 0 = 슬레이브 ACK
  return (err == 0);
}

// 전 순서쌍 순회 (setup에서 1회). sda != scl, 대칭 아님(뒤바뀐 쌍도 별개 케이스).
static void runPinScan() {
  Serial.printf("[pinscan] candidates=%d, ordered pairs=%d, target=0x%02X @ %lukHz\n",
                PIN_COUNT, PIN_COUNT * (PIN_COUNT - 1),
                PINSCAN_TARGET_ADDR, (unsigned long)(PINSCAN_I2C_FREQ_HZ / 1000));

  int attempts = 0;
  g_foundCount = 0;

  for (int i = 0; i < PIN_COUNT; i++) {
    for (int j = 0; j < PIN_COUNT; j++) {
      if (i == j) continue;                     // sda != scl

      // 리셋 발생 시 "어느 쌍에서 죽었는지"가 진단 정보 → 시도 직전 flush로 유실 방지.
      const PinCandidate& sda = PINS[i];
      const PinCandidate& scl = PINS[j];
      Serial.flush();

      bool ack = probePair(sda.gpio, scl.gpio);
      attempts++;

      Serial.printf("[pinscan] SDA=GPIO%d(%s)%s SCL=GPIO%d(%s)%s -> %s\n",
                    sda.gpio, sda.dLabel, sda.strapping ? "[strapping]" : "",
                    scl.gpio, scl.dLabel, scl.strapping ? "[strapping]" : "",
                    ack ? "ACK 0x29 *** FOUND ***" : "no ack");
      Serial.flush();

      if (ack && g_foundCount < (int)(sizeof(g_foundPairs) / sizeof(g_foundPairs[0]))) {
        g_foundPairs[g_foundCount++] = (uint16_t)((i << 8) | j);
      }

      // 워치독 대응: 관측된 "스캔 중 리셋"의 유력 원인 = 버스 잠김 → 태스크 워치독 리셋.
      // 각 시도 사이 delay + yield로 워치독 급양 보장.
      delay(PINSCAN_SETTLE_MS);
      yield();
    }
  }

  // === 요약 재출력 ===
  if (g_foundCount > 0) {
    Serial.printf("\n=== FOUND (%d pair%s ACK 0x29) ===\n",
                  g_foundCount, g_foundCount == 1 ? "" : "s");
    for (int k = 0; k < g_foundCount; k++) {
      const PinCandidate& sda = PINS[(g_foundPairs[k] >> 8) & 0xFF];
      const PinCandidate& scl = PINS[g_foundPairs[k] & 0xFF];
      Serial.printf("  SDA=GPIO%d(%s)  SCL=GPIO%d(%s)\n",
                    sda.gpio, sda.dLabel, scl.gpio, scl.dLabel);
    }
    Serial.printf("=== (SSoT 기대: SDA=GPIO5(D4), SCL=GPIO6(D5)) ===\n");
  } else {
    Serial.printf("\n=== NONE FOUND (0x29 no ack on any of %d pairs) ===\n", attempts);
  }
  Serial.flush();
}

void setup() {
  Serial.begin(115200);
  delay(PINSCAN_BOOT_DELAY_MS);

  // 학부생이 모니터 접속 타이밍을 반복적으로 놓친 실측 이력 → 3초 카운트다운.
  // 진단 하네스는 결과 관측이 목적이라 로그 유실이 치명적.
  Serial.println("\n[BOOT] ddingdong ToF I2C pin-scan (PoC-(34) bringup diagnostic)");
  for (int s = 3; s >= 1; s--) {
    Serial.printf("[pinscan] starting in %d..\n", s);
    Serial.flush();
    delay(1000);
  }

  runPinScan();

  Serial.println("[pinscan] scan complete — loop() idle (5s heartbeat).");
}

void loop() {
  // 순회는 setup()에서 1회. loop()는 idle heartbeat (tof_test 컨벤션 일치).
  static uint32_t last_log = 0;
  const uint32_t now = millis();
  if ((now - last_log) >= PINSCAN_LOOP_IDLE_MS) {
    last_log = now;
    Serial.printf("[pinscan] idle — %d found. reset+flash to re-scan.\n", g_foundCount);
  }
  delay(100);
}
