# Firmware

ESP32-S3 펌웨어 (PlatformIO + Arduino framework). 띵동 청각장애인용 소리 분류 알림 시스템의 본체 MCU 코드.

## 빌드 / 업로드 / 모니터

```bash
pio run -e poc                 # 빌드
pio run -e poc -t upload       # 업로드
pio device monitor -b 115200   # 시리얼 모니터
```

## 구조

```
firmware/
├── platformio.ini   # 빌드 설정 (env:poc)
├── src/
│   └── main.cpp     # 현재: 빈 sketch (컴파일 검증용)
├── include/         # 헤더 (아직 비어있음)
└── lib/             # 로컬 라이브러리 (아직 비어있음)
```

## 5/8 ~ 5/11 일정 (채팅방 2 위임 예정)

| 날짜 | 모듈 | 파일 | 반영 사전 검증 |
|------|------|------|------------------|
| 5/8  | WiFi 단독 | `src/wifi_test.cpp` | - |
| 5/9  | 카메라 단독 | `src/camera_test.cpp` | 사전 검증 ② (OV3660 xclk_freq_hz=20000000, fb_count=2, JPEG vTaskDelay) |
| 5/10 | 마이크 단독 | `src/microphone_test.cpp` | INMP441 + I2S1 |
| 5/11 | ToF 단독 | `src/tof_test.cpp` | 사전 검증 ① (SparkFun 메인 우선, I2C 1MHz, 단일 센서, 폴백 Adafruit_VL53L5) |
| 5/21~| PoC 통합 | `src/integrated_test.cpp` | 사전 검증 ② (Core 0=audio/tof, Core 1=camera/writer) |

## 핀 할당표

| 모듈 | 신호 | XIAO 핀 | GPIO | 페리페럴 |
|------|------|---------|------|---------|
| INMP441 | SCK | D1 | 2 | I2S1 |
| INMP441 | WS  | D2 | 3 | I2S1 |
| INMP441 | SD  | D8 | 7 | I2S1 |
| INMP441 | VDD/GND/L_R | 3V3/GND/GND | - | - |
| VL53L5CX | SDA | D4 | 5 | I2C |
| VL53L5CX | SCL | D5 | 6 | I2C |
| 카메라 OV3660 | 보드 내장 | - | - | I2S0 (LCD_CAM+GDMA) |

> 현재 핀 표의 단일 진실 원천: `docs/decisions.md` 카테고리 2.
> 변경 시 본 표 먼저 수정하지 말고 decisions.md 먼저 갱신할 것.

## 사전 검증 결과 반영 내역 (platformio.ini)

- 사전 검증 ① (VL53L5CX): `lib_deps`에 SparkFun 메인 + Adafruit 폴백 둘 다 명시
- 사전 검증 ② (OV3660 멀티코어): `build_flags`에 `-DCAMERA_MODEL_XIAO_ESP32S3`, `-DBOARD_HAS_PSRAM`, `-mfix-esp32-psram-cache-issue` 3개 필수
