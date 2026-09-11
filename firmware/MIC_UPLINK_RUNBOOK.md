# 마이크 2초 스냅샷 업로드 ④런타임 Runbook (M5-d, `env:mic_uplink`)

> 2026-09-11 작성. **실행은 학부생**, 본 문서는 절차서다.
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
[mic][M5d] ring filled — 's' 키로 스냅샷 전송 가능
```

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
[mic][M5d] http=201 rtt=842ms cls=knock conf=0.51 tof=tof_absent
```
- ✅ **둘 다 `http=201`**, 둘 다 `tof=tof_absent`(본 env 는 ToF 필드를 보내지 않는다 → 서버 fail-open).
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
[mic][M5d] http=201 rtt=812ms cls=... conf=... tof=tof_absent
[mic][M5d] http=429 rtt=18ms cls=? conf=? tof=?
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
[mic][M5d] stk_free=1824 psram_free=8123456
```
- `stk_free` = `micUplinkTask` 스택 최저 여유(bytes). `MIC_TASK_STACK_SIZE=4096` 기준
  (decisions.md 6.3(l) ① 경고 항목). **0 에 근접하면 보고** — 다만 POST 는 이 태스크가 아니라
  loop 태스크에서 돌므로 큰 여유가 나오는 것이 정상이다.
- `psram_free` = 전송마다 같은 값이어야 한다(버퍼는 부팅 시 1회 할당). **단조 감소하면 누수**다.

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
