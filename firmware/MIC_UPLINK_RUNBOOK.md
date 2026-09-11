# 마이크 2초 스냅샷 업로드 ④런타임 Runbook (M5-d, `env:mic_uplink`)

> 2026-09-11 작성. **실행은 학부생**, 본 문서는 절차서다.
> 2026-09-11 PoC-(45) 갱신: ToF 메타 4필드 송신(9절) 추가 + 로그 줄 분리(5절 기대 로그 갱신).
> 네트워크 prereq(핫스팟 함정 5건 / 포트 / 토큰 3곳 일치)는 `firmware/UPLOAD_TEST_RUNBOOK.md`
> 1~3절과 **완전히 동일**하므로 여기서 복제하지 않는다. 먼저 그 문서대로 환경을 세운 뒤 아래로 온다.

## 0. 이 세션이 증명하려는 것

M5-a 링버퍼(2.048초 PSRAM 32슬롯)에서 뜬 스냅샷이 **실제로 서버까지 도달하는가**.
판정(RMS 임계·pre/post 비율)은 이 PR의 범위가 아니다 — 트리거는 시리얼 `s` 키 수동 입력이다.

⚠️ **변경 전후 값이 같으면 아무것도 증명되지 않는다.** 아래 3개 대조 실험은 전부
"조건을 바꾸면 값이 바뀐다"를 보게 설계돼 있다. 한 번만 돌리고 200 이 떴다고 끝내지 말 것.

## 1. 네트워크 전제

- **폰 핫스팟에 노트북과 보드가 동시 접속**해야 한다(보드 → 노트북 LAN 직통).
- 아이폰: 설정 → 개인용 핫스팟 → **"호환성 최대화" ON**(2.4GHz 강제. XIAO ESP32-S3 는 5GHz 불가).
- 노트북 IP 확인: `ipconfig getifaddr en0` → 핫스팟이면 `172.20.10.x` 대역.

## 2. secrets 설정 (파일 1개, `firmware/include/secrets.h` — gitignore 대상)

본 env는 **새 매크로를 만들지 않는다.** `env:upload_spike` 가 쓰던 3개를 그대로 재사용한다:

| 매크로 | 값 |
|---|---|
| `WIFI_PRIMARY_SSID` / `_PASSWORD` | 폰 핫스팟 SSID / 비번 (1순위로 두면 부팅이 빠르다) |
| `SPIKE_SERVER_HOST` | 노트북 LAN IP (`ipconfig getifaddr en0` 결과). **핫스팟 IP는 매번 바뀐다 → 갱신 후 재flash** |
| `SPIKE_SERVER_PORT` | `5000` |
| `SPIKE_DEVICE_TOKEN` | 서버 기동 시 넘긴 `DEVICE_TOKEN` 과 **동일 값** |

> `device_id` 는 펌웨어 상수 `UPLINK_DEVICE_ID = "ddingdong-mic-uplink-001"`(`uplink_common.h`)로
> 고정돼 있고 하네스(`ddingdong-upload-spike-001`)와 분리돼 있다 → 두 env 가 서로의 rate limit 을 밟지 않는다.

## 3. 서버 기동 (노트북)

```
cd server && source venv/bin/activate && DEVICE_TOKEN=<토큰> flask --app run run --host=0.0.0.0 --port=5000
```

- `--host=0.0.0.0` **필수**(`run.py` 는 127.0.0.1 하드코딩 = frozen).
- 이 터미널을 **닫지 말 것** — 서버 로그가 아래 (a) 대조 실험의 서버측 관측 채널이다.
- 현재 `server/.env` 에 `DDINGDONG_MODEL_PATH` 가 **없다** → 서버는 **mock 추론 모드**다.
  ⚠️ 따라서 응답의 `predicted_class` / `confidence` 는 **오디오와 무관한 난수**다
  (`server/app/utils.py:169 mock_prediction` = `random.choice`). 이 값이 손뼉에 반응할 거라고
  기대하지 말 것 — 오디오 내용에서 파생된 서버측 관측값은 **아래 로그 한 줄뿐**이다:

  ```
  detect audio decoded: samples=32768 dtype=float32 duration_s=2.048 min=... max=... rms=... decode_ms=...
  ```

## 4. 플래시 · 모니터 (**분리 실행** — 포트는 1개만 점유한다)

```
~/.platformio/penv/bin/pio run -d firmware -e mic_uplink -t upload
```
```
~/.platformio/penv/bin/pio device monitor -b 115200
```

부팅 기대 로그:

