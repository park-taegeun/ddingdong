# `env:enrich_uplink` ④런타임 Runbook — 보드 2차 체인 (PR-B)

> 형식은 `CAMERA_PROBE_RUNBOOK.md` 준용. 본 PR 세션에서 **④런타임은 수행되지 않았다**
> (③컴파일 + 호스트 테스트 + NC 까지). 아래는 학부생 로컬에서 밟을 절차다.

---

## 0. 이 세션이 증명하려는 것

`/detect` → `enrich_status` 게이트 → 카메라 1장 + 5.120초 녹음 → `/enrich` 가
**실제로 관통하는가**. 판정은 이미 서버에서 끝나 있고 보드는 경로만 잇는다.

증명해야 하는 4가지:

1. `/detect` 201 응답에서 `enrich_status` 를 **읽어냈는가** (`gate=pending|skip|parsefail` 로그)
2. `pending` 일 때만 2차가 나가는가 (skip 에서 2차가 나가면 서버가 409·404 를 낸다)
3. 2차 오디오가 **5.120초 · 163,840 B** 로 도착하는가 (서버 `enrich audio decoded: duration_s=5.120`)
4. 이미지가 JPEG 로 도착하는가 (서버가 SOI 400 을 내지 않는가)

**확정하지 않는 것**: 타임아웃 최종값 · 녹음 길이 최종값 · 해상도 — 전부 **PR-C 소관**이다.

---

## 1. 전제

- 보드는 현재 **`camera_probe` 가 플래시돼 있다** → **재플래시가 선행**이다.
- `firmware/include/secrets.h` 의 `SPIKE_SERVER_HOST` / `SPIKE_SERVER_PORT` / `SPIKE_DEVICE_TOKEN`
  이 실제 서버를 가리켜야 한다. **실값을 로그·문서·PR 본문에 남기지 말 것.**
- 서버(`server/`)가 기동돼 있어야 한다. `/enrich` 는 `/detect` 가 먼저 행을 만든 뒤에만 200이다
  (순서 역전 = **404**, 재처리 = **409** — decisions.md 6.5(b)).
- 카카오 토큰·NCP 자격증명이 설정돼 있으면 **실발송·실과금이 일어난다**. 세션 상한 12를
  코드가 걸어 두지만, 그 상한은 **부팅마다 리셋**된다(재부팅 = 새 세션).
- 포트 1개만 점유 — 모니터를 켠 채 업로드하지 말 것.

---

## 2. 빌드 · 플래시 · 모니터

```
cd firmware
pio run -e enrich_uplink                       # 빌드만
pio run -e enrich_uplink -t upload             # 플래시 (모니터 끈 상태에서)
pio device monitor -e enrich_uplink            # 115200
```

부팅 배너에서 확인할 줄:

```
[BOOT] ddingdong enrich uplink (PR-B, 수동 's' 트리거)
[uplink] PSRAM alloc OK tag=snapshot bytes=65536
[uplink] PSRAM alloc OK tag=multipart bytes=66560
[uplink] PSRAM alloc OK tag=enrich-rec bytes=163840
[uplink] PSRAM alloc OK tag=enrich-body bytes=676864
[BOOT] rec=163840B 5120ms ebody=676864B
[BOOT] micEnrichTask started (Core 0) — POST 는 loop 태스크
[mic][e2] ring filled — 's' 로 2차 체인 시작
```

4개 alloc 중 하나라도 FAILED 면 전송이 비활성된다(적재는 계속). PSRAM 총 점유 ≈ 1.07 MB
= 부팅 여유 8.3 MB 의 **12.9%** — 실패하면 그 자체가 보고 대상이다.

---

## 3. 절차

1. `[mic][e2] ring filled` 이 뜰 때까지 기다린다(약 2초).
2. **소리를 내면서** `s` 를 친다. 2차 녹음은 `s` **시점부터** 5.120초 담긴다(pre 0) —
   `s` 를 친 **뒤에** 말해야 그 말이 2차 오디오에 들어간다.
3. 아래 로그 6~8줄이 순서대로 나온다. 전부 ≤80B 다(6.3(j)).

```
[tof][e2] presence=true near=13/64 ndet=1/16 age_ms=42
[e2] trigger — 2차 녹음 시작 + 1차 스냅샷 요청
[e2] id=e2-89abcdef-1 rms=812 peak=9044
[e2] stk=2048 psram=7234560 gaps=0 tof_stk=1536
[e2] d http=201 rtt=1043ms cls=doorbell conf=0.97
[e2] gate=pending sent=0/12
[e2] cam ms=383/121 len=5438 soi=1
[e2] e http=200 rtt=2210ms body=169700
```

