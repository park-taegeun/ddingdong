# 🔴 Decisions Log (변경 이력)

> `decisions.md`의 변경 이력 추적용. 결정이 바뀔 때마다 한 행씩 추가.

| 날짜 | 항목 | 변경 전 | 변경 후 | 근거 |
|------|------|---------|---------|------|
| 2025-04 | 초인종 유사도 검증 | 코사인 단독 | SP/DTW + cosine distance | PMC3745477 |
| 2025-04 | 템플릿 저장 형식 | 1D flatten | 2D 그대로 (T, 128) | FastDTW 입력 형식 |
| 2025-04-28 | YAMNet 입력 | 멜스펙트로그램 | raw waveform 16kHz mono | YAMNet 사양 |
| 2026-04-29 | 1순위 피드백 해결 | (없음) | A-1+A-3 통합 (사진+STT 자막) | 중간 발표 피드백 |
| 2026-05-06 | EC2 사양 | t2.micro | t3.small (2GB RAM) | OOM 위험 |
| 2026-05-06 | ToF 차단 위치 | ESP32 | 서버 클래스별 분기 | 화재경보 누락 방지 |
| 2026-05-06 | 음향 트리거 | (미정) | 단순 RMS 임계값 (옵션 A) | 학부생 작업 단순화 |
| 2026-05-07 | Git commit 언어 | (미정) | 한국어 + 이모지 컨벤션 | 발표 자료/회고 가독성 |
| 2026-05-07 | firmware 폴더 구조 | firmware/poc/ | firmware/ 평탄화 + env 분기 | 본 개발 전환 비용 절감 |

---

## 2026-05-07 (종료 시점 통합 갱신)

### 결정 변경
1. **사전 준비 일정**: 5/7~5/10 (4일) → 5/7~5/17 (11일, 옵션 A)로 확장
   - 사유: 사전 검증 ①②를 5/7 오전에 우선 배치 (코드 작성 전제조건)
   - WiFi를 Day 2 우선 처리로 변경 (가장 위험한 작업 회복 시간 확보)

### 결정 신규
1. **사전 검증 ①② 결과** → 카테고리 12 추가
   - ① VL53L5CX SparkFun lib + ESP32-S3 = 조건부 GO
   - ② Lokch777 OV3660 멀티코어 = OV2640 포팅 추정 GO
2. **5/9 카메라 / 5/11 ToF / 5/21 코어 분배** 사전 반영 사항 → 카테고리 13, 14, 15 추가
3. **monorepo + PlatformIO 셋업** 완료 → 카테고리 16 추가
   - 컴파일 SUCCESS (14.25초, RAM 5.6% / Flash 7.6%)
   - Commit `6f1cecf` + `dd55759`
4. **11주차 issue #620 + 5/12 self-checkpoint** → 카테고리 17 추가
5. **채팅방 운영 구조** → 카테고리 18 추가
   - SSoT 우선순위, 작업 체인, Claude Code MCP 활용 원칙, 분리 트리거, 인계 패키지
6. **노션 PoC 트래킹 도입** → 카테고리 19 추가
   - VIEW 전용, 의사결정은 절대 노션에서 X
7. **Git 워크플로우** (5/18 도입 예정) → 카테고리 20 추가
   - GitHub Flow 단순화, `feat/{domain}-{task}` 브랜치, Squash merge
8. **매일 밤 작업 종료 루틴** → 카테고리 21 추가

### 폐기
- PoC-(1) 인계 패키지의 5/7~5/10 4일 일정안 폐기

---

## 2026-05-07 (보강)

### 결정 신규 (카테고리 18, 19, 21 보강)
1. **컨텍스트 무게 자체 모니터링** → 카테고리 18 sub-section 추가
   - 클로드 능동 분리 제안 + 무거움 신호 6가지 + 알림 형식
2. **노션 셋업 완료 결과 + ID 4개** → 카테고리 19 보강
3. **노션 PoC 트래킹과 Velog 분리 운영** → 카테고리 19 sub-section 추가
4. **자체 검증 3단계 강제 (코드 작성 위임)** → 카테고리 21 sub-section 추가
5. **노션 매일 갱신 5단계 표준 워크플로우** → 카테고리 21 sub-section 추가

### 사유
- commit c8784c9 이후 본 채팅방에서 결정된 운영 룰 5건이 메모리에만 등록되어 있어
  다른 채팅방 / Claude Code MCP / 후속 채팅방에 전파 X