```
[BOOT] ddingdong mic uplink (M5-d, 수동 's' 트리거)
[uplink] PSRAM alloc OK tag=snapshot bytes=65536
[uplink] PSRAM alloc OK tag=multipart bytes=66176
[uplink] WiFi connected SSID=... RSSI=-52 IP=172.20.10.x
[BOOT] client_request_id nonce=3f8a1c07
[BOOT] micUplinkTask started (Core 0) — POST 는 loop 태스크
[tof] I2C ready (SDA=GPIO5/SCL=GPIO6, clock=400000Hz)
[tof][StageB-1] motion indicator ready (8x8, 400~1500mm, 16 aggregates)
[tof] VL53L5CX ready (8x8, 15Hz, continuous)
[BOOT] tofTask started (Core 0, prio 3) — ToF 4필드 송신 활성
[mic][M5d] ring filled — 's' 키로 스냅샷 전송 가능
```

ToF 가 결선되지 않았거나 init 에 실패하면 `[BOOT] tof init 실패 — 4필드 미전송(서버 tof_absent 로 degrade)`
가 뜨고 **나머지는 PR #52 와 동일하게 동작**한다(응답 `tof=tof_absent`). 이것은 오류가 아니라 degrade 다.
ToF 가 살아 있으면 `[tof][StageA]`(2초 주기) / `[tof][StageB-1]`(1초 주기) 줄이 상시 흐른다 — tof_dummy 와
같은 포맷이며 9절 (a)(d) 의 관측 채널이다.

`ring filled` 가 뜨기 전(부팅 후 약 2초)에 `s` 를 누르면 `ring 미충전` 이 뜬다 — 정상 가드다.

---

## 5. ★ 대조 실험 (3건 — 전부 "값이 달라져야" 통과)

### (a) 조용한 상태 vs 손뼉 — 입력이 페이로드를 바꾸는가

1. 조용한 상태에서 `s` 1회 → 로그 기록.
2. **5초 이상 대기**(rate limit).
3. 마이크 30cm 앞에서 손뼉을 치는 **동시에** `s` → 로그 기록.

기대 (펌웨어):
```
[mic][M5d] id=m5d-3f8a1c07-1 bytes=65536 rms=58 peak=213        ← 조용
[mic][M5d] id=m5d-3f8a1c07-2 bytes=65536 rms=2140 peak=18900    ← 손뼉
```
- ✅ 통과 조건: **`rms` 가 한 자릿수배 이상 벌어진다.** `bytes` 는 둘 다 정확히 `65536`.
- ❌ 두 `rms` 가 비슷하면: 손뼉이 2.048초 창 밖이었거나(다시), 링버퍼가 안 돌고 있다.

기대 (서버 로그 — **오디오 내용에서 파생된 유일한 서버측 관측값**):
```
detect audio decoded: samples=32768 ... rms=0.0018 ...   ← 조용
detect audio decoded: samples=32768 ... rms=0.0653 ...   ← 손뼉
```
- ✅ **교차검증**: 서버 `rms` × 32768 ≈ 펌웨어 `rms`. (예: 0.0653 × 32768 ≈ 2140)
  이 둘이 맞으면 **바이트가 int16 LE 로 온전히·순서대로 도착했다**는 증거다.
  크게 어긋나면 스냅샷 복사나 엔디안을 의심할 것.
- ✅ `samples=32768` / `duration_s=2.048` 고정.

기대 (양쪽 모두):
```
[mic][M5d] http=201 rtt=842ms cls=knock conf=0.51
[mic][M5d] tof=presence=false near=0/64 center=n/a ndet=0/16
```
- ✅ **둘 다 `http=201`**. `tof=` 줄은 PoC-(45)부터 **별도 줄**이다(reason 이 길어져 80B 분리).
  ToF 결선 시 `presence=… near=…` 텔레메트리, ToF 미결선/init 실패 시 `tof=tof_absent`(fail-open).
- ✅ **DB 행이 1건씩 증가**:
  ```
  cd server && venv/bin/python3 -c "import sqlite3;print(sqlite3.connect('ddingdong.db').execute('select count(*) from notifications').fetchone())"
  ```
  (a) 전 / (a)-1 후 / (a)-2 후 세 번 찍어 `n`, `n+1`, `n+2` 를 확인한다.
- ⚠️ `cls`/`conf` 는 mock 난수다. 두 요청에서 달라도 정상이고, 같아도 정상이다 — **판정 근거로 쓰지 말 것**.

