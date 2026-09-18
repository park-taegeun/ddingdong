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
| `[e2] e http=-1` | 타임아웃·소켓 실패 | 15초를 넘겼다 → **PR-C 재판정 입력**. rtt 값을 기록 |
| `[e2] rec 미완 filled=N/163840` | i2s_read 가 멈췄다 | `gaps` 와 함께 보고. 6.3(n) 축과 대조 |
| `[e2] 세션 상한 도달` | 12건을 이미 보냈다 | 정상. 더 필요하면 재부팅(= 새 세션) |

---

## 6. 수집해서 넘길 것 (PR-C 입력)

1. **2차 POST rtt** (`e http=... rtt=...ms`) 를 **전 이벤트** 기록 → §2-2(a) 잠정값 15,000ms
   재판정의 유일한 실측 입력이다. 12.1초는 **미실측 산술 상한**이다(7.7(l)).
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
- 2차 rtt 가 15,000ms 를 반복 초과 → §2-2(a) 잠정값이 부족. **값을 이 자리에서 바꾸지 말 것**(PR-C)
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
