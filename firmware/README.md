# Firmware

ESP32-S3(XIAO ESP32S3 Sense) 펌웨어 — PlatformIO + Arduino framework. 띵동 본체 MCU 코드.
결정 · 근거의 단일 출처는 `docs/decisions.md`이고, 이 문서는 길 안내만 한다.

## 빌드 / 업로드 / 모니터

`pio`는 PATH에 없다. `firmware/`에서 전체 경로로 실행하고, `-e`로 env를 반드시 지정한다
(`default_envs = poc`는 초기 WiFi 더미라 제품 바이너리가 아니다). repo 루트에서는 `pio run`에 `-d firmware`를 붙인다.

```bash
~/.platformio/penv/bin/pio run -e <env>                 # 빌드
~/.platformio/penv/bin/pio run -e <env> -t upload       # 업로드
~/.platformio/penv/bin/pio device monitor -b 115200     # 시리얼 모니터 (업로드와 따로 실행)
```

WiFi · 서버 주소 · 토큰은 `include/secrets.h.template`을 `include/secrets.h`로 복사해 채운다(`secrets.h`는 commit 금지).

## env 구성 (`platformio.ini`)

env 하나 = 독립 바이너리. 모든 env는 `build_src_filter = -<*>` 다음에 필요한 `.cpp`만 나열하는 화이트리스트다
(카테고리 27.6). 진단용 · 이전 env는 frozen — 고치지 말고 복제해 새 env를 만든다. 이름 = `{domain}_{purpose}`.

| 성격 | env | 무엇 | 절차 |
|------|-----|------|------|
| 제품 경로 | `enrich_uplink` | `/detect` → `enrich_status` 게이트 → 카메라 1장 + 녹음 → `/enrich`. 시리얼 `s` 수동 트리거 | [ENRICH_UPLINK_RUNBOOK](ENRICH_UPLINK_RUNBOOK.md) |
| 제품 경로 | `enrich_autotrig` | `enrich_uplink`과 같은 소스 + `-DENRICH_AUTO_TRIGGER`(64ms 버퍼 RMS 자동 트리거, 규칙 · 상수 = `include/auto_trig.h`) | [ENRICH_AUTOTRIG_RUNBOOK](ENRICH_AUTOTRIG_RUNBOOK.md) |
| 배관 | `mic_uplink` | 마이크 2초 스냅샷 + ToF 메타 → `/detect`. 시리얼 `s` 수동 트리거 | [MIC_UPLINK_RUNBOOK](MIC_UPLINK_RUNBOOK.md) |
| 진단 하네스 | `camera_probe` | 카메라 · 마이크 · ToF 동시 구동 관측(서버 호출 0) | [CAMERA_PROBE_RUNBOOK](CAMERA_PROBE_RUNBOOK.md) |
| 진단 하네스 | `mic_noiseprobe` | ToF 측정 중 마이크 클립 원인 분리(모드 `0`~`4` + `s`) | [MIC_NOISEPROBE_RUNBOOK](MIC_NOISEPROBE_RUNBOOK.md) |
| 진단 하네스 | `mic_trigprobe` | 64ms 버퍼 단위 RMS 계측(트리거 판정 0) | [MIC_TRIGPROBE_RUNBOOK](MIC_TRIGPROBE_RUNBOOK.md) |
| 진단 하네스 | `tof_pinscan` · `tof_lineprobe` | ToF 브링업 — I2C ACK 핀 쌍 전수 스캔 · 전원/도통 실측 | `platformio.ini` 해당 env 머리 주석 |
| 업로드 지연 실측 | `upload_spike` · `upload_spike_tls` | 합성 PCM multipart POST 왕복 지연(HTTP · HTTPS) | [UPLOAD_TEST_RUNBOOK](UPLOAD_TEST_RUNBOOK.md) |
| 초기 더미 | `poc` · `camera_v1` · `camera_v2` · `mic_dummy` · `tof_dummy` | 모듈 단독 브링업(`main.cpp` WiFi · `camera_test_v1/v2.cpp` · `mic_test.cpp` · `tof_test.cpp`) | — |

카메라가 들어가는 env는 `-DCAMERA_MODEL_XIAO_ESP32S3`가 필수(없으면 `camera_common.h`의 `#error`), ToF를 쓰는 env는
SparkFun VL53L5CX를 `lib_deps`에 넣는다. 설치 core = Arduino-ESP32 2.0.17(패키지 버전 `3.20017`을 core 3.x로 읽지 말 것 —
`platformio.ini` `env:upload_spike_tls` 머리 주석).

## 런북 색인