### (b) 5초 안에 연속 2회 — rate limit 과 "재시도 없음"

`s` 를 누르고 **2초 안에** 다시 `s`.

기대:
```
[mic][M5d] http=201 rtt=812ms cls=... conf=...
[mic][M5d] tof=presence=...
[mic][M5d] http=429 rtt=18ms cls=? conf=?
[mic][M5d] tof=?
```
- ✅ 두 번째가 **429**(`DEVICE_RATE_LIMIT_SECONDS=5`, `rate_limit.py`).
- ✅ `cls`/`conf`/`tof` 가 전부 **`?`** — 429 에러 바디에는 그 키가 없어서 파싱이 실패한 것이고,
  `?` 는 "못 찾았다"를 숨기지 않는 표시다(조용히 옛 값을 재출력하지 않는다).
- ✅ **429 뒤에 재전송 줄이 없다.** 1차 재시도 없음 정책 — 같은 `id` 가 다시 나가면 **실패**다.
- ✅ DB 행은 **1건만** 증가(429 는 저장되지 않는다).

### (c) 재부팅 후 전송 — `client_request_id` 충돌 없음

1. (a) 를 한 번 돌려 `[BOOT] ... nonce=XXXX` 와 전송 `id` 를 적어둔다.
2. 보드 리셋 버튼(또는 USB 재연결) → 부팅 로그의 `nonce` 를 적는다.
3. 다시 `s`.

기대:
```
[BOOT] client_request_id nonce=3f8a1c07   ← 1회차
[BOOT] client_request_id nonce=c04e91b2   ← 2회차, 값이 다르다
```
- ✅ **두 nonce 가 다르다** → `id` 가 재부팅 간 충돌하지 않는다.
- ✅ 2회차 응답이 **`http=201`** 이고 헤더 `Idempotent-Replay` 경로를 타지 않는다.
  (하네스 방식인 `millis()` 단독이었다면 재부팅 후 `spike-1234-1` 이 그대로 재생산돼
   서버가 24h 캐시 응답을 **200 으로 replay** 한다 = 새 소리를 보냈는데 옛 판정이 돌아온다.)
- ❌ 만약 `http=200` 이 뜨면 nonce 가 안 걸린 것이다 — 즉시 보고.

---

## 6. 추가 관측 (매 전송 자동 출력)

```
[mic][M5d] stk_free=1824 psram_free=8123456 gaps=0 tof_stk=4100
```
- `stk_free` = `micUplinkTask` 스택 최저 여유(bytes). `MIC_TASK_STACK_SIZE=4096` 기준
  (decisions.md 6.3(l) ① 경고 항목). **0 에 근접하면 보고** — 다만 POST 는 이 태스크가 아니라
  loop 태스크에서 돌므로 큰 여유가 나오는 것이 정상이다.
- `psram_free` = 전송마다 같은 값이어야 한다(버퍼는 부팅 시 1회 할당). **단조 감소하면 누수**다.
- `gaps` = `i2s_read` 실패 누적(링버퍼 구멍). 9절 (b) 동시 구동에서 **증가 0** 이어야 한다.
- `tof_stk` = `tofTask` 스택 최저 여유(`TOF_TASK_STACK_SIZE=6144` 기준). ToF 없으면 0.

## 7. 실패 시 로그 대응표

| 로그 | 의미 | 조치 |
|---|---|---|
| `PSRAM alloc FAILED` | PSRAM 미활성/부족 | `-DBOARD_HAS_PSRAM` 빌드 확인 |
| `WiFi both SSIDs failed` | 핫스팟 미연결 | UPLOAD_TEST_RUNBOOK 2절 함정 5건 |
| `ring 미충전` | 부팅 2초 미경과 | 기다린 뒤 재시도 |
| `WiFi 끊김 — 전송 생략` | 런타임 연결 유실 | 핫스팟 재방송(재시도 없음이 설계다) |
| `http=401` | 토큰 3곳 불일치 | 서버 `DEVICE_TOKEN` ↔ `SPIKE_DEVICE_TOKEN` |
| `http=-1 ... 전송실패` | 타임아웃/소켓 | 서버 `--host=0.0.0.0` / IP 갱신 |
| `snapshot bytes=... != 65536` | 스냅샷 복사 불완전 | **즉시 보고** (도달해서는 안 되는 가드) |

## 8. 호스트 단위 검증 (하드웨어 없이 언제든 재실행)

