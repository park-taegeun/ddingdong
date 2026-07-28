# ESP32 업로드 지연 실측 Runbook

> 2026-07-28 PoC-(27) 최초 실측 시 확립. 시연 네트워크(카테고리 23 모바일 핫스팟)와 동일 구성이라 발표 리허설에도 재사용.
> 다음 실측(ToF Stage B ④런타임, 재측정 등) 시 prereq 배선 재헤맴 방지용. 실측 수치 상세 = `docs/decisions.md` 6.2 (`9d56852`).

## 0. 준비물

- XIAO ESP32-S3 보드 + u.FL 외장 안테나(6/22 장착분, 미장착 시 WiFi 0)
- USB-C **데이터** 케이블(충전전용 X)
- iPhone(핫스팟) + Mac(서버 + flash)
- 서버 코드(`server/`), PR #25 하네스(`env:upload_spike`)

## 1. prereq 체크리스트 (순서 중요)

1. 보드 USB 연결 → `ls /dev/cu.usbmodem*` 로 포트 확인(예: `usbmodem1101`)
2. u.FL 안테나 장착 확인(선이 커넥터에 딸깍 — 실패 시 런타임 RSSI 안 뜸)
3. iPhone 핫스팟: 설정 → 개인용 핫스팟 → "다른 사람의 연결 허용" ON + **"호환성 최대화" ON(2.4GHz 강제, XIAO는 5GHz 불가)**. 설정 화면 열어두기(절전 방지)
4. Flask 서버(Mac):
   ```
   cd server && source venv/bin/activate && DEVICE_TOKEN=<토큰> flask --app run run --host=0.0.0.0 --port=5000
   ```
   - **`host=0.0.0.0` 필수**(`run.py`는 127.0.0.1 하드코딩 = frozen이라 CLI 오버라이드)
   - 5000 포트 점유 시 `lsof -ti :5000 | xargs kill`
   - macOS AirPlay 5000 점유 함정: `lsof -i :5000`에 AirTunes 뜨면 **AirPlay 수신기 OFF**
5. Device Token 생성: `python3 -c "import secrets; print(secrets.token_hex(16))"` → 서버 재기동 값 + `secrets.h` 동일 값(**3곳 일치 필수**: 서버 / `secrets.h` / curl)

## 2. ★ 핫스팟 연결 함정 5건 (2026-07-28 실증, 다음에도 재현 가능)

1. **IP 가변성**: 노트북이 핫스팟 붙으면 IP가 `172.20.10.x` 대역(랩실은 `192.168.0.x`). `secrets.h`의 `SPIKE_SERVER_HOST`를 그 IP로 매번 갱신 + 재flash. `ipconfig getifaddr en0`로 확인.
2. **맥이 핫스팟 IP 못 받음(`192.0.0.2` 유령주소)**: IPv6 협상이 IPv4 DHCP를 밀어냄. 해결 = `sudo networksetup -setv6off Wi-Fi` 후 `sudo networksetup -setv6automatic Wi-Fi`(껐다 켜기) → DHCP 재협상으로 `172.20.10.x` 획득.
3. **맥 목록에 iPhone 안 뜸**: 맥 블루투스 OFF면 자동 핫스팟(Instant Hotspot) 협상 실패. **맥 블루투스 ON** 필수(같은 Apple ID여도).
4. **보드가 핫스팟 못 붙음(timeout)**: 노트북 붙은 후 핫스팟 밴드 꼬임. 해결 = **폰 핫스팟 껐다 켜서 2.4GHz 재방송**(호환성 최대화 켜져있어도 재시작 필요).
5. **flash ↔ 시리얼 모니터 포트 배타**: 포트는 1개만 점유. flash 전 모니터 `Ctrl+C`로 끄기(안 끄면 "port busy" 에러).

## 3. 변수격리 절차 (결정론적 디버깅)

flash 전 curl로 서버 계층 사전검증 → 보드 실패 시 원인이 하드웨어(안테나/WiFi)로 좁혀짐:

- **인증 검증**: `curl -s -o /dev/null -w "%{http_code}\n" -X POST http://<IP>:5000/api/v1/detect` → `401`(토큰 없음, 정상)
- **토큰 통과**: 위 + `-H "Authorization: Bearer <토큰>"` → `400`(오디오 없음, 정상)
- **전체 경로**: 64KB 더미 + multipart → `201`(성공).
  ```
  head -c 65536 /dev/urandom > /tmp/f.pcm
  curl ... -F "audio=@/tmp/f.pcm" -F "client_request_id=t1" -F "device_id=t"
  ```

→ curl `201`이면 서버 OK 확정. 이후 보드 실패 = 안테나/WiFi.

## 4. flash + 측정 실행

1. `secrets.h` 4값 확인(`WIFI_PRIMARY_SSID` / `WIFI_PRIMARY_PASSWORD` / `SPIKE_SERVER_HOST`=현재 IP / `SPIKE_DEVICE_TOKEN`)
2. `cd firmware && ~/.platformio/penv/bin/pio run -e upload_spike` (재컴파일, secrets 반영 확인 = Flash 크기 변화)
3. `~/.platformio/penv/bin/pio run -e upload_spike -t upload` (flash, `Hash verified` + `Hard resetting` 확인)
4. `~/.platformio/penv/bin/pio device monitor -e upload_spike` → 로그 안 흐르면 보드 RESET 버튼
5. 성공 로그: `[WIFI] Connected via PRIMARY (RSSI=-XX)` → `[SPIKE] iter=N status=201 OK` → `[STATS] p50/p95`
6. 로그를 **repo 밖** `ddingdong-측정결과/` 폴더에 저장(휘발 방지)

## 5. 2026-07-28 실측 결과 (기준값)

- **p50 305 / p95 1043ms**(64KB×14, `201` 14/14), TCP connect가 지연 절반(connect 270 / post 279 / total 549)
- 스윕 32/64/128KB avg 95.7 / 318.3 / 358.0ms (크기 2배여도 미미 = 무선 오버헤드 지배)
- **판정**: 5초 예산 대비 p95 ~20%, **업로드 병목 아님.** keep-alive 재사용 = 14주차 튜닝 타겟.
- 상세 = `docs/decisions.md` 6.2 (`9d56852`)