4. 최소 **3회** 반복한다 — ① `pending` 관통 1회 ② 저신뢰로 `skip` 이 나오는 건 1회
   (조용한 소리) ③ 같은 `client_request_id` 재요청 없이 연속 2회.

---

## 4. ★ 수신 1회 도착 확인 (생략 금지)

> **근거 = decisions.md 6.6(d)**: `ARP_QUEUEING=1` 때문에 대상 기기가 없어도 `sendto()` 가
> 성공을 돌려준다. **`txerr=0` 은 「무선으로 나갔다」를 보장하지 않는다.** 2차 실업로드도 같은
> 함정을 공유한다 — **보드 로그의 `e http=200` 만으로 「서버가 받았다」를 확정하지 말 것.**

**서버 쪽에서** 아래 3개를 눈으로 확인한다(시각 판정은 **서버 access log 기준** — 6.3(m):
시리얼은 USB CDC 지연으로 밀린다):

| 확인 | 어디서 | 기대 |
|---|---|---|
| 요청 도달 | 서버 access log | `POST /api/v1/enrich` 1줄 |
| 오디오 길이 | 서버 app log | `enrich audio decoded: ... duration_s=5.120` |
| STT 호출 여부 | 서버 app log | `enrich stt: mode=real\|mock ...` |

`duration_s` 가 5.120 이 아니면 **본 PR 의 버퍼 산술이 틀린 것**이다 — 값과 함께 정지 보고.

---

## 5. 로그 대응표

| 로그 | 뜻 | 할 일 |
|---|---|---|
| `[e2] gate=skip` | 서버가 2차를 안 한다고 판정 | **정상**. 409·404 를 만들지 않으려고 안 보낸 것 |
| `[e2] gate=parsefail` | `enrich_status` 를 못 읽었다 | 응답 바디가 잘렸거나 4xx. **기본값 폴백 없음** = 설계대로 |
| `[e2] cam ms=.../... soi=0` | JPEG SOI 불일치 | 2차 미발송. 카메라 재시도 없음 — 다음 `s` 로 |
| `[e2] fb_get NULL` | 프레임버퍼 고갈 | 32.2 / 17 #620 축. WiFi 동시 구동 부하와 함께 기록 |
| `[e2] e http=404` | 선행 `/detect` 행이 없다 | 1차가 실패했는데 2차가 나갔다는 뜻 → **게이트 버그** |
| `[e2] e http=409` | 이미 처리된 알림 | 같은 `client_request_id` 재전송 → nonce 확인 |
| `[e2] e http=-1` | 타임아웃·소켓 실패 | 15초를 넘겼다 → rtt 값을 기록. 확정값(2026-09-23)의 **재판정 트리거와 대조**(`uplink_common.h` 주석) |
| `[e2] rec 미완 filled=N/163840` | i2s_read 가 멈췄다 | `gaps` 와 함께 보고. 6.3(n) 축과 대조 |
| `[e2] 세션 상한 도달` | 12건을 이미 보냈다 | 정상. 더 필요하면 재부팅(= 새 세션) |

---

## 6. 수집해서 넘길 것 (PR-C 입력)

1. **2차 POST rtt** (`e http=... rtt=...ms`) 를 **전 이벤트** 기록 → §2-2(a) 15,000ms 는
   **2026-09-23 확정**(값 변경 없음). 이후 rtt 기록은 재판정 트리거(`uplink_common.h` 주석) 대조용이다.
   12.1초는 7.7(l)이 **과소평가**로 판정한 미실측 산술 상한이다 — 확정 근거가 아니다.
2. **캡처 ms / init ms** (`cam ms=init/cap`) — 6.6(c) 의 383ms 와 대조.
3. **서버 `duration_s` / `decode_ms`** — 녹음 길이 확정(§2-2(b)) 입력.
4. **`[MEM:e2-pre-init]` / `[MEM:e2-post-deinit]`** free 값 — 카메라 누수 0 재확인(6.6(c)).
5. `gaps` 증가 여부 — 2차 녹음 memcpy 가 i2s_read 를 잠식하는지.

---

## 7. 호스트 단위 검증 (하드웨어 없이 언제든 재실행)

```
c++ -std=c++17 -Wall -I firmware/include -o /tmp/ewt firmware/tools/enrich_wire_test.cpp && /tmp/ewt
```