```
c++ -std=c++17 -Wall -o /tmp/jpt firmware/tools/jsonpeek_test.cpp && /tmp/jpt
```
`mic_uplink_main.cpp` 의 `jsonPeek` 를 실제 `/detect` 201 응답 바디로 검증한다
(`"skip_reason"` 오매치 / 키 부재 / 에러 바디 / 버퍼 초과 negative control 포함).

```
c++ -std=c++17 -Wall -I firmware/include -I firmware/tools/host_stubs \
    -o /tmp/tjt firmware/tools/tof_judge_test.cpp firmware/src/tof_common.cpp && /tmp/tjt
```
`tof_common.cpp` 의 `tofJudgeFrame`(승격된 Stage A/B-1/B-2 판정 본문)을 **실제 소스 그대로 링크**해
합성 프레임으로 검증한다(디바운스 N=3 / 임계 8·1000mm / center 27·28·35·36 / latch 75 / ndet≥1 /
프레임 단위 AND / 전이 로그 verbatim). 스텁 = `firmware/tools/host_stubs/`(Serial·Wire·SparkFun 표면만).

negative control(각각 **반드시 실패**해야 통과. 변형 후 원복 필수 — `git diff` 로 0 확인):
| # | 변형(파일 · 1건 치환) | 검출 위치(2026-09-11 실측) |
|---|---|---|
| ① | `tof_common.h` `TOF_PRESENCE_DEBOUNCE_FRAMES = 3` → `2` | T2 2프레임째 `!r.presence_state` |
| ② | `tof_common.h` `TOF_MOTION_LATCH_FRAMES = 75` → `74` | T6 74프레임째 `r.fused` |
| ③ | `tof_common.h` `TOF_CENTER_ZONES` `{27,…}` → `{26,…}` | T5 `center_mm == 500` |
| ④ | `tof_common.cpp` `presence_state && latch_active` → `\|\|` | T2 전이 로그 verbatim(B-2 줄이 먼저 뜸) / T7 |
①~③은 `static_assert` 가 컴파일 단계에서 먼저 잡는다. **행동 단언**이 잡는지를 보려면
`-DTOF_TEST_NO_CONST_PIN` 을 붙여 컴파일한다.

---

## 9. ★ ToF 메타 4필드 송신 (PoC-(45)) — ④런타임 대조 실험 4건

### 9.0 이 절이 증명하려는 것
PR #52 까지 응답은 **항상** `tof=tof_absent` 였다(4필드 미전송). 이 PR 이후 ToF 가 결선된 상태에서는
응답이 **달라져야** 한다. 변경 전 값(`tof_absent`)과 같으면 아무것도 증명되지 않는다.