- 5/8 작업 시 채팅방 X / Claude Code MCP가 git pull로 인지할 수 있도록 SSoT 동기화

---

## 2026-05-08

### 신규 카테고리
- **카테고리 23**: 시연 네트워크 환경 = 모바일 핫스팟
  - 학교 WiFi 802.1X 폐기, WPA2-Personal 통합 환경 채택
  - 영향: WiFi 본 작업 (commit 3ec17d4) 약 40% 시간 단축

- **카테고리 24**: IDE 환경 (.clangd 시도 + 한계 + 우회)
  - 시도 3건 (commits 70c0664 / d801e01 / db38da0)
  - 결과: Unknown argument 4종 해결, cascading 11건 잔존
  - 결론: IDE 인식 한계, 펌웨어 동작 영향 0 → 무시 결정

### 펜딩 (17시 이후 별도 처리)
- 카테고리 22 동적 갱신: 디바이스마트 자동 취소 + 환불 23,870원 처리 추적

---

## 2026-05-08 (동적 갱신 — 자성리얼 부품 배송 일정 변경)

### 카테고리 22 — 자성리얼 부품 배송 일정 변경
- **변경 전**: 도착 예정 5/9~5/11
- **변경 후**: 도착 예정 5/15~5/28 (영업일 5~14일)
- **사유**: 자성리얼 판매자 SMS 통보 — 국내 일시 품절로 미국 본사 해외 직발송 전환
- **영향**: 사전 준비 11일 큰 틀 변동 X (5/15가 11일 안에 포함). 5/9~5/14는 외부 계정 셋업 + 호환성 검증으로 자연 활용
- **통관정보 회신**: 5/8 완료 (개인통관고유번호 P210018836994 + 박태근 + 휴대폰)
- **부품 모델/금액 변동 X** (XIAO ESP32-S3 Sense Pre-Soldered, 36,540원 그대로)
- **반영 위치**:
  - decisions.md 카테고리 22.2 (배송 형태 / 일정 / 마지막 갱신 / 갱신 사유)
  - decisions.md 카테고리 22.5 (즉시 액션 항목)
  - decisions.md 카테고리 22.6 신설 (사전 준비 11일 영향 평가)
- **최악 시나리오 (5/28 도착)**: PoC 1주차 진입 후 부품 도착 → Plan B 다단계 트리거 검토 필요 (별도 미결정 사항으로 DB3 추적)

---

## 2026-05-08 (동적 갱신 — 5/12 self-checkpoint 분리)

### 카테고리 17 — 5/12 self-checkpoint 분리 (메모리 / 타이밍)
- **변경 전**: 5/12 self-checkpoint (단일, 입력 데이터 3종 모두 실측 필요 — 카테고리 15)
- **변경 후**: self-checkpoint 두 종류로 분리 (카테고리 17.1 신설)
  - **메모리 self-checkpoint** (5/12 진행, 부품 X): 더미 테스트 컴파일 결과 RAM/Flash 사용량 합산 → PSRAM 8MB 한계 / fragmentation 위험 평가
  - **타이밍 self-checkpoint** (부품 도착 + 실측 후, 잠정 5/18+): 실측 데이터 3종 (mic priority / cameraTask vs writerTask / ToF 15Hz) → 코어 분배 잠정안 유효성
- **사유**:
  - 자성리얼 부품 배송 일정 변경(5/15~5/28, commit `847c599`)으로 5/9~5/11 실측 데이터 수집 불가
  - 단, 5/8 WiFi 테스트와 동일한 "더미 테스트" 패턴(컴파일 + 메모리 사용량)은 부품 없이 진행 가능
  - self-checkpoint 입력 데이터 = 메모리(부품 X 가능) + 타이밍(부품 필요)으로 분리 가능 발견
- **5/21 통합 코어 분배 최종 확정 시점**: 두 self-checkpoint 모두 완료 후, PoC 1주차 진행 상황 보면서 재평가 (시점 자체 변경 X)
- **학부생 의사결정**: 옵션 A 선택 (PoC-(5), 2026-05-08)
- **연관 카스케이드**: 카테고리 22 동적 갱신(commit `847c599`)으로부터 파생, 카테고리 17.1 신설로 발전
- **반영 위치**:
  - decisions.md 카테고리 17 (5/12 self-checkpoint 메모 + 17.1 신설)
  - 노션 DB3 5/12 self-checkpoint row (메모리 정의 갱신)
  - 노션 DB3 신규 row (타이밍 self-checkpoint, 잠정 5/18)
  - 노션 페이지 메타 콜아웃 + 일정 vs 실제 표