기대: `enrich_wire_test: 90 checks passed`

### 7-1. negative control 5종 — **각각 반드시 실패해야 한다**

★ **변형 적용 증명에 바이너리 md5 를 쓰지 말 것** — macOS clang 은 동일 소스 2회 컴파일에도
md5 가 갈린다(카테고리 20, 2026-09-18). **전처리 출력(`c++ -E`) md5** 로 대체한다.

| NC | 변형 (`firmware/include/enrich_wire.h`) | 깨지는 불변식 | 도달 가능 입력 |
|---|---|---|---|
| NC-1 | `enrichBuildMultipart` 의 image/audio 파트 이름 **스왑** | I1 이름↔바이트 대응 | 모든 2차 발송 → 서버 SOI 400 |
| NC-2 | `enrichGateFromDetectBody` 가 항상 `PENDING` 반환 | I2 skip 시 미발송 | `enrich_status="skipped"` 응답 → 409 |
| NC-3 | 파싱 실패 시 `PARSE_FAIL` → `PENDING` 폴백 | I3 조용한 통과 금지 | 잘린 응답 바디 → 근거 없는 2차 발송 |
| NC-4 | `sent < MAX` → `sent <= MAX` | I4 과금 상한 | 12건째 이후 → CSR 일 한도 초과 |
| NC-5 | `ENRICH_AUDIO_BUFFERS` 80 → 62 | I5 녹음 ≥5.000초 | 모든 2차 → 3.968초 오디오 |

⚠️ **파트 「순서」만 뒤집는 변형은 쓰지 않았다** — 서버 계약상 무해할 수 있어(6.5(d) 함정 예고)
깨지는 불변식을 세울 수 없다. 대신 NC-1 은 **이름 스왑**이고, 검출자는 이름 카운트가 아니라
**이름 뒤 바이트 대조**다(이름만 세면 스왑이 통과한다 — 2026-09-18 실측으로 확인).

### 7-2. 도달 불가로 분류한 항목

| 변형 | 왜 도달 불가인가 |
|---|---|
| `enrich_uplink_main.cpp` 의 게이트 배선(`if (gate != ENRICH_GATE_PENDING)`) 제거 | 그 파일은 Arduino/ESP-IDF 의존이라 **호스트 테스트 표면이 없다**. 단언이 무딘 게 아니라 **단언 자체가 없다**. 보드 플래시 + 서버 로그로만 검출된다 → **§4 의 「수신 1회 도착 확인」이 이 NC 의 런타임 대역물**이다 (6.6(f) 선례) |
| 카메라 fb 고갈 / PSRAM alloc 실패 | 보드 플래시 필요 |

---

## 8. 정지 트리거 (보고 후 사용자 판단)

- 서버 `duration_s` 가 5.120 이 아님 → 버퍼 산술 오류
- `gate=pending` 인데 `/enrich` 가 404 → 게이트가 1차 실패 건을 통과시킴
- 2차 rtt 가 15,000ms 를 반복 초과 → §2-2(a) 확정값(2026-09-23)의 **재판정 트리거 후보**. **값을 이 자리에서 바꾸지 말 것**(판정 PR 소관)
- `gaps` 가 0 에서 증가 → 2차 녹음이 I2S 를 잠식. 6.3(n) 과 엮지 말고 **따로** 보고
- 6.3(n) 「ToF I2C 통신 시 마이크 SD 비트 오류」 해결책 ①②③ 중 하나를 고르게 되는 상황

---

## 9. 이 PR 이 바꾸지 않는 것

- `server/` · `dashboard/` · `ml/` — **1바이트도 미접촉**
- `mic_common.*` · `mic_uplink_main.cpp` · `camera_common.*` · `tof_common.*` · `probe_*.h` — 무변경
- `uplink_common.*` 의 **기존** 함수·상수 — 무변경(추가만)
- 기존 12개 env — 무수정(`platformio.ini` 는 추가 39줄 · 삭제 0줄)
- 1차 `UPLINK_HTTP_TIMEOUT_MS = 10000` — 무변경
- 6.3(n) 해결책 ①②③ · G29 pre:post 비율 · RMS 자동 트리거 — 전건 미판단

---

## 10. 기기 heartbeat — 보드가 30초마다 「살아 있음」을 보고 (env:enrich_uplink · env:enrich_autotrig 공통)