| 런북 | 용도 |
|------|------|
| [ENRICH_UPLINK_RUNBOOK.md](ENRICH_UPLINK_RUNBOOK.md) | `env:enrich_uplink` 보드 2차 체인 ④런타임 절차 |
| [ENRICH_AUTOTRIG_RUNBOOK.md](ENRICH_AUTOTRIG_RUNBOOK.md) | `env:enrich_autotrig` 자동 트리거가 실보드에서 같은 시점 · 같은 창으로 도는지, 무음 · 노크 · 초인종 반응 관측 |
| [MIC_UPLINK_RUNBOOK.md](MIC_UPLINK_RUNBOOK.md) | `env:mic_uplink` 마이크 2초 스냅샷 업로드 ④런타임 절차 |
| [CAMERA_PROBE_RUNBOOK.md](CAMERA_PROBE_RUNBOOK.md) | `env:camera_probe` 카메라(와 WiFi 송신)가 마이크 클립을 악화시키는지 관측 |
| [MIC_NOISEPROBE_RUNBOOK.md](MIC_NOISEPROBE_RUNBOOK.md) | `env:mic_noiseprobe` ToF 측정 중 조용한 스냅샷 클립의 근본원인 진단 |
| [MIC_TRIGPROBE_RUNBOOK.md](MIC_TRIGPROBE_RUNBOOK.md) | `env:mic_trigprobe` 64ms 버퍼 단위 RMS 로그 수집 |
| [UPLOAD_TEST_RUNBOOK.md](UPLOAD_TEST_RUNBOOK.md) | ESP32 업로드 지연 실측 + 네트워크 prereq(핫스팟 · 포트 · 토큰) — MIC_UPLINK 런북이 이 문서 1~3절을 그대로 따른다 |

## 구조

```
firmware/
├── platformio.ini      # env 정의 (위 표)
├── *_RUNBOOK.md        # 장비 절차 (위 색인)
├── src/                # env별 *_main.cpp · 초기 더미 *_test*.cpp · 공용 모듈 *_common.cpp
│                       #   (camera · mic · tof · uplink · upload_spike(_tls))
├── include/            # 공용 헤더 + 호스트에서 검산하는 순수 판정 헤더
│                       #   (auto_trig.h · noise_stats.h · trig_line.h · enrich_wire.h · heartbeat_wire.h …)
│                       #   secrets.h.template → secrets.h (commit 금지)
├── tools/              # 호스트 단위 테스트 *_test.cpp · tls_probe_server.py(upload_spike_tls 대상) · certs/
│   └── host_stubs/     # 호스트 빌드용 가짜 Arduino.h · Wire.h · SparkFun 헤더
└── lib/                # 비어 있음(.gitkeep)
```

## 호스트 단위 테스트

`tools/*_test.cpp`는 실제 헤더/소스를 그대로 include · 링크해 `c++`로 빌드한다. 정확한 빌드 · 실행 명령은 각 파일
머리 주석에 있다(repo 루트 기준). 예외: `jsonpeek_test.cpp`는 머리 주석에 명령이 없다.

## 핀 할당표

| 모듈 | 신호 | XIAO | GPIO | 페리페럴 |
|------|------|------|------|---------|
| INMP441 | SCK | D1 | 2 | I2S1 |
| INMP441 | WS  | D2 | 3 | I2S1 |
| INMP441 | SD  | D8 | 7 | I2S1 |
| INMP441 | VDD/GND/L_R | 3V3/GND/GND | - | - |
| VL53L5CX | SDA | D4 | 5 | I2C |
| VL53L5CX | SCL | D5 | 6 | I2C |
| VL53L5CX | PWREN | 3V3 직결 | - | (전원 enable) |
| VL53L5CX | LPn   | 3V3 직결 | - | (I2C enable) |
| OV3660 카메라 | XCLK | - | 10 | LCD_CAM |
| OV3660 카메라 | SIOD / SIOC (SCCB) | - | 40 / 39 | I2C 포트 1 |
| OV3660 카메라 | Y9~Y2 (데이터 8비트) | - | 48 / 11 / 12 / 14 / 16 / 18 / 17 / 15 | LCD_CAM |
| OV3660 카메라 | VSYNC / HREF / PCLK | - | 38 / 47 / 13 | LCD_CAM |
| OV3660 카메라 | PWDN / RESET | - | -1 (미사용) | - |

- ESP32-S3의 카메라는 LCD_CAM 페리페럴이다(「카메라 = I2S0」은 ESP32 원조 프레이밍 오기 — 카테고리 1 · 27.8(m)④).
  마이크와의 분리 근거 = 핀 교집합 ∅ + I2C 포트 분리(카메라 SCCB 포트 1 / ToF `Wire` 포트 0, 카테고리 2 · 6.6).
- ToF I2C 클럭 = `include/tof_common.h`의 `TOF_I2C_FREQ_HZ`(400kHz, `src/tof_common.cpp`의 `Wire.setClock`). 근거 = 카테고리 9.1.
- PWREN/LPn을 HIGH로 구동하지 않으면 SDA가 LOW로 고착돼 I2C 전면 불통(카테고리 9.1).

> 핀 표의 단일 진실 원천: `docs/decisions.md` 카테고리 2.
> 변경 시 본 표 먼저 수정하지 말고 decisions.md 먼저 갱신할 것.