---

## 2026-05-09 (동적 갱신 — 디바이스마트 환불 처리 완료)

### 카테고리 22.5 — 디바이스마트 자동 취소 + 환불 처리 완료
- **변경 전**: 🔴 디바이스마트 자동 취소 처리 확인 (5/8 17시 이후, 환불 23,870원)
- **변경 후**: 🟢 디바이스마트 자동 취소 + 환불 23,870원 정상 처리 완료 (2026-05-09 확인)
- **사유**: 5/8(금) 17시 자동 취소 + 5/9 환불 23,870원 입금 확인 (XIAO ESP32-S3 Sense Pre-Soldered 102010635 품절)
- **영향**: 사전 준비 11일 후반부 리스크 1건 해소 (자성리얼 5/15~5/28 트래킹만 남음)
- **반영 위치**:
  - decisions.md 카테고리 22.5 (첫 줄 🔴 → 🟢)
  - 노션 DB3 "디바이스마트 자동 취소 + 환불 처리 추적" row (상태 🔴 → 🟢)
- **관련 commit**: `92c023d`

---

## 2026-05-09 - 카테고리 16 신설 (16.1 더미 테스트 누적 측정 표)

**변경 카테고리**: 16 (16.1 신설)
**변경 내용**: 5/8~5/9 더미 테스트 누적 RAM/Flash 측정 표 추가, env 분리 구조 명시
**영향**: 5/12 메모리 self-checkpoint 입력 데이터 명확화, 정적 budget 검증 범위 확정
**관련 commit**:
- `aa6116d` 🔧 Settings: platformio.ini에 camera_v1/camera_v2 env 추가
- `8ce56ed` ✨ Feat: 카메라 더미 테스트 코드 추가 (Version A/B 두 가지)
- `282a973` 📝 Docs: 카테고리 16, 17.1.1, 17 갱신 (5/9 카메라 측정 + 11주차 동적 heap 추적)

---

## 2026-05-09 - 카테고리 25 신설 (Khangura 6개 함정 코드 반영 표)