> **무엇을 가르나**: 서버 `POST /api/v1/heartbeat` · 대시보드 실판정(PR #103)에 보드 쪽 보고를 붙였다. 컴파일 · 호스트 테스트 · 서버 계약(테스트 클라이언트 204 → `/stats` online)까지는 증명했고, **배선 · 동시성 · 메모리는 보드에서만** 드러난다.
> 사용자 결정(권고 수용) 2026-10-06 — 보고 30초 · 서버 꺼짐 판정 90초(둘 다 잠정) · 보내는 값 = device_id · rssi · uptime_s · fw · enrich_sent.

### 10-1. 무엇을 언제 보내나

- 별도 태스크(`hbTask`, loop 와 같은 Core 1 · 같은 우선순위 · 스택 8192)에서 보낸다. loop 의 자동 트리거 수락 창(발화 뒤 약 20버퍼 = 1.28초)을 망 지연에 묶지 않기 위해서다.
- 태스크는 **PSRAM 버퍼 4개 + 마이크 태스크가 다 떴을 때만** 생긴다(아니면 `[BOOT] heartbeat 미기동 …` 또는 mic init 실패의 조기 return → 대시보드는 계속 「꺼짐」 = 정상).
- 매 주기 판정 순서 = **WiFi → RSSI(−127 ~ −1) → 마이크 진행(직전 보고 이후 슬롯 적재 수가 늘었나)**. 하나라도 아니면 보내지 않고 사유만 찍는다. 재시도 0.
- device_id = `/detect` 와 같은 `UPLINK_DEVICE_ID`(서버 heartbeat 는 rate limit 을 부르지 않는다 — 초인종 429 유발 없음, PR #103 테스트로 고정).
- 상수(전부 잠정 — `firmware/include/heartbeat_wire.h` 주석에 근거 · 재판정 트리거): 주기 30,000ms · 첫 보고 3,000ms · connect 3,000ms · 무응답 3,000ms(최악 총 경과 산술 18,200ms < 주기).

### 10-2. 로그 줄 읽는 법 (`[hb]` 줄은 hbTask 가 낸다 — 마이크 태스크 Serial 0줄 유지)

| 줄 | 뜻 | 최악 길이 |
|---|---|---|
| `[BOOT] heartbeat period=30000ms first=3000ms fw=enrich_autotrig` | 태스크 생성됨. **period 가 30000 이 아니면 테스트 훅 빌드**다 | 63B |
| `[BOOT] heartbeat 미기동 — PSRAM 버퍼 없음(대시보드 꺼짐 유지)` | 버퍼 실패 → 보고 안 함 | — |
| `[BOOT] heartbeat 태스크 생성 실패 — 보고 없음(재시도 없음)` | 내부 RAM 부족 의심 → 정지 · 보고 | — |
| `[hb] http=204 rtt=12ms rssi=-55 up=123 stk=5120` | 보고 성공. `stk` = 태스크 스택 **여유** high-water(B) | 65B |
| `[hb] http=-1 …` / `http=401` / `http=400` | 전송 실패 / 토큰 불일치 / 본문 계약 위반 → 400 은 정지 · 보고 | 65B |
| `[hb] skip=wifi rssi=0 mic=…` | WiFi 끊김 — 보드는 재연결하지 않는다(기존 동작) | 39B |
| `[hb] skip=rssi rssi=0 mic=…` | 연결 확인과 RSSI 읽기 사이에 끊김(0 = 「강함」 오표시 방지로 거름) | 39B |
| `[hb] skip=mic rssi=-55 mic=…` | 30초 동안 마이크 슬롯 적재 0 = i2s 정지 → 정지 · 보고 | 39B |
| `[hb] build=0` | 본문 조립 실패(도달 불가 가드) → 정지 · 보고 | — |

### 10-3. ④런타임 판정 절차 (학부생 몫)

| # | 절차 | 기대 |
|---|---|---|
| H1 | 부팅 → 약 3초 뒤 | 보드 `[hb] http=204`, 대시보드 「켜짐」(폴링 3초 이내) |
| H2 | 5분 관찰 | `[hb] http=204` 줄 ≈ 10 · 서버 access log 의 `POST /api/v1/heartbeat … 204` 수와 일치 |
| H3 | USB 뽑기 | 뽑은 뒤 약 **60 ~ 93초** 사이에 「꺼짐」. 산술: 마지막 보고 = 뽑기 0 ~ 30초 전 · 서버 판정 = 마지막 보고 + 90초 **초과** · 대시보드 폴링 3초 |
| H4 | 대조 실험(loop 무간섭 확인) | 같은 자리 · 같은 소리로 **정상 빌드 ↔ 테스트 훅 빌드**(`HB_PERIOD_MS_TEST=2000`) 교대 블록, 자동 감지 노크 각 10회 → `[e2a] busy · drop · ring · late` 계수와 수락 수 비교. **훅 빌드에서 late · 놓침 증가 0**(증가 시 정지 · 보고). 블록 경계 = 학부생이 알린 시작 시각 + 서버 detect 수 |
| H5 | 핫스팟 끄기 | `[hb] skip=wifi` 반복 + 90초 뒤 「꺼짐」 = 정상(그 자체가 「기기 연결 확인」 신호) |
| H6 | 직접녹음 수신기(`server/tools/record_receiver.py`)와 쓸 때 | 수신기 창에 30초마다 heartbeat **404** 줄 = 정상(수신기는 `/detect` · `/enrich` 두 경로만 흉내 — 무수정) |
| H7 | 내부 메모리 | 이벤트 때 `e2-pre-init` 메모리 진단 줄의 내부 RAM 여유가 이전 런 대비 태스크 스택(약 8KB)만큼 준 것 외 이상 없음 · 카메라 init 성공 |

테스트 훅 빌드(ini 무변경 — 환경 변수로만 주입. 끝나면 반드시 플래그 없이 다시 빌드 · 플래시):

```bash
cd firmware
PLATFORMIO_BUILD_FLAGS="-DHB_PERIOD_MS_TEST=2000" pio run -e enrich_autotrig -t upload   # [BOOT] period=2000ms 확인
pio run -e enrich_autotrig -t upload                                                     # 정상 빌드로 복귀 — period=30000ms 확인
```

훅 값은 1000 이상만 컴파일된다(`HB_PERIOD_MS_TEST=500` → static_assert 실패로 빌드가 멈춘다 — 훅이 컴파일에 닿는다는 증명).

### 10-4. 호스트 단위 검증 (repo 루트에서)

```bash
c++ -std=c++17 -Wall -I firmware/include -o /tmp/hbt firmware/tools/heartbeat_wire_test.cpp && /tmp/hbt
```

negative control — `heartbeat_wire.h` 를 아래처럼 바꾸면 **반드시 실패**해야 한다(되돌리면 통과):

| 변형 | 깨지는 불변식 | 결함이 되는 조건 | 함정 |
|---|---|---|---|
| hbDecide 가 마이크 진행을 무시(항상 SEND) | 「모르면 정상」 금지 | i2s 가 멈춰도 「켜짐」 | WiFi 끊김 케이스만 보면 통과 |
| hbBuildJson 이 잘려도 부분 길이 반환 | 부분 본문 금지 | 서버 400 · 깨진 본문 | cap 이 넉넉하면 안 드러남 → n · n+1 경계 |
| 필드 이름 `uptime_s` → `uptime` | 서버 계약 | 서버 400 | 정확 바이트 케이스가 잡는다 |
| `HB_PERIOD_MS` 31000 | 꺼짐 판정 ≥ 보고 3회분 | 연속 2회 유실 전에 헛 「꺼짐」 | 서버 constants.py 텍스트 대조가 잡는다 |
| 판정 순서 뒤집기(마이크 먼저) | 사유 로그 = 가장 앞선 원인 | WiFi 끊김이 `skip=mic` 로 찍힘 | 단일 원인 케이스만 보면 통과 |
| RSSI 범위 검사 제거 | RSSI 0 미전송 | 0 이 나가 대시보드 「강함」(서버 검증으론 못 잡음) | 정상 RSSI 만 보면 통과 |
| RSSI 상한 −1 → 0 | 〃 | 〃 | 0 경계 1점이 잡는다 |
| 위험 문자 검사 제거 | 이스케이프 발명 금지 | 따옴표 든 값이 JSON 을 깸 | — |

### 10-5. 이 절이 바꾸지 않는 것

- `platformio.ini` 0줄 · `server/` · `dashboard/` · `record_receiver.py` 무변경
- `uplink_common.*` 기존 함수 6개 · 상수 — 무변경(끝에 `uplinkPostHeartbeat` 추가만)
- loop · `micEnrichTask` · `tofEnrichTask` · `autoTrigAccept` · `runEvent` 본문 — 마이크 슬롯 계수 1줄 · `g_enrichSent` volatile 외 무변경
- WiFi 자동 재연결 · 끊김 카톡 알림 — 범위 밖(별도 결정)