**결과 판정은 서버 access log 시각 기준**으로 한다 — 보드 모니터의 `http=` 줄은 다음 입력 시점까지
지연 출력된 선례가 있다(PR #52 댓글 "모니터 결과 줄 지연 출력", CDC 출력 지연 추정). 서버 터미널의
`detect tof meta: state=… applied=… passed=… reason=…` 줄과 짝지어 읽을 것.

### 9.1 전제
- **결선 변경 금지.** ToF = `tof_dummy` 와 같은 SDA=GPIO5(D4)/SCL=GPIO6(D5), PWREN/LPn=3V3
  (decisions.md 9.1(d)). 마이크 I2S1(GPIO2/3/7)과 핀 겹침 없음.
- **센서 앞 1.5m 이상 빈 공간** 확보. 9.2(e) 시야 가장자리 오염(near 가 2~8/64 로 상시, center `n/a`)
  이 나오면 무자극 기준선이 서지 않는다 — 책상 위 물건·모니터를 시야에서 치울 것.
- 핫스팟 설정 화면을 열어 둔다(1~3절 동일).
- 전송 사이 **5초 이상** 간격(rate limit).

### 9.2 (a) 센서 앞 비움 vs 손·사람 40~150cm — presence 가 바뀌고 서버 게이트가 **적용**되는가
1. 센서 앞을 비운 채 5초 이상 기다린 뒤 `s`.
2. 5초 대기. 손(또는 사람)을 센서 앞 40~150cm 에 두고 **움직이면서**(latch 재충전) `s`.
3. 손을 그대로 둔 채 **정지** 5초 이상(latch 75프레임 만료) 후 `s`.

기대 (펌웨어, `s` 직후 즉시 1줄):
```
[tof][M5d] presence=false near=0/64 center=n/a ndet=0/16 age_ms=41        ← 1. 비움
[tof][M5d] presence=true near=31/64 center=612mm ndet=3/16 age_ms=12      ← 2. 손 움직임
[tof][M5d] presence=false near=30/64 center=608mm ndet=0/16 age_ms=55     ← 3. 손 정지 5초+
```
- `presence` = **fused**(Stage A presence ∧ motion latch, decisions.md 6.4(b)). 3번에서 `near` 는
  높은데 `presence=false` 인 것이 **정상**이다(9.4(d) "latch 만료" 사례 재현). 이것이 wire 매핑 증거다.
- `age_ms` = 마지막 ToF 프레임 → `s` 까지 경과. 15Hz 면 **상시 < 100ms**. 수백 ms 가 반복되면 보고
  (신선도 정책은 미도입 — 분포를 적어 두는 것이 판정 재료다).

기대 (응답 + 서버 로그):
```
[mic][M5d] tof=presence=false near=0/64 center=n/a ndet=0/16           ← 1
[mic][M5d] tof=presence=true near=31/64 center=612mm ndet=3/16         ← 2
detect tof meta: state=present applied=True passed=True reason=presence=true near=31/64 center=612mm ndet=3/16
```
- ✅ **`tof_absent` 가 사라진다** → `applied=True`. 1·3번은 `passed=False`(doorbell/knock 이면
  `skip_reason=tof_rejected`), 2번은 `passed=True`. `fire_alarm` 이 뜨면 `fire_alarm_bypass (…)` 로
  우회된다(카테고리 3) — mock 난수라 클래스는 고를 수 없으니 여러 번 눌러 3클래스가 한 번씩은 나오게.
- ✅ 펌웨어 `[tof][M5d]` 줄의 4값과 서버 reason 의 4값이 **정확히 같다**(같은 어휘 `near=n/64` /
  `center=NNNNmm` / `ndet=n/16`). 다르면 필드 매핑 버그다 — 즉시 보고.
- ❌ 여전히 `tof_absent` 면: `[BOOT] tof init 실패` 였는지(degrade 경로) 먼저 확인.
- ❌ `tof_invalid(…)` 면 값 표기가 서버 허용표 밖 — 즉시 보고(도달해서는 안 되는 경로).

### 9.3 (b) 동시 구동 부하 — ToF 15Hz + 마이크 + WiFi 수 분 가동 중 5회 이상 전송
5분 이상 켜 둔 채 30~60초 간격으로 `s` 를 **5회 이상**. 매회 아래 줄을 적는다:
```
[mic][M5d] stk_free=1824 psram_free=8123456 gaps=0 tof_stk=4100
[tof][M5d] … age_ms=23
```
- ✅ `gaps` 가 5회 내내 **0 (증가 0)** — tofTask(prio 3)가 micUplinkTask(prio 4)의 DMA 적재를
  밀어내지 않는다는 증거. 1 이라도 오르면 보고(ToF I2C 읽기 ≈ 수십 ms 가 원인 후보).
- ✅ `age_ms` 상시 작음(< 100ms). ✅ `psram_free` 불변. ✅ `stk_free` / `tof_stk` 가 회차 간
  **단조 감소하지 않음**(최저 여유라 첫 회차 이후 고정되는 것이 정상). 두 값 모두 기록.

### 9.4 (c) PR #52 회귀 요약
- `s` 후 **2초 안에** 다시 `s` → 두 번째 `http=429` + `tof=?` + **재전송 줄 없음**(재시도 없음).
- RESET 후 `[BOOT] client_request_id nonce=` 가 **달라지고** 다음 전송이 `http=201`(200 replay 아님).
- (a) 의 `bytes=65536` / 서버 `samples=32768` 불변.

### 9.5 (d) 승격 회귀 — `tof_dummy` 재플래시
```
~/.platformio/penv/bin/pio run -d firmware -e tof_dummy -t upload
```
- ✅ 부팅~2초 주기 `[tof][StageA] frame #N near=…/64 presence=… center=…` / 1초 주기
  `[tof][StageB-1] mi: g1=… ndet=…/16 st=… aggmax=… | near=… center=…` 가 **PR #39 와 같은 포맷**.
- ✅ 사람 접근 시 `[tof][StageA] presence: NONE -> DETECTED (near=…, center=…, streak=3)` 전이와
  `[tof][StageB-2] fused #N: NONE -> PERSON (…, latch=75/75, ndet=…)` 전이가 관측된다.
- 판정 본문은 `mic_uplink` 와 **같은 함수**(`tofJudgeFrame`)라 여기서 포맷이 같으면 승격이 로직을
  바꾸지 않았다는 ④ 증거다(호스트 테스트 8절이 ③ 증거).