**변경 카테고리**: 25 (신설)
**변경 내용**: Manjot Khangura Medium 글 6개 함정 전체 코드 반영 여부 분석 + 분류 (#1~#6)
**영향**:
- 5/9 카메라 더미 테스트 코드 (commit `8ce56ed`) 검증 완결
- 부품 도착 후 (5/15~5/28) 처리 항목 2건 명확화 (#2 DMA / #6 gain tuning)
- 학습 13 (전제 검증 누락 패턴) 정착 트리거
**검토 결과**: ✅ 2개 / 🟡 2개 (B 분류) / ❌ 2개 (C 분류). 코드 보강 0건 (HEAD `8ce56ed` 유지)
**관련 commit**: `2a7c1d8` 📝 Docs: 카테고리 25 신설 (Khangura 6개 함정 코드 반영 표)

---

## 2026-05-09 - 카테고리 17 갱신 (11주차 동적 heap 추적 항목 추가)

**변경 카테고리**: 17
**변경 내용**: 11주차 진입 전 esp32-camera issue #620 재현 시도에 동적 heap 추적 (`ESP.getMinFreeHeap()` + stack high-water mark) 항목 동시 진행 명시
**영향**: 5/12 메모리 self-checkpoint = 정적 budget 한정, 동적 heap = 11주차 통합 테스트로 분리. SSoT 일관성 확보
**근거**: 5/9 카메라 더미 테스트 결과 §4 메모리 budget 평가에서 SRAM 동적 heap 추적 필요 alert 발생
**관련 commit**: `282a973` 📝 Docs: 카테고리 16, 17.1.1, 17 갱신 (5/9 카메라 측정 + 11주차 동적 heap 추적)

---

## 2026-05-09 - 카테고리 12 보충 기록 (firecrawl 검색 결과 0건)

**변경 카테고리**: 12 (변경 X, 기록만)
**변경 내용**: 5/9 카메라 작업 시 firecrawl-mcp로 "OnlyFeet" / "Lokch777" 키워드 검색 결과 0건. 카테고리 12 사전 검증 ② "OnlyFeet 80% 매칭 + 4건"의 출처는 별도 GitHub 검색 결과로 추정 (별도 채팅방 진행)
**영향**: 부품 도착 후 fb_get 비교 시점에 사례 재검증 검토 항목 추가
**관련 commit**: `1cd6f14` 📝 Docs: decisions-log.md 2026-05-09 entries 추가 (5건)

---

## 2026-05-09 - Claude Code MCP 환경 이슈 처리 패턴 정립 (참조용)

**변경 카테고리**: (decisions.md 변경 X, 본 log만)
**변경 내용**: Claude Code MCP 자동 업데이트 실패 (`Auto-update failed`) → npm prefix 충돌 (`~/.npm-global` vs Homebrew Node) → 잔여 폴더 청소 → 재설치 단순 패턴
**처리 절차**: `rm -rf ~/.npm-global/lib/node_modules/@anthropic-ai/claude-code` + `rm -rf ~/.npm-global/lib/node_modules/@anthropic-ai/.claude-code-*` → `npm i -g @anthropic-ai/claude-code` → `claude --version` 검증
**결과**: 2.1.119 → 2.1.137 정상 업데이트
**영향**: 향후 동일 패턴 발생 시 sudo 백업 옵션 호출 X. 학습 12 정착
**관련 commit**: `1cd6f14` 📝 Docs: decisions-log.md 2026-05-09 entries 추가 (5건)

---

## 2026-05-09 - 카테고리 7 갱신 (화재경보 알림 형식 = 정부 대응 수칙 동시 발송)

**변경 카테고리**: 7
**변경 내용**: 화재경보 알림 형식 명시 추가 (강조 표현 + 정부 지정 대응 수칙 동시 발송, 1차 알림만, ToF 우회)
**영향**: 카테고리 26.3 진입점 3 (화재경보 시연) 정책 SSoT 정착, 13~14주차 카카오톡 작업 시 메시지 템플릿 결정 기준
**근거**: 5/13 졸작 중간 발표 스크립트 슬라이드 7 명시 + 카테고리 26 신설 카스케이드
**관련 commit**: `ae9e441` 📝 Docs: 카테고리 7 갱신 (화재경보 알림 형식 = 정부 대응 수칙 동시 발송)

---

## 2026-05-09 - 카테고리 26 신설 (시연 시나리오 틀)

**변경 카테고리**: 26 (신설)
**변경 내용**: 5/13 졸작 중간 발표 스크립트 기준 시연 시나리오 확정 틀 정착 (USP 2개 / 부스 환경 / 진입점 3개 / 시연 메시지 3가지 / 백업 영상 / 디벨롭 추적 / Demo-Verify 검증 채널)
**영향**:
- 18주차 통합 테스트 + 19~22주차 시연 시점 SSoT 기준점 확보
- Demo-Verify-(N) 채팅방 신설 시 검증 기준 정착
- 노션 "데모 시나리오" 페이지 (위임 2 작업) 연동 SSoT
- 4/29 중간 발표 1순위 + 2순위 피드백 반영 결과물
**근거**: 5/13 졸작 중간 발표 스크립트 (`docs/presentation/2026-05-13-script.md`) + 학부생 5/9 결정 (옵션 B 채택)
**관련 commit**: `1fc695f` 📝 Docs: 카테고리 26 신설 (시연 시나리오 틀)

---

## 2026-05-09 - docs/presentation/ 폴더 신설 (발표 자료 보존)

**변경 카테고리**: (decisions.md 변경 X, 별도 폴더 신설)
**변경 내용**: `docs/presentation/` 폴더 신설 + `2026-05-13-script.md` 추가 (5/13 졸작 중간 발표 스크립트 8개 슬라이드 분량)
**영향**:
- 향후 9/30 졸작 발표 시점 발표 자료 누적 폴더 정착
- 발표 자료와 decisions.md 도메인 분리 (역할별 폴더 분리)
- 카테고리 26.7 발표 스크립트 출처 외부 링크 연동
**근거**: 5/13 발표 스크립트 보존 + 9/30 졸작 발표 자료 누적 도메인 정착
**관련 commit**: `d593f8a` ✨ Feat: docs/presentation/ 폴더 신설 + 5/13 발표 스크립트 추가

---

## 2026-05-10 - 카테고리 16.1 갱신 (5/10 mic_dummy RAM/Flash 추가)

**변경 카테고리**: 16.1
**변경 내용**: 5/10 mic_dummy 행 추가 (RAM 8.1% / Flash 8.1%, env 분리). env 분리 구조 목록에 `env:mic_dummy` 추가. 부연 항목 3건 추가 (legacy `driver/i2s.h` 채택 / 정적 메모리 8 KiB BSS / 250ms 노이즈 처리)
**영향**:
- 5/12 메모리 self-checkpoint 입력 데이터 갱신 (WiFi + camera v1/v2 + mic_dummy = 4건 누적)
- 5/11 ToF 더미 테스트 진행 시 동일 표 행 추가 패턴 정착
**근거**: `pio run -e mic_dummy` SUCCESS 2.43초, RAM 26644/327680 (8.1%) / Flash 271549/3342336 (8.1%)
**관련 commit**: `ab1b89b` 📝 Docs: decisions.md 갱신 (16.1 + 27/28/29 신설)

---

## 2026-05-10 - 카테고리 27 신설 (위임 프롬프트 repo 구조 가정 검증 강제, 학습 14)

**변경 카테고리**: 27 (신설)
**변경 내용**: 위임 프롬프트 작성 시 인계 패키지의 추상 표현 신뢰 X, 실제 파일 경로 + build 설정 패턴 catch 검증 강제 패턴 명문화. firmware/ 컨벤션 (디렉토리 구조 + 환경 격리 패턴) 명문화.
**5/10 catch 사례**: PoC-(7) 위임 프롬프트가 `firmware/dummy_tests/camera_dummy/` 가정 → 실제 5/9 카메라는 `firmware/src/` 직접 + `build_src_filter` 격리 패턴 → Claude Code MCP가 첫 단계 `git status` / `ls` 실행 시 catch → 학부생 결정 후 옵션 1 (실제 카메라 패턴 일치) 채택
**영향**:
- 향후 모든 위임 프롬프트 작성 시 "현재 상태 확인 (`git status` + `ls [관련 폴더]`)" 첫 단계 강제
- 자체 검증 ② 리팩토링 "기존 컨벤션 일치" 항목이 자동 catch 그물 역할
**근거**: 5/10 PoC-(7) 위임 프롬프트 결과 보고서 Step 1 (현재 상태 확인 → 디렉토리 구조 불일치 catch)
**관련 commit**: `ab1b89b` 📝 Docs: decisions.md 갱신 (16.1 + 27/28/29 신설)

---

## 2026-05-10 - 카테고리 28 신설 (packaging 제약 vs 공식 권장 분리 검증, 학습 15)

**변경 카테고리**: 28 (신설)
**변경 내용**: 학습 13 (전제 검증) 보강 형태. 외부 출처 인용만으로는 부족, 실제 환경(SDK / 패키지) 노출 여부까지 검증 강제. 4단계 검증 절차 (공식 권장 → 헤더 노출 → 컴파일 통과 → 런타임 동작) 명문화.
**5/10 catch 사례**:
- ESP-IDF 5.x 공식 권장: `driver/i2s_std.h` (new API)
- arduino-esp32 v3.20017 SDK packaging: 새 API 헤더 미노출 (`fatal error: driver/i2s_std.h: No such file or directory`)
- 직접 검증: `find ~/.platformio/packages/.../include/driver/` → `i2s.h`만 존재
- 채택: legacy `driver/i2s.h` fallback (deprecation warning 0건 컴파일 출력 직접 확인)
**영향**:
- 향후 모든 라이브러리/API 채택 결정 시 4단계 검증 절차 강제
- 마이그레이션 트리거 명시: arduino-esp32 새 API 헤더 노출 시 또는 ESP-IDF 직접 사용 전환 시
**근거**: 5/10 PoC-(7) 위임 프롬프트 결과 보고서 § 학습 13 catch 검증 결과 B 항목 #5
**관련 commit**: `ab1b89b` 📝 Docs: decisions.md 갱신 (16.1 + 27/28/29 신설)

---

## 2026-05-10 - 카테고리 29 신설 (위임 프롬프트와 실제 컨벤션 충돌 시 기존 컨벤션 우선, 학습 16)

**변경 카테고리**: 29 (신설)
**변경 내용**: 위임 프롬프트의 구체 코드 패턴 vs 기존 repo 컨벤션 충돌 시 → 기존 컨벤션 우선 원칙 명문화. 위임 프롬프트는 일반론, 기존 컨벤션은 실제 검증된 패턴, 일관성 우선.
**5/10 catch 사례**:
- 위임 프롬프트 (PoC-(7)): `while (!Serial && millis() < 2000) { delay(10); }` (Serial race 방지 패턴 A)
- 실제 카메라 v1/v2 컨벤션: `delay(SERIAL_BOOT_DELAY_MS=200)` (패턴 B)
- Claude Code MCP 채택: 패턴 B (camera v1/v2 컨벤션 일치 원칙 우선 적용)
**영향**:
- 향후 위임 프롬프트 작성 시 "기존 [관련 모듈] 컨벤션 우선" 명시 우선순위 부여
- 자체 검증 ② 리팩토링 "camera v1/v2 컨벤션 일치" 항목이 자동 catch 그물 역할
**근거**: 5/10 PoC-(7) 위임 프롬프트 결과 보고서 § 자체 검증 ③ 오류 방지 검토 "Serial 미초기화 race" 항목
**관련 commit**: `ab1b89b` 📝 Docs: decisions.md 갱신 (16.1 + 27/28/29 신설)

---

## 2026-05-10 - 5/10 마이크 더미 테스트 작업 결과 종합 (eb1b451 + ff3f46b)

**변경 카테고리**: (decisions.md 변경 X, 본 log만 — 작업 결과 종합 entry)
**HEAD**: `e71c01f` → `eb1b451`
**컴파일**: SUCCESS 2.43초 / RAM 8.1% (26644/327680 bytes) / Flash 8.1% (271549/3342336 bytes)
**라이브러리**: legacy `driver/i2s.h` (학습 15 trigger, 카테고리 28 신설 근거)
**학습 13 catch**:
- INMP441 datasheet: 6/6 항목 (VDD 1.62~3.63V / SNR 61dBA / 24-bit Philips I²S / 2^18 SCK startup ≈ 256ms / L/R=GND→좌채널 / SCK 0.5~3.2MHz·WS 7.8~50kHz)
- ESP-IDF I2S: 5/5 항목 (I2S0/I2S1 분리 / new vs legacy API / DMA 설정 / ESP32-S3 controller 2개 / arduino-esp32 packaging 제약)
- 라이브러리 비교: 3/3 선택지 (arduino-esp32 `<I2S.h>` X / legacy `driver/i2s.h` ✅ / new `driver/i2s_std.h` X)
- 합계: 13/13 ✅
**자체 검증 3단계**:
- ① 효율성 6개 항목 모두 통과 (DMA 8×1024 적정성 / Core 0 task priority / heap fragmentation X / blocking 무관 / 매직 넘버 const화 / 250ms+14 buffer 폐기 효율)
- ② 리팩토링 6개 항목 모두 통과 (camera v1/v2 컨벤션 일치 / 매직 넘버 const화 / warmup 함수 분리 / 변수명 명료성 / DRY 무관 = 환경 격리로 분리 X / Serial prefix 일관)
- ③ 오류 방지 11개 항목 모두 통과 (init 실패 graceful / 부품 부재 graceful / Serial race 처리 / deprecation warning 0건 / i2s_read 반환값 체크 / sign extension placeholder / Core 0 핀고정 / static BSS 채택 / L/R GND 좌채널 / 250ms 일치 / SCK·WS 권장값 준수)
**부품 도착 후 (5/15~5/28) 추가 작업 placeholder**: 32-bit MSB-align → 24-bit 추출 (arithmetic shift) → 16-bit downcast (YAMNet 입력) → RMS 임계값 트리거 (wakeWord 검증)
**근거**: 5/10 PoC-(7) 위임 프롬프트 결과 보고서 (Set 1 작업 결과 종합)
**관련 commit**: `ff3f46b` 🔧 Settings: platformio.ini에 mic_dummy env 추가 + `eb1b451` ✨ Feat: 마이크 더미 테스트 코드 추가 (INMP441 + I2S1)

---

## 2026-05-11 - 5/11 ToF 더미 테스트 작업 결과 종합 (b2434af + dd8ed66)

**변경 카테고리**: (decisions.md 카테고리 16.1 누적 표 + 부연만 갱신, 카테고리 1~15 / 17~29 변경 X)
**HEAD**: `ee1f691` → `dd8ed66`
**컴파일**: SUCCESS 10.44초 / RAM 6.1% (20124/327680 bytes) / Flash 11.1% (371209/3342336 bytes)
**라이브러리**: SparkFun_VL53L5CX_Arduino_Library 1.0.3 (1차 채택, 코드에서 사용) + Adafruit_VL53L5 master (폴백, lib_deps만 등록 / dead code elimination으로 link 단계에서 SparkFun만 binary 포함)
**핀 매핑**: SDA=GPIO5(D4) / SCL=GPIO6(D5) (decisions.md 카테고리 2 핀 표 그대로)
**I2C clock**: 1MHz (사전 검증 ① 워크어라운드 — VL53L5CX datasheet max 1Mbits/s + SparkFun Example3_SetFrequency 검증 패턴 / OnlyFeet 400kHz와 차이는 의도적)
**8x8 / 15Hz**: datasheet 8x8 mode max (4x4는 60Hz) / SparkFun Example3 검증 / OnlyFeet 매칭 80%
**FreeRTOS**: tofTask Core 0 priority 3 (micTask Core 0 priority 4와 분리, decisions.md 카테고리 14 5/21 PoC 분배 잠정안 적용)
**graceful**: `initToF()` 실패 시 task spawn 생략 + `loop()` idle 진단 (mic_test 패턴 100% 일치) / 2회 retry + I2C bus scan 진단 (OnlyFeet 패턴 채택)
**static buffer**: `VL53L5CX_ResultsData measurementData` ~1356B BSS (task 스택 6 KiB 폭주 방지, mic_test `audio_buffer` 8 KiB BSS 패턴 일치)
**학습 13 catch**: 33개 (datasheet 6 + SparkFun 10 + Adafruit 8 + OnlyFeet 5 + arduino-esp32 Wire 4), 누락 0
**학습 14 mic 컨벤션 일치**: 10개 항목 100% (헤더 분리 / Serial race 200ms / graceful return / 매직 넘버 constexpr / setup 구조 / xTaskCreatePinnedToCore / 함수 분리 / 로그 prefix `[tof]`·`[BOOT]`·`[MEM:tag]` / include 순서 / platformio.ini env 패턴)
**학습 15 4단계**: 1 공식 권장 ✅ + 2 패키지 헤더 ✅ + 3 컴파일 통과 ✅ (SparkFun + Adafruit 양쪽 archived) + 4 런타임 동작 보류 (자성리얼 5/15~5/28 부품 도착 후)
**자체 검증 3단계** (학습 16 catch 그물):
- ① 효율성 8개 모두 통과/무관 (1MHz / 8x8·15Hz / DMA 무관 / lib RAM 검증 / PSRAM static / Core 0 점유율 67ms idle / O(64) 순회 placeholder)
- ② 리팩토링 7개 모두 통과 (변수명 / 기존 컨벤션 일치 / DRY 의도적 분리 / 매직 넘버 const화 / 네이밍 일관성 / 함수 분리 / 로그 prefix)
- ③ 오류 방지 12개 모두 통과 (graceful / I2C NACK retry / FW upload 실패 catch / null pointer X / heap 할당 X / Wire 단독 / core 3.x 호환 / -Wall 경고 0건 / power-on / Serial race)
**부품 도착 후 (5/15~5/28) 추가 작업 placeholder**: 64 zone 순회 (`measurementData.distance_mm[i]`) → `target_status==5||9` valid 필터 → center 4 zones (27,28,35,36) 평균 침입자 거리 메트릭 (OnlyFeet 패턴) → Motion Indicator (Adafruit lib API, 5주차 사람 검증 단계)
**근거**: 5/11 PoC-(7) 위임 프롬프트 결과 보고서 (ToF 더미 테스트 종합)
**관련 commit**: `b2434af` 🔧 Settings: platformio.ini에 tof_dummy env 추가 + `dd8ed66` ✨ Feat: ToF 더미 테스트 코드 추가 (VL53L5CX + I2C)

---

## 2026-05-11 - Adafruit_VL53L5 lib_deps master 추적 채택 결정 (PoC 단계, 8주차 prod 진입 시 commit pin 재검토)

**변경 카테고리**: (decisions.md 변경 X, 본 log만 — 학부생 alert 처리 entry / 8주차 진입 시 카테고리 28 row 신설 검토 트리거)
**결정**: 현 PoC 단계는 `https://github.com/adafruit/Adafruit_VL53L5.git` master 브랜치 추적 (commit pin 미적용)
**근거**:
1. Adafruit 공식 라이브러리는 안정적 (breaking change push 빈도 낮음)
2. PoC 기간 짧음 (~3주, 5/8~5/28)
3. SparkFun 1차 채택이라 Adafruit은 폴백 전용 (실제 사용 코드 없음, link 단계 dead code elimination으로 binary 미포함)
**트레이드오프**:
- master 추적 (현 채택): 최신 패치 자동 / 단 Adafruit이 breaking change push 시 빌드 깨짐
- commit pin (8주차 검토): 안정 보장 / 단 보안·버그 패치 누락 시 수동 갱신 필요
**재검토 시점**: 8주차 prod 진입 시 (`env:prod` 추가 시점, decisions.md 카테고리 5 참조). 채택 시 카테고리 28 (packaging 제약 vs 공식 권장 분리) row 신설 검토.
**노션 DB3**: 신규 row 1건 신설 (트리거 일자 = 8주차 진입 / 알림 태그 "Adafruit master vs commit pin")
**근거**: 5/11 PoC-(7) 위임 프롬프트 § 학부생 alert (DB3 row 신설용)
**관련 commit**: `dd8ed66` ✨ Feat: ToF 더미 테스트 코드 추가 (VL53L5CX + I2C) — `firmware/include/tof_common.h` 출처 인용 라인에 master 추적 명시 + `firmware/platformio.ini` `[env:tof_dummy]` 주석에 학부생 alert 명문화

---

## 2026-05-11 - 학습 14 catch 그물 작동 사례 (5/10 mic 컨벤션 → 5/11 tof 100% 일치 검증)

**변경 카테고리**: (decisions.md 변경 X, 본 log만 — 카테고리 27/29 명문화 효과 확인 entry)
**사례**: 5/10 mic_dummy에서 catch한 컨벤션 10개 항목이 5/11 tof_dummy 작성 시 자체 검증 ② 리팩토링 "기존 컨벤션 일치" 항목에서 자동 catch 그물로 작동 → 100% 일치 강제
**컨벤션 10개 항목**:
1. 헤더 분리 (`*_common.h` const+API / `*_common.cpp` init+helper / `*_test.cpp` setup+loop+static task)
2. Serial race 방지 (`Serial.begin(115200); delay(*_SERIAL_BOOT_DELAY_MS=200);` 후 `\n[BOOT] ...`)
3. graceful 패턴 (`if (!init*()) { Serial.println("..."); return; }` + `loop()` 5초 idle 진단)
4. 매직 넘버 (모두 prefix + `constexpr`)
5. setup() 구조 (Serial→delay→[BOOT]→init→(warmup)→xTaskCreate→[BOOT] started)
6. xTaskCreatePinnedToCore (`(fn, "name", STACK, nullptr, PRIORITY, nullptr, CORE)`)
7. 함수 분리 (common: init/helper / test: static task + setup + loop)
8. 로그 prefix (`[tof]`·`[mic]` 런타임 / `[BOOT]` 부팅 / `[MEM:tag]` 메모리)
9. include 순서 (h: `<Arduino.h>` → 라이브러리 헤더 / cpp: `"*_common.h"`)
10. platformio.ini env 패턴 (`extends` 미사용, 모든 필드 직접 명시 / `lib_deps` env에 명시 / `build_src_filter = -<*> +<...>`)
**라인 번호 직접 인용 (자체 검증 ② 리팩토링)**: `firmware/src/mic_test.cpp:42-57` (setup 패턴) vs `firmware/src/tof_test.cpp:45-60` (동일 구조)
**효과**:
- 카테고리 27 (위임 프롬프트는 추상 표현 신뢰 X, 실제 파일 경로/build 설정 catch 강제) 명문화 효과 확인
- 카테고리 29 (위임 프롬프트와 실제 컨벤션 충돌 시 기존 컨벤션 우선) 명문화 효과 확인
- 위임 프롬프트 → 실제 코드 컨벤션 일치까지 자동 catch
**근거**: 5/11 PoC-(7) 위임 프롬프트 결과 보고서 § 자체 검증 ② 리팩토링 "기존 컨벤션 일치" 항목 (mic_test.cpp / tof_test.cpp 라인 번호 직접 인용)
**관련 commit**: `dd8ed66` ✨ Feat: ToF 더미 테스트 코드 추가 (VL53L5CX + I2C)
