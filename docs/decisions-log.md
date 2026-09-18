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
| 2026-05-28 | API 엔드포인트 버저닝 | `/api/detect`, `/api/enrich` | `/api/v1/*` (detect/enrich/notifications/stats) | v1/v2 병행 + 대시보드 폴링 엔드포인트 확장 |

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

---

## 2026-05-12 - 메모리 self-checkpoint 결과 (카테고리 17.1.1 통합 budget 추정)

**변경 카테고리**: 17.1.1 (본문 갱신, 17.1.1.1~17.1.1.4 sub-section 신설)
**HEAD**: `6c9c0fc` (시작) → 본 commit
**배경**: 사전 준비 11일 단독 페리페럴 테스트 5건 (5/8 WiFi / 5/9 camera_v1·v2 / 5/10 mic / 5/11 tof) 완료. 4종 페리페럴 동시 활성 시 통합 budget 정적 추정 필요. 5/8 PoC-(5) 사전 추정(SRAM 22% / Flash 42% / PSRAM 50KB)을 5/10·5/11 실측 데이터로 정정.
**결정**:
- **방법 1 (delta sum, 채택)**: 정적 SRAM **18.2%** (~59.6 KB) / 정적 Flash **31.6%** (~1.06 MB) / PSRAM ~50 KB (0.6%)
- **방법 2 (단순 합산, 참고)**: SRAM 35.0% / Flash 54.4% (베이스라인 4× 중복 over-count)
- **페리페럴별 정적 contribution (delta 분해)**:
  - WiFi/HTTPS: +8.2pp RAM / +18.2pp Flash (esp_wifi + lwIP + mbedtls + HTTPClient + ArduinoJson)
  - 카메라: +1.4pp RAM / +1.8pp Flash (esp_camera driver, frame buffer는 PSRAM)
  - 마이크: +2.5pp RAM (8 KiB BSS audio_buffer + scratch) / +0.5pp Flash (legacy driver/i2s.h)
  - ToF: +0.5pp RAM (1.6KB measurementData) / +3.5pp Flash (FW upload buffer ~84 KB + driver)
- **Plan B 트리거 정량화 (학습 16 적용)**:
  - Stage 1 (알람): 정적 SRAM ≥ 25% OR Flash ≥ 40% — 동적 측정 권장
  - Stage 2 (최적화): 정적 SRAM ≥ 35% OR Flash ≥ 60% — DMA buffer 축소 / VL53L5CX FW PSRAM 이전 / WiFi sdkconfig minimal
  - Stage 3 (Plan B): 정적 SRAM ≥ 50% OR Flash ≥ 75% — 카메라 해상도/ToF 모드 축소 / WiFi → ESP-NOW
  - **현 상태 모든 Stage 미발동** (정적 18.2%/31.6%, Stage 1 25%/40% 안전 여유)
**5/8 사전 추정과의 차이 (정정 분석)**:
- SRAM **-3.8pp** (22% → 18.2%): mic +5% 가정 → 실측 +2.5pp / tof +3% 가정 → 실측 +0.5pp
- Flash **-10.4pp** (42% → 31.6%): tof FW image +6%(~200KB) 가정 → 실측 +3.5pp(~117KB)
- PSRAM 0 변동 (50KB 카메라 frame buffer만)
- → 실측 모두 사전 추정 안에 안전 수렴
**근거**:
- ESP32-S3 datasheet (5개 항목): 512KB SRAM / 320KB user-available / 8MB PSRAM / 8MB Flash / dual LX7 240MHz
- arduino-esp32 v3.20017 (4개): WIFI_STA ~45KB heap (issue #5990) / WiFi.h ~500KB Flash (issue #9741) / MIN free heap 60-90KB peak / framework 3.20017.241212
- ESP-IDF heap_caps (3개): `MALLOC_CAP_8BIT` / `MALLOC_CAP_DMA` (internal SRAM) / `MALLOC_CAP_SPIRAM`
- esp_camera 패턴 (4개): `fb_count` continuous mode / `CAMERA_FB_IN_PSRAM` / `CAMERA_FB_IN_DRAM` 옵션 / issue #620 WiFi join 후 fb_get
- legacy driver/i2s.h (3개): arduino-esp32 v3.20017 `i2s_std.h` 미노출 (카테고리 28 학습 15) / DMA static / I2S0·I2S1 분리
- VL53L5CX (5개): FW upload ~84KB (UM2884) / 매 power-on I2C upload / RAM-based sensor / I2C max 1 Mbits/s / ULD driver
- 출처 catch 합계: 24개 (학습 13 목표 21+ 충족 ✅)
**한계**:
- 정적 분석 한정 (BSS + DATA + Flash 컴파일 시점)
- 동적 heap (`ESP.getMinFreeHeap()` + stack high-water mark): 부품 도착 후(5/15+) 또는 11주차 통합 테스트로 분리 (카테고리 17)
- 페리페럴 동시 활성 fragmentation: PoC 1주차 통합 시 실측 (5/21, 카테고리 17.1.3)
- Plan B 임계값: 정적 1차 추정 — 동적 측정 후 재조정 가능
- WiFi 동적 추정 ~80KB: arduino-esp32 일반 패턴 인용, 본 프로젝트 실측 미진행
**관련 카테고리**: 16.1 (입력 데이터 5건) / 17.1.1 (본 갱신 대상) / 17.1.3 (5/21 통합 시점 입력) / 14 (코어 분배 잠정안 재확정 입력) / 28·29 (학습 15·16 적용 그물)
**관련 commit**: 본 entry 자체 (`docs/decisions.md` 17.1.1 갱신 + `docs/decisions-log.md` 본 entry 추가)

**PoC-(9) 객관 검증 catch (학습 14 catch 그물 작동, 5/12 사례)**: 1차 판정에서 옵션 A (갱신 없음) 추천 → 학부생 push back ("진짜 갱신이 필요없는지 객관적으로 검증") → 2차 객관 검증 시 카테고리 16.1 / 15 / 17.1.3 cross-reference 충돌 5건 발견 (critical 1건 + moderate 2건 + minor 2건) → 후속 commit으로 critical/moderate 3건 보강. **학습 14 catch 그물 사례 추가 (사전 준비 11일 누적 5건째)**.

---

## 2026-05-13 - Day 7 외부 계정 셋업 + 졸작 중간 발표 결과 (카테고리 30 신설 + 26 v1 확정 + 11 5/13 row 갱신)

**변경 카테고리**: 30 신설 / 26 v1 확정 1줄 추가 / 11 5/13 row 활동 3건 갱신
**HEAD**: `6fa17c9` (시작) → 본 commit
**학부생 의도 (chunk 경계 예외)**: 5/14 오전 카카오 셋업(11분)을 5/13 Day 7 외부 계정 셋업 연속선상으로 통합 처리 (학습 9 chunk 경계 정렬 예외 — 11분 단독 chunk 불필요 + 외부 계정 셋업이라는 도메인 일관성 우선)

**활동 1 — 졸작 중간 발표 (5/13 수)**:
- 발표 내용: 데모 시나리오 v1 (카테고리 26 기반, `docs/presentation/2026-05-13-script.md`)
- 결과: 교수님 반응 좋음, 추가 피드백 0건 → v1 그대로 확정
- DB1 v2 row 신설 불필요, DB3 미결정 "5/13 발표 후 카테고리 26 갱신 가능성" 🟢 해결 처리

**활동 2 — AWS 가입 + 보안 4종 (5/13 23:06~23:41, 35분)**:
- 계정: Account ID `953926452053` / 별칭 `xorms` / 리전 `ap-northeast-2` / 메일 `bagtaegeun278@gmail.com`
- MFA(루트 + Google Authenticator `xorms-iphone`) / IAM `ddingdong-admin` (AdministratorAccess) / 결제 알람 2종 (Zero-Spend $0.01 + Monthly $100/85%/100%/예상 100%)
- **AWS 가입 정책 변경 catch (학습 13 catch 1건)**: 2024-07~ 신규 가입자 무료(6개월)/유료 선택 강제. 무료 = 200 USD 크레딧 + 6개월 자동 해지 → 졸작 9/30 종료가 무료 기간(~2026-11-13) 안에 자연 수렴 → 카테고리 30.1 유효 기간 명시 근거. 출처: AWS 가입 화면 직접 catch

**활동 3 — 카카오 디벨로퍼스 셋업 (5/14 10:26~10:37, 11분, Day 7 통합)**:
- 신규 앱 `Ddingdong` 앱 ID `1456718` / 회사 `xorms` / 카테고리 `라이프스타일` (기존 카카오 계정 재사용)
- 카카오 로그인 ON / talk_message scope **선택 동의** 채택 (이용 중 동의 X)
- **카카오 비즈 앱 회피 결정 catch**: memo API("나에게 보내기")만 사용 → 비즈 앱 심사(사업자 등록증) 불필요. "선택 동의" 채택 근거 3건 (memo 한정 / 본인 본인 동의 / 카카오 로그인 동의 단순). 카테고리 7 "memo + 비즈 앱 회피" 일치. 출처: 카카오 디벨로퍼스 공식 문서

**영향**:
- 카테고리 22.6 "5/9~5/14 외부 계정 셋업 전진 활용" AWS + 카카오 ✅ (Naver Cloud Platform 미진행 — 카테고리 30.6에 11~14주차 진입 시 신규 row 검토 명시)
- 11~14주차 카카오톡 작업 진입 시 추가 placeholder (플랫폼 등록 / Redirect URI / 토큰 발급 / 메시지 발송 테스트) 카테고리 30.5 명시
- 사전 준비 11일 후반부 (5/13~5/17) Day 7 외부 계정 셋업 chunk 완료. 5/14 호환성 추가 검증 / 5/15 부품 수령 chunk로 이행

**근거**: 본 chat 직접 catch (AWS 콘솔 / 카카오 디벨로퍼스 콘솔 실제 셋업 결과). 5/13 발표 결과는 학부생 직접 보고. 자격증명은 본 entry 절대 미기록 (카테고리 30 두번째 콜아웃 일치).

**관련 commit**: 본 entry 자체 (`docs/decisions.md` 카테고리 30 신설 + 11 5/13 row + 26 v1 확정 + `docs/decisions-log.md` 본 entry 추가)

---

## 2026-05-16 - Day 8 NCP 회원가입 + 그린루키 사전 catch + 옵션 B 채택 (카테고리 30.7~30.10 신설 + 22.6 갱신)

**변경 카테고리**: 30 헤더 갱신 / 30.6 정정 (미진행 → 완료) / 30.7~30.10 신설 / 22.6 cross-reference 갱신
**HEAD**: `2b4b4d3` (시작) → 본 commit
**배경**: 사전 준비 11일 후반부 진입. 5/14~5/15 학교 축제 휴식 (작업 0건) 후 5/16 재개. 자성리얼 부품 도착 대기 + 외부 계정 셋업 잔여 (NCP) 우선 처리 결정. 학부생이 화면 직접 catch 강제 + Claude Code MCP 위임 강제로 학습 13/14 그물 작동.

**작업 결과**:
1. NCP 회원가입 완료 (`2021304034@skuniv.ac.kr`, 개인 회원, 14:36 시작 ~ 14:42 크레딧 100,000원 부여, 6분)
2. 결제수단 등록 완료 (회원가입 절차 중 자동, 신용카드, 자동 과금 활성화)
3. 2차 인증 SMS 등록 완료 (휴대 전화번호, AWS OTP와 다른 방식, 학부생 의도 분리)
4. IP 보안 OFF / Idle Time 3시간 (학부생 환경 적정)
5. 그린루키 사전 catch (MCP 위임 12분, 미제휴 확정 → 옵션 B 채택)

**학습 13 catch 그물 작동 (5/16)**:
- 학부생이 NCP 회원가입 완료 화면에서 "무료 이용 크레딧 100,000원" 직접 catch → 사전 박았던 "100,000원 / 100일" 정정
- 학부생이 크레딧 받기 팝업에서 "3개월간 사용가능한 청구 할인 크레딧" 직접 catch → 만료 일자 8/16 정정 + 자동 과금 catch 그물 작동
- AI 일반 패턴 박기 X, 학부생 화면 catch 우선 강제 → 학습 13 강화 사례

**학습 14 catch 그물 작동 7건째 (5/16)**:
- 학부생이 그린루키 신청 메일 발송 전 "서경대 제휴 여부 사전 검증" 강제 요구
- Claude Code MCP 위임 12분 결과: NCP 공식 명단 32개 기관 시각적 catch → 서경대 미포함 확정
- 3중 출처 (NCP 공식 + 서경대 사이트 + 비공식) 일관 미발견 → 미제휴 사실상 확정
- 결정: 옵션 B (메일 발송 X) → 단기 손실 5분 + 단기 이득 0 (거절 답변 가능성 매우 높음) ROI 낮음
- 학습 14 catch 그물 사례 누적: 5/10 (camera_dummy) → 5/11 (mic 컨벤션) → 5/12 (cross-reference) → 5/13 (row A 부재) → 5/16 (그린루키 사전 검증) **5건째 (사전 준비 11일 기준)**

**위임 프롬프트 형식 SSoT 강제 작동 사례 (5/16)**:
- 그린루키 사전 catch 위임 프롬프트 9개 섹션 구조 준수 강제
- MCP 12분 단축 완료 (예상 20~30분 대비) → 위임 프롬프트 형식 효율 검증
- 자체 검증 표 (학습 13/14 만족 / 학습 15/16 무관) 출력 강제 → 출력 품질 통과

**관련 카테고리**: 30.7 (NCP 본 entry 대상) / 30.8 (그린루키 사전 catch) / 30.9 (11~14주차 placeholder) / 30.10 (학습 catch 누적) / 22.6 (사전 준비 11일 영향, NCP 5/16 통합 갱신) / 7 (STT Clova Speech) / 26 (시연 시나리오, 변경 X)
**관련 commit**: 본 entry 자체 (`docs/decisions.md` 카테고리 30 + 22.6 갱신 + `docs/decisions-log.md` 본 entry 추가)

**학부생 의도 명시 (학습 9 chunk 경계 정렬 적용)**:
- 5/14~5/15 학교 축제 휴식 = chunk 경계 자연 정렬 (작업 0건, 노션 DB1 row 추가 X, 자연 누락 패턴)
- 5/16 Day 8 통합 처리 = 사전 준비 11일 마지막 chunk 진입 (5/16~5/17 2일 남음)
- 5/18 PoC 1주차 진입 전 자성리얼 부품 도착 catch 강제 재개 (학습 10 매일 묻기 재개)
- 옵션 D (산학협력단 메일) 5/18 이후 평일 진입 시 결정 (장기 가치 처리)

---

## 2026-05-25 - 5/17~5/25 누적 chunk 9일치 통합 (카테고리 22.7 신설 + 11 append + 학습 17 신규 발굴)

**배경**:
- 2026-05-16 (HEAD fc47eed, Day 8 NCP 셋업 완료) ~ 2026-05-25 (본 entry 작성 시점) 9일 누적 chunk
- 5/17~5/22 (6일): 작업 0건 (학교 랩실 적응 + 전공 공부, 학습 9 chunk 경계 정렬 6일 확장)
- 5/23 (토): 자성리얼 도착 결과 catch (ESP32-S3 Sense 메인 보드 부재, ESP32-C3만 도착) + 메이크잇펀 재발주 ₩28,600
- 5/24 (일): 작업 0건 (학습 9 확장)
- 5/25 (월): Day N 명명 폐기 결정 + 매일 밤 3-set 루틴 + 학습 17 신규 발굴

**작업 결과**:
1. 카테고리 22.7 신설 — 자성리얼 ESP32-S3 메인 보드 부재 catch + 메이크잇펀 재발주 (₩28,600, 주문번호 2026052312703221, 도착 예상 5/26~5/29)
2. 카테고리 11 끝 append — Day N 명명 폐기 사실 (Day 1~Day 11 본문 보존 + append, 학습 8 패턴)
3. **학습 17 신규 발굴**:
   - 인계 패키지 본문 catch 그물 강제 — PoC-(N) 채팅방 진입 시 인계 패키지 본문에 박힌 카테고리 번호 / 본문 인용 / 작업 단계 전부 실제 SSoT (`git show <hash>:<path>`) 결과로 검증 필수. 본 5/25 PoC-(12) 위임 프롬프트 = 인계 패키지에서 전파된 카테고리 번호 6건 박음 정정 후 재작성 사례
   - 유도리 마인드 (22주 일정 = 가이드라인) — 22주 마스터 스케줄은 정량 데드라인 X, 가이드라인. chunk 단위 휴식 / 지연 발생 시 매일 묻기 강제 룰 등 자연 폐기 허용. Day N 명명도 외부 의존 chunk 진입 시 폐기, 날짜 기반 명명으로 전환. 학부생 의도 "유도리 마인드" (5/23 발언) 정합

**학습 적용**:
- 학습 13 (출처 catch): 적용 — 본 entry 모든 수치/일자/카테고리 번호 학부생 직접 SSoT catch 결과 인용
- 학습 14 (가정 검증): 적용 — 본 entry 작성 전 위임 프롬프트 v1 (카테고리 26 박음) → 학부생 catch → 위임 프롬프트 v3 (카테고리 11 정정 + Claude Code CLI 정상화 폐기) 재작성 사례. catch 그물 작동 누적 (5/16 시점 7건 + 5/23~5/25 누적, 정확한 누적 횟수는 다음 chunk에서 catch 강제)
- 학습 15 (packaging vs 공식): 무관 (코드 작업 X)
- 학습 16 (기존 컨벤션 우선): 적용 — decisions.md 헤더 마커 부재 = 기존 컨벤션 = 발명 X. 카테고리 11 + 22 본문 형식 100% 보존
- 학습 17: **본 entry로 정식 추가**

**관련 카테고리**: 11 / 22.7 (신규)

**학부생 의도**:
- 5/17~5/22 + 5/24 작업 0건 = 학교 랩실 적응 + 전공 공부 + 학습 9 chunk 경계 정렬 7일 (자발 결정)
- Day N 명명 폐기 = 학부생 "유도리 마인드" (5/23 발언) 정합
- Claude Code CLI 정상화 작업 (5/25)은 학부생 개인 환경 도구 이슈로 본 entry 미기록 (학습 12 npm prefix 충돌 패턴 동일, 프로젝트 SSoT 아님)

---

## 2026-05-26 (화) — 메이크잇펀 일시품절 catch + 5/26~6/14 chunk 단계별 진행 결정

**배경**:
- 2026-05-25 (HEAD 8f4dd7d, Set 1 매일 밤 루틴 완료) 이후 2026-05-26 (화) 진입 시점 catch 사항
- 5/26 14:20 카카오톡 통보 — 메이크잇펀 김정열 판매자 발송일 변경 통보 (일시품절, 2026-06-15까지 입고 후 발송 예정)

**작업 결과**:
1. **카테고리 22.7 보강 — 일시품절 catch append**:
   - "도착 예상" 영역 5/26 학부생 직접 화면 catch 결과 (학습 13) 정정 — 2026-06-15까지 입고 후 발송 → 도착 약 6/17~6/19 예상
   - "22.6 사전 준비 11일 영향 재평가" 영역 5/26~6/14 약 20일 chunk 자연 슬립 + 카테고리 8 단계별 진행 cross-reference 추가
   - 학습 14 catch 그물 작동 사례 (외부 환경 가정 검증 강제 — 발주 시점 catch만으로 부족, 발송 시점 별도 catch 강제)

2. **카테고리 8 본문 끝 append — 5/26~6/14 chunk 단계별 진행 결정 (8.1 신설)**:
   - Phase 1: React 웹 대시보드 단독 (학부생 익숙 영역, mock JSON + REST 폴링 3초 구조)
   - Phase 2: React + Flask 동시 (Flask 학습 진입, 학부생 MacBook M4 로컬 진행, AWS 비용 0원)
   - Phase 1 → Phase 2 전환 시점 = 학부생 자율 (학습 17 정합 — 세부 날짜 박지 X)
   - **위임 프롬프트 mismatch 자체 정정 사례 (학습 14 catch + 학습 16 적용)**: 위임 프롬프트 본문은 "카테고리 9 (Vite + React + shadcn/ui + Tailwind + REST 폴링 3초 + 접근성 UI 본문)" + "9.X 신설"로 박았으나 `git show 8f4dd7d:docs/decisions.md` SSoT catch 결과 = 카테고리 8 (대시보드) 본문 100% 일치, 카테고리 9 = VL53L5CX 사람 검증 단계 (ML 영역, 무관). 학습 16 (기존 컨벤션 우선)로 자체 정정 — 카테고리 8.1로 신설. 학부생 의도 100% 정합 (웹 대시보드 본문 끝 append)

3. **학습 17 강화 본문 추가**:
   - AI 추천 박은 세부 날짜 (Phase 1 5/26~6/3 / Phase 2 6/4~6/14) → 학부생 push back "단계별로 세부 날짜까지는 확정짓지마" → 학습 17 유도리 마인드 직접 위반 catch 정정 사례
   - Claude (AI) 본인도 학습 17 catch 그물 작동 대상 — chunk 단위 작업 범위만 SSoT, 세부 날짜는 학부생 자율

**학습 적용**:
- **학습 13 (출처 catch)**: 적용 — 메이크잇펀 일시품절 정보 학부생 직접 화면 catch (카카오톡 스크린샷). AI 일반 패턴 박기 X
- **학습 14 (가정 검증)**: 적용 — 5/23 시점 가정 (도착 5/26~5/29) 무효화 catch + 학부생 React/Flask 익숙도 catch (학부생 직접 진술) + **위임 프롬프트 본문 카테고리 9 박음 mismatch catch (실제 카테고리 8)**
- **학습 15 (packaging vs 공식)**: 무관 — 코드 작업 X
- **학습 16 (기존 컨벤션 우선)**: 적용 — 카테고리 22.7 / 카테고리 8 본문 형식 100% 보존, append만. 위임 프롬프트 박음 카테고리 9 → 실제 카테고리 8 자체 정정
- **학습 17 (인계 패키지 catch + 유도리 마인드)**: **본 entry로 강화 사항 정식 추가** — AI 본인도 catch 그물 작동 대상 영구 반영

**관련 카테고리**: 22.7 (보강) / 8.1 (신설)

**학부생 의도**:
- 5/26~6/14 chunk 부품 무관 작업 진행 = 학습 17 유도리 마인드 정합 (학부생 자발 제안)
- 단계별 진행 (Phase 1 → Phase 2) = 학부생 React 익숙 + Flask 처음 학습 곡선 catch 결과
- 세부 날짜 박지 X = 학습 17 유도리 마인드 직접 적용 (AI push back으로 정정)
- 본 entry는 학습 17 catch 그물 AI 본인 대상 강화 영구 반영 사례

---

## 2026-05-27 (수)

### 변경 사항

1. **카테고리 30.8 본문 정정** — 옵션 D 연기 → 옵션 D 폐기 (학부생 직접 결정)
2. **카테고리 31 신설** — Claude 박음 본문 사전 자가검증 3단계 강제 룰

### 사유

**옵션 D 폐기 (catch 1)**:
- 학부생 직접 결정 (5/27 PoC-(13) 본 채팅방)
- 학부생 작품 기간 (~2026-09-30) 안에서 NCP 제휴 추진 불가
- 후배 가치 창출 기회 폐기 수용

**자가검증 3단계 강제 룰 영구 반영 (catch 2)**:
- 학부생 push back (5/27 PoC-(13) 본 채팅방)
- 박음 본문: "코드 관련해서 나한테 제안할 때는 항상 전문가 시선에서 자가검증을 거치고 나한테 제안해줘"
- 학습 17 3차 강화 정직 작동 11건째 (AI 본인도 catch 그물 작동 대상 정직 영구 반영 결정적 증거)
- 추가 학부생 push back: "자가검증 3단계는 백그라운드에서 진행해 답이 너무 길게 보이면 내가 가독성이 떨어져서 파악하는데 힘들어" → 백그라운드 진행 룰 추가 (31.4)

### 영향

- 모든 후속 PoC / Domain 채팅방에서 Claude 박음 본문 자가검증 3단계 강제 적용
- 매일 밤 3-set 루틴 Set 2 (프로젝트 지침 수정본)에 본 룰 추가 박음 강제

---

## 2026-05-28 (목) — PoC-(14) Phase 1 React 대시보드 완료 + 결정 1~8 SSoT 반영

**배경**:
- 2026-05-26 (HEAD 142121b, 카테고리 8.1 신설) ~ 2026-05-28 chunk. 5/26~6/14 부품 무관 작업 영역(카테고리 8.1)에서 Phase 1 React 단독 대시보드 진행.
- 2026-05-28 PoC-(14): 결정 1~8 확정 (API 명세 5건 + 기술 스택 + 컴포넌트 17개 + 페이지 5종 + 디자인 토큰) + Phase 1 PR #1 머지 + GitHub Flow 첫 PR 완주.

**작업 결과 (decisions.md 반영)**:
1. **카테고리 4 (ML)** — predicted_class 3종 enum 추가: 초인종(`doorbell`) / 노크(`knock`) / 화재경보(`fire_alarm`), Dense(3) 매핑
2. **카테고리 6 (서버) + 6.1 신설** — API 명세 1차 확정:
   - **엔드포인트 버저닝 결정 변경**: `/api/detect`·`/api/enrich` → `/api/v1/*` (detect / enrich / notifications / stats). 상단 표 행 추가
   - Device/Dashboard Bearer Token 분리 + HTTPS 강제 + `client_request_id`/`request_id`(ULID) 분리 + HTTP status 8종 + rate limit(device_id 5초 1회, Retry-After) + idempotency_keys(24h TTL) + stats period=today
   - 상세 JSON 미박음, 코드 포인터만 (`dashboard/src/types/`)
3. **카테고리 7 (알림)** — 카카오 토큰 상태 API = 상대값 `kakao_token_expires_in_minutes` + status enum(valid/expiring/expired)
4. **카테고리 8 + 8.2 신설** — Phase 1 확정 기술 스택(Vite + React 19 + TS + Tailwind v4 CSS-first + shadcn/ui) + 컴포넌트 17개(4계층) + 페이지 5종 + 디자인 토큰(터치 44~56px / 화재경보 shake+pulse-border / 한국 대중 앱 영감)
5. **카테고리 8.1** — Phase 1 완료 마킹 (PR #1, 69파일/9180줄, Playwright 검증 통과)
6. **카테고리 20** — 문서/코드 push 분리 명문화 (문서 단독 = main 직접 push / 코드 = feat 브랜치 + PR 강제), Squash 기본 유지
7. **카테고리 27 (학습 14) 27.5 신설** — 라이브러리 설정 방식/버전 가정 검증 사례 (Tailwind v3 박음 → v4 CSS-first 공식 기본값 catch)
8. **카테고리 29 (학습 16) 29.5 신설** — 용어 컨벤션 (위임 '도어벨' → SSoT '초인종')

**PR #1 정정 기록 (오기 catch)**:
- 위임 프롬프트 본문: "Squash merge로 머지" + "브랜치 삭제 완료"로 기술
- 실제: **PR #1 = merge commit으로 머지** (`95c3208`, Squash 설정 미적용 — 1회성 예외). origin 브랜치 삭제 완료(학부생 웹 확인), 로컬 feat 브랜치 정리 완료 (`git branch -d` + `git fetch --prune`)
- **복구 계획**: 다음 PR 전 repo Settings에서 Squash merging 활성화 → 카테고리 20 "Squash 기본" SSoT 복구. 카테고리 20 룰 자체는 유지 (완화 X)

**학습 17 catch 그물 작동 (위임 프롬프트 카테고리 번호 혼동)**:
- 위임 프롬프트가 학습 N ↔ 카테고리 N 혼동: "카테고리 4(API)" / "카테고리 14(학습)" / "카테고리 16(학습)" / "카테고리 11(chunk 일지)"
- `git show HEAD:docs/decisions.md` SSoT 대조 결과 정정:
  - API 명세 → 카테고리 6(서버)/4(ML)/7(알림) 분산 (cat 4 단독 X, cat 6 기존 `/api/detect` 충돌)
  - 학습 14 = 카테고리 27 (cat 14 = ToF 코드), 학습 16 = 카테고리 29 (cat 16 = monorepo)
  - chunk 일지 = 본 decisions-log 날짜 entry (cat 11 = 동결된 사전 준비 일정, 미수정)
- 학부생 확인 후 SSoT 위치로 자체 정정 (5/26 "카테고리 9→8" 자체정정 선례 정합)

**학습 적용**:
- 학습 13 (출처 catch): 적용 — API 결정/컴포넌트/페이지 전부 `dashboard/src/types/` + 머지 코드 직접 대조 후 박음
- 학습 14 (가정 검증): 적용 — Tailwind v3 가정 → v4 공식 기본값 catch (27.5) + 위임 카테고리 번호 SSoT 대조
- 학습 15 (packaging vs 공식): 적용 — Tailwind v4 = 현재 공식 기본값(`package.json` 실제 설치 + context7) 대조
- 학습 16 (기존 컨벤션 우선): 적용 — '도어벨'→'초인종' 용어 정정 (29.5) + decisions.md 본문 형식 100% 보존 (append만)
- 학습 17 (인계 패키지 catch + 유도리 마인드): 적용 — 위임 카테고리 번호 혼동 catch + Phase 2 전환 날짜 미고정 유지

**관련 카테고리**: 4 / 6 (6.1 신설) / 7 / 8 (8.2 신설) / 8.1 / 20 / 27 (27.5 신설) / 29 (29.5 신설)
**관련 commit**: 본 entry 자체 (`docs/decisions.md` + `docs/decisions-log.md`, 문서 단독 변경 = 카테고리 20 신규 룰로 main 직접 push)

---

## 2026-06-14 (일) — Phase 2-1차 Flask 백엔드 골격 완료 + 미결 2건 + 데모 트리거 재설정

**배경**:
- 2026-05-28 (HEAD `1838bec`, Phase 1 완료) ~ 2026-06-14 chunk. 5/29~6/13 약 보름 작업 0건 슬립 — 메이크잇펀 부품 6/17~19 도착 대기 + 학교 일정. **학습 17 유도리 마인드 정합** (외부 의존 chunk 슬립 시 정량 데드라인 X, 부품 무관 작업 자유 재배치).
- 2026-06-14 Phase 2-1차: Flask 백엔드 골격 구현 → **PR #2 Squash 머지** (`1838bec`→`37a92b3`, 브랜치 `feat/server-flask-skeleton` 머지 후 삭제). 카테고리 20 "Squash 기본" SSoT 복구 확인 (PR #1 1회성 merge commit 예외 → PR #2 Squash 정상 적용).

**작업 결과 (Phase 2-1차 구현, decisions.md 8.1 반영)**:
- `server/` = Flask app factory + Blueprint(`/api/v1`) + Flask-SQLAlchemy 모델 2종(`notifications` / `idempotency_keys` 24h TTL) + 엔드포인트 4종(`detect` / `enrich` / `notifications` / `stats`)
- 인증 Device/Dashboard Bearer Token 분리 + rate limit(device_id 5초 1회, Retry-After) + idempotency(`client_request_id` 기반) + HTTP Status 8종, curl 15종 통과
- ML 추론 = mock (실제 YAMNet 11주차) / HTTPS·EC2 = 11주차 (현재 로컬 http, AWS 비용 0원)
- **JSON 1:1 = `dashboard/src/types/`** (api.ts / notification.ts / stats.ts) SSoT 단일화 유지 (카테고리 6.1 코드 포인터 정합)

**미결 2건 박음 (decisions.md 반영)**:
1. **카테고리 6 — rate limit Redis 교체 (11주차)**: 현재 rate limit = in-memory dict. Gunicorn 워커 2개(`preload_app=True`, 카테고리 6) 시 워커별 dict 분리 → rate limit 무효화. 11주차 배포 진입 시 Redis(공유 스토어) 교체 필요.
2. **카테고리 8.1 — api.ts cursor 타입 부재 (2-2차 추가)**: 현재 `NotificationsApiResponse = { notifications }` 단일 → 백엔드 cursor 메타(`next_cursor` / `has_more`)는 additive. 2-2차 React 연동 시 `dashboard/src/types/api.ts`에 cursor 타입 추가 필요.

**데모 시나리오 트리거 재설정 (카테고리 26.8)**:
- Demo-Verify-(N) 채팅방 신설 시점 "5월 중" → **7월 초 재설정**. 근거: 메이크잇펀 부품 슬립 + Phase 2 진행 중(2-1차 6/14 완료) + ML/시연 준비 단계(8주차~) 정렬. 정량 데드라인 X(학습 17 유도리 마인드) 유지, 상세 = 노션 DB3 (Set 3).

**학습 적용**:
- 학습 13 (출처 catch): 적용 — Phase 2-1차 구현 내용 = PR #2 머지 코드 + `dashboard/src/types/` 직접 대조 후 박음.
- 학습 17 (인계 패키지 catch + 유도리 마인드): 적용 — 5/29~6/13 슬립을 데드라인 위반 아닌 정상 chunk 재배치로 기록 + 데모 트리거 정량 데드라인 X 유지 + 위임 카테고리 번호(6 / 8.1 / 26) `git show` SSoT 사전 대조 후 박음.

**관련 카테고리**: 6 / 6.1 / 8.1 / 20 / 26 (26.8)
**관련 commit**: 본 entry 자체 (`docs/decisions.md` + `docs/decisions-log.md`, 문서 단독 변경 = 카테고리 20 main 직접 push)

---

## 2026-06-15 (월) — Phase 2-2차 React 실제 API 연동 완료 + 부품 전량 도착 (인두기 불필요 확정)

**배경**:
- 2026-06-14 (HEAD `37a92b3`, Phase 2-1차 Flask 골격) ~ 2026-06-15 chunk. 2-1차에서 박은 미결 2건 중 1건(카테고리 8.1 api.ts cursor 타입 부재)을 2-2차에서 해소.
- 2026-06-15 Phase 2-2차: React mock → 실제 Flask API 연동 → **PR #3 Squash 머지** (`37a92b3`→`cec9c9b`). 카테고리 20 "Squash 기본" SSoT 정합.
- 동일 6/15 메이크잇펀 발송 예정일에 부품 전량 조기 도착 (XIAO + 디바이스마트 동시 catch). 5/26 catch 시점 도착 예상 약 6/17~6/19 대비 조기.

**작업 결과 (Phase 2-2차 구현, decisions.md 8.1 / 6 반영)**:
- `dashboard/src/types/api.ts`에 cursor 메타(`next_cursor` / `has_more`) **additive 추가** (2-1차 박은 미결 해소, 기존 `NotificationsApiResponse` 형식 보존)
- React mock → 실제 fetch 전환 — `apiGet` **공용 헬퍼로 DRY** 처리, 폴링 훅(`usePolling` 등) 무수정 (학습 16 기존 컨벤션 우선 정합)
- **CORS = Vite dev proxy(dev 전용)로 우회** — `flask-cors` 미설치, env `VITE_API_BASE_URL=/api/v1` 상대 경로 → Vite가 백엔드로 프록시 (동일 origin)
- 미니 E2E 전항목 통과: seed 11건 렌더 + detect 오늘 주입 → stats 0→1 반영 + CORS 0건 + 폴링 3초 + 콘솔 0 에러 + tsc / eslint / build 통과

**미결 2건 박음 (decisions.md 반영)**:
1. **카테고리 6 — 배포 CORS (11주차)**: Vite dev proxy = 개발 전용. 11주차 배포 진입 시 proxy 무효 → Nginx 동일 origin 서빙(대시보드 정적 + `/api/v1` 리버스 프록시) or 백엔드 CORS 헤더 별도 필요.
2. **카테고리 8.1 — stats 폴링 중복 (follow-up)**: 2-2차 연동 후 `/stats`가 폴링 주기당 2회 호출 (`useStats` 통계 섹션 + `useDevice` 헤더 독립 폴러). GET = rate-limit 제외 + 3초 주기라 현재 안전. 공유 폴러 or Context 통합 권고(추후 폴리시 or 11주차). 학습 16에 따라 이번엔 미변경.

**부품 전량 도착 catch (카테고리 22.7 반영, 학습 13·14)**:
- 메이크잇펀 XIAO ESP32-S3 Sense **Pre-Soldered** 수령 (SKU `102010635`, ST 정품, 학부생 직접 화면 catch). 발송 예정 6/15 → **실제 6/15 조기 도착(추가 슬립 없음)**.
- 디바이스마트 부품 전량: INMP441 모듈("납땜" 버전) / VL53L5CX-SATEL(ST 정품, `497-VL53L5CX-SATEL-ND`) / 점퍼선 3종(M-M / M-F).
- **인두기 불필요 확정** — INMP441 라벨 "납땜" + SATEL 정품 헤더 + XIAO Pre-Soldered = 전량 납땜 완료 상태. 다이소 잔여 = **브레드보드만**(USB-C 케이블 집 보유).

**학습 적용**:
- 학습 13 (출처 catch): 적용 — 2-2차 구현 내용 = PR #3 머지 코드 + `dashboard/src/types/api.ts` 직접 대조 후 박음 + 부품 = 학부생 직접 화면 catch (SKU / 부품번호 / "납땜" 라벨 실물 확인).
- 학습 14 (가정 검증): 적용 — "납땜 필요?" 가정 → 실물 라벨/헤더 직접 catch로 인두기 불필요 확정 (catch 그물 작동) + 위임 카테고리 번호(6 / 8.1 / 8.2 / 22.7) `git show` SSoT 사전 대조 후 박음.
- 학습 16 (기존 컨벤션 우선): 적용 — `apiGet` 공용 헬퍼 + 폴링 훅 무수정으로 기존 컨벤션 보존 + stats 폴링 중복도 이번 chunk 미변경(권고만 박음).
- 학습 17 (인계 패키지 catch + 유도리 마인드): 적용 — 부품 조기 도착을 슬립 단축으로 흡수 + 정량 데드라인 미고정 유지.

**관련 카테고리**: 6 / 8.1 / 22.7 / 20
**관련 commit**: 본 entry 자체 (`docs/decisions.md` + `docs/decisions-log.md`, 문서 단독 변경 = 카테고리 20 main 직접 push)

---

## 2026-06-22 (월) — PoC-(17) 1차 부팅 검증 완료 (camera_v1 + poc PASS) + 카테고리 32 신설

**배경**:
- 5/7~5/11 작성 더미 펌웨어의 **실보드(XIAO ESP32-S3 Sense Pre-Soldered) 1차 부팅 검증**. 6/15 부품 전량 도착(전 entry) 후 첫 실보드 검증. USB-C 단독(결선 0)으로 가능한 2종(카메라·WiFi)만 진행. 학부생 = 결과 판정, MCP = 실행/해석. **검증 전용 = firmware 0 수정 / commit·push 0 / secrets.h 미열람**.
- HEAD `0d15fe2` (Phase 2-2차) 기준, 검증 전후 working tree clean 유지.

**검증 결과 (PASS 2종)**:
- **카메라(camera_v1) PASS**: 센서 **OV3660 실측 확정**(PID `0x3660` = 라이브러리 SSoT 일치, 가정 적중 → 센서 코드 수정 불필요). PSRAM 8MB OCTAL 인식 / QVGA JPEG ~6KB ~30fps 연속 캡처 / fb_get NULL 0건 / 힙 누수 없음.
- **WiFi(poc) PASS — 안테나 진단 적중**: 안테나 미장착 시 양쪽 SSID 15s timeout 반복 → **u.FL 외장 안테나 장착 즉시 `Connected via PRIMARY` (RSSI -53dBm, 0.7초 연결) + HTTPS POST 200**. 0순위 가설(XIAO WiFi = 외장 안테나 필수) 확정. secrets.h 자격증명·2.4GHz는 정상이었음.

**발견 이슈 2건 (별도 수정 위임 — 본 검증 코드 0 수정)**:
1. **env:poc src_filter blacklist 회귀**: `[env:poc]`만 blacklist(`+<*>`) 잔존 → 5/10·5/11 추가된 mic_test/tof_test의 `setup()`/`loop()` 흡수 → multiple definition 링크 충돌(5/8 이후 미재빌드로 잠복). 1차 검증은 `PLATFORMIO_BUILD_SRC_FILTER` 환경변수 override로 우회. 근본 = whitelist 통일 별도 위임(카테고리 27.6).
2. **camera_common.cpp PID 버그**: `id.PID == 0x36` 비교 vs 실제 `uint16_t 0x3660` → 라벨 `(UNKNOWN)` 오표기 + OV3660 dark-image 보정(Khangura #6) 미실행. **캡처는 정상**, 시연 밝기 위해 `0x36→0x3660` 수정 필요. 별도 수정 위임.

**환경 변경 1건 (코드 아님, 학부생 승인)**:
- **pio penv 복구/정정**: `/tmp/pio-venv`(5/7 기록) = `/tmp` 재부팅 소실 → 공식 설치 스크립트로 `~/.platformio/penv`(표준)에 PlatformIO Core **6.1.19** 복구(system python 무수정). 정적 기록의 재부팅 무효화 = **학습 14 사례**로 카테고리 16 정정.

**SSoT 반영 (decisions.md)**:
- 카테고리 1 — OV3660 실측 확정 + WiFi 외장 안테나 필수 append
- 카테고리 16 — `/tmp/pio-venv` → `~/.platformio/penv` 정정(학습 14) + env:poc src_filter 회귀 기록
- 카테고리 27.6 — env:poc whitelist 통일 방향 + blacklist 금지 예방 명문화
- **카테고리 32 신설** — PoC-(17) 1차 부팅 검증 결과(범위/카메라/WiFi/이슈 2건/환경 변경/제약 준수)

**학습 적용**:
- 학습 13 (출처 catch): 적용 — OV3660 = 시리얼 실측 PID `0x3660`을 라이브러리 `sensor.h` SSoT와 직접 대조 후 박음(AI 패턴 짜맞춤 X). 캡처 프레임/RSSI/HTTPS status 전부 실제 시리얼 로그 catch.
- 학습 14 (가정 검증): 적용 — `/tmp/pio-venv` 정적 기록 → 재부팅 소실 실측으로 정정 + WiFi timeout "안테나?" 가정 → 장착 실측으로 확정(catch 그물 작동) + 카테고리 번호(1/16/27/32) `git show` SSoT 사전 대조.
- 학습 17 (catch 그물 + 유도리): 적용 — 블로커 3건(pio 부재 / src_filter 충돌 / WiFi timeout) 전부 임의 결정 X, `AskUserQuestion` 후 진행 + 발견 이슈 2건은 본 검증 범위 밖(코드 0 수정)으로 분리해 별도 위임 명시.

**후속 수정 완료 — 발견 이슈 2건 (PR #4 `c4c8f47` Squash 머지, 2026-06-22)**:
- **이슈 ② camera PID**: `camera_common.cpp` `0x36` 리터럴 → **`OV3660_PID` 매크로**로 정정 (L49 `case 0x36` → `case OV3660_PID` + L79 OV3660 dark-image 보정 분기). 학습 15 헤더 노출 검증 통과(`sensor.h:22`에 `OV3660_PID` 정의 확인) → dark-image 보정(Khangura #6) 분기 정상 작동 복구.
- **이슈 ① env:poc**: `[env:poc]` blacklist → **whitelist `-<*> +<main.cpp>`** 통일 + 임시 우회(`PLATFORMIO_BUILD_SRC_FILTER` 환경변수) 제거. footprint = **poc RAM 13.8% / Flash 25.8% = 5/8 원본 poc(commit `3ec17d4`) footprint 일치** → main.cpp 단독 컴파일·회귀 해소 증명. (참고: camera_v1 9.4% 무변동.)
- SSoT 동기화: 카테고리 27.6 "방향 → ✅ 완료" / 카테고리 32.4 이슈 ①② "예정 → ✅ 수정 완료" append (기존 이력성 문장 보존, 학습 8).

**관련 카테고리**: 1 / 16 / 25 / 27.6 / 32
**관련 commit**: 본 entry 자체 (`docs/decisions.md` + `docs/decisions-log.md`, 문서 단독 변경 = 카테고리 20 main 직접 push) + 발견 이슈 2건 수정 = **PR #4 `c4c8f47`** (`firmware/` 코드 수정, Squash 머지)

---

## 2026-06-29 (월) — PoC-(19) 웹 대시보드 베테랑 리뷰 + Phase B 접근성 3PR 완결 + 학습 18 신설

**배경**:
- Phase 2 완료(2-2차, PR #3 `cec9c9b`) 이후 별도 chunk. 웹 대시보드 **베테랑 리뷰(read-only)** + **접근성 3PR(B-0/B-1a/B-1b)** 진행. HEAD = `3408d97`(PR #7 머지) = origin/main, working tree clean.
- 본 entry는 위 결과의 SSoT(decisions.md) + 변경 이력(decisions-log.md) 동기화. 문서 단독 = 카테고리 20 main 직접 push.

**작업 결과 (decisions.md 카테고리 8.3 신설 반영)**:
- **B-0 (PR #5 `56e44b8`)**: dashboard `tsconfig` strict 활성화 — Phase B 타입 안전 토대.
- **B-1a (PR #6 `e9b9879`)**: a11y 색상 단독 의존 해소(텍스트/아이콘 병행) + `aria-live` announcer로 폴링 갱신 SR 공지. announcer = notifications 폴러 1개 신규.
- **B-1b (PR #7 `3408d97`)**: 본문 바로가기(skip link) + 모바일 drawer 키보드 포커스 트랩/복원.
- **베테랑 리뷰(read-only, 코드 0 수정)**: 🔴 0 / 🟡 4 / 🟢 6 / deferred 6. 🟡🟢 = Phase B 작업으로 분류·반영.

**폴링 배율 정정 (decisions.md 8.1 follow-up, 이력성 보존)**:
- 기존 "stats 폴링 주기당 **2회**"는 과소 집계 → 실측 **3중**(StatsPage + StatsCardsSection + Header) + B-1a announcer 폴러 +1 = **폴링 통합 대상 = stats 3중 + announcer 1**. 통합(공유 폴러/Context)은 deferred 유지(8.3 미결, 11주차). 기존 "2회" 문장 덮어쓰기 X, 정정 sub-bullet append(학습 8).

**학습 18 신설 (decisions.md 카테고리 20 보강)**:
- **학습 18 (PR 웹 머지 후 로컬 main 동기화 필수)**: GitHub 웹 PR squash 머지 → remote main 새 해시 생성 → 로컬 main 미반영. 다음 feature 브랜치 따기 전 `git checkout main && git pull origin main` 강제. 누락 시 squash로 사라진 원본 커밋 위에서 브랜치 갈라져 다음 PR이 이전 PR 커밋 끌고 감.
- **사건 (2026-06-29 PR #6 꼬임)**: 원인 = PR #5 머지 후 로컬 main 미pull 상태에서 B-1a 브랜치 분기 → PR #6에 PR #5 strict 커밋 끌려옴 + merge commit 생성. 해결 = fast-forward pull로 정상 복구. 교훈 = "git pull 폐지"(동일 로컬 머신) 룰의 **명시적 예외 = PR 웹 머지 직후**.

**github MCP write 인증 이슈 (decisions.md 카테고리 18 반영)**:
- MCP "connected"여도 write 시 `Bad credentials` 발생 가능(연결 ≠ PAT 유효). 트리거 = 재현 시 PAT 재발급, 우회 = git-native 명령. 본 항목 자체가 이번 갱신 반영 대상.

**학습 적용**:
- 학습 13 (출처 catch): 적용 — PR #5/#6/#7 해시 + 카테고리 번호를 `git log --oneline` / `git show HEAD:docs/decisions.md` SSoT 직접 대조 후 박음. 리뷰 🔴0/🟡4/🟢6/deferred6 = chunk 인계 수치 그대로 기록(AI 임의 가공 X).
- 학습 14 (repo 구조 가정 검증): 적용 — 인계 추정 카테고리 번호(8.1 하위 vs 8.3 / 학습 위치 / 폴링 기록 위치) 전부 실측 정정. 폴링 정정 대상은 카테고리 6 아닌 **8.1 follow-up(L146)** 실측 확인.
- 학습 16 (기존 컨벤션 우선): 적용 — 8.1/8.2 기존 기록 보존 + 폴링 "2회" 문장 덮어쓰기 X(정정 append) + Phase B 잔존 항목 코드 미변경.
- 학습 17 (유도리 + AI도 catch): 적용 — Phase B → 8.3 신설 판단을 실제 구조(8.1=날짜 chunk / 8.2=기술스택) 근거로 결정(임의 X), 신규 최상위 카테고리 33 불필요 판단으로 구조 보존. 날짜 정량 데드라인 미박음.

**관련 카테고리**: 8 (8.1 / 8.2 / 8.3) / 18 / 20
**관련 commit**: 본 entry 자체 (`docs/decisions.md` + `docs/decisions-log.md`, 문서 단독 변경 = 카테고리 20 main 직접 push) + Phase B = **PR #5 `56e44b8` / PR #6 `e9b9879` / PR #7 `3408d97`** (`dashboard/` 코드, Squash 머지)

---

## 2026-06-30 (화) — PoC-(20) 화재경보 청각장애인 대응 수칙 확정 + SSoT 반영 (카테고리 7.1 신설)

**배경**: 기존 카테고리 7 "화재경보 알림 형식"은 "강조 표현 + 정부 지정 대응 수칙 동시 발송"만 추상 기재. 정작 **수칙 본문**은 미확정 + 초안에 "119 즉시 신고 / 낮은 자세 대피 / 젖은 수건" 식 결함 카피 잔존.

**작업 흐름 (1차 출처 조사 → 정정 → 검증 → 확정)**:
- **1차 출처 조사**: 소방청 「119 안전교육」 청각장애인용 교재(S1, 페르소나 직격) 확보 + 신고수단 현행성(손말이음센터 107 영상통화 / 긴급신고 바로앱 / korea.kr 2025.4.17 개통) 교차 확인.
- **결함 3건 교정**: ① "119 즉시 신고"(음성 전제) → "즉시 대피, 안전 확보 후 신고" ② 대피-신고 순서 역전 교정(대피 우선) ③ 출처 라벨 부재 → 출처 명기.
- **페르소나 누수 3건 정정**(AI 자체 카피 변환 단계 누수, 학습 17): catch 1 외치기 의도적 제외 / catch 2 신고수단 확정수단 우선(영상통화·문자 메인, 앱은 이름만) / catch 3 구조요청 → 시각·문자 수단 구체화.
- **베테랑 검증 통과**(2026-06-30) → **확정**.

**작업 결과 (decisions.md 카테고리 7.1 신설 반영)**:
- 확정 카피 ①(대시보드 도움말) + ②(카카오 알림) 본문 박음 — **검증 완료분 임의 윤문 X**.
- 출처 등급: S1 1차 최우선 / S4 영상통화 현행 / S2·S3 앱 존속(최신 업데이트 **2024-01-20** → 보조 병기) / S5 보조.
- 잔존 유보 1건: "손전등·밝은 천 흔들기" = 1차 직접 근거 없는 일반 시각 구조신호 → 발표 전 시·도 소방 자료 추가 확인 권고.
- 본 수칙 = **도움말 카드 + 카카오 알림 공용 SSoT**.

**비범위 (후속 이월)**: `dashboard/` 도움말 카드 실제 교체는 **B 단계 UI 작업과 묶어 별도 PR**(본 docs-only 위임 제외). 코드 0 수정.

**학습 적용**:
- 학습 13 (출처 catch): 적용 — 행동요령 전수 인용 블록(A 3단계+예외 / B 4요소) 원문 무변경, 카피 표현 레이어만 정정. S1~S6 인벤토리 그대로 승계.
- 학습 14 (카테고리 번호 사전 검증): 적용 — "카테고리 7" / HEAD `a071361`을 `git show HEAD:docs/decisions.md` 실측 대조 후 7.1 하위절 부여(6.1/8.1식 관례 준수, 추정 X).
- 학습 17 (유도리 + AI도 catch 대상): 적용 — 정정 3건 = AI 자신의 카피 변환이 흘린 "소리 전제" 누수를 catch-net으로 회수.

**관련 카테고리**: 7 (7.1 신설) / 3 (화재경보 ToF 우회) / 26 (시연 시나리오)
**관련 commit**: 본 entry 자체 (`docs/decisions.md` + `docs/decisions-log.md`, 문서 단독 변경 = 카테고리 20 main 직접 push)

---

## 2026-06-30 (화) — PoC-(20) Phase B 페르소나 정합 (웹 대시보드 라이트/건강카드 + 화재 도움말 반영, PR #8·#9)

> 동일 날짜 선행 entry(화재 수칙 확정 `223d000`)에 이어진 **B chunk 웹 대시보드 페르소나 정합** 작업. A 화재 수칙은 위 entry 참조(재기술 X).

**배경**: PoC-(20) B chunk — 5060 청각장애인 페르소나 직격 관점에서 웹 대시보드 정합. 산출 코드 2 PR + docs 반영.

**작업 결과 (카테고리 8.3 B-2~B-4 append 반영)**:
- **PR #8 `a615162`(feat) → `3544db4`(머지) — 라이트 테마 기본 전환**: 다크 기본 → 라이트 기본(다크 토글+localStorage opt-in 보존). 위임 "다크 위주" 가설 = `:root` 라이트 토큰 이미 완비로 **거짓 판명**(학습 17 catch). 폰트 토큰 상향(body 16→17 / caption 14→15) + footer dev cruft 제거 + 연결배지 3구분(색+shape+텍스트, WCAG 1.4.1).
- **PR #9 `ca61e1b` — 시스템 건강 카드 + 화재 도움말 반영 + 대비 보정**: 빈 화면 에러카드 → "시스템 정상 작동" 안심 카드(3지표). 타입 SSoT ㄴ안(`SystemHealth` 재사용 + `signal_strength` additive, 신규 필드 난립 X — 학습 16/29). device_status mock=online 고정(실 heartbeat 11주차). 도움말 화재 카드 = 7.1 확정 카피 ① 4단계 **verbatim 교체**. 화재 텍스트 대비 `#FF4444`(3.0:1) → `#CC0000`(~5.2:1).

**페르소나 그물 작동 (학습 17 = AI도 catch 대상)**:
- 화재 카피 페르소나 누수 4건 정정(외치기 제외 / 119 음성신고 전제 제거 / 신고수단 확정수단 우선 / 구조요청 시각·문자 구체화) — 선행 entry에서 회수.
- AI 위임 가정 2회 catch: ① "다크 위주" 테마 가설(실측 거짓) ② 타입 신규 필드 가정 → 기존 `SystemHealth` 재사용으로 교정.

**잔존(여전히 deferred — 본 PR로 미해소)**: 폴러 통합(stats 3중 + announcer 1 + **건강카드 useDevice +1**) / Pretendard self-host / large-text / SR 실청취 / (신규)화재 번호뱃지 대비 ~3:1 발표 전 실측 권고. → 11주차 or 폴리시.

**학습 적용**:
- 학습 14 (카테고리 번호 사전 검증): 적용 — 8.3/7.1 + commit hash(`223d000`/`a615162`/`3544db4`/`ca61e1b`) `git show`·`git log` 실측 대조 후 인용.
- 학습 16/29 (기존 컨벤션·타입 우선): 적용 — `SystemHealth` 재사용 + additive 필드.
- 학습 17 (AI도 catch 대상): 적용 — 위임 가정 2건 실측 반증.
- 학습 18 (웹 머지 후 pull): 적용 — PR #8/#9 머지 후 2회 정상 fast-forward.

**비범위**: 노션/지침 동기화 = 별도 Set(2·3) 이월. deferred 항목 상태 변경 없음(미착수 유지).

**관련 카테고리**: 8 (8.3 B-2~B-4 append) / 7 (7.1 도움말 반영 한 줄 보강) / 20 (docs-only main 직접 push)
**관련 commit**: 코드 PR #8 `a615162`/`3544db4` · PR #9 `ca61e1b` (기 머지) + 본 entry 자체 (`docs/decisions.md` + `docs/decisions-log.md` docs-only)

---

## 2026-07-01 (수) — ML 크리티컬 패스 선작업: dataset 파이프라인 + 4대 버그 fix + YAMNet 예비 학습 성공 (카테고리 33 신설 + 5.1 append + 학습 19 신설)

> 8~10주차 ML fine-tuning 크리티컬 패스 **선작업** 대량 진행. 코드 5 PR(#10~#14) 머지 완료 → 학부생 로컬 예비 학습 성공(test 검증) → 본 entry로 SSoT 반영. 실 파이프라인·학습 = 학부생 로컬(데이터셋 EPERM), repo 안은 합성 더미 관통 검증만.

**배경**: 2026-06-30(HEAD `978af68`, Phase B 완결) ~ 2026-07-01 chunk. ML 데이터셋 파이프라인 부재 → 8주차 fine-tuning 진입 전 크리티컬 패스 선작업으로 착수.

**코드 작업 결과 (5 PR Squash 머지, 카테고리 33.1~33.2 반영)**:
- **PR #10 `de05c7e` — 파이프라인 구축(`ml/pipeline`)**: 01_clips(2,798) → 02 preprocess → 파일단위 split → 03 augment(train만) → 05 조립 + 누수 guards. 원커맨드 `run_all` + manifest.
- **PR #11 `adbf349` — 빈·초단파 클립 가드**: fire_alarm 길이-0 wav 6개(AI Hub S_103)가 augment FFT 크래시 → `MIN_DURATION_SEC=0.1` skip(1차) + augment 진입 가드(2차). 1648→1642. 원본 무수정.
- **PR #12 `cd9c16e` — 원본(source) 단위 group split**: 조각(`_\d{7}$`) 흩어짐 = data leakage → 원본 단위 통째 배정 + 조기 무결성 assert. 누수가드 정상 검출 사건이 근거.
- **PR #13 `01715aa` — YAMNet 학습 골격(`ml/training`) + 05 auto-clean**: frozen backbone + head(131,587 trainable) transfer learning + class_weight balanced 자동 + assemble 05 재생성 전 auto-clean(stale 16797 잔여물 제거).
- **PR #14 `749c4a6` — 02/03 stale auto-clean (학습 19 근거)**: 빈클립 05 부활 재발 → **당초 가설(split이 01 읽음) = git log -L로 no-op 반증** → 진짜 원인(02/03 clean 부재) 재확정 → 05 idiom을 02/03에 일반화.

**예비 학습 성공 (2026-07-01, py3.11+TF2.16, CPU, 카테고리 33.2)**:
- early stopping(best epoch 18). **val_accuracy 0.902 / val_macro_f1 0.856**.
- **test(n=424, 미사용): accuracy 0.887 / macro_f1 0.848** — doorbell f1 0.736 / knock 0.881 / fire_alarm 0.927.
- pre-trained Top-1(초30/노40/화20%) 대비 대폭 상승 → 카테고리 4 fine-tuning 필요성 수치 확정.
- confusion: `doorbell→fire_alarm` 오분류 10건(최다, doorbell 최소 클래스) → 8주차 직접 녹음 보강 예정. **안전 방향 편향**(역방향 화재 놓침 8건뿐).
- 05 실측 배분: **train 11,586 / val 437 / test 424**(계획값과 다름 = source split + train augment + 빈6 제외, 카테고리 5.1).

**미결 3건 등록 (카테고리 33.3)**: ① pitch shift 대상(`KOREAN_SOURCE_MARKERS` 빈 상태, 8주차 전) ② SpecAugment(hub embedding 모드 미적용, logmel 배선 남음, 발표 전) ③ SavedModel export 버그(untracked resource, 11주차 배포 전).

**학습 19 신설 (카테고리 33.4)**: **근본원인 진단 재검증** — 위임의 근본원인 진단(가설)도 코드 SSoT로 재검증, no-op이면 맹목 적용 금지 후 pivot. 학습 17(AI도 catch 대상) 확장. ※ MCP가 "학습 18"로 칭한 번호 충돌을 **학습 19로 정정**(SSoT 학습 18 = PR 웹 머지 후 pull, 별개).

**학습 적용**:
- 학습 14 (카테고리 번호 사전 검증): 적용 — `git show HEAD:docs/decisions.md | grep "^## 카테고리"` 실측(최신=32 → 신규 33 확정) 후 append.
- 학습 17 (AI도 catch 대상): 적용 — PR #10~#14 매핑을 GitHub API 실측 대조(#11/#12 커밋 subject `(#N)` 미표기 → API로 PR 번호 확정).
- 학습 19 (진단 재검증): 본 chunk에서 신설 + 자기 적용(PR #14 no-op 반증 사례).

**비범위**: 노션/지침 동기화 = 별도 Set 이월. deferred 항목(폴러 통합 등) 상태 무변경.

**관련 카테고리**: 33 (신설) / 5 (5.1 append) / 4 (fine-tuning 필요성 수치 확정 연동) / 20 (docs-only main 직접 push)
**관련 commit**: 코드 PR #10 `de05c7e` · #11 `adbf349` · #12 `cd9c16e` · #13 `01715aa` · #14 `749c4a6` (기 머지) + 본 entry 자체 (`docs/decisions.md` + `docs/decisions-log.md` docs-only)

---

## 2026-07-01 (수) Set 1 — SavedModel export 버그 해결 반영 (33.3-③ 클로즈 + 근본원인 정정)

> PoC-(22)에서 미결 33.3-③(SavedModel export untracked resource 버그) 해결. PR #15(`feat/ml-savedmodel-export`) 머지 완료 + 학부생 로컬 실 YAMNet export + reload 추론 검증 통과 → 본 entry로 SSoT 반영.

**PR #15 머지 (`6d9411e`)**: `ml/training/export.py` 독립 엔트리포인트 신설(`python -m ml.training.export`) — **재학습 없이** `best.keras`(head) + frozen YAMNet 합성 → 서빙 SavedModel(`ml/models/yamnet/inference_savedmodel/`, git 미커밋) 산출. 서빙 시그니처 = 입력 `waveform (1, None) float32`(배치 1 고정·단일 클립) → 출력 `(1, 3) float32`(라벨 순서 = `CLASSES` 상속). 방식 = `tf.saved_model.save` → **Keras 3 `model.export()`** 전환으로 미추적 리소스 해소.

**33.3-③ 클로즈 (미결 3건 → 2건)**: ③ SavedModel export 버그 → **✅ 해결(2026-07-01 PoC-(22), PR #15)**. 항목은 이력 보존(학습 8 원본 보존)으로 삭제 없이 해결 표기(strikethrough + 해결 주석). 미결 카운트 3→2 정합(잔여 = ① pitch shift 대상 ② SpecAugment 배선).

**근본원인 정정 (학습 19 정합)**: 당초 전제("frozen hub backbone 변수 미추적")는 방향은 맞았으나 정확한 메커니즘은 **`build_inference_model`(model.py)이 raw `hub.load()` 객체를 Keras `Lambda`(`yamnet_backbone`) 클로저로 캡처 → Lambda가 클로저 trackable을 객체 그래프에 미등록**. `model.export()`의 `ExportArchive`가 서빙 `tf.function`을 트레이스하며 캡처 리소스를 함께 추적·직렬화해 해소. 진단 재검증 후 실측 메커니즘 반영.

**학습 적용**:
- 학습 18/19 (진단 재검증): 적용 — 위임 프롬프트가 기재한 입력 시그니처 `(None, None)`를 코드(`export.py`/`model.py`) 실측으로 재검증 → 실제 `tf.keras.Input(shape=(None,), batch_size=1)` = `(1, None)`로 **정정 후 기재**(코드 SSoT 우선).
- 학습 17 (인계 catch): 적용 — 33.2/33.3 실제 문구를 `git show HEAD:docs/decisions.md`로 실측 인용 후 diff 적용, 카테고리 33 ↔ 학습 19 번호 혼동 방지.

**비범위**: 카테고리 33.1/33.4/5.1/1~32 무수정, ml 코드 무수정(문서 단독). 노션/지침 동기화 = 별도 Set 이월.

**관련 카테고리**: 33 (33.2 체크포인트 정정 + 33.3-③ 클로즈) / 20 (docs-only main 직접 push)
**관련 commit**: 코드 PR #15 `6d9411e` (기 머지) + 본 entry 자체 (`docs/decisions.md` + `docs/decisions-log.md` docs-only)

---

## 2026-07-06 (월) — PoC-(22) 발표 데모 마무리(대시보드 라이트박스 + 알림 속도 실계측 + 데모 시드) + 밀린 정정 5건 (카테고리 3/6.1/8.3/18/19 append)

> PoC-(22) 후속 chunk. 코드 3 PR(#16·#17·#18) 머지 완료(2026-07-06) → 본 entry로 SSoT 반영 + 밀린 정정 5건 동시 회수. 문서 단독(코드 0), main 직접 push.

**A. 신규 반영 (코드 3 PR 기 머지)**:
- **PR #16 `6b26bd6` — 데모 시드 + 더미 이미지** (카테고리 6.1 append): `server/seed.py` 결정론적 5건(초인종 완료/노크 완료/노크 2차 처리중/화재 우회/초인종 미발송) delete→insert idempotent, `detected_at` 동적 오늘. 더미 이미지 = `dashboard/public/static/captures/*.svg`(직접 생성, 저작권·초상권 무관, vite public 서빙). 발표용 완성 UX 확정 렌더(mock random 재현 불가 대체).
- **PR #17 `c25f789` — 알림 사진 라이트박스 + "크게 보기" 힌트 뱃지** (카테고리 8.3 B-5 append): radix Dialog 재사용, 3경로 닫기(X 44px/배경/ESC) + 포커스 트랩·복원 + scroll-lock + `aria-modal`, `object-contain` 무크롭. 힌트 뱃지 = `Maximize2` + "크게 보기" 텍스트 병기(WCAG 1.4.1), caption 15px 노안 상향, `aria-hidden`.
- **PR #18 `d57f3ae` — 데모 마무리(이미지 잘림 수정 + 알림 속도 카드 실계측)**: ① 더미 SVG 가로 2:1 + 세로중앙 safe-zone 재작성 → `object-cover h-40` 무잘림(8.3). ② `_build_stats` `timing_metrics` 하드코딩 0 → **실 타임스탬프 집계**(1차=primary_sent_at−detected_at, 2차=secondary_sent_at−detected_at, 목표 5초/15초 달성률). null 안전(`is not None` 필터) + ZeroDivision 가드, `stats.ts` `TimingMetrics` 6키 1:1(카테고리 6.1). **수정 2곳 한정**(routes.py timing 블록 + seed.py), 타 집계·프론트·타입 무변경. **의의**: 11주차 실 계측 몫 선작업 → 실 하드웨어 유입 시 실값 산출(재사용 코드).

**B. 밀린 정정 5건 회수**:
- 🔴 **신뢰도 임계값 코드 불일치 (미결 등록, 카테고리 3)**: SSoT=0.70인데 `server/app/constants.py:15 CONFIDENCE_THRESHOLD = 0.6` → **코드가 SSoT 위반**. seed는 confidence 명시 세팅으로 `/detect` 임계값 로직 미경유(데모 무영향). 코드 정정(0.6→0.7) = **별도 fix PR 필요**(2026-07-06 미착수) → 다음 서버 코드 작업 우선.
- 🟢 **large-text 실측 정정 (카테고리 8.3, stale→shipped)**: 8.3 잔존 리스트의 "large-text deferred"는 stale. `index.css:160 html.large-text{zoom:1.15}` + `SettingsContext` 토글 + `SettingsPage` 배선 전부 shipped. 문서만 정정(코드 무변경).
- 🟡 **화재 번호뱃지 대비 실측 (카테고리 8.3)**: "~3:1 추정" → **실측 3.41:1**(white on `#FF4444`). WCAG large-text 3:1 충족 / normal-text 4.5:1 미달. 보정안 `#CC0000` = 5.89:1(미착수, 별도 소형 a11y PR 예정). ※ 본문 텍스트는 PR #9에서 이미 `#CC0000` 보정 완료 — 본 건은 번호뱃지 배경 한정.
- **카테고리 18 무거움 신호 6→8 싱크**: decisions.md 카테고리 18에 신호 7(일자 전환)·8(패턴 전환) append(지침엔 이미 8개, decisions.md만 6개로 뒤처짐).
- **카테고리 19 노션 plan 게이트 정정**: `query-data-sources`(SQL)만 Business plan 차단, `notion-search`+`notion-fetch`(by-ID)로 DB row 실 열람·특정 갱신 우회 가능(hand-mirror 불필요) — PoC-(22) Set 3 실측. + update-content old_str 불일치 silent no-op → re-fetch 검증 필수 명시.

**학습 적용**:
- 학습 14 (카테고리 번호·commit 사전 검증): 적용 — 8.3/6.1/3/18/19 실번호 `grep` 대조(프롬프트 추정 전부 일치) + PR #16/#17/#18 커밋 hash `git log` 실측 후 인용.
- 학습 16 (기존 컨벤션·타입 우선): 적용 — `timing_metrics` `stats.ts` 6키 재사용(신규 필드 X), decisions.md append 컨벤션·strikethrough 정정 관용 준수.
- 학습 19 (진단 재검증): 적용 — 문서화 주장(large-text shipped / 대비 3.41:1 / constants 0.6 / 무거움 신호 6개)을 전부 **코드·계산으로 재검증** 후 반영(추정 기재 금지).

**비범위**: 코드 0 수정(위 3 PR은 기 머지, 본 entry는 docs-only). 카테고리 1/2/4/5/7/9~17/20~33 무수정. ML(33.3) 무변경. 신뢰도 코드 정정·화재 뱃지 보정 = 별도 fix PR 이월(미착수).

**append 정합 확인 (자체검증 = 문서라 코드 3단계 N/A, 대신 훼손 0 확인)**: 기존 항목 삭제 0(정정은 strikethrough+주석으로 이력 보존, 학습 8) / 신규는 전부 append / 카테고리 번호 전부 Step 0 실측 기준.

**관련 카테고리**: 3 (신뢰도 임계값 미결) / 6.1 (timing 실계측 + seed 인프라) / 8.3 (라이트박스 B-5 + large-text·화재뱃지 정정) / 18 (무거움 신호 7·8) / 19 (노션 plan 게이트 정정) / 20 (docs-only main 직접 push)
**관련 commit**: 코드 PR #16 `6b26bd6` · #17 `c25f789` · #18 `d57f3ae` (기 머지) + 본 entry 자체 (`docs/decisions.md` + `docs/decisions-log.md` docs-only)

---

## 2026-07-07 (화) — PoC-(24) 결정 3건 코드 반영 클로즈 (신뢰도 임계값 + 화재뱃지 대비 + ML 미결 2건) → decisions.md 4곳 SSoT 정정

> 2026-07-07 PoC-(24)에서 코드 fix 2건 + ML 미결 2건 결정 완료(PR #19/#20/#21 전부 머지). 본 entry로 상태 반영. 문서 단독(코드 0, 위 3 PR은 기 머지), main 직접 push.

**A. 코드 3 PR 클로즈 (기 머지, decisions.md 상태 정정)**:
- **PR #19 `d614370` — 신뢰도 임계값 SSoT 정합** (카테고리 3): `server/app/constants.py:15 CONFIDENCE_THRESHOLD` **0.6→0.7** 정정. 경계 = `utils.py:94 if top < CONFIDENCE_THRESHOLD`(strict) → 정확히 0.70 발송 = "70% 미만 미전송" SSoT(0.70) 정합. 🔴 코드 불일치 → ✅ 해결(strikethrough+append, 학습 8).
- **PR #20 `4f563a2` — 화재 번호뱃지 대비 보정** (카테고리 8.3 B-5): 번호뱃지 배경 `bg-danger`(#FF4444, 3.41:1)→`bg-danger-deep`(#CC0000, **5.89:1**) = WCAG AA normal 4.5:1 충족. 대상 = `NotificationCard.tsx:104`/`HelpPage.tsx:87` 2곳. salience fill #FF4444(animate) 유지. 🟡 미착수 → ✅ 완료.
- **PR #21 `2dd8f9c` — ML 증강 결정 코드 각인** (카테고리 33.3, B 방식=값 추측 0/주석 각인): pitch 대상=직접녹음(`direct_`)만/S_103 제외/실행 defer(마커 `()` 유지+결정 주석, 경고 `warning`→`info`), SpecAugment=embedding 유지/logmel 배선 defer(레이어 보존, `SPECAUG_MODE` 죽은 상수 회피 = 주석만).

**B. decisions.md 정정 4곳**:
- 카테고리 3: 🔴 코드 불일치 strikethrough + ✅ 해결(PR #19) append.
- 카테고리 5: Augmentation pitch 항목에 "한국 환경음" 정의 확정(=`direct_` prefix 직접녹음, S_103 제외) note append → 33.3-① 링크.
- 카테고리 8.3 B-5: 🟡 화재뱃지 "미착수" strikethrough + ✅ 보정 완료(PR #20) append.
- 카테고리 33.3: 헤더 "미결 2건" → "**활성 미결 0건**"(①② 결정 확정·실행 defer / ③ 클로즈). (1)pitch·(2)SpecAugment 각 항목에 🟢 결정 확정 append(기존 미결 설명 보존, strikethrough 아님).

**C. ML 활성 미결 2건 → 0건**: ① pitch + ② SpecAugment 결정 확정(실행 defer). 직접녹음 명명 규칙 = `direct_` prefix 확정. 8주차 직접녹음 유입 시 `config.py` 마커 `("direct_",)` 한 줄 교체로 pitch 활성화.

**SSoT 정합 검증 (문서라 코드 3단계 N/A, 대신 머지 코드↔문서 1:1 실측)**: `constants.py:15 = 0.7` ✓ / `utils.py:94 if top < CONFIDENCE_THRESHOLD`(strict) ✓ / `--danger-deep: #CC0000` + 뱃지 2곳 `bg-danger-deep` ✓ / `config.py:75 KOREAN_SOURCE_MARKERS = ()` ✓ — 문서 기술 전부 실 머지 코드와 일치.

**학습 적용**:
- 학습 14 (카테고리 번호 사전 검증): 적용 — 3/5/8.3/33.3 실번호 `git show HEAD:docs/decisions.md | grep` 실측(36/61/249/1442, drift 0) + PR #19/#20/#21 hash `git log` 실측 후 인용.
- 학습 16 (기존 컨벤션 우선): 적용 — strikethrough 이력보존 관용 준수, `SPECAUG_MODE` 신규 상수 미발명(죽은 상수 회피).
- 학습 8 (원본 이력보존): 적용 — 🔴/🟡 정정 = 물리 삭제 0, strikethrough+append.

**비범위**: 코드 0 수정(3 PR 기 머지, 본 entry docs-only). 카테고리 1/2/4/6~32/33.1/33.2/33.4 무수정. 노션/지침 동기화 = 별도 Set 이월.

**append 정합 확인 (훼손 0)**: 기존 항목 삭제 0(정정=strikethrough+주석, 학습 8) / 신규 전부 append / 카테고리 번호 전부 grep 실측.

**관련 카테고리**: 3 (신뢰도 임계값 클로즈) / 5 (한국 환경음 정의) / 8.3 (화재뱃지 클로즈) / 33.3 (ML 미결 2→0) / 20 (docs-only main 직접 push)
**관련 commit**: 코드 PR #19 `d614370` · #20 `4f563a2` · #21 `2dd8f9c` (기 머지) + 본 entry 자체 (`docs/decisions.md` + `docs/decisions-log.md` docs-only)

---

## 2026-07-08 (화) — PoC-(25) 서버 조기경보 + SP/DTW 개체구분 스파이크 + pretest 8.42 규명 → USP 정량 근거 재정립 (카테고리 6.2 + 33.5 신설)

> 2026-07-08 오늘 완료 3건(A 서버 조기경보 실측 / B DTW 개체구분 스파이크 / C pretest 8.42 포렌식 규명)을 decisions.md에 각인. 코드는 PR #22·#23 기 머지 — 본 entry는 기록(코드 0). 문서 단독, main 직접 push.

**A. 서버 ML 추론 서빙 조기경보 실측 (카테고리 6.2 신설, PR #22 `169a2fc`)**:
- 메모리 peak RSS **489.1MB / 2048MB** 예산 OK(분해: baseline 35.8 → +TF import 375.8 → +YAMNet 51.9 → infer 489.1), **TFLite 불필요**(권고선 1740.8MB 미달).
- 지연 p50 **4.26ms** / p95 **6.74ms** / 5000ms 예산 OK. **★ 1차 ≤5초 병목 = ML 아님** → 실 병목 = ESP32 업로드 + 카카오 왕복(14주차 튜닝 타겟 재조정).
- gunicorn 2워커 preload COW = 1×모델 + 2×오버헤드(2×모델 아님), 2GB 안.
- 🔴 **wire 계약 갭**: `/detect` 오디오 바이트 미수신(mock random) + transport 계약(multipart/base64/raw) 미정의 + int16 가정 firmware 미검증(INMP441 I2S 24/32bit) → **11주차 통합 체크포인트**.

**B. SP/DTW 초인종 개체 구분 스파이크 (카테고리 33.5, PR #23 `086c6da`)**:
- 분리 마진 **1.713**(Cohen's d류) → 권고선 2.0 미달 = **NO-GO/재검토**. intra 0.2601±0.1150 / inter 0.4263±0.0748, 정확도 83.6% / EER 17.5%, 182 원본그룹.
- 🔴 캐비앗: intra=인접조각≠독립 재-누름 = **낙관 상한** → 직접녹음(04) 재검증 필수.

**C. pretest "8.42" 정체 규명 (읽기전용 포렌식, 코드 무변경, 카테고리 33.5)**:
- 8.42 출처 = pretest `step4_dtw_evaluate.py`(`907c950`) = **(B) 클래스 간 분리**(초인종 vs 노크/화재) = 2차 필터 변별력. **USP(개체 간=옆집 구분) 근거로 무효**('같은 집' 버킷도 실제 다른 FSD50K 클립 = 개체 개념 부재).
- 8.42 vs 1.713 **직접 비교 무효**(측정대상·특징 64/128bin·정규화·마진정의 4중 상이 + pretest 마진 정의 부재). 확신도: 측정대상=클래스 간 **높음** / 8.42 산술 재현 **낮음**(repo·git 전체 "8.42" 부재).
- 8.42 폐기 아님 — 위상만 "2차 필터 변별력"으로 재배치.

**★ (B)+(C) 종합 = USP 정량 근거 재정립 (오늘 최대 발견)**: 초인종 개체 구분 = pretest 미검증 확정, 스파이크 1.713(낙관 상한) 권고선 미달 → 직접녹음 90클립 재-누름 intra로 재검증(스파이크 코드 `--clips-dir` 04, 11~12주차). 카테고리 26.3 진입점 2에 USP 정량 근거 상태 note append.

**미결정 신규 등록 (33.5 미결 항목)**: ① USP 정량 근거 재정립(발표 슬라이드 8.42 인용 정정 대상, 개체 구분 재검증 대기) ② 인용 논문 Meliza 2013(PMC3745477) 위상 재검토 ③ **별도 코드 태스크**: `constants.py:25 PRETEST_MARGIN` 오도성 주석("카테고리 근거") → "클래스 간 변별, USP 근거 아님" 정정(본 태스크 문서단독 §7 코드 무수정 → 후속 등록만).

**8.42 처리 방식 (catch 결과 명기)**: `git show HEAD:docs/decisions.md | grep "8.42"` = **0건** → decisions.md에 8.42 원래 부재 = **취소선 정정 대상 없음.** 8.42는 스파이크 코드 `constants.py:25`에만 존재(§7 수정금지) → **취소선 X, 순수 신설 note로 위상 명문화**(학습 19 = 위임 Step 4 "8.42 취소선" 전제가 실측과 불일치 → §9 정지 + AskUserQuestion pivot 승인 후 진행, 날조 회피).

**703 태그 대조 (Step 7)**: decisions.md:703 "노션 plan 게이트 정정 (2026-07-06 **PoC-(22)** Set 3)" ↔ decisions-log 2026-07-06 entry = **PoC-(22)** 일관(894행 "PoC-(22) Set 3 실측") → 태그 정확, **현상 유지**(억지 수정 X).

**SSoT 정합 검증 (문서라 코드 3단계 N/A, 대신 머지 코드↔문서 spot-check)**: `server/inference/constants.py`(`SAMPLE_RATE=16000` / `MEM_BUDGET_MB=2048` / `LATENCY_BUDGET_MS=5000` / `TFLITE_ADVISE_RATIO=0.85`) ✓ / `ml/experiments/dtw_doorbell/`(constants·distance·experiment·features·synth_smoke·README·__init__·tests) 존재 ✓ / 기록 숫자(489MB·6.74ms·1.713·8.42=클래스간)가 실 머지 산출물과 모순 없음 ✓.

**학습 적용**:
- 학습 19 (근본원인 진단 재검증): 적용 — 위임 Step 4 "8.42 decisions.md 취소선" 전제가 grep 0건으로 **실측과 불일치** → 맹목 적용(날조) 금지, §9 정지 + pivot 승인 후 신설 note로 전환.
- 학습 14 (카테고리 번호 사전 검증): 적용 — 6·33 실번호 grep 실측 + PR #22/#23 hash `git log` 실측 후 인용.
- 학습 8 (원본 이력보존): 적용 — 물리 삭제 0(신규 전부 append), 703 태그 억지 수정 X.

**비범위**: 코드 0 수정(PR #22/#23 기 머지 + constants.py 주석은 후속 코드 태스크 등록만, 손대지 않음). docs 2파일(`decisions.md` + `decisions-log.md`)만. 카테고리 1~5/6.1/7~32/33.1~33.4 무수정. 노션 동기화 = 별도 Set 이월.

**관련 카테고리**: 6.2 (서버 조기경보 신설) / 33.5 (DTW 스파이크 + 8.42 규명 + USP 재정립 신설) / 26.3 (진입점 2 USP 근거 상태 note) / 20 (docs-only main 직접 push)
**관련 commit**: 코드 PR #22 `169a2fc` · #23 `086c6da` (기 머지) + 본 entry 자체 (`docs/decisions.md` + `docs/decisions-log.md` docs-only)

---

## 2026-07-09 (수) — PoC-(26) transport A안 확정 + PR #24·#25 wire 하네스 + ToF Stage B(B)판정 + USP 2층 재정립 + 4유닛 프로토콜 (카테고리 6.2/9/26.3/33.5 append + 5.1 append)

> 2026-07-09 오늘 확정 6건(transport A안 / PR #24 디코딩 실증 / PR #25 업로드 하네스[런타임 대기] / 서빙 3결정 / ToF Stage B(B)판정 / USP 2층 재정립 + 4유닛 프로토콜)을 decisions.md에 각인. 코드는 PR #24 `6ab693f` · PR #25 `f0e4163` 기 머지 — 본 entry는 기록(코드 0). 문서 단독, main 직접 push.

**A. transport 계약 A안 확정 + PR #24·#25 wire 하네스 (카테고리 6.2 append)**:
- **A안 확정**: multipart/form-data + int16 PCM raw bytes(64KB/2초). 근거 = 업로드가 1차 5초 병목 후보(6.2)라 페이로드 최소화(base64 +33% 오버헤드 회피) + `audio_decode.py` int16 계약 무수정 정합. → **wire 갭 transport 절반 CLOSE**(나머지 절반 = INMP441 I2S→int16 변환 검증, 마이크 결선 후).
- **PR #24** (`6ab693f`): `/detect` JSON→multipart 교체 + `audio_decode.py`(frozen) 디코딩 실증 — 합성 440Hz 64KB → RMS **0.353528**(이론 0.3536 일치)/decode 0.038ms. curl 회귀 10종 0.
- **PR #25** (`f0e4163`): ESP32 PSRAM 합성 PCM + multipart POST + 지연측정(N=14, ≥6초 간격) 하네스. **컴파일 성공**(RAM 13.5%/Flash 22.2%, Stage 2 트리거 미달). **⏳ 런타임 미실측**(보드 USB 미연결 → compile-only + prereq 체크리스트 핸드오프).
- **서빙 연결 3결정**: (a) 모델 싱글턴 1회 로드 (b) TF venv RSS +375~490MB(6.2 실측) → 11주차 EC2 2GB 재확인+아키텍처 결정 (c) mock_prediction 딕셔너리 매핑. infer 103ms(콜드)≠6.2의 6.74ms(웜) 위상 구분 명시.

**B. ToF Stage B Motion Indicator 노출 확정 (카테고리 9 append, 판정 B)**:
- 래퍼 전용 메서드 0건 → 번들 ULD 함수(`vl53l5cx_motion_indicator_*`) `imager.Dev` 핸들 직접호출. RAM +156B. **⏳ 런타임 = 센서 대기**(브레드보드 결선 후, 학습 15 4단계 중 ③까지 확정). frozen 파일 0 수정.

**C. USP 2층 재정립 (카테고리 26.3 + 33.5 append, ★ 발표 직결)**:
- 옆집 구분 = **2층 구조**: 1차 ToF 사람 존재 검증(카테고리 9, VL53L5CX 단독) + 2차 보조 SP/DTW 오디오 지문(등록 시). 이전 "USP 붕괴"는 SP/DTW **단층 평가 아티팩트** — 8.42 폐기 아님(클래스 간 2차 필터 변별로서 유효), "옆집 구분 주력 근거" 위상만 mislabel이었음.
- 26.3 진입점 2 라벨 정정: `"옆집 초인종 잘못 반응 X" (SP/DTW)` → `(ToF presence 1차 융합 + SP/DTW 보조 2차)`(strikethrough 이력보존).
- **정직 표기**: 양층 런타임 미검증 — ToF presence 설계 견고하나 미측정(브레드보드 후), SP/DTW 1.713 낙관 상한(직접녹음 4유닛 재검증). 위상 = "2층 설계 확정 + 양층 검증 예정"(근거 없음 아님).
- 데모 방향 = ToF presence 리드 시연(우리집=사람+소리→알림/옆집=스피커만·사람없음→억제/등록=SP/DTW 보너스), SP/DTW 4종 라이브 단독 시연 NO(1.713 약함 노출 회피).
- 33.5 미결 항목 ①②를 strikethrough+화살표로 진화(이력보존, 학습 8): ① USP 2층 설계 확정으로 갱신, ② Meliza 2013 위상=보조층 근거로 조정 완료.

**D. 직접녹음 4유닛 프로토콜 확정 (카테고리 5.1 append)**:
- 파일명 확장 `direct_doorbell_{유닛}_{테이크}.wav` — 유닛 식별 없인 재-누름 intra 측정이 구조적으로 불가능(기존 `direct_doorbell_001`은 파일=원본그룹이라 전부 inter로 오분류)했던 문제 해소.
- 4유닛(★ 같은 모델 ×2 필수) × 15~18테이크 ≈ 90클립, inter=C(4,2)=6쌍(같은모델 1쌍+다른모델 5쌍). 3유닛 검토 후 4유닛 확정(1.713 상한 교훈=오염 벤치 회피).

**노션 미러 (Set 3)**: DB1 신규 row(PoC-(26)) + 페이지 상단 메타 콜아웃/오늘 작업/일정표 갱신(re-fetch 검증 통과) + DB3 신규 3건(ToF Stage B 런타임 / 업로드 런타임 / 서빙 3결정 실행) + 기존 "USP 정량 근거 재정립" row 코멘트로 진화(🟡 보류 유지, 트리거 7/27 > D+7).

**학습 적용**:
- 학습 13/14 (카테고리 번호·SSoT 문구 사전 실측): 적용 — 6.2/9/26.3/33.5/5.1 실번호 `git show HEAD:docs/decisions.md | grep` 실측(115/309/1027/1472/78) 후 편집, 26.3 "(SP/DTW)" 라벨 + 7/8 note 실물 grep 확인 후 진행(§9 정지 트리거 미발동).
- 학습 18 (PR 웹 머지 후 로컬 main pull 필수): 무관(본 태스크는 문서 단독, 코드 PR 아님) — 단 PR #24/#25가 이미 머지된 HEAD(`f0e4163`) 위에서 편집 시작함을 `git log` 실측으로 확인.
- 학습 8 (원본 이력보존): 적용 — 26.3 라벨 정정(strikethrough+신규 병기) + 33.5 미결 항목 ①② 진화(strikethrough+화살표), 물리 삭제 0.
- github MCP 인증 이슈(카테고리 18) 참고: 본 entry는 문서 단독 push라 github MCP `create_pull_request` 자체를 호출하지 않음(PR 미생성) — Bad credentials 재현 여부 무관(직전 PR #25 생성 시 `gh` CLI 폴백으로 이미 재현·우회 완료).

**SSoT 정합 검증 (문서라 코드 3단계 N/A, 대신 머지 코드↔문서 spot-check)**: `server/app/routes.py` multipart 파싱 + `AUDIO_FILE_FIELD`/`AUDIO_MAX_BYTES` 상수(PR #24) ✓ / `firmware/platformio.ini` `[env:upload_spike]` whitelist + `firmware/src/upload_spike_*.cpp`(PR #25) ✓ / 기록 숫자(RMS 0.353528·RAM 13.5%·Flash 22.2%·RAM+156B) 실 머지 산출물과 모순 없음 ✓.

**비범위**: 코드 0 수정(PR #24/#25 기 머지, 본 entry docs-only). 카테고리 1~4/5(위 append 제외)/6.1/7/8/10~25/27~32/33.1~33.4(위 append 제외) 무수정. secrets/개인정보 실값 미기록.

**관련 카테고리**: 6.2 (transport A안 + PR #24·#25 + 서빙 3결정 append) / 9 (ToF Stage B 판정 append) / 26.3 (진입점 2 라벨 정정 + USP 2층 note) / 33.5 (USP 2층 재정립 신설 + 미결 항목 진화) / 5.1 (direct_ 파일명 확장 + 4유닛 프로토콜 append) / 20 (docs-only main 직접 push)
**관련 commit**: 코드 PR #24 `6ab693f` · #25 `f0e4163` (기 머지) + 본 entry 자체 (`docs/decisions.md` + `docs/decisions-log.md` docs-only)

---

## 2026-07-28 (화) — PoC-(27) ESP32 업로드 지연 런타임 실측 (⏳→✅, 인계 미검증 2건 중 ①번 해소) → 카테고리 6.2 SSoT 반영

### 결정 진화 (카테고리 6.2, PR #25 line 127)
- **⏳ 런타임 미실측 → ✅ 런타임 실측 완료** (strikethrough+append, 학습 8 이력보존). PR #25 하네스(합성 int16 PCM multipart POST)를 실보드에서 구동.
- 실측 환경: XIAO ESP32-S3 + iPhone 핫스팟(2.4GHz, RSSI -45dBm) + Flask 로컬(172.20.10.3:5000, M4), 서버=mock 추론, transport=multipart+int16 64KB.
- 수치: Phase1 64KB×14 = min156/p50 305/p95 1043/max1879ms, 201 14/14. Phase2 스윕 32/64/128KB avg 95.7/318.3/358.0ms(크기 2배여도 미미=무선 오버헤드 지배). Phase3 분해 connect 270/post 279/total 549 = **TCP 연결이 지연 절반**. iter11~13 튐(1879/1043/640)=핫스팟 무선 간헐 스파이크.
- **판정**: 1차 5초 예산 대비 p95 1043ms = 20%, 업로드 병목 아님. 인사이트: TCP connect가 지연 절반 → keep-alive 재사용 시 절감 여지(14주차 타이밍 튜닝 타겟).

### prereq 배선 6단계 확립
- 핫스팟 IPv6 off로 IP 정상화 / 2.4GHz 재방송 등 6단계로 런타임 실행 경로 확립.

### 학습
- **인계 IP 하드코딩 가변성 실증**: 랩실 192.168 → 핫스팟 172.20 전환으로 IP 하드코딩의 환경 의존성 실측 확인.

**SSoT 정합 검증 (문서라 코드 3단계 N/A)**: 전제 문구 "⏳ 런타임 미실측"을 `git show HEAD:docs/decisions.md | grep` line 127 실측 hit 후 편집(§9 정지 트리거 미발동). 카테고리 6/20 실번호 실재 확인. 로그 원본 = repo 밖 `ddingdong-측정결과/upload_spike_2026-07-28.txt`(SSoT엔 요약만, 원본 미커밋).

**비범위**: 코드 0 수정(PR #25 기 머지, frozen 하네스 import/read만). `docs/decisions.md`(line 127) + `docs/decisions-log.md`만 편집. 인계 미검증 2건 중 ②번(ToF Stage B 등)은 별도.

**관련 카테고리**: 6.2 (업로드 지연 실측 append) / 20 (docs-only main 직접 push)
**관련 commit**: 코드 PR #25 `f0e4163` (기 머지) + 본 entry 자체 (`docs/decisions.md` + `docs/decisions-log.md` docs-only)

---

## 2026-07-29 (수) — 카카오 memo 왕복 실측 (마지막 미측정 구간 CLOSE) → 1차 5초 체인 전 구간 실측 완성 (카테고리 7.2 신설 + 6.2 합산 판정)

### 신설 (카테고리 7.2)
- **카카오 memo(나에게 보내기) default/send 왕복 실측**: **p95 84.1ms / p50 69.2 / min 51.4 / max 93.0 / avg 67.8**, 성공 **10/10**(http 200 + result_code 0). 웜(keep-alive) p50 67.8/p95 72.8, 콜드 93.0 → 절감 25.2ms. 연결분해(무발송 소켓 프로브) dns 38.4/tcp 7.1/tls 20.8 = conn 66.3ms.
- 조건: 학부생 로컬 M4 → kapi 서울, 텍스트 memo N=10 간격 2s. 하한 성격이나 EC2 서울 리전 유사 조건. 2차 이미지 memo 별개·미측정.
- 하네스 = repo 밖 커스텀 스크립트(연결분해는 메시지 미발송 프로브 → N=10 도배 예산 무소모). 로그 원본 = repo 밖 `ddingdong-측정결과/kakao_memo_2026-07-29.txt`.

### 결정 진화 (카테고리 6.2 append)
- **1차 5초 체인 전 구간 실측 완성**: 업로드 p95 1043(7/28) + 디코딩 0.04(PR #24) + 추론 웜 6.74(PR #22) + 카카오 84.1(7/29) = **합산 p95 ≈ 1134ms = 예산 23%**, 잔여 ≈3.87초. **판정: 동기 발송 충분, 비동기 발송 아키텍처 불필요.** 실질 병목 = 업로드 단독(체인 92%).
- 6.2 기존 "실 병목 = 업로드 + 카카오 왕복" 서술에 ※ cross-ref 1줄 정정(이력보존, 원문 무삭제): 카카오 84.1ms → 병목은 업로드 단독.
- "카카오 왕복 = 유일 미측정 구간" **CLOSE** — 업로드(7/28)·디코딩(PR #24)·추론(PR #22)에 이어 마지막 구간 해소.

### 인프라/보안
- **카카오 OAuth 토큰 발급 절차 뚫음**: 액세스 토큰 발급 경로 확립, 토큰은 로컬 secrets(gitignored/env)로만 관리 — 코드·로그·문서·commit 어디에도 값 미기록.
- **시크릿 rotate 완료**: 측정 후 노출면 최소화 차원 rotate 수행.

**SSoT 정합 검증 (문서라 코드 3단계 N/A)**: 카테고리 6.2/7 실번호를 `git show HEAD:docs/decisions.md | grep -nE "^## 카테고리|^### "`로 실측 확정(117행/132행) 후 편집. 정정 대상 문구 "실 병목 = ESP32 오디오 업로드(네트워크) + 카카오 발송 왕복" grep 실존 hit(122행) 후에만 cross-ref 추가(§9 정지 트리거 미발동). 인용 수치 전건 = 측정 로그 원본 직접 read 대조(프롬프트 참고값과 일치, 소수점 실측 우선).

**비범위**: 코드 0 수정(server/firmware frozen 미접촉). `docs/decisions.md`(7.2 신설 + 6.2 append + 122행 cross-ref) + `docs/decisions-log.md`만 편집. 측정 스크립트·결과 repo 밖 유지(미커밋). 토큰/시크릿 값 미기록.

**관련 카테고리**: 7.2 (카카오 왕복 실측 신설) / 6.2 (5초 체인 합산 판정 append + 병목 서술 정정) / 20 (docs-only main 직접 push)
**관련 commit**: 본 entry 자체 (`docs/decisions.md` + `docs/decisions-log.md` docs-only, PR 없음)

---

## 2026-07-29 (수) — PoC-(29) HTTPS(TLS) 업로드 재실측 런타임 완료 (⏳→✅) + 서빙 b-1 확정 + core/pio 실측 정합 주석 (카테고리 6.2)

### 실측 (카테고리 6.2 HTTPS 하네스 ⏳→✅)
- **Δ_TLS(tls_handshake) p50 678 / p95 862ms**. secure_connect(TCP+TLS) p50 720/p95 882 vs 평문 TCP connect p50 48/p95 245. post(64KB) p50 917/p95 1105. **total(conn+post) p50 1677 / p95 1863ms**. 성공 14/14 + HTTP 200 14/14, heap 최저 워터마크 244,616B(리셋 0회).
- **세션 재개 없음**: Phase 2 back-to-back tls_hs ~695ms = 콜드와 동일 → connect마다 fresh 핸드셰이크(context7 정합). cipher = `TLS-ECDHE-ECDSA-WITH-AES-256-GCM-SHA384`(F4 cert 실반영), 측정 = TLS 1.2/2-RTT(core 2.0.17 mbedTLS 2.28.7).
- 조건: iPhone 핫스팟 RSSI -37 + 로컬 tls_probe_server.py(M4, ECDSA P-256 self-signed). 프로덕션 가산 = 2-RTT×EC2_RTT(~15ms)+DNS 1회 ≈ +50ms → 추정 total p95 ≈ 1.9초.
- **★ 판정: TLS 켜도 1차 체인 총합 p95 ≈ 2.0초 = 예산 40% — 동기 발송 충분, keep-alive 필수 아님**(콜드 862ms 매 이벤트 물어도 예산 내). 7/28 HTTP total 1043 대비 Δ +820ms = TLS 핸드셰이크분. 로그 원본 = repo 밖 `ddingdong-측정결과/upload_spike_tls_2026-07-29.txt`. PR #26 `ca19230` 머지.

### 결정 (카테고리 6.2 (b) 서빙 아키텍처)
- **b-1 웹프로세스 상주 확정**: gunicorn preload + ModelRunner 싱글턴 상주(COW 공유). 근거 = 실측 RSS 489MB=2GB의 24%(분리 압박 없음) + 추론 웜 6.74ms(IPC 분리 이득 0) + 졸작 규모에 b-2 오버엔지니어링. ⚠️ 트리거 = 11주차 EC2(t3.small) 실측 RSS 예산 초과 시 b-2 재검토. chunk 2(/detect 실 서빙 통합) 선행 게이트 해소.

### 정합 주석 (첫 턴 catch)
- **core 버전**: firmware core = Arduino-ESP32 2.0.17 / mbedTLS 2.28.7 — "v3.20017"은 PIO 패키지 버전 문자열(3.20017.241212)이며 core 3.x 아님(레거시 driver/i2s.h 의존 = 2.0.x 확정).
- **pio 경로**: `~/.platformio/penv/bin/pio` 절대경로 실행(PATH 미등록, 7/28·7/29 재현).

**SSoT 정합 검증 (문서라 코드 3단계 N/A)**: 6.2 위치(117행) + "★ 1차 5초 체인 전 구간 실측 완성"(130행) + (b) 열린 문구 "웹프로세스 상주 vs 별도 서빙 프로세스"(129행) + "⏳ 런타임 미실측"(131행) 전건 `git show HEAD` grep 실존 hit 후 append(§9 정지 트리거 미발동, 학습 14).

**비범위**: 코드 0 수정(docs 2파일만). 측정 로그 원본 repo 밖 유지(미커밋). 토큰/IP/비번 미기록. 이력보존 = 기존 ⏳ 문구 취소선 없이 ✅ append.

**관련 카테고리**: 6.2 (HTTPS 실측 ⏳→✅ + b-1 확정 + core/pio 주석) / 20 (docs-only main 직접 push)
**관련 commit**: 코드 PR #26 `ca19230`(기 머지) + 본 entry 자체 (`docs/decisions.md` + `docs/decisions-log.md` docs-only, PR 없음)

---

## 2026-07-31 (금) — PoC-(30) 2차 enrich wire 계약 서버 절반 + /detect 실추론 배선(pivot) + detected_at 정의 확정 (카테고리 6.2/6.1)

### 구현 (카테고리 6.2 append)
- **2차 /enrich wire 계약 서버 절반 착수 (PR #27 `fccde75`)**: JSON→multipart 교체, 이미지·오디오 파트 둘 다 required. `IMAGE_FILE_FIELD="image"`/`IMAGE_MAX_BYTES=512000`(abuse/메모리 가드 전용, 해상도 무관) 신설 + `AUDIO_*` 재사용. 이미지 검증 = 크기+SOI 매직바이트(0xFFD8), 오디오 = 프로즌 `audio_decode.py` 재사용 디코딩. curl 15종 회귀 0. mock 상태전이 커밋(image_url/stt/enrich_status/secondary_sent_at) — 실 카카오 업로드/Clova STT는 11주차 defer. → 2차 15초 체인 계약 토대, 나머지 절반(ESP32 이미지/오디오 전송 펌웨어)은 마이크·카메라 결선 후.
- **/detect 실추론 배선 (PR #28 `a0b87a2`)**: `mock_prediction()` → `ModelRunner` 싱글턴(프로즌 `model_runner.py` import) 실추론 교체. env 게이트 `DDINGDONG_MODEL_PATH`(부재 시 mock 유지) + TF lazy import + 실추론 모드 TF 부재 시 fail-fast. warmup = app factory 기동 1회(요청당 3.66s 로드 회피) — gunicorn preload+COW 최적화는 11주차 배포 defer(dev 단일프로세스라 검증 불가).

### ★ pivot (§9 정지 후 승인)
- 위임 초기 가정("threshold 게이트가 routes.py 예측 뒤")이 실측으로 반박됨 — 판정 로직(threshold 비교/fire_alarm 우회/ToF mock/primary_sent·enrich_status·skip_reason 결정)이 `mock_prediction()`(utils.py) 안에 랜덤 생성과 응집돼 "예측값만 교체" 불가 확인. → `_apply_prediction_policy()` 순수 추출(로직 무변경, 리팩토링 전후 500시드 mock 반환 dict 바이트 동일 증명)로 mock/real 경로 공유하는 pivot 승인. `CONFIDENCE_THRESHOLD=0.7`·strict 경계 불변. 학습 19 사례(위임 근본원인 진단도 코드 재검증) 추가.
- **⏳ real 모드 미검증**: 로컬 TF 미설치 환경이라 로직만 검증(합성 (1,3) 점수 3종 → pending/skipped 분기 + fail-fast 실증). 실 SavedModel warmup 로그 + real curl = 학부생 로컬 M4 venv 검증 대기.

### 결정 (카테고리 6.1 append — detected_at 정의)
- **detected_at 시작점 = ESP32 트리거 시각 확정**: `timing_metrics` 1차 지연(`primary_sent_at − detected_at`)의 detected_at = 소리 감지(ESP32 트리거) 시각, 서버 수신 시각 아님. ※ decisions.md SSoT에 미결로 등록된 적이 없어(114행은 기존 완료 서술) **취소선 위상이동이 아닌 순수 신규 결정으로 append**(§9 정지 사유, 학부생 승인 후 진행). 근거 = 청각장애인 체감 정직 반영 + HTTPS 포함 전체 체인 p95 ≈2.0초(카테고리 6.2)라 5초 예산에 3초 여유 = 달성률 손실 0. 구현(ESP32 타임스탬프 동봉 + NTP 시계 동기화)은 11주차 defer, 현재는 정의만 확정.

**SSoT 정합 검증 (문서라 코드 3단계 N/A)**: 6.2 실번호(117행)·append 지점(133행, HTTPS/실추론 정합 주석 마지막 줄) `git show HEAD` grep 실측 확정. detected_at은 `grep "detected_at"`/`grep "미결"` 전건 확인 결과 미결 문구 부재 확인 → §9 정지 트리거 ② 발동, AskUserQuestion으로 학부생 승인(옵션: 취소선 없이 순수 신규 결정 append) 받은 뒤 진행. decisions-log 포맷 = 직전 2개 엔트리(PoC-(28)/(29)) 동형 확인 후 작성. PR #27/#28 번호 = `git log --oneline -10`으로 커밋 해시 대조 실측.

**비범위**: 코드 0 수정(docs 2파일만, server/firmware frozen 미접촉). PR #27/#28은 기 머지된 코드 변경 인용일 뿐 본 entry에서 재수정 없음.

**관련 카테고리**: 6.2 (enrich 계약 + 실추론 배선 append) / 6.1 (detected_at 정의 신규 결정) / 20 (docs-only main 직접 push)
**관련 commit**: 코드 PR #27 `fccde75` + PR #28 `a0b87a2`(기 머지) + 본 entry 자체 (`docs/decisions.md` + `docs/decisions-log.md` docs-only, PR 없음)

---

## 2026-07-31 (금) — PoC-(30) 후속: D real 검증 완료 + E 이미지 memo 실측 + 카테고리 7 정정 + 7.3 신설 + numpy 규명 (카테고리 6.2/7)

### 실측 (카테고리 6.2 real 검증 ⏳→✅)
- **`/detect` real 모드 로컬 검증 완료**: 학부생 로컬 M4, Python 3.11 별도 venv(`server/venv_real`, 기존 `server/venv`=3.14는 TF wheel 부재로 real 불가)에서 `make_dummy_savedmodel` 더미 SavedModel + `DDINGDONG_MODEL_PATH` 기동 → real 추론 경로 실증. curl `/detect`(합성 int16 64KB) → HTTP 201 + `all_scores` 합=1.00(doorbell 0.37/knock 0.46/fire_alarm 0.17) + confidence 0.46<0.7 → `skip_reason=low_confidence`+`primary_sent=false`(`_apply_prediction_policy` threshold 게이트 real 경로 작동 확인) + `enrich_status=skipped`. "로직 검증 + real 런타임 대기" → "**real 경로 로컬 검증 완료**"로 정직 승격(학습 19).
- **`model_serving.py` frozen 등록 확정**: real 검증 통과로 후보 → 확정(라이브 앱 import 호출만, 파일 무수정 대상 편입).
- **numpy 버전 규명**: `numpy==2.5.1` 핀(PR #24 `6ab693f`) = `server/venv`(Python 3.14) 당시 최신 안정값을 그대로 하드핀한 **우연값**(버전 근거 커밋 없음). 라이브+프로즌 numpy 사용처 전수 = 2.0 breaking API 의존 0. `venv_real`(numpy 1.26.4)에서 프로즌 4종 실행 + `audio_decode` RMS 0.353528 비트 일치 실증(학습 15) → **1.26.4 안전 확정**. `requirements.txt`는 이번 미수정(무수정 원칙) — `numpy>=1.26,<3` 완화는 [미결] 11주차/소액 PR로 등록.

### 실측 (카테고리 7 이미지 memo — 신설 7.3)
- **카카오 이미지 업로드 API 부재 확인**: 카카오톡 메시지 API(나에게 보내기)엔 이미지 파일 업로드 엔드포인트가 **없다**. memo 3종 전부 이미지를 `content.image_url`(사전 호스팅 public URL 문자열)로만 수신 — 바이트 미통과, 스코프는 `talk_message` 단일(텍스트와 동일, 추가 동의 불필요). 카테고리 7 "이미지: 카카오 이미지 업로드 API (S3 불필요)" 서술을 **취소선 + 정정 append**로 이력보존(학습 8) — 진실 = 서버(11주차 EC2)가 이미지를 스스로 public 호스팅해야 함.
- **7.3 신설 — 이미지 memo 왕복 실측**: `feed/default/send` × image_url 3스윕(40.5/97.3/200.4KB) × N=10, 성공 30/30. p95 = 487.9/461.3/485.3ms, **크기 민감도 없음**(스프레드 26.6ms) → 카카오 발송 시점 동기 fetch 안 함. 절대값(텍스트 84.1ms 대비 5~6배)은 로컬 WiFi 노이즈 섞인 근사치로 정직 표기(학습 19). **함의: 2차 15초 체인에서 카카오는 병목 아님** — 남은 리스크 = ① 이미지 public 호스팅(11주차 arch) ② Clova STT 왕복(미측정) ③ ESP32 2차 페이로드 업로드(미측정).

**SSoT 정합 검증 (문서라 코드 3단계 N/A)**: 정정 대상 문구(카테고리 7 "카카오 이미지 업로드 API" line 146 / 6.2 "real 모드 미검증" line 138) `git show HEAD:docs/decisions.md | grep` 실존 hit 확인 후에만 취소선 처리(§9 트리거 미발동, 학습 8/14). 카테고리 6/6.2/7/7.2 실번호 = `grep -nE "^## 카테고리|^### "`로 실측 확정 후 편집. 인용 수치(real curl 응답값·이미지 memo p95·numpy RMS) = 선행 세션(D-후속/E) 산출값 그대로 인용, 재측정 없음.

**비범위**: 코드 0 수정(`server/*`/`firmware/*`/`ml/*` 전부 read only). `docs/decisions.md`(카테고리 7 정정 + 7.3 신설 + 6.2 append 4건) + `docs/decisions-log.md`만 편집. 브랜치 없이 main 직 push(카테고리 20, 문서 단독). 토큰/시크릿 미기록. 지침·노션 갱신 없음(Set 2·3 별도).

**관련 카테고리**: 7 (이미지 업로드 API 정정) / 7.3 (이미지 memo 왕복 신설) / 6.2 (real 검증 완료 + frozen 확정 + numpy 규명 + 미결 등록)
**관련 commit**: 본 entry 자체 (`docs/decisions.md` + `docs/decisions-log.md` docs-only, PR 없음)

---

## 2026-08-02 (일) — PoC-(32) A-2 이미지 호스팅 스켈레톤 + numpy/stale 미결 해소 + STT 제품 통합 발견 (카테고리 6.2/7)

### 반영 (카테고리 7 — A-2 이미지 public 호스팅 스켈레톤)
- **서버측 스켈레톤 실코드화 완료 (PR #29 `c30e728`)**: 기존 "서버 자체 public 호스팅 필수(image_url)" 정정에 이어, opaque capability URL(추측불가 랜덤 키, `notification_id` 미유래) + 비인증 서빙 라우트(카카오 lazy fetch가 비인증이라 인증 붙이면 깨짐, 유일 게이트 = opaque 키 + traversal 화이트리스트) + TTL 72h(lazy fetch라 짧게 못 잡음, cleanup 헬퍼 미스케줄) + 로컬 FS 단일 concrete(11주차 EC2 static/오브젝트 스토리지 교체 지점)로 실코드화. 로컬 라운드트립 실증(enrich→image_url→GET 200 바이트 일치). ★ 실 public 호스팅 제품(EC2 static vs 오브젝트 스토리지) 확정은 여전히 11주차 미결 — 스켈레톤 완료지 호스팅 방식 확정 아님.

### 해소 (카테고리 6.2 — 미결 2건, PR #30 `50995ba`)
- **numpy 핀 완화**: `[미결 신규] numpy==2.5.1 핀 완화` 문구를 취소선 처리하고 해소 append. `numpy==2.5.1` → `numpy>=1.26,<3` 완화 반영. 임시 venv install 검증(해석 버전 회귀 0 + `audio_decode` RMS 0.353539 재현) 통과.
- **inference stale 정정**: `[소액 정정 후속] server/inference/README.md + __init__.py stale 문구` 문구를 취소선 처리하고 해소 append. `routes.py`/`model_serving.py` 실 import 근거로 "더 이상 standalone 아님" 현행 정정 완료.

### 발견, 결정 아님 (카테고리 7 — STT 제품 통합)
- **note append (취소선 없음)**: 2026-08-02 콘솔 화면 catch + 공식 안내 확인 — 네이버가 CSR 기능을 CLOVA Speech로 통합 제공 안내. CSR 문서(User Guide 14/FAQ 6)는 잔존하나 신규 이용이 CLOVA Speech로 유도되는지 불명. ∴ STT 제품 선택(CSR 유지 가능 여부 vs CLOVA Speech 전환) 재검토 필요 — 11주차 서버 연동 전 확정. A-1 STT 왕복 실측은 제품 결정 후 defer. **제품 전환·확정 결정은 이번 태스크 범위 아님**(미결정 상태 그대로 기록만).

**SSoT 정합 검증 (문서라 코드 3단계 N/A)**: 취소선 대상 2건(numpy 미결/stale 미결) `git show HEAD:docs/decisions.md | grep` 실존 hit 확인 후 처리(학습 19, 없는 문구 취소선=날조 회피). 카테고리 6/6.2/7 실번호 = `grep -nE "^## 카테고리|^### "`로 실측 확정. PR 해시(#29 `c30e728`/#30 `50995ba`) = `git log --oneline -5` 대조 실측. STT는 결정 아닌 발견으로만 표기(제품 확정 문구 금지).

**비범위**: 코드 0 수정(`server/*`/`firmware/*`/`ml/*` 전부 read only, PR #29/#30은 기 머지된 코드 변경 인용). `docs/decisions.md`(카테고리 7 append 2건 + 6.2 취소선+해소 2건) + `docs/decisions-log.md`만 편집. 브랜치 없이 main 직 push(카테고리 20, 문서 단독). 토큰/시크릿 미기록.

**관련 카테고리**: 7 (A-2 이미지 호스팅 스켈레톤 완료 + STT 제품 통합 발견 note) / 6.2 (numpy 핀 완화 + inference stale 미결 해소)
**관련 commit**: 코드 PR #29 `c30e728` + PR #30 `50995ba` + venv_real gitignore `5e8da96`(기 머지) + 본 entry 자체 (`docs/decisions.md` + `docs/decisions-log.md` docs-only, PR 없음)

---

## 2026-08-03 (월) — PoC-(33) STT CSR 유지 확정 + DTW 유닛 그룹핑 모드(PR #31) 해소 + 라벨 오기 정정 (카테고리 7/5.1)

### 결정 (카테고리 7 — STT 제품 = CSR 유지 확정)
- **note → 결정 승격 (취소선 없이 append, 2026-08-02 통합 발견 note 원문 보존)**: 2026-08-02 "CSR→CLOVA Speech 통합 발견, 재검토 필요" note의 재검토 결론 = **CSR 유지 확정**. 근거 3 — ① NCP 콘솔 `AI·Application Service > AI·NAVER API > Application` 등록 화면에서 CSR 신규 선택 가능 확인(학부생 화면 catch, 학습 13 화면 우선) ② CSR 스펙(16kHz 이상·60초·REST 파일 업로드)이 우리 용도(5초/16kHz mono) 정합 ③ 통합 배너 ≠ 종료 공지. 폴백 = CLOVA Speech 단문인식(REST 60초 동일 패턴), gRPC 스트리밍은 이질적 프로토콜이라 후순위. ⚠️ **A-1 STT 왕복 실측 = 미실측(defer, 학습 19)** — 제품 결정으로 언블록됐으나 실측 자체는 미수행, 선행 = CSR Application 생성 + Client ID/Secret 발급(학부생 몫).
- **요금 정정 (30.9 취소선+append)**: 기존 "초당 0.5원/분당 30원" ↔ 현행 CSR 요금 ≈ 15초당 4원(2026 KR 요금표) 불일치 발견 → 취소선+현행값 정정. 저빈도라 기본 크레딧 100,000원 안전 수렴 결론은 불변, 실 과금 사용량 catch는 11~12주차 defer.

### 해소 (카테고리 5.1 — DTW 스파이크 유닛 그룹핑 미결)
- **"DTW 스파이크에 유닛 그룹핑 모드 추가 필요" 취소선 + 해소 append (PR #31 `a332343`)**: 자동 `direct_` prefix 분기(KOREAN_SOURCE_MARKERS 컨벤션 정합) 추가 → `--clips-dir 04` 재실행만으로 재-누름 intra 측정 가능. 회귀 근거 = 01_clips 436→182 그룹 불변 + 멤버십 sha256 before==after 동일(1.713 재현성·비교가능성 보존) + 단위테스트 19/19, 마진 공식·거리·정규화·출력 무변경. ⚠️ **04=0이라 실 개체 마진 미산출**(그룹핑 로직+회귀 검증까지만) — 실측 = 직접녹음 유입 후 defer(학습 19).

### 정정 (라벨 오기 — 취소선 없이 문자열 교체)
- **2026-08-02 세션 라벨 `PoC-(31)` → `PoC-(32)`**: `decisions.md` 3곳(numpy 해소/stale 해소/A-2 스켈레톤) + `decisions-log.md` 헤더 1곳 = 총 4곳. 내용·해시(#29 `c30e728`/#30 `50995ba`)·PR 번호 전부 정확했고 **세션 번호 라벨만 오기**라 취소선 불필요(단순 문자열 교체, 학습 8 이력 훼손 아님).
- ⚠️ **시퀀스 관찰(학부생 확인 요망)**: 정정 후 PoC 카운터 = …(30)×2 07-31 → **(32)** 08-02 → **(33)** 08-03. (28) 결번은 기존부터 존재, 본 정정으로 (31)도 결번화. PoC 번호는 학부생이 관리하는 세션 카운터라 repo 단독 진위 확정 불가 — 위임 명시 지시(단순 오기)대로 적용했으나 실제 카운터와 대조 권장.

### 부속 (하드웨어)
- **브레드보드 830핀 주문** (2026-08-03) — 내일(2026-08-04) 도착 예정. 회로 사전 배선 준비. (실물 도착·배선 실측은 도착 후 별도 entry.)

**SSoT 정합 검증 (문서라 코드 3단계 N/A)**: 취소선/정정 대상 문구 전건 `git show HEAD:docs/decisions.md | grep` 실존 hit 확인 후 처리(학습 19, 없는 문구 취소선=날조 회피) — CSR note(148-149)/유닛 그룹핑(82)/요금(1375)/PoC-(31) 3곳 실측. 카테고리 7·5.1 실번호 = `grep -nE "^## 카테고리|^### "`로 확정. PR 해시(#31 `a332343`) = `git log --oneline -5` 대조 실측. PoC-(32) 미존재 = 중복 위험 없음 grep 확인. 미실측 항목(A-1 STT 왕복 / 실 개체 마진)은 defer로 정직 표기.

**비범위**: 코드 0 수정(`server/*`/`firmware/*`/`ml/*` 전부 read only, PR #31은 기 머지된 코드 변경 인용). `docs/decisions.md`(카테고리 7 결정 승격 + 30.9 요금 취소선+정정 + 5.1 취소선+해소 + PoC 라벨 3곳) + `docs/decisions-log.md`(라벨 헤더 1곳 + 본 entry)만 편집. 브랜치 없이 main 직 push(카테고리 20, 문서 단독). 토큰/시크릿/계정 개인정보 미기록.

**관련 카테고리**: 7 (STT CSR 유지 확정 + 요금 정정) / 5.1 (DTW 유닛 그룹핑 PR #31 해소)
**관련 commit**: 코드 PR #31 `a332343`(기 머지) + 본 entry 자체 (`docs/decisions.md` + `docs/decisions-log.md` docs-only, PR 없음)

---

## 2026-08-07 (금) — PoC-(34) ToF 브레드보드 브링업 **성공** + 근본원인 규명 + 실측 핀맵 SSoT 반영 (카테고리 2/9.1)

### 결정 (카테고리 9.1 — 브레드보드 브링업 실측 확정, 신설)
- **2026-08-06~07 이틀 브링업이 2026-08-07 성공**: `env:tof_dummy` 런타임 로그로 `VL53L5CX ready (8x8, 15Hz, continuous)` + `frame #1/#31 (64 zones)` + heap 실측 확정. 카테고리 9에 **9.1 절 신설**로 전문 기록(성공 로그 verbatim / 근본원인 / 실측 핀맵 / 결선 6가닥 / 하네스 2종 / 소거 표 / 미결 2건).
- **★ 근본원인 = PWREN/LPn 미구동**: 두 핀이 HIGH로 구동되지 않으면 센서가 셧다운 상태로 남아 **SDA를 LOW 고착** → I2C START 불성립 → 어떤 핀 조합으로도 0x29 ACK 부재. 단일 원인 확정. 근거 = DS13754("LPn logic1 → I2C comms") / AN5717(PWR_EN=레귤레이터 enable) / UM2884 §4.1(LPn=High, I2C_RST=0), 각 15단어 이내 인용.
- **SATEL 실측 핀맵 정정**: `B30=SDA/B31=SCL/B33=PWREN/B34=LPn/B35=IOVDD/B36=GND`(삼각형 마커=36). 뒷면 실크 단일 열 판독은 오독 — AN5717 Table 1 = **9핀 커넥터 2개** 구조로 정정. 최종 결선 6가닥 표를 재현용 SSoT로 기록.
- **카테고리 2 핀 표 확장**: 기존 SDA/SCL 2행 무수정(실측 일치=SSoT 유지) + **PWREN/LPn 2행 추가** + PWREN/LPn HIGH 미구동 시 SDA LOW 고착 note 추가.

### 방법론 산출 (진단 하네스 2종 — 기 머지 코드 인용)
- **PR #32 `env:tof_pinscan`(`06e671f`)**: GPIO 순서쌍 110개 전수 I2C ACK 스캔(수동 순회 대체).
- **PR #33 `env:tof_lineprobe`(`601937d`)**: **멀티미터 없이 전원·배선 실측**하는 수단 확립. ★ 2회 대조 실험(SATEL 연결/분리)이 "LOW 출처=SATEL측" 격리의 결정타 → XIAO·브레드보드 결백 증명.

### 해소 (33.5-③ — constants.py:25 오도성 주석)
- **`constants.py:25` `PRETEST_MARGIN` 주석 정정 미결 취소선+✅ 해소**: `git show HEAD:ml/experiments/dtw_doorbell/constants.py` 실측 = 주석이 이미 "클래스 간 변별(pretest), USP 개체구분 근거 아님"으로 정정 완료 상태. 코드는 이미 SSoT 정합, **문서만 미표기였던 stale** — 본 커밋으로 해소(별도 코드 PR 불필요).

### 정정 (1MHz 서술 — 취소선 없이 cross-ref append)
- **카테고리 12①/14-2/16.1의 "I2C 1MHz" 3곳에 실측 cross-ref append**(원문 보존): 브레드보드+20cm 점퍼 환경 **400kHz로 15Hz 프레임 정상 동작**, 1MHz 실환경 미검증. 1MHz는 datasheet 상한으로 여전히 유효라 취소선 없이 append만. 카테고리 17.1 "I2C max 1 Mbits/s(datasheet)"는 **스펙 상한 서술이지 동작 클럭 주장 아님 → 무수정**(과잉 정정 회피).

### 미결 (defer)
- **I2C 클럭 정책**: `tof_common.h TOF_I2C_FREQ_HZ` 1000000→400000 **미커밋 수정** 상태(400kHz 실동작 확인). 본 문서 태스크는 코드 무변경 → 클럭 정책 확정(1MHz 복원 or 400kHz 정식)은 별도 코드 PR로 defer. **본 커밋에 firmware/ 미포함**(무접촉 유지).
- **Stage A/B 구현**: `tof_test.cpp`는 프레임 카운트 로그만 — zone 순회/`target_status` 필터/임계값은 TODO 주석 상태(별도 코드 태스크).
- **Motion Indicator 런타임**: 브링업 로그는 `tof_dummy`(기본 프레임)라 `.motion_indicator` 필드 런타임은 미측정 — 해당 env 재빌드로 별도 재확인 대기(카테고리 9.1 Stage B 절 cross-ref).

**SSoT 정합 검증 (문서라 코드 3단계 N/A)**: 취소선/정정 대상 문구 전건 `git show HEAD:docs/decisions.md | grep`/`sed` 실존 확인 후 처리 — 1MHz 3곳(401/437/501)/33.5-③(1550) 실측. constants.py:25 정정 완료 상태 = `git show HEAD:` 실측(해소 판정의 근거). 카테고리 2·9 실번호·9.1 미존재 = `grep -nE "^## 카테고리|^### "`로 확정. PR 해시(#32 `06e671f`/#33 `601937d`) = `git log --oneline` 대조 실측. 카테고리 17.1(datasheet 상한)은 동작 주장 아니라 의도적 무수정(학습 16/19 판단). 미측정 항목(Motion Indicator 런타임 / Stage A·B / 1MHz 실환경)은 defer로 정직 표기.

**비범위**: 코드 0 수정(`server/*`/`firmware/*`/`ml/*` 전부 read only — PR #32/#33은 기 머지된 코드 인용). **firmware/ 무접촉**: `tof_common.h`(400kHz 미커밋)·`firmware/logs/`(untracked)는 커밋 제외, `git add`는 `docs/` 경로만 명시. `docs/decisions.md`(카테고리 2 핀 표 확장 + 9.1 신설 + 9 Stage B cross-ref + 12①/14/16.1 1MHz cross-ref + 33.5-③ 취소선+해소) + `docs/decisions-log.md`(본 entry)만 편집. 브랜치 없이 main 직 push(카테고리 20, 문서 단독). 토큰/시크릿/계정 개인정보 미기록.

**관련 카테고리**: 2 (핀 표 PWREN/LPn 확장) / 9.1 (브레드보드 브링업 실측 확정 신설) / 12①·14·16.1 (1MHz cross-ref) / 33.5-③ (constants.py 주석 해소)
**관련 commit**: 진단 하네스 코드 PR #32 `06e671f` + PR #33 `601937d`(기 머지) + 본 entry 자체 (`docs/decisions.md` + `docs/decisions-log.md` docs-only, PR 없음)

---

## 2026-08-08 (토) — PoC-(35) ToF Stage A ④런타임 검증 완료 + 미결 2건 해소 + 별건 stale 2건 catch (카테고리 9/19/26)

### 결정 (카테고리 9.2 — Stage A ④런타임 검증 완료, 신설)
- **2026-08-08 학부생 로컬 ④런타임 통과**: PR #34(`ecfe5a0`, Stage A 실코드화 + I2C 400kHz 정식) → PR #35(`af1fbf9`, 연속 3프레임 대칭 디바운스)로 실코드화된 Stage A가 실측 검증됨. 성공 로그 `presence: NONE -> DETECTED (near=13/64, center=1015mm, streak=3)` verbatim 수록. 사람 접근(2.9m→5.6cm) 전 구간 전환 1회만 발생, 무인 near 0~2에서 전환 0건. 카테고리 9에 **9.2 절 신설**로 전문 기록(검증 결과 / 성공 로그 / 거리-near 곡선 표 / 임계값 8 타당성 / 디바운스 N=3 / Stage B 미검증 병기).
- **★ 임계값 8 타당성 실측 근거 신설(값 변경 없음)**: 1m 지점 사람 near 9~13 / 무인 0~2 → 8이 양측 분리. 세션 중 "8→20 상향" 안은 근거 수치(near 37~55)가 실제로는 center 0.4~0.6m 값이었음이 판명되어 **폐기**(20 적용 시 1m 사람 미검출 위험, 학습 19 실증).
- **디바운스 N=3 실증**: 전환 직후 near 13→9 하락에도 DETECTED 유지 = 단일 프레임 하락 불반전 확인. 15Hz×3≈200ms, 진입/이탈 대칭.

### 해소 (카테고리 9.1(g)(h) 미결 → ✅)
- **(g) I2C 클럭 정책 해소**: `TOF_I2C_FREQ_HZ` 400000 정식 채택(PR #34 `ecfe5a0`). 근거 = 15Hz는 8x8 datasheet 상한이라 1MHz 이득 0, OnlyFeet도 400kHz, 1MHz 실환경 미검증(실익 부재). 원문 취소선 없이 ✅ append(미결→해소). 12①·14-2·16.1 cross-ref는 8/07 append 완료분(재수정 불요), 17.1 datasheet 상한 서술 무접촉(과잉 정정 회피).
- **(h) Stage A 구현 해소 / Stage B 미결 유지**: Stage A(64 zone 순회 / status 5·9 필터 / center div-by-zero 가드 / 임계 8 + 디바운스) = 해소. **Stage B(Motion Indicator)는 실구현·④런타임 미착수로 미결 유지** — 매크로 gitignore 원복 문제 존치.

### 정정 (별건 stale 2건 — 오늘 catch, 원인은 이전 세션)
- **gap F — 카테고리 19 노션 서술**: ~~`notion-query-data-sources`(SQL 쿼리)만 Business plan 차단~~ 취소선 + ✅ 정정. 단일 data source SQL 전수 스캔 정상 작동 실측(DB3 42행, `has_more:false`), 멀티 소스 조인만 잔여 제약. ★ 발견일(2026-08-07 PoC-(34) Set 3 실측 — 프로젝트 지침·인계 패키지엔 반영됐으나 decisions.md만 미반영 = SSoT 역방향 stale) ≠ 문서 반영일(2026-08-08 3소스 대조 catch) 분리 표기. `notion-update-content` re-fetch 검증 필수 서술은 유효라 보존.
- **gap G — 카테고리 26.4 시연 메시지 2**: `우리집과 옆집 초인종 구분 ~~(SP/DTW)~~` → **ToF presence 1차 융합 + SP/DTW 보조 2차** 정정. 26.3 진입점 2는 2026-07-09 PoC-(26)에서 정정됐으나 26.4 반영 누락분을 2026-08-08 catch. 26.3 정정 형식과 동일 스타일 적용, 26.4 나머지 항목·26.5~ 무접촉.

### 미결 (defer)
- **Stage B Motion Indicator ④런타임**: 실구현·런타임 미착수(9.1(h)/9.2(f)/9 Stage B 절). Stage C/D도 미착수. "Stage A 완료 ≠ ToF 사람 검증 완료" 병기 강제.
- **DB3 노션 오염(3출처)**: by-ID fetch로 우회 접근은 가능하나 오염 자체는 Set 3(노션) 소관 미결.

**SSoT 정합 검증 (문서라 코드 3단계 N/A)**: 취소선/정정 대상 문구 전건 `git show HEAD:docs/decisions.md | grep`/`sed` 실존 확인 후 처리 — gap F("Business plan" 822-823)/gap G("우리집과 옆집 초인종 구분 (SP/DTW)" 1160)/9.1(g)(h)(416/418) 실측 O. 신설 절 번호 9.2 = `grep -nE "^## 카테고리|^### "`로 9.1만 존재 확인(충돌 없음). PR 해시(#34 `ecfe5a0`/#35 `af1fbf9`) = `git log --oneline` 대조 실측. 26.3 정정 형식(1147) 대조로 gap G 스타일 정합. 17.1 datasheet 상한은 동작 주장 아니라 의도적 무접촉(학습 16/19). 미측정 항목(Stage B/C/D 런타임)은 defer로 정직 표기.

**비범위**: 코드 0 수정(`firmware/*`/`server/*`/`ml/*`/`dashboard/*`/`.gitignore` 전부 read only — PR #34/#35는 기 머지된 코드 인용). 노션 미수정(Set 3 소관) / 프로젝트 지침 미수정(Set 2 소관) / 시연 스크립트 세부 미수정(데모 재설정 chunk 소관). `docs/decisions.md`(9 Stage A cross-ref + 9.1(g)(h) 해소 + 9.2 신설 + 19 gap F 취소선+정정 + 26.4 gap G 취소선+정정) + `docs/decisions-log.md`(본 entry)만 편집. 브랜치 없이 main 직 push(카테고리 20, 문서 단독). 토큰/시크릿/계정 개인정보 미기록.

**관련 카테고리**: 9 (Stage A cross-ref) / 9.1 (g·h 해소) / 9.2 (Stage A ④런타임 검증 완료 신설) / 19 (노션 게이트 서술 정정 gap F) / 26.4 (시연 메시지 정정 gap G)
**관련 commit**: 코드 PR #34 `ecfe5a0` + PR #35 `af1fbf9`(기 머지) + 본 entry 자체 (`docs/decisions.md` + `docs/decisions-log.md` docs-only, PR 없음)

---

## 2026-08-12 (화) — PoC-(36) ToF Stage B-1 계측 계층 ④런타임 실측 + 9.1(h) 유령 미결 무효화 + SSoT 정정 2건 + 역방향 stale 4건 등재 (카테고리 9/20/21/30)

### 결정 (카테고리 9.3 — Stage B-1 Motion Indicator 계측 계층 ④런타임 실측, 신설)
- **2026-08-12 학부생 로컬 ④런타임 통과**: PR #36(`84f2272`, 브랜치 `feat/firmware-tof-stage-b-1`, 3파일 +97줄)로 Motion Indicator **계측 계층**(관측 전용, presence 판정 무융합·임계값 미하드코딩) 실코드화 + ④런타임 실측. 초기화 로그 `[tof][StageB-1] motion indicator ready (8x8, 400~1500mm, 16 aggregates)` verbatim 수록. 카테고리 9에 **9.3 절 신설**(초기화 로그 / 필드 정의 / 4종+ 대조 실측표 / 핵심 결론 3건 / 측정 환경 주의 / Stage A 회귀 / B-2 설계 방향 / stale (G)(H)).
- **★ Stage B 유효성 실측 확정**: 정지 사물(ndet=0)과 접근하는 사람(ndet 1~6)이 motion으로 완전 분리 — near로는 둘 다 임계 8 초과라 구분 불가. Stage B가 "선택"이 아니라 **"필수"**임이 실측으로 확인.
- **★ 정지한 사람 = 정지 사물 구분 불가(속도 의존)**: ③(사람 1m 정지)이 ②(정지 사물)와 동일 ndet=0. 30초간 center 1069→805mm(20cm) 표류에도 motion 미검출 → motion은 속도 의존 → **B-2는 "최근 N초 내 움직였는가"(latch) 설계** 방향(수치 확정은 B-2 소관, 본 entry 확정 금지).
- **임계값 후보** = ndet ≥ 1 또는 aggmax ≥ 50(노이즈 상한 37/사람 하한 45 사이). B-2 소관 미확정.

### 정정 (기존 SSoT 정정 2건 — 사유 명시)
- **(C) 카테고리 9 Stage B 정의 "per-zone threshold" → aggregate 단위 (취소선+append)**: **사유** = motion 데이터는 per-zone(8x8=64)이 아니라 **aggregate 단위**(활성 16개, 각 2x2 super-zone, `motion[32]`). 라이브러리 실물(`motion_indicator.cpp:150-155`) 대조로 판명. **설계 파급** = Stage A(8x8)와 motion(4x4) 해상도 불일치로 "near zone이 움직이는가"를 1:1로 못 물음 → 사람·정지물이 같은 super-zone 겹치면 분리 원리적 불가. 발원 = 2026-07-09 판정 B에서 반환 shape 미확인(학습 15 ②단계 함수까지만).
- **(B) 카테고리 9.1(h) Stage B "클린 빌드 매크로 원복 문제" 미결 무효화 (취소선+append)** ★ 본 세션 최중요: **사유** = 해당 미결은 **유령**이었음. `SparkFun_VL53L5CX_Arduino_Library` v1.0.3/main/master **3개 ref 모두** `platform.h:121`이 `// #define VL53L5CX_DISABLE_MOTION_INDICATOR`(주석)로 배포 + 로컬 sha256 `c061451…09d9` 업스트림 바이트 동일 → 매크로 패치 불필요, 클린 빌드로 원복될 대상 자체가 없음. **발원 ≠ 반영**: 2026-07-09 판정 B의 "매크로 주석처리로 컴파일 활성"이 **관찰 서술**인데 **행위 서술**로 오독 → 2026-08-08 "클린 빌드 원복 리스크" 파생 / 반증·반영 = 2026-08-12. → **학습 21 신설**(미결도 유령일 수 있다 — 등재된 미결도 실물 검증 대상).

### 신규 (역방향 stale 4건 등재 — 지침·인계엔 있었으나 decisions.md 미등재, 각 "발견 2026-08-08 / 반영 2026-08-12")
- **(a) 카테고리 9.3(G) — ToF 벽면 실사용 환경 정확도 미측정**: 거리-near/motion 실측 전부 실내 책상/바닥, 현관 벽·문틀 반사 미측정. ⚠️ 미결.
- **(b) 카테고리 9.3(H) — 환경 오염과 알고리즘 결함의 분리 원칙**: Stage A 첫 실측 전환 도배는 플리커가 아니라 케이블 15cm 감지(center 118~175mm 증거). 무자극 기준선 선확보 원칙. ③컴파일↔④런타임 사이 "측정 환경 유효성" 층.
- **(c) 카테고리 21 — 프로세스 위생(좀비 Claude 인스턴스)**: `--dangerously-skip-permissions` 세션 터미널 종료 후 잔존 → 주기 `ps aux | grep claude` / `pkill -f claude` 후 단일 재기동. "전부 죽었다"=계통 신호.
- **(d) 카테고리 20 — 학습 20 = 원격 브랜치는 `git ls-remote origin`**: `git branch -r`은 스테일 캐시. `refs/pull/N/head`는 닫힌 PR 아카이브(삭제 대상 아님). ★ 학습 18·19는 등재됐으나 20만 부재였음 → 학습 번호 SSoT 부재가 번호 혼동 재발 원인이라 정의와 함께 등재.

### 반영 (카테고리 30.9 — NCP CSR Application 등록 + 한도 실측)
- **(E) CSR Application 등록 완료**: 이름 `ddingdong-stt`, CSR 단독(Voice-Premium 미선택), Client ID/Secret 발급(실값 미기록). ★ **신규 실측 호출 한도 = 당일 30,000초 / 당월 300,000초**(1건 5초 기준 당일 6,000/당월 60,000건 → 제약 없음). 콘솔 경로 정정 = `AI·NAVER API > Application`(AI Services 8종에 CSR 부재). 관문 ③ = 목록 "서비스구분" 열 직접 확인(수정 진입 불요). 크레딧 만료 2026-08-16 미해소 유지.

**SSoT 정합 검증 (문서라 코드 3단계 N/A)**: 취소선/정정 대상 문구 전건 `git show HEAD:docs/decisions.md | grep`/`sed` 실존 확인 후 처리 — per-zone("per-zone threshold" 359, grep -c=1)/9.1(h) 클린빌드("클린 빌드 시 원복" 422, grep -c=1) 실측 O. 역방향 stale 4건 부재 = `grep -nE "벽면|문틀|반사"`/`"좀비|pkill|dangerously-skip"`/`"학습 20|ls-remote"` 각 0건 실증, 대조군 `"학습 18|학습 19"`는 다수 존재 = 20만 부재 확정. 신설 절 번호 9.3 = `grep -nE "^## 카테고리|^### "`로 9.2까지만 존재(충돌 없음). 신설 학습 20/21 = `grep -oE "학습 [0-9]+"` 최대 19 확인(충돌 없음). PR #36 머지 = `git log --oneline`(HEAD 84f2272) + `git ls-remote origin`(refs/heads/main=84f2272) 대조. 라이브러리 3 ref/sha256은 이전 세션 실측 인용(학습 13 전수 catch). NCP Client ID/Secret 실값 미기록(§7 준수).

**비범위**: 코드 0 수정(`firmware/*`/`server/*`/`ml/*`/`.pio/*` 전부 read only — PR #36은 기 머지된 코드 인용, 본 세션 미접촉). 노션 미수정(Set 3 소관) / 프로젝트 지침 미수정(Set 2=학부생 직접) / `docs/git-convention.md` 무접촉 / Stage B-2 임계값·N값·latch 시간 미확정(설계 방향만). `docs/decisions.md`(9 Stage A/B cross-ref + Stage B per-zone 정정 + 9.1(h) 유령 무효화+학습 21 + 9.3 신설 + 카테고리 20 학습 20 + 카테고리 21 좀비 위생 + 30.9 NCP 실측) + `docs/decisions-log.md`(본 entry)만 편집. 브랜치 없이 main 직 push(카테고리 20, 문서 단독). 토큰/시크릿/계정 개인정보 미기록.

**관련 카테고리**: 9 (Stage A/B cross-ref) / 9.1(h) (유령 미결 무효화 + 학습 21) / 9.3 (Stage B-1 계측 ④런타임 실측 신설) / 20 (학습 20 ls-remote 등재) / 21 (좀비 인스턴스 위생) / 30.9 (NCP CSR Application 실측)
**관련 commit**: 코드 PR #36 `84f2272`(기 머지) + 본 entry 자체 (`docs/decisions.md` + `docs/decisions-log.md` docs-only, PR 없음)

---

## 2026-09-02 (수) — PoC-(37) 마이크 M1~M4 완주(`>>14` 확정) + wire 계약 갭 전체 CLOSE + NCP 콘솔 화면 catch 4건 + stale 정정 3건 + 역방향 stale 2건 등재 (카테고리 3/6/16/17/20/27/30)

### 결정 (카테고리 6.3 — 마이크 M 시리즈 신설)
- **M1 결선 (2026-09-02)**: INMP441 M/F 점퍼 6가닥. 모듈이 2열×3핀 구조라 브레드보드 직접 삽입 불가 → **공중 부양 + 점퍼 직결**. SCK=J6(D1) / WS=J7(D2) / SD=B10(D8) / L/R=C6(GND) / GND=A6 / VDD=A35(3V3 경유). ★ VDD가 A35인 이유 = XIAO가 D행 점유로 **E7이 보드에 덮여 물리적 접근 불가** → ToF 빨강선이 있는 B35와 같은 줄 A35로 3V3 확보. 음향 포트 = 실크면 중앙 구멍(핀 반대면). **카테고리 2 핀 표 GPIO 배정과 일치 → 핀 표 무변경**(물리 위치 추가분만 6.3(a) 표로 수록).
- **M2 계측 PR #37 (`17ce212`)**: raw int32 통계 계측 계층 — `or_acc` 비트 OR 누적 + trailing zeros + min/max/mean/pp/rms + hex 덤프. 변환·판정 0줄. RAM +4B(`.data`, 신규 심볼 0) / Flash +1140B.
- **M3 ④런타임 실측 (2026-08-20 랩실)**: 39윈도우(w=233~271, 무자극/박수/육성). ★ **`or=0xFFFFFFC0` / `tz=6`이 진폭 60배 변동에도 전 구간 불변** → raw = 24bit << 6 확정. err=0 / 배경 rms 2,104,135~2,646,435 / 박수 max 296,542,208 / mean(DC) -1,210,351~+1,045,075 **부호 변동**. ⚠️ **3종 프로토콜 중 ③ 부분 충족** — 육성만 실측, **초인종 음원 미실측**(헤드룸 재확인 = M5).
- **M4 판정 PR #38 (`25b0d16`) + ④런타임 통과 (2026-09-02)**: ★ **`int16 = raw >> 14` 확정**. 도출(호스트 검산) = tz=6 → `8388607 << 6 >> 14 = 32767 = INT16_MAX` 정확 일치. 폐기안 `>>16`(기존 주석 계획)은 약 12dB 손실. saturation 가드(clamp + clip 카운트) 포함. RAM **순증 0**(union 흡수, `.bss` 13280 불변) / Flash +392B. ④런타임 27윈도우 `raw/i16` = 16,390~16,786(기대 16384) + **clip=0 전 구간**. 편차 +2.5% = raw rms(double) vs i16 rms(정수 반올림) 양자화 오차(작은 값일수록 큼) = 예상 거동.
- ⚠️ **정직 표기 — clip=0의 조건 병기**: clip=0은 **int16 풀스케일 9% 조건에서의 실증**이다(9/02 박수 i16 max 2,928 = 8/20 박수 환산 18,099·55%보다 7.4배 약함) → **헤드룸 상한 검증 아님**. saturation 로직 자체는 PR #38 **호스트 검산 7건 = 논증**이며 ④런타임 실측과 같은 층위로 적지 않음.
- **미해결 잔여(defer, 판정 방법 병기)**: ① DC 오프셋(부호까지 변동 = 단순 뺄셈 불가 → M5 조용한 환경 장시간 로그로 주기·진폭 측정 후 HPF 필요성 판정) ② RMS 트리거 임계값(카테고리 3 "80% 지점" 미확정 — ⚠️ **배경 rms 2.4M은 랩실 사람 대화 포함 = 무음 기준선 아님**, 이 값으로 임계값 산출 금지 → 조용한 환경 재측정 + 초인종/노크 실측 후 분리점) ③ 초인종 음원 헤드룸.
- **측정 로그 원본**: repo 밖 `~/ddingdong-측정결과/mic_m3_2026-08-20/` · `mic_m4_2026-09-02/` (`.gitignore` 차단분, SSoT엔 요약만).
- **★ "체감 상태 ≠ 실제 상태" 재실증**: 9/02 학부생 체감 박수 시점(w=21~22) vs 로그 실제(w=18~20)가 3~4윈도우(약 10~13초) 어긋남. 2026-08-12 9.3(e)/(H) 원칙의 재실증.

### 해소 (카테고리 6.2 wire 계약 갭 — 전체 CLOSE)
- **131 "int16 가정은 firmware 미검증" 취소선 + append**: `tz=6` 실측으로 `>>14` 확정(PR #38) → 서버 `audio_decode.py` int16 LE 계약과 정합 = **포맷 불일치 잠복 해소**. 원문 삭제 없음(grep -c=1 잔존 증명).
- **132 "나머지 절반은 마이크 결선 후" append**(취소선 없음 — 오류가 아니라 후속 완료): transport 절반은 2026-07-09 CLOSE, **나머지 절반도 2026-09-02 CLOSE** → **wire 계약 갭 전체 CLOSE**.

### 반영 (카테고리 30.7·30.9 — NCP 외부 콘솔 화면 catch 4건)
- **(1) 크레딧 만료일 정정**: ~~2026-08-16~~ → **유효기간 2026-05-01 ~ 2026-08-31**(콘솔 크레딧 관리 화면). ★ 발원 = 5/16 화면 catch값 "100,000원 / 3개월"에서 **가입일+3개월로 계산한 파생값**이 8/16이었음 → **학습 13의 새 변형 = "화면 catch한 값"과 "그 값에서 계산한 파생값"은 신뢰도가 다르다. 파생값도 catch 대상.**
- **(2) 상태 = 만료 경과 (D+2)**: 잔액 **100,000원 전액 미사용 소멸**, 결제수단 등록됨(신용카드 자동이체, 2026-05-16 등록) → **실과금 구간 진입**. 단 8월 청구요금 0원 / CSR 호출 이력 0건(당월 0/300,000 · 당일 0/30,000) = 실지출 0원. 30.7 "2026-08-16 의사결정 트리거" 취소선 + 경과 처리.
- **(3) 호출 한도 설정 완료(2026-08-20 설정)**: 일 500초 / 월 5,000초 + 임계 70% 알림 + 통보대상 등록(시스템 상한 = 일 10,000,000 / 월 30,000,000). ⚠️ 화면 안내 원문 기준 **소프트 한도** — "설정 적용 중 수 초 내 초과 호출 가능" = 하드 스톱 아님.
- **(4) 콘솔 경로 실측 정정 (URL 최초 등재)**: 크레딧/청구/결제 = **`console.ncloud.com/billing/*`**(포털 마이페이지 아님) — 트리 = 과금 정보 및 비용 관리 > 청구 및 결제 관리 > {청구서 / 결제 정보 관리 / 크레딧 관리 / 코인 관리 / 할인 관리} + 비용 관리 > {Dashboard / Cost Insight / Cost Analysis / Budgets / 솔루션 이용 현황}. Application/한도 = **`console.ncloud.com/naver-service/application`**, 버튼 **[한도 및 알림 설정]**(탭 3종). ⚠️ `console.ncloud.com/service-quota/quota-status`는 **별개** — 거기 "AI·NAVER API 기본 한도 50 / 사용량 1"은 **Application 개수 quota**이지 호출량 한도 아님.
- ★ **콘솔 화면 catch 우선 원칙 2회차 실증**: 공식 문서(`guide.ncloud-docs.com`) 기반 **추정 경로가 실화면과 불일치**. 8/12 "AI Services에 CSR 부재"에 이은 2회차.

### 정정 (stale 3건)
- **(A) 카테고리 16 `env:poc` blacklist 서술 stale**: ~~"근본 수정 = whitelist 통일 별도 위임(27.6 / DB3 등록 예정)"~~ → **정정 (해소 PR #4 `c4c8f47` / 발견 2026-09-02 세션 / 문서 반영 2026-09-02)**. 2026-09-02 `firmware/platformio.ini` 실물 조회 = **실존 env 9개 전부 whitelist**(`-<*>` 선행): poc / camera_v1 / camera_v2 / mic_dummy / tof_dummy / upload_spike / upload_spike_tls / tof_pinscan / tof_lineprobe. "별도 위임 예정" 서술이 3개월 잔존한 stale(27.6·1619는 6/22에 이미 ✅ 기록). ★ **학습 21 3회차**(8/12 매크로 유령 → 9/02 poc blacklist). 본 세션 M2 위임이 "poc는 blacklist일 것"을 전제로 §9 정지 조건을 걸었으나, MCP가 **실물 조회로 whitelist임을 확인해 정지 없이 진행**한 것이 경계 판단 모범 사례.
- **(B) 카테고리 17.1.1.3 "arduino-esp32 v3.20017" 상호 참조 부착**: 원문(5/12 출처 표기)은 **보존**하고, 항목 2·5를 함께 덮는 ※ 주석으로 "PIO 패키지 버전 문자열(`3.20017.241212`)이며 core 3.x 아님 / 실제 core = 2.0.17(6.2 2026-07-29 실측 정합 주석 참조)" 명시. 삭제·취소선 미사용(정직한 시점 기록 훼손 회피). ※ `mic_common.h` 동일 오독은 PR #37에서 코드측 정정 완료.
- **(C) 카테고리 3 음향 트리거 "80% 지점" 주의 부착**: 배경 rms 2.4M을 기준선으로 오용하지 않도록 6.3(e) cross-ref + **임계값 미확정 유지** 명시(추가만, 기존 결정 무변경).

### 확정 (카테고리 9.3(I) — 8/12 로그 원본 미보존, ★ 학습 21 적용)
- 지침·인계에 3주간 등재됐던 "⏳ 미이관 TODO: 2026-08-12 Stage B-1 로그 → `tof_stage_b1_2026-08-12`"는 **이관 대기가 아니라 원본 부재**였다. 2026-09-02 실측 = `~/ddingdong-측정결과/`에 해당 폴더 **부재**(존재분 = tof_bringup_2026-08-06_실패세션 / tof_stage_a_2026-08-08 / mic_m3_2026-08-20 / mic_m4_2026-09-02 등) + `firmware/logs` 부재 + device-monitor 로그 0건. → **"미이관 TODO" → "원본 미보존 확정"** 상태 전환. ⚠️ **데이터 손실 없음** — 4종+ 대조 실측표(9.3(c)) + 초기화 로그 verbatim(9.3(a))이 decisions.md 본문 보존.

### 신규 (역방향 stale 2건 등재 — 지침·인계엔 있었으나 decisions.md 미등재)
- **(i) 카테고리 20 — 관측/판정 계층 PR 단위 분리("계측 → 실측 → 판정")**: 한 PR에 계측과 판정을 섞지 않는다. 근거 = 판정을 먼저 박으면 실측 전 임계값을 추정으로 고정하게 되고, 되돌릴 때 계측 코드까지 흔들려 원인 분리 불가. **실증 2회** — PR #36 ToF Stage B-1(계측 → 9.3 실측 → B-2 판정 분리) / PR #37→M3→PR #38 마이크(`>>16` 추정을 실측이 `>>14`로 뒤집음). 발견·정착 2026-08-12 / 등재 2026-09-02.
- **(ii) 카테고리 27.7 — repo 절대경로는 실측값만 사용, `~` 축약 금지**: 본 repo 실경로는 공백·한글 포함(`/Users/xorms/Desktop/서경대학교/시험 준비/26-1/공학종합설계1/프로젝트/ddingdong`)이라 `~/ddingdong` 축약 시 진입 실패(**2회 실증**). 위임 §3에는 `pwd` 실측 절대경로 전문 + 모든 명령 큰따옴표 강제. 발견 2026-08-12 / 등재 2026-09-02.

### 미등재 판정 (역방향 stale 후보 5건 중 3건)
- **(iii) 동일 위치 대조 원칙** — **미등재 + §9 사용자 판단 요청**. 근거 = 등재 쪽(측정 결정에 직접 영향 + 9.3(H) "측정 환경 유효성" 층과 동일 계열) vs 미등재 쪽(9.3(e)/(H)가 이미 환경 통제를 다루므로 중복 등재 위험, 배치처도 9.3 확장 / 신설 카테고리로 갈림)이 **팽팽해 임의 결정하지 않음**. → **2026-09-02 후속 사용자 판단 = ① 9.3(H) 흡수 확장으로 등재 확정**(아래 후속 entry 참조).
- **(iv) 리드타임 우선 원칙** — **미등재**. 일정·발주 운영 원칙(카테고리 22 인접)이지 기술 결정이 아님. decisions.md = 결정 문서 / 프로젝트 지침 = 운영 원칙 문서 분리 기준 적용. 대조군 grep "리드타임" 0건(부재 실증 완료).
- **(v) 명령·용어는 목적부터 / 실측 프로토콜 "왜 재는지"** — **미등재**. 커뮤니케이션·문서작성 원칙으로 결정 문서 소관 아님. 대조군 grep "목적부터|왜 재는지" 0건(부재 실증 완료).

**SSoT 정합 검증 (문서라 코드 3단계 N/A)**: 취소선/정정 대상 문구 **전건 실존 선확인 후** 처리 — `git show HEAD:docs/decisions.md | grep -n` 기준 (b)"int16 가정은 firmware 미검증" 131 O / (c)"blacklist 회귀" 624·1619 O / (d)"v3.20017" 139·640·724·774·777·1392 O / (e)"2026-08-16" 1505·1506·1534·1541 O / (g)`^### 9.3` 464 O. **(f)"console.ncloud.com" = 0건(부재)** → 취소선 대상 없음으로 판정, **추가(신규 등재)로만 처리**(없는 문구에 취소선 = 날조 회피, §9 정지 사유 미해당). 처리 후 **원문 보존 증명** = 7개 원문 문구 전건 `grep -c = 1` 잔존 확인. 신설 절 번호 **6.3** = `grep -nE "^### 6\."`로 6.1·6.2만 존재 확인(충돌 없음; "6.3" 평문 매치 3건은 84.1ms·26.3 = 정규식 아티팩트로 배제). **27.7** = `^### 27\.`로 27.1~27.6 확인. PR #37 `17ce212` / #38 `25b0d16` 머지 = `git log --oneline` + `git ls-remote origin`(refs/heads/main=25b0d16) 대조 실측. env whitelist 9건 = `firmware/platformio.ini` 직접 grep 실측(위임 전제 재검증 = 학습 19). 8/12 로그 부재 = `ls ~/ddingdong-측정결과/` 실측. 근거유형 분리 표기(④런타임 실측 vs 호스트 검산 논증) 준수. NCP 학번·카드번호·연락처 미기록(결제수단은 "등록됨(2026-05-16)"까지).

**비범위**: 코드 0 수정(`firmware/*`/`server/*`/`ml/*`/`dashboard/*`/`firmware/platformio.ini` 전부 read only — PR #37/#38은 기 머지된 코드 인용, 본 세션 미접촉). 카테고리 2 핀 표 무변경(GPIO 배정 일치 확인). 노션 미수정(Set 3 소관) / 프로젝트 지침 미수정(Set 2 = 학부생 직접) / `docs/git-convention.md` 무접촉. M5(초인종 음원 헤드룸 / DC 오프셋 HPF / RMS 임계값) 미착수 = defer. 역방향 stale (iii) 미등재 = 사용자 판단 대기. `docs/decisions.md`(3 RMS 주의 + 6.2 갭 해소 2건 + 6.3 신설 + 9.3(I) + 16 blacklist stale 정정 + 17.1.1.3 v3.20017 주석 + 20 계층 분리 등재 + 27.7 신설 + 30.7·30.9 NCP 4건) + `docs/decisions-log.md`(본 entry)만 편집. 브랜치 없이 main 직 push(카테고리 20, 문서 단독). 토큰/시크릿/계정 개인정보 미기록.

**관련 카테고리**: 3 (RMS 임계값 주의) / 6.2 (wire 계약 갭 전체 CLOSE) / 6.3 (마이크 M 시리즈 신설) / 9.3(I) (8/12 로그 원본 미보존 확정) / 16 (env:poc blacklist stale 정정) / 17.1.1.3 (v3.20017 상호 참조) / 20 (계층 분리 원칙 등재) / 27.7 (절대경로 실측값 등재) / 30.7·30.9 (NCP 크레딧 만료·한도·콘솔 경로)
**관련 commit**: 코드 PR #37 `17ce212` + PR #38 `25b0d16`(기 머지) + 본 entry 자체 (`docs/decisions.md` + `docs/decisions-log.md` docs-only, PR 없음)

---

## 2026-09-02 (수) 후속 — PoC-(37) Set 1 §9 판단 반영: 역방향 stale (iii) "동일 위치 대조 원칙" 9.3(H) 흡수 확장 (카테고리 9)

### 결정 (사용자 판단 = ① 9.3(H) 흡수 확장)
- 본일 오전 entry에서 **§9로 올린 (iii) 동일 위치 대조 원칙**에 대해 사용자가 **① 9.3(H) 흡수 확장**으로 판정. 신설 절/신설 카테고리 안은 폐기.
- **판정 근거(사용자 제시)**: ⓐ (H)와 **동일 층위**(측정 설계 단계의 통제 원칙) — 신설 시 인접 절이 같은 주제를 분할 서술하게 됨 ⓑ **사례 2건 확보**로 원칙 성립 ⓒ 9.3이 이미 (a)~(I) **9항목**이라 카테고리 9 하위 추가 신설은 **탐색성 저하**.

### 반영 (카테고리 9.3(H))
- (H) 본문 **무훼손 append**. 하위 원칙 1개 + 사례 2건 + 적용 지침 1건 추가. 취소선 없음(오류 정정이 아니라 원칙 확장이므로).
- **원칙**: 대조군과 실험군은 **같은 자리·같은 조건**에 둔다. 위치·거리·세기가 함께 변하면 관측 차이의 **변수 분리가 불가**하고 판정 자체가 성립하지 않는다. (H) 본문 = "환경 오염 vs 알고리즘 결함" 분리 / 본 하위 원칙 = 그 앞단인 **자극 조건 통제**.
- **사례 ① 2026-08-12 ToF Stage B-1**: ②정지 사물과 ③사람을 같은 위치에 두어야 motion 차이와 위치(거리) 차이가 섞이지 않음. 위치를 함께 바꾸면 near/center 변화가 "움직임 때문"인지 "더 가까워서"인지 분리 불가.
- **사례 ② 2026-09-02 마이크 M4 (6.3(d))**: 같은 "박수"인데 거리·세기 미통제로 8/20 대비 **7.4배 약함**(9/02 i16 max 2,928 vs 8/20 환산 18,099) → clip=0이 풀스케일 **9% 조건**에 그쳐 **헤드룸 상한 검증 불성립**. 조건 미통제가 판정을 무효화한 실증.
- **적용**: M5 등 후속 실측은 대조군/실험군을 **동일 위치·거리·세기 프로토콜**로 잡고, 조건 변경 시 **한 번에 한 변수만**.

**SSoT 정합 검증 (문서라 코드 3단계 N/A)**: 삽입 앵커 = (H) 말미 "③컴파일과 ④런타임 사이에 \"측정 환경 유효성\" 층이 하나 더 있음" **grep -c=1** 선확인 후 단일 매치 치환(다중 매치 시 abort하는 스크립트 가드 사용). 처리 후 **원문 보존 증명** = (H) 본문 문구 "환경 오염과 알고리즘 결함의 분리 원칙" / "센서 위 케이블을 15cm에서 감지한 것" 각 `grep -c=1` 잔존, 취소선 0개 추가. 인용 수치 **2,928 / 18,099 / 7.4배 / 9%**는 6.3(d)에 기 등재된 값과 대조 일치 확인(날조 아님). 오전 entry (iii) 항목은 **삭제 없이 append**로 결론 링크. 신설 절 번호 없음(기존 (H) 하위이므로 번호 충돌 검사 N/A).

**비범위**: 코드 0 수정(`firmware/*`/`server/*`/`ml/*`/`dashboard/*`/`firmware/platformio.ini` 전부 미접촉). 6.3(d)·9.3(e)·(I) 본문 무변경(cross-ref만 신규 텍스트 안에서 참조). 역방향 stale (iv) 리드타임 / (v) 목적부터는 **미등재 판정 유지**(본 후속 범위 아님). `docs/decisions.md`(9.3(H) 하위 항목) + `docs/decisions-log.md`(본 entry + 오전 entry (iii) 결론 append)만 편집. 브랜치 없이 main 직 push(문서 단독).

**관련 카테고리**: 9.3(H) (동일 위치 대조 하위 원칙 등재) / 6.3(d) (사례 ② 출처) / 20 (문서 단독 main 직 push)
**관련 commit**: 본 entry 자체 (`docs/decisions.md` + `docs/decisions-log.md` docs-only, PR 없음). 선행 = `a35271e`(본일 오전 PoC-(37) 반영)

---

## 2026-09-02 (수) 후속 2 — PoC-(38) Set 1: 9.3(d)-3 산술 오기 정정 + Stage B-2(9.4) + Cloudflare Tunnel(7.4) + 카카오 토큰 재발급 + 감사 6건 반영 (카테고리 3/6.1/6.2/6.3/7/9)

### 반영 대상 5군

1. **[A] 9.3(d)-3 산술 오기 정정**: "`aggmax ≥ 50` (노이즈 상한 37 / 사람 하한 45 사이)" — 50은 45보다 커서 그 구간 밖. 실제 허용 구간 = 38~45. 채택 시 9.3(c)④(하한 45)에서 미탐 발생. **판단 오류가 아니라 산술 오기**로 성격 규정. 취소선 + append(원문 보존).
2. **[B] 카테고리 9.4 신설**: Stage B-2 판정 계층(PR #39 `a0953fb`) — 채택 `TOF_MOTION_NDET_MIN=1`(기각근거 3종) + latch `TOF_MOTION_LATCH_FRAMES=75`(논증) + footprint(RAM 순증0/Flash+236B) + ④런타임 실측(`tof_stage_b2_2026-09-02/monitor.txt` 182줄, latch만료 #4621 ≈4.9초 실측=설계값 5.0초 일치, latch붙잡기 #4291~4351, presence측 끊김 #3811/#4377/#4649/#5020, 재충전 #4648) + 프로토콜②(정지 사물 대조) 미수행 명시(부분 충족) + 위임 전제 오류 2건(학습19).
3. **[C] 카테고리 7.4 신설**: Cloudflare Tunnel 이미지 호스팅 실측 — 터널 관통·`/detect` 201·`/enrich` 200·env 교체만으로 image_url 전체 URL화(코드 0 수정, `config.py:37` 기존 env 주입 설계)·카카오톡 앱 이미지 렌더 확인(전 구간 실측). ★ 감사 결론 "EC2 유일 선행" 폐기 → "정식 배포 수단"으로 위상 변경. ★★ 단, quick tunnel = 임시주소+가동보장없음 → 안전망이지 정공법(EC2) 대체 아님을 명시 병기.
4. **[D] 카테고리 7 토큰 항목에 재발급 사실 append**: 7.2/7.3 실측일 기반 만료 추정(2026-09-27~29, 논증)이 발표 구간(9/21~9/30)과 겹치는 리스크 → 2026-09-02 카카오 디벨로퍼스에서 재발급(scope=talk_message 단독 확인) → 60일 리셋. 재발급일을 SSoT化하여 재발경로 차단. 토큰 실값 미기록.
5. **[E] 2026-09-02 전체 시스템 감사(34건 중 위임이 제시한 15건을 검토) — 6건 등재 / 1건 판단불가 각하 / 8건 지침 전용**:
   - 등재: G10(🔴 6.2, `/detect` ToF 메타 필드 부재 — `utils.py:92,101` 하드코딩 문자열 실측 확인, 위임의 "두 줄 다 zone_count=11" 인용은 부정확 — 실제 92행=9/101행=11로 정정 인용) / G29(🟡 6.2, 2초 캡처 윈도우 예산 미반영, 논증) / G28(🟡 6.3(e), 입력 레벨 6.2x 변동 미검증) / G12(⚠️§9 카테고리 3, fire_alarm이 신뢰도 게이트도 우회하는지 미결 — `utils.py` fire_alarm 분기가 threshold 비교보다 선행함을 코드로 확인, 결론은 미결로만 등재) / G14(🟡 6.1, `primary_sent_at=detected_at` 동일변수 확인) / G22(7.4 (a)~(c) 실측으로 이미 흡수, 별도 신규 절 불요).
   - 판단불가 각하: **G34** — 위임 원문 "routes.py·constants.py는 PR #29(c30e728) 이후 수정 이력 있음"을 `git log c30e728..HEAD -- server/app/routes.py server/app/constants.py`로 검증한 결과 **공커밋**(c30e728 자체가 두 파일의 최후 수정 커밋, 그 *이후*엔 수정 이력 없음) — 위임 전제가 실물과 불일치(학습 19). 게다가 decisions.md에는 애초에 "routes.py/constants.py가 frozen"이라는 문구 자체가 등재된 적이 없어(grep 0건) 취소선 정정 대상도 부재. utils.py "프로즌 아님"은 이미 6.2(PR #28 pivot 기록, 143행 상당)에 정확히 등재돼 추가 정정 불요. → decisions.md 미등재, 프로젝트 지침(Set 2 소관) 쪽 문제일 가능성 있음을 보고로 남김.
   - 지침 전용(등재 불요, decisions.md는 결정 문서지 운영 원칙 문서 아님): G01~G03(물리/페리페럴 근거 정정 — 결정 변경 없음, 서술 보강 성격) / G31~G33(위생·프로즌 준수 확인 — 결과가 "이상 없음"이라 결정문서에 남길 신규 사실 없음) / G19·G20(이미 등재된 미결의 재확인 — 기존 SSoT와 동일 결론이라 append할 신규 정보 없음). ※ 위임이 명명한 15건 외 나머지(34−15=19건)는 본 위임 프롬프트 본문에 개별 근거가 제시되지 않아 이번 세션에서 검증·등재 판단을 내리지 않음(범위 밖).

### SSoT 정합 검증 (문서라 코드 3단계 N/A)

**문구 실존 선확인**: [A] "aggmax ≥ 50 ... 37 / ... 45 사이"는 `grep -n "aggmax"` 545행에서 O(실존) 확인 후 처리 — 날조 아님. 취소선 총수 = 작업 전 **30줄** → 작업 후 **31줄**(신규 1건, [A] 단독 — [B]~[E]는 전부 append/신규 등재이지 정정이 아니므로 취소선 미사용). 정정 후 "노이즈 상한 37" 원문 문구 `grep -c=1` 잔존 확인(삭제 0줄, 취소선 안에 보존). 신설 절 번호 **9.4**·**7.4** = `grep -nE "^### 9\.|^### 7\."`로 기존 9.1~9.3/7.1~7.3만 존재·번호 공백 확인(충돌 없음). [B] 근거는 `git show a0953fb --stat`(2파일 변경, PR 본문에 임계값 기각근거·footprint 수치 verbatim 일치) + `~/ddingdong-측정결과/tof_stage_b2_2026-09-02/monitor.txt`(182줄, `#3811/#4291/#4351/#4377/#4621/#4648/#4649/#5020` 전건 grep 실물 대조, latch=73~75/75 잔존 상태에서 presence측 전환임을 직접 확인) + `firmware/src/tof_test.cpp`(`presence_state` static 위치 67행, `motion_indicator` 독립 재참조 188행 — 위임의 두 전제 오류를 코드로 직접 검증, 학습 19) 실측. [C]는 `server/app/config.py:37`(`CAPTURE_URL_BASE` env 주입) 코드 대조로 "코드 0 수정" 주장 검증. [E] G10은 `server/app/utils.py:92,101` grep으로 인용문 재확인 중 위임 원문의 인용 부정확(둘 다 "zone_count=11"로 인용했으나 실제 92행은 "zone_count=9")을 catch, decisions.md엔 정확한 값으로 등재(맹목 인용 금지). G34는 `git log --oneline -- server/app/routes.py`·`constants.py` 전체 이력 대조로 위임 전제 자체가 실물과 어긋남을 확인 후 미등재로 pivot(§9 트리거 미해당 — "정정 대상 부재"이자 "위임 전제 오류" 이중 사유).

**근거유형 분리**: [A]는 산술 검산(오기 성격 규정, 실측 아님) / [B](a)는 논증(9.3(c) 대조), (d)는 "논증→실측 승격" 명시 표기, (f)는 위임 전제 재검증(코드 대조) / [C]는 실측(전 구간) + 안전망 단서(정공법=EC2 별도 명시) / [D]는 재발급 사실=사실, 만료추정=논증(명시 표기) / [E]는 항목별 실측·논증 태그 개별 부여(G10=실측 재현 포함, G29·G28=논증, G12=코드 확인+미결). 세 층위(실측/논증/미확인)가 한 문장에 섞인 곳 없음.

### 비범위

코드 0 수정(`firmware/*`/`server/*`/`ml/*`/`dashboard/*` 전부 read only — PR #39는 기 머지된 코드 인용, 본 세션 미접촉). G12는 **결론 내지 않고 §9 미결로만 등재**(코드 수정도 옳고그름 판정도 하지 않음). 노션 미수정(Set 3 소관) / 프로젝트 지침 미수정(Set 2 = 학부생 직접) / `docs/git-convention.md` 무접촉. 카카오 토큰 실값 미기록. 감사 34건 중 15건만 위임 본문에 근거가 있어 그 15건만 판단(전건 등재 금지 원칙 준수, 나머지 19건은 미평가로 명시). `docs/decisions.md`([A] 9.3(d)-3 정정 + 9.4 신설 + 7.4 신설 + 카테고리 7 토큰 append + 카테고리 3 G12 append + 6.1 G14 append + 6.2 G10·G29 append + 6.3(e) G28 append) + `docs/decisions-log.md`(본 entry)만 편집. 브랜치 없이 main 직 push(문서 단독, PR 불요).

### commit 이모지 소거법

`docs/git-convention.md` 14종(🎉✨🐛🎨♻️🔧🗃️➕📝🔀🚀🚚🔥⏪) 실물 확인 후 **📝 Docs**만 성립: 🎉(신규 프로젝트 아님)·✨(신규 기능 아님, 코드 0)·🐛(코드 버그 수정 아님)·🎨(CSS/UI 아님)·♻️(코드 리팩터 아님)·🔧(설정 파일 아님, decisions.md는 설정이 아니라 문서)·🗃️(코드 주석 아님)·➕(의존성 추가 아님)·🔀(수동 브랜치 병합 아님, 직 push)·🚀(배포 아님)·🚚(파일 이동/개명 아님)·🔥(삭제 전용 작업 아님 — 원문 보존 원칙상 삭제 0줄)·⏪(롤백 아님) 전부 소거. 선례(`b2bce35`/`a35271e` 등 문서 전용 커밋)도 전부 📝 Docs.

### §9 사용자 판단 요청

- **G12(카테고리 3)**: fire_alarm 분기가 신뢰도 임계값 게이트도 함께 우회하는지 — decisions.md엔 충돌 발견 + 코드 실측 + 양쪽 서술 인용만 등재, 결론 미기재. 사용자 판단 필요.

**관련 카테고리**: 9.3(d)·9.4 (Stage B-2) / 7 토큰·7.4 (Tunnel 실측) / 3 (G12 미결) / 6.1(G14)·6.2(G10·G29)·6.3(e)(G28) (감사 반영)
**관련 commit**: 코드 PR #39 `a0953fb`(기 머지, 인용) + 본 entry 자체(`docs/decisions.md` + `docs/decisions-log.md` docs-only, PR 없음)

---

## 2026-09-03 (목) — PoC-(39) A-1 카카오톡 1차 텍스트 알림 end-to-end 완주 + 200자 상한 반증 + REST키 rotate 유령 확정 + OAuth refresh 부트스트랩 (카테고리 6.1/6.2/7/7.5/20)

### 결정 (카테고리 7.5 신설 — A-1 end-to-end 완주 + 토큰 재발급 실무 확정)

- **(a) end-to-end 관통 (근거유형 = 실측, 학부생 로컬 M4 + `flask run`)**: PR #40 `70aea1d`로 토큰 SQLite 모델 + 자동 갱신 + memo 실발송 + 확정 카피 ② 배선. 부트스트랩 → 갱신 API 실호출 성공(access 토큰 길이 64) → `/detect` doorbell 0.79 → `primary_sent=true` → 카카오톡 도착(화면 catch). `fire_alarm` 0.92 → 확정 카피 ② 266자 전문 도착(절단 없음). doorbell 0.68 → `primary_sent=false`(threshold 0.7 엄격 경계 실경로 실증, 카테고리 3 정합). ⚠️ 감사 G18/G21/G24 CLOSE는 **decisions.md 미등재 ID**(Notion DB3 전용 감사 ID) — 노션 반영은 별도 세션 소관이며 본 entry는 사실만 기록한다.
- **(b) ★ 확정 카피 ② 200자 상한 반증 (근거유형 = 실측, 7.1 연동)**: 카카오 공식 문서 + 담당자 답변 기준 "text 템플릿 200자 상한, 초과 시 말줄임표 절단"이 **266자 / 603 bytes / 9줄 무절단 렌더**(HTTP 200, `result_code` 0)로 반증됐다. ⚠️ decisions.md에 "200자 상한" 서술 자체가 부재해 **취소선 대상 없음 → 순수 신규 실측 등재**(없는 문구에 취소선 = 날조 회피, 2026-09-02 (f) 선례 준용). ★ **성격 구분** = 앞선 실측 반전 3회(ToF near 8→20 폐기 / 마이크 `>>16`→`>>14` / ToF aggmax≥50→ndet≥1)는 전부 내부 추정·문서가 뒤집힌 것이나, 본 건은 **외부 1차 출처(카카오 공식 문서)가 실화면 앞에서 뒤집힌 첫 사례**다. 파급 = 분할 발송·축약 카피 전부 불요(코드에 분할 로직 0줄). ⚠️ "200자가 무엇을 의미하는지"(byte 기준인지 등)는 **미확인 — 추측 기록 금지**.
- **(c) ★ 카카오 REST API 키 rotate = 유령 미결 확정 (근거유형 = 실측 화면 catch, 학습 21 계열)**: 2026-07-31 노출 이후 이월돼 있던 "REST키·client_secret rotate" 항목(⚠️ 이것도 **decisions.md 미등재**, Notion DB3 전용 추적 항목). 실화면 = 플랫폼 키 카드 ⋮ 메뉴에 수정/복제 키 생성뿐, 삭제·재발급 없음. 수정 페이지에도 키 값 재발급 항목 부재 → 노출된 REST API 키를 무효화할 방법이 **콘솔에 없다** = rotate는 애초 **실행 불가능한 작업**이었다. 대안 = client_secret 재발급(재발급일 2026-09-03)으로 토큰 교환 관문 복원. 위협 평가(근거유형 = **논증**) = REST키 단독으로는 memo 발송 불가(인가 코드는 등록 Redirect URI로만 전달 / 토큰 교환에 client_secret 필수 / 본인 동의 필요 / memo는 토큰 소유자 본인에게만). 기각안 = 호출 허용 IP 설정(카카오 공식 권고) — 부스가 모바일 핫스팟(카테고리 23)이라 IP 가변, 적용 시 데모 파손.
- **(d) ★ 카카오 콘솔 경로 정정 (근거유형 = 실측 화면 catch, 학습 13 화면 우선)**: client_secret 실측 위치 = 앱 설정 → 플랫폼 키 → REST API 키 카드 → [클라이언트 시크릿] 칩(URL 패턴 `/console/app/{appId}/config/platform-key/rest/{keyId}`). 콘솔이 멀티 REST 키 구조로 개편됨. REST API 키 생성 일시 2026-05-14(카테고리 30.2 셋업일 정합). ⚠️ **본 세션에서 AI가 콘솔 경로·기능 유무를 3회 연속 오안내**(① REST키 재발급 UI 부재 추정 ② 시크릿 위치 ③ rotate 가능 판단) — 2026-09-02 NCP 콘솔 오안내에 이은 연속 → **원칙: AI가 제시한 외부 콘솔 경로·기능 유무는 화면 catch 전까지 전부 추정.**
- **(e) ★ OAuth refresh 부트스트랩 절차 확정 (근거유형 = 실측)**: REST API 테스트 도구는 access만 발급하고 refresh는 인가 코드 흐름으로만 얻는다 — 카테고리 7 상단 "토큰" 항목의 2026-09-02 재발급 기술을 이 사실로 정정. 확정 절차 = Redirect URI 등록(`http://localhost:5000/oauth`) → 인가 URL 접속 → 동의 → `ERR_CONNECTION_REFUSED` 주소창에서 `code=` 복사(서버 미기동이 정상) → curl 토큰 교환. refresh 발급일 2026-09-03, `refresh_token_expires_in` 5,183,999초(60일), 다음 만료 ≈ **2026-11-02**(추정 아니라 실측). ⚠️ "잔여 1개월 미만일 때만 재발급"은 **문서 인용·미실측** — 판정 방법 = 2026-10월 초 갱신 시 `refresh_token` 값 변경 여부 로그 확인. ⚠️ 조건 = 만료 전 서버가 최소 1회 발송해야 갱신이 돈다. 토큰·시크릿 실값 미기록.
- **(f) 데스크톱 vs 모바일 렌더 차이 — 카피 조정 불요 (근거유형 = 실측 화면 catch)**: 데스크톱 카카오톡에서 확정 카피 ②의 어절 분절 관측("천/으로", "음/성통화"). 5060 노안 가독성 우려로 줄바꿈 조정을 검토했으나 **휴대폰 실화면에서 분절 미발생** → 조치 불요. 원칙 = 렌더 결과는 클라이언트 폭 종속이며, 실사용 환경(모바일) 미확인 상태로 데스크톱만 보고 카피를 손대면 7.1 검증본을 훼손한다.
- **(g) feed 본문 2줄 제약 → A-2 defer (근거유형 = 문서 인용, 미실측)**: 이미지 포함 템플릿은 본문 2줄만 표시 — A-2(2차 이미지 + STT 자막) 직결. ⚠️ **(b)에서 반증된 200자 건과 근거유형이 동일**(문서 인용 출발, 미실측)이므로 판정 전까지 결론 선반영 금지. 판정 방법 = A-2 착수 전 실 feed 1건 발송 후 앱 화면 육안(프로브 컨벤션). ※ 본 항목은 2026-09-04 PoC-(41)에서 **확증**된다(아래 PoC-(41) entry).
- **(h) ★★ 7.4(c) 단서 실증 — 터널 주소 소멸 (근거유형 = 실측 화면 catch)**: 2026-09-02 터널 실측으로 카톡에 전송했던 이미지가 2026-09-03 확인 시 **회색 빈 박스**로 렌더(fetch 실패). 7.4(c) "quick tunnel은 임시 주소라 재기동 시 변경"이 실물로 증명됨 = 발표 당일 리허설 필요성의 직접 근거.
- **(i) 회귀 테스트 자산 부재 → 자산화 (학습 21 계열)**: 6.2의 "curl 회귀 10종/15종/25종" 서술은 **실행 기록이지 repo 자산으로 존재한 적이 없었다**(PR #40 작업 중 확인) — 6.2 본문은 당시 실제 수동 실행 기록이라 정정 대상 아님. PR #40에서 `server/app/tests/test_detect_regression.py`(stdlib unittest, 30 케이스)로 자산화.

### 해소 (카테고리 6.1 — G14)

- 2026-09-02 감사 G14(`primary_sent_at`이 `detected_at`과 동일 변수로 세팅됨)를 PR #40 실발송 배선으로 해소. 실발송이 붙으며 `primary_sent_at`이 실제 발송 시각을 갖게 됐다.

### 반영 (카테고리 6.2 G29 / 카테고리 20 — 기준선 정정)

- G29(2초 캡처 윈도우가 1차 5초 예산에 미반영)의 두 설계안 수치를 기준선으로 재정리(사후 녹음 ≈3,954ms=79% vs 사전 링버퍼 ≈1,954ms=39%, 근거유형 = 논증). **확정은 본 세션에서 하지 않고 §9로 올림**(결론 = 아래 PoC-(40) entry의 B안).

**SSoT 정합 검증 (문서라 코드 3단계 N/A)**: 신설 절 번호 **7.5** = `grep -nE "^### 7\."`로 7.1~7.4까지만 존재 확인(충돌 없음). (b)/(c)의 취소선 대상 문구는 `grep` **0건**으로 부재 실증 후 **신규 등재로만** 처리(없는 문구에 취소선 = 날조, 2026-09-02 (f) 선례). PR #40 머지 = `git log --oneline`(`70aea1d`) 대조. 카카오 토큰·시크릿·REST키 실값 미기록. 근거유형 3층(실측 / 논증 / 문서 인용·미실측)을 (a)~(i) 항목별로 개별 태그.

**비범위**: 코드 0 수정(PR #40은 기 머지 코드 인용, 본 문서 세션 미접촉). 노션 미수정(Set 3 소관) / 프로젝트 지침 미수정(Set 2 = 학부생 직접). (g) feed 2줄은 **판정 전이라 결론 미기재**. 카테고리 20 [J] 실증 횟수 표기 변경은 **사용자 판단 대기**(아래 후속 entry에서 확정). `docs/decisions.md`(7.5 신설 + 카테고리 7 토큰 항목 정정 + 6.1 G14 해소 + 6.2 G29 기준선) + `docs/decisions-log.md`만 편집. 브랜치 없이 main 직 push(문서 단독).

**관련 카테고리**: 7.5 (A-1 end-to-end 신설) / 7 (토큰·2차 알림) / 7.1 (확정 카피) / 7.4 (터널 주소 소멸 실증) / 6.1 (G14 해소) / 6.2 (G29 기준선 · curl 회귀 자산화) / 20 (계측→실측→판정)
**관련 commit**: 코드 PR #40 `70aea1d`(기 머지) + 문서 반영 `02e8aa1`(`docs/decisions.md` + `docs/decisions-log.md` docs-only, PR 없음)

---

## 2026-09-03 (목) 후속 — PoC-(39) Set 1 §9 판단 반영: 카테고리 20 [J] "계측 → 실측 → 판정" 실증 횟수 2회 → 3회 확정 (카테고리 20)

### 결정 (사용자 판단 = [J-확정] 3회)

- 본일 entry에서 **§9로 올린 "실증 횟수 표기 변경 여부"**(PR #34→#35 ToF Stage A 디바운스를 3번째 실증으로 셀지)에 대해 사용자가 **3회로 갱신** 확정. 기존 "실증 2회" 서술을 취소선 처리하고 아래 3건으로 재정리.
- **(1) 2026-08-08 ToF Stage A**: PR #34 관측 → ④런타임 실측(9.2 거리-near 곡선) → PR #35 판정(임계값 8 확정). 실측이 뒤집은 것 = "8→20 상향" 안 폐기(근거유형 = 실측, 9.2(d)).
- **(2) 2026-08-12~09-02 ToF motion**: PR #36 계측 → ④런타임 실측(9.3) → PR #39 판정(9.4). 실측이 뒤집은 것 = `aggmax≥50` → `ndet≥1`.
- **(3) 2026-09-02 마이크 shift**: PR #37 계측 → M3 ④런타임 실측(tz=6) → PR #38 판정(6.3). 실측이 뒤집은 것 = `>>16` → `>>14`.
- ★ **근거 등급 분리(숨기지 않음)**: (2)(3)은 이 3단계 패턴을 **의식하고 설계한 사례**이고 (1)은 **사후 소급 분류**다 — PR #34는 Stage A 구현 PR로 기획됐지 "관측 전용 계측 PR"로 설계되지 않았다. 패턴의 명시적 정착 시점은 **2026-08-12 PR #36부터**이고 원칙 문장의 decisions.md 등재는 **2026-09-02**다. 그럼에도 3회로 세는 이유 = 3단계 구조가 (1)에서도 실제로 성립했고, 본 원칙의 **가장 강한 근거**(near 8→20 상향안 폐기)가 (1)에서 나왔기 때문.

**SSoT 정합 검증 (문서라 코드 3단계 N/A)**: 정정 대상 문구 "**실증 2회**" 실존 `grep` 선확인 후 취소선 + append(원문 삭제 0줄, 취소선 안에 보존). 인용한 PR 번호·해시(#34/#35/#36/#37/#38/#39)와 뒤집힌 값(8→20 / aggmax≥50→ndet≥1 / `>>16`→`>>14`)은 전부 9.2·9.3·9.4·6.3 기 등재값과 대조 일치(날조 아님). 신설 절 없음(기존 카테고리 20 항목 확장이므로 번호 충돌 검사 N/A).

**비범위**: 코드 0 수정. 노션 미수정(Set 3 소관) / 프로젝트 지침 미수정. `docs/decisions.md`(카테고리 20 [J] 항목) + `docs/decisions-log.md`만 편집. 브랜치 없이 main 직 push(문서 단독).

**관련 카테고리**: 20 (관측/판정 계층 PR 단위 분리 — [J-확정])
**관련 commit**: 문서 반영 `f0529e7`(docs-only, PR 없음). 선행 = `02e8aa1`(본일 PoC-(39) 반영)

---

## 2026-09-03 (목) — PoC-(40) 마이크 M5-a/a2 계측·관측 계층 + M5-b 무음 기준선·분리 마진·시리얼 절단 실측 + M4 판정 근거 2건 반증 + G29 B안 확정 (카테고리 6.2/6.3/7/20)

※ 작업일 2026-09-03(랩실 M5-b 실측 포함) / PR #42 머지·문서 반영은 2026-09-04. 발견일과 반영일이 갈리는 항목은 각 항목에 "(발견 … / 문서 반영 …)"로 병기한다.

### 결정 (카테고리 6.3 (h)(i) — 계측·관측 계층 2단, 카테고리 20 원칙 적용)

- **(h) M5-a PR #41 `b4b880a`(내부 커밋 `b3e9c9d`) — 2초 PSRAM 링버퍼 계측 계층**: 신설 `MIC_RING_SLOTS=32`(2.048s = 32,768샘플 = 65,536B int16) / `MicRingStatus` / `initMicRingBuffer` / `micRingSlot`(inline) / `micRingAdvance`. 채택 근거 = 2.000초는 31.25버퍼라 정수배가 아니어서 부분 버퍼 처리 로직을 피하려 32(2.048초) 채택. 서버 수용 확인 = 서빙 시그니처 `waveform(1,None)` 가변 길이 + `AUDIO_MAX_BYTES` 320,000 대비 20.5%. footprint(실측) = RAM 순증 0(4회 연속) / Flash +804B. ④런타임(2026-09-03, 랩실 사람 없음, 실측) = ring=on / PSRAM 8,386,231 → 8,320,559(Δ 65,672 = 링버퍼 65,536 + 헤더 136) / gaps=0(전 42윈도우) / wrap-around 전수 정합.
- ★ **위임 원안 API 기각 (근거유형 = 논증)**: bool 반환 + 내부 전역 보관안이 본 파일 3곳에 명문화된 "static/전역 신설 금지 = RAM 순증 0" 컨벤션과 충돌(전역 포인터 1개 = `.bss` +4B) → `int16_t*` 반환 + `micRingSlot(base, idx)` 순수 함수로 변경(카테고리 29 "위임과 실제 컨벤션 충돌 시 기존 컨벤션 우선" 적용).
- **(i) M5-a2 PR #42 `d024e23`(내부 커밋 `462c029`) — 윈도우 진폭 누적 관측 계층**: 배경(실측) = (h) ④런타임에서 **의도적으로 친 박수가 전혀 검출되지 않았다**. 로그 게이트가 50버퍼당 1버퍼 = 시간의 2%만 관측이고 박수는 약 100ms → 창에 들어갈 확률 2%. → **8/20 M3(6.3(c))의 박수 검출이 오히려 우연이었다**는 재해석. 신설 = micTask 지역 누적 4종(`win_peak`/`win_rms_max`/`win_rms_min`/`win_clip`) + `win_nbuf` → `[mic][M5a2]` 별도 로그 줄, 판정 로직 0줄. footprint = RAM 순증 0(5회 연속) / Flash +268B. ★ **센티넬 없는 설계** — `win_nbuf == 0 || rms < win_rms_min` 가드만 사용해 센티넬 상수가 없으니 "누출 경로를 막을" 필요 자체가 소멸(방어 코드 대신 문제의 부재).
- ★ **위임 자기모순 발견 + 해소**: "PSRAM 실패 시에도 진폭 관측 유효"(원 지시)와 "M2 로그 포맷 불변"(원 지시)이 union 구조상 양립 불가(폴백 dst = `audio_buffer.i16` = raw[0..511]과 동일 메모리) → 후자를 우선하고 폴백 윈도우는 n/a 분기 처리(카테고리 27/29 패턴 재적용).
- ★★ **negative control 미검출 2회 (방법론 자산)**: (h)에서 위임 지정 변형 MOD 32→31이 검출되지 않았다 — 모듈러를 줄이면 버퍼를 덜 쓸 뿐 경계를 넘지 않기 때문 → 커버리지 불변식을 양방향(31 부족/33 초과)으로 보강. (i)에서 지정 "센티넬 오초기화" 변형도 위반 0건이었다 — `win_nbuf==0` 가드가 있으면 첫 표본이 무조건 덮으므로 그 변형은 **무해**했고, 실제로 새는 유일 경로는 "표본 0건 윈도우"였다 → 신규 NC-2를 설계해 오변형에서 `2,147,483,647` 출력을 검출. **지정 문구대로만 돌렸으면 근거 없이 "안전"으로 오판할 뻔했다.**

### 실측 (카테고리 6.3(j) — M5-b ④런타임, 2026-09-03 랩실 사람 없음, 근거유형 = 실측)

- 로그 원본 = `~/ddingdong-측정결과/mic_m5b_2026-09-03/monitor.txt`(446줄, `.gitignore` 차단분 — SSoT엔 요약만). 프로토콜 = ①무자극 w=7~63(57윈도우) ②박수 w=64~76 ③노크 w=77~86, 구간 경계는 자기보고 기준(±1윈도우).
- ★ **무음 기준선 = rms_min 최솟값 63**(w=40, 안정 구간 63~79) — 6.3(e)의 "배경 rms 2.4M은 랩실 대화 포함이라 무음 기준선 아님" 갭을 메운다. ⚠️ 단 **"조용한 랩실"이지 완전 무음은 아니다**(에어컨·공조음 상시 포함) — 이 두 사실은 항상 같은 문장으로 인용할 것.
- 분리 마진 = rms_max 171 vs 노크 988 **5.8배** / peak 724 vs 8,584 **11.9배**. ★ peak 마진이 rms의 약 2배이나 본 값은 **3.2초 윈도우 집계**이고 실제 트리거는 64ms 버퍼 단위라 그대로 적용 불가 → **카테고리 3 SSoT("단순 RMS 임계값") 변경 판단은 M5-c로 보류**(본 Set에서 SSoT 미변경).
- ★ 박수 구간 w=67(peak 428)/w=73(peak 1299)이 무자극 수준 = 3.2초 윈도우 사이에 이벤트가 미포함됐다는 실증 → **윈도우 단위로는 이벤트 타이밍을 잡을 수 없다** = 트리거 판정이 버퍼 단위여야 한다는 근거.
- 시리얼 절단 정량화 = (h) 로그 기준 **31줄/147줄 = 21.1%** 손상, 형태는 줄 끝 절단이 아니라 **줄 중간 10~15B 덩어리 소실**. 태그별 M2(141B) 57.9% / raw dump(108B) 12.5% / M4(81B) 16.7% / M5a(80B) 0% / MEM(78B) 0% — **≤80B 62줄에서 손상 0건**, 손상률이 줄 길이에 단조 증가.
- ★ **baud 대역폭 가설 약화 (실측 + 논증)**: ① 보드 정의가 `-DARDUINO_USB_MODE=1` + `-DARDUINO_USB_CDC_ON_BOOT=1`이라 Serial은 UART가 아니라 **USB CDC** — 115200은 호스트 포트 명목값일 뿐 장치측 전송률과 무관(실측 = 빌드 설정 원문) ② 평균 듀티 = 윈도우당 323B ÷ 3.2s = 101B/s ÷ 11,520B/s = **0.9%**(논증) ③ UART라면 FIFO 포화 시 블로킹이지 드롭이 아니다(논증, 미실측). → `monitor_speed` 상향은 효과 없을 공산이나 **어느 쪽도 확정 아님**, 확정하려면 ④런타임 A/B 필요.

### 정정 (카테고리 6.3(k) — M4 판정 근거 2건 반증, 발견 2026-09-03 / 문서 반영 2026-09-04, 실측 반전 5회차)

- **(k-1) "24bit 유효 폭" 전제 반증**: 6.3(d) 검산은 raw 상한 = 24bit << 6 = 536,870,848을 전제하나 M5-b 실측 raw max = **1,585,489,920**(w=69) = 전제값의 **2.95배**. 역산 `1,585,489,920 >> 6 = 24,773,280`으로 24bit signed 최대(8,388,607)를 약 3배 초과. → **tz=6(정렬 폭)은 전 구간 불변으로 재확인**됐고 반증된 것은 "그 위가 24bit"라는 **유효 폭 부분뿐**이다. ⚠️ **`>>14`가 틀렸다는 뜻이 아니다** — shift 재판정은 초인종 실측 후로 보류. 6.3(c)/(d) 해당 서술은 취소선 처리(원문 보존).
- **(k-2) `mic_common.h` 주석과의 정합 확인**: 해당 주석(88~90행)은 "박수 max 296542208 >> 14 = 18099 = 풀스케일 55% → 클리핑 없음, 헤드룸 약 1.8배"라 적고 있으나 **decisions.md에는 이 "헤드룸 확정" 프레이밍이 애초에 등재된 적이 없다**(grep 확인 — (d)는 이미 "헤드룸 상한 검증 아님"으로 유보돼 있었다) → 취소선 대상 부재이므로 **순수 신설로 처리**(학습 17 catch). 오늘 박수 raw max는 296,542,208의 **5.35배**이고 clip=311(w=64)/163(w=69)/124(w=72)이 실측돼 주석의 "헤드룸 1.8배·클리핑 없음"은 근거를 잃었다. ⚠️ **주석 정정은 본 Set 범위 밖**(별도 코드 PR 소관, `firmware/` 0줄 수정 원칙) — 본 문서는 어긋난다는 사실만 기록.

### 확정 (카테고리 6.2 G29 — B안 채택, 2026-09-03 사용자 결정)

- G29(2초 캡처 윈도우가 1차 5초 예산에 미반영)를 **B안(하이브리드) = 트리거 시점 기준 pre-roll 일부 + post 일부로 2초 페이로드 구성**으로 확정(근거유형 = 논증). 기각 = 전량 pre-roll(A안, ≈1,954ms/39%)이면 트리거 이전 구간이 대부분 무음.
- **🔗 파급 — `KAKAO_HTTP_TIMEOUT_SECONDS` 재계산 (역방향 stale 해소, 발견 2026-09-04, 근거유형 = 논증)**: 상수값 1.5초는 **A안 전제로 역산**된 값이었다(5000 − 업로드 1900 − 105 ≈ 3000 ÷ 2회). B안 확정에 따라 재계산 = 5000 − post 1500 − 업로드 1900 − 105 = 1,495 ÷ 2회 ≈ **750ms**. ⚠️ **문서 등재만 한다** — 상수 코드 값 변경은 별도 PR 소관이며 본 Set 미수행.

**SSoT 정합 검증 (문서라 코드 3단계 N/A)**: 취소선 대상 문구는 6.3(c) "raw는 24bit를 6칸 좌시프트한 형태" / 6.3(d) "24bit max `8388607 << 6 >> 14 = 32767 = INT16_MAX` 정확 일치" **실존 선확인 후** 처리, 원문 삭제 0줄(취소선 안에 보존). (k-2)의 "헤드룸 1.8배" 프레이밍은 decisions.md `grep` **0건** = 부재 실증 후 신설로만 처리. 반증 수치(1,585,489,920 / 2.95배 / 24,773,280 / 5.35배 / clip 311·163·124)는 전부 M5-b 로그 원본 대조. PR #41 `b4b880a` / #42 `d024e23` 머지 = `git log --oneline` 대조. footprint RAM 순증 0은 4회·5회 연속으로 카운트 명시.

**비범위**: 코드 0 수정(`firmware/*`/`server/*`/`ml/*`/`dashboard/*` 전부 read only — PR #41/#42는 기 머지 코드 인용). `mic_common.h` 주석 정정 **미수행**(별도 코드 PR 소관, 사실만 등재). 카테고리 3 RMS 임계값 SSoT **미변경**(M5-c 보류). `KAKAO_HTTP_TIMEOUT_SECONDS` **상수 코드 미변경**(문서 등재만). 노션 미수정(Set 3 소관) / 프로젝트 지침 미수정(Set 2). `docs/decisions.md`(6.3 (h)(i)(j)(k) + 6.2 G29 확정 + 파급) + `docs/decisions-log.md`만 편집. 브랜치 없이 main 직 push(문서 단독).

**관련 카테고리**: 6.3(h)(i)(j)(k) (M5-a/a2 계층 · M5-b 실측 · M4 반증) / 6.2 (G29 B안 확정 + 타임아웃 재계산) / 3 (RMS 임계값 = M5-c 보류) / 20 (계측 → 실측 → 판정 · negative control 설계) / 29 (위임 vs 기존 컨벤션 충돌)
**관련 commit**: 코드 PR #41 `b4b880a` + PR #42 `d024e23`(기 머지) + 문서 반영 `c238f2c`(docs-only, PR 없음)

---

## 2026-09-05 (토) — PoC-(41) `/detect` ToF 메타 wire 확장(G10 수신측 CLOSE) + A-2 카카오톡 2차 알림 배선 + feed 2줄·CSR 왕복·15초 과금·토큰 자동갱신 실측 + 신규 미결 5건 (카테고리 6/6.4/7/7.5/7.6/8.3/20/21/30.9)

※ 작업일 2026-09-04(PR #43 · feed 2줄 프로브) ~ 2026-09-05(PR #44 · CSR 왕복 · 문서 반영). 자정을 넘긴 2일 세션이라 각 항목에 실측일과 문서 반영일을 병기한다.

### 결정 (카테고리 6.4 신설 — `/detect` ToF 메타 wire 확장, PR #43 `8827946`, 2026-09-04)

- ⚠️ **G10 수신측 CLOSE ≠ G10 CLOSE** — 송신측(마이크 M5-d + 통합 펌웨어가 실제로 ToF 메타를 실어 보내는 코드)은 여전히 **0줄**이며, 본 절이 닫은 것은 "서버가 받을 준비를 마쳤다"까지다.
- **(a) 산출물 (실측, `git show 8827946 --stat` 대조)**: 신설 `server/app/tof_meta.py` = 순수 함수 4개(`absent_meta`/`parse_tof_meta`/`telemetry_summary`/`evaluate_gate`). `constants.py` = wire 필드명 4 + 구조 상수 2(`TOF_ZONE_TOTAL=64` / `TOF_MOTION_AGGREGATE_TOTAL=16`). 수신 필드 4종은 6.2 G10이 지정한 이름 **그대로**(신규 필드 발명 0, 학습 16).
- **(b) ★ 핵심 설계 — 서버는 `tof_presence`를 재판정하지 않는다 (논증)**: Stage A 디바운스 3프레임(9.2)과 Stage B-2 latch 75프레임(9.4)은 **시간축 판정**이라 단발 POST 스냅샷으로 재구성 불가 → presence는 펌웨어 판정을 그대로 신뢰하고 나머지 3필드는 증거·표시용 telemetry로만 쓴다. 필드 표기 어휘(`near=n/64` / `center=NNNNmm` / `ndet=n/16`)를 9.3(b) 로그 정의와 맞춰 **서버 기록 ↔ 펌웨어 시리얼 로그 대조 가능**.
- **(c) 부재·범위이탈 처리 (논증)**: ToF 필드 부재 = **fail-open**(A-1 무회귀). 단 "게이트 통과"와 "ToF 부재로 미적용"이 응답·DB·로그에서 **구분 가능해야 한다**는 불변식. 범위 이탈은 400 거절도 부재도 아닌 **제3상태 "invalid"**로 기록. ★ `tof_center_mm` **상한 미설정** — 9.2(c) 최대 관측치 2953mm는 "그날 그 자리의 값"이지 센서 구조 상한이 아니라, 상한을 박으면 실측 없는 판정을 코드에 고정하는 셈(9.4(c) `aggmax` 기각 논리와 동형).
- **(d) 회귀 + 전 분기 열거 (실측)**: 회귀 30 → **42**(신규 12). 전 분기 **648건** 열거(ToF 4상태 × telemetry 3필드 각 3상태 = 108 × 클래스 3 × 신뢰도 2), 미정의 동작 **0**. ★★ **648건이 고유 24행 결정표로 완전 붕괴** — 결과가 (클래스, 신뢰도, ToF state, presence) 4-튜플만으로 결정되고 telemetry 3필드는 결과 영향 **0** = (b)의 **코드 증명**. negative control 5건 전건 검출, 위임 예고 NC-3("ToF 부재를 presence=true로 취급")이 **실재**했다.
- **(e) ④런타임 (실측 2026-09-04 / 문서 반영 2026-09-05)**: **하드코딩 문자열 소멸 확인** — 6.2 G10이 증거로 인용한 `zone_count=9 >= 8 + motion=true` / `zone_count=11 …`이 실호출 응답에서 **사라졌다**. ToF 부재 → `{"applied":false,"passed":null,"reason":"tof_absent"}` + `primary_sent=true`. doorbell·knock + `presence=false` → `primary_sent=false` + `skip_reason="tof_rejected"` + **카카오톡 미도착**(차단이 화면으로 증명). `fire_alarm` → 우회 + `reason="fire_alarm_bypass (…)"`, 카카오톡 도착. 결정표 24행 중 **실경로 확인 9행**.

### 결정 (카테고리 7.6 신설 — A-2 2차 알림 배선, PR #44 `a431961`, 2026-09-05)

- ⚠️ **A-2 발송 배선 CLOSE ≠ A-2 완료** — 자막이 아직 **mock 문구**(`server/app/utils.py` `_MOCK_TRANSCRIPTS`)이고 실 STT 소스 배선은 **0줄**이다. 발송 경로와 자막 소스는 분리해 읽어야 한다.
- **(a) 산출물 (실측)**: `kakao.py` 함수 5개(`_feed_description`/`_build_secondary_title`/`_post_memo_feed`/`_send_part`/`send_secondary`) + `constants.py` 3종.
- **(b)(c) 순서와 재시도 (논증)**: 사진 먼저, 자막 나중("누가 왔는지"가 "뭐라고 말했는지"보다 먼저 필요). 재시도는 **실패한 건만 개별 1회** — 2건 통째 재시도는 성공한 사진을 중복 발송하므로 금지. 분류는 예외 클래스 기준(`KakaoSendError`만 재시도, `KakaoTokenError`(401)는 재시도 없음). ★ 사진에서 401을 받으면 **자막 왕복도 태우지 않는다**.
- **(d) ★ 상태 표현 = 기존 키 값 조합, 프론트 수정 0 (실측)**: `secondary_sent` = **전부 성공** / `secondary_sent_at` = 사진 전달 시각 / `enrich_status="failed"` = 자막 실패. `to_dict()` 최상위 키 수 **11 불변**(프론트 `NotificationItem` 11필드와 1:1, 양쪽 실물 대조). ★ **결정적 근거** = `NotificationStatusBadge.derive()`가 `secondary_sent`를 `enrich_status`보다 **먼저** 보므로, `secondary_sent`를 "사진 성공"으로 정의하면 **부분 성공이 "전송 완료"로 렌더**된다 → "전부 성공"으로 정의.
- **(e) 자막 부재·길이 정책 (논증, 근거 판정은 7.5(g) 실측)**: 자막 부재 시 feed 1건만 발송하고 text 미호출 — **자막 없음 ≠ 실패**. description = 감지 시각 1줄(약 20자 고정). 7.5(g)가 "상한 기준은 글자 수가 아니라 줄 수"라 판정했으므로 **자막 길이 상한 상수를 만들지 않고, 애초에 상한이 필요 없는 길이만 생성**한다.
- **(f) 동기 발송 유지 (논증·산술)**: 정상 p95 ≈1초(예산 6.5%), 최악 ≈7.5초(50%) — 펌웨어 `HTTP_TIMEOUT_MS=10000` 안. 비동기 아키텍처 불요.
- **(g) 회귀 + 전 분기 (실측)**: 회귀 42 → **60**(신규 18). 전 분기 **164건** 열거, 미정의 동작 **0** → **고유 6행 결정표로 붕괴**. negative control **7건** 전건 검출, NC-4(발송 순서 뒤집기)가 **실재** — 결과만 검사하는 케이스로는 무해했고 **wire 요청 시퀀스를 직접 검사**해야 잡혔다.
- **(h) ④런타임 (실측 2026-09-05)**: 카카오톡 **3건 도착** — 1차 텍스트 → 사진 카드 → 자막, **순서 실물 확인**. 사진 렌더 정상(600×400 JPEG) / description "9월 5일 13:39 감지" 무절단 / 자막 전문 표시. 2차 체인 지연 = 13:39:04.434 → 13:39:07.044 = **2.61초**(15초 예산의 17.4%). ⚠️ **ESP32 캡처·업로드 미포함 — 2차 전 구간 수치가 아니다.** `doorbell 0.70`이 `pending`으로 통과 = 신뢰도 경계(strict `<`) **실증 3회차**.

### 실측 (7.5(g) feed 2줄 확증 / 카테고리 7 STT · 30.9 CSR 왕복 / 7.5(e) 토큰 자동 갱신)

- **★ feed 본문 2줄 제약 = 확증 (실측 2026-09-04 / 문서 반영 2026-09-05, 근거유형 = 문서 인용·미실측 → 실측 승격)**: 실계정 memo feed **3단계 프로브** + 모바일 육안 — P1 자막 15자 **1줄 전문 렌더** / P2 52자 **2줄 절단 + 말줄임표** / P3 110자 **2줄 절단 + 말줄임표**. **판정 1** = 2줄 상한 실재(문서 인용이 맞았다). **판정 2** = **상한 기준은 글자 수가 아니라 줄 수이며 절단 지점은 렌더 폭에 종속** — 52자와 110자가 둘 다 2줄에서 **서로 다른 글자 위치**에서 잘렸다 → 서버에서 "자막 N자 상한"을 정하는 것은 **원리적으로 불가능**. 이 판정이 7.6(e) 설계를 낳았다. ★★ **근거유형 교훈**: 7.5(b)에서 **반증된** 200자 건과 본 건은 **같은 "문서 인용·미실측" 등급**이었는데 결과가 갈렸다(하나는 반증, 하나는 확증) — **근거유형이 같아도 결과는 갈린다.** 프로브 없이 "이번에도 문서가 틀렸겠지"로 넘어갔다면 자막이 잘린 채 A-2를 짰을 것이다.
- **★ CSR 왕복 ④런타임 + 15초 단위 과금 확증 (30.9, 실측 2026-09-05)**: `POST https://naveropenapi.apigw.ntruss.com/recog/v1/stt?lang=Kor`, 입력 16kHz mono 16bit PCM WAV **131,756 B**(약 4.1초, macOS `say` TTS 생성) → 응답 `{"text":"택배 왔습니다 문 앞에 두고 갈게요"}`, **왕복 0.892초**(15초 예산의 5.9%). ⚠️ **정직 표기** — 원문 첫 어절 "계세요?"가 **누락**됐고 TTS 어택 문제인지 인식 실패인지 **미규명**이다(실측 1건, **단정 금지**). ★★ **15초 단위 과금 = 문서 인용 → 실측 확증**: 콘솔 Usage Statistics에서 4.1초 호출 1건이 **usage=15**로 계상 → **5초를 쓰든 15초를 쓰든 요금이 같다** = 2차 녹음을 15초까지 늘려도 추가 비용 0원이며, 현재 5초 설계는 카카오 15초 예산 제약이지 **요금 제약이 아니다**. 한도 소진 = 일 500초 중 15초(3%) / 월 5,000초 중 0.3%. 콘솔 경로 정정(학습 13 화면 우선 3회차) = Usage Statistics 실 URL `console.ncloud.com/naver-service/usage`(Application과 별도 메뉴). ★ Client ID·Secret 실값 미기록.
- ⚠️ **STT 왕복 실증 ≠ 서버 배선** — `server/`의 STT 호출 코드는 여전히 **0줄**이고 7.6 A-2 자막은 mock 문구다. 이 두 사실은 분리해 읽어야 하며, 카테고리 7 STT 항목 / 7.6 서문 / 30.9 세 군데에 동반 등재했다.
- **★ 카카오 토큰 자동 갱신 실증 (7.5(e), 실측 2026-09-05)**: `.env`의 `KAKAO_ACCESS_TOKEN`이 만료(`ACCESS_TOKEN_EXPIRED`, code -401) 상태였는데도 발송이 성공했다. DB(`kakao_tokens` SINGLETON_ID=1)의 access 토큰으로 `/v1/user/access_token_info`를 조회하니 `expires_in 21083`초 — 6시간 TTL(21600) 대비 약 8.6분 전 발급이고 그 시각이 그날 첫 `/detect` 호출 시점과 일치 → PR #40의 **401 자가 치유 + refresh 갱신 배선이 실동작함이 시계로 증명**됐다. ⚠️ 단 **"잔여 1개월 미만일 때만 refresh 재발급"은 여전히 문서 인용·미실측**이며 판정 방법(2026-10월 초 로그 확인)도 그대로 유효하다.
- **터널 재기동 절차 확정 (7.4(d), 실측 2026-09-05)**: 세션 중 컴퓨터 재부팅으로 터널·서버가 소실돼 전 절차를 재수행한 것이 발표 당일 리스크의 실물 예행이 됐다. 확정 절차 = 터널 기동 → 새 주소 확인 → `.env`의 `DDINGDONG_CAPTURE_URL_BASE` 교체 → 서버 재기동 → 관통 확인. ★ **관통 확인은 변수격리 도구** — 외부 URL로 `/api/v1/notifications`를 찍어 401이면 서버 도달 성공(인증만 미통과), 530·502면 터널이 서버를 못 찾은 것이라 **한 번의 호출로 두 원인을 가른다**. ⚠️ 그럼에도 실 public 호스팅 제품 확정은 미결 유지(터널은 SLA 없는 백업 경로).

### 신규 (카테고리 20 · 21 — 방법론 자산 3건)

- **카테고리 20 「negative control은 `python3 -B`로 실행 — `.pyc` 캐시 오염」 (발견·반영 2026-09-05, 실측)**: PR #44 NC-5의 실패 목록이 NC-4의 것을 통째로 포함한 8건으로 나왔다. 원인 = NC-4의 순서 swap 변형이 두 블록을 맞바꾸기만 해 **파일 크기가 보존**됐고 복원 쓰기가 **같은 초 안에** 일어나 `.pyc` 무효화 조건(mtime + size)을 둘 다 피해 캐시된 변형 바이트코드가 로드됐다. `python3 -B` 재실행으로 참값 확보. ★ 이번엔 오염이 **거짓 양성 방향**이라 단서가 남았지만, **반대 방향이었다면**(변형이 미적용돼 "검출 X") 근거 없이 "가드가 없다"는 결론을 얻고 **없는 문제를 고치러 갔을 것**이다. ★ **층이 다르다** — PR #41(MOD 31 무해) → #42(센티넬 무해) → #43(NC-3 실재)의 계보 4회차이나 앞 셋은 **불변식 설계 문제**이고 본 건은 **실행 환경 문제**다.
- **카테고리 20 「negative control 함정 예고 = 2회 연속 적중」 (발견·반영 2026-09-05, 실측)**: PR #43 NC-3과 PR #44 NC-4가 둘 다 **실재**했고, 둘 다 결과만 검사하는 케이스로는 무해했으며 전용 불변식(응답 3키 동시 고정 / wire 요청 시퀀스 검사)을 설계해야 잡혔다. PR #41·#42의 "지정 변형이 무해했다" 실패 이후 위임에 **"그 변형이 어떤 불변식을 깨는지 함께 적으라"**를 넣은 것이 효과를 냈다.
- **카테고리 21 「시크릿 파일(`.env`) 편집 위생」 (발견·반영 2026-09-05, 실측)**: `echo 'KEY=값' >> .env`를 **파일 끝 개행 확인 없이** 실행해 `KAKAO_REFRESH_TOKEN` 값 뒤에 URL이 이어붙어 **토큰이 무효화**됐다(복구 후 정상 동작 확인). 실측 실행 환경이 파손되면 그 위에서 낸 측정값이 전부 무효가 되므로 「프로세스 위생」과 같은 층의 검증 유효성 문제다. 재발 방지 ① `.env`에 `>>` 하기 전 `tail -c 1 .env | xxd`로 마지막 바이트가 `0a`인지 확인 ② 내용 확인은 `grep -oE '^[A-Z_][A-Z0-9_]*' .env`(키 이름만)로 한다 — **값을 찍는 grep은 시크릿을 화면에 노출한다**. 이 사고에서 **리프레시 토큰이 실제로 화면에 노출됐다**(값 자체는 미기록). 🟡 파생 미결 = `.gitignore`가 `.env`·`.env.local`만 잡고 **`.env.bak`은 잡지 않는다**(기록만, `.gitignore` 수정은 별도 소관).

### 신규 미결 5건 (발견 2026-09-04~05 / 문서 반영 2026-09-05)

- 🟡 **6.4(f) 가짜 ToF 하드코딩 잔존 (실측 grep)**: `/detect` 경로에서는 소멸했으나 `server/seed.py`(시드 5건 중 **4건**) + `dashboard/src/lib/mock-data.ts`(5건 중 **4건**)에 `zone_count=… >= 8 + motion=true` 문자열이 그대로 남아 있다(나머지 1건씩은 `fire_alarm_bypass`). **부스 데모에서 seed 데이터가 화면에 뜨면 가짜 ToF 문자열이 관람객에게 보인다**(카테고리 26 연동). 해소 = 데모 시나리오 소관.
- 🟡 **7.6(i) 2차 자막 실패의 영구 포기 정책 (논증)**: (d)에서 `/enrich` 종결 상태에 `"failed"`를 넣어 재처리를 막았다. 대안(중복 사진 발송)보다 낫다고 판단했으나 **일시적 네트워크 실패와 영구 실패를 구분할 근거가 아직 없다**(PR #44 한계 = 네트워크 타임아웃 미재현). 트리거 = 실 ESP32 2차 클라이언트 연동 후 재판단.
- 🟡 **8.3 프론트 뱃지 과소 표기 (실측)**: `NotificationStatusBadge.derive()`가 (사진 실패 + 자막 성공) / (자막 없음 + 사진 실패) 조합을 "1차 발송"으로 렌더한다. 금지선인 "부분 성공 → 완전 성공" **오표기는 아니지만** 과소 표기다. 해소 = `derive()` 분기 1개 추가, 대시보드 소액 PR 소관.
- 🟡 **8.3 ToF 상세가 화면에 미표시 (실측 grep)**: `dashboard/src/components`·`pages`에서 `tof_check` 참조 **0건**. USP 2층의 1차가 ToF 융합 서사인데 **화면에 그 근거가 없다** — 6.4로 서버가 실 ToF 값을 내기 시작했으므로 표시 대상이 생겼다.
- 🟡 **카테고리 6 2워커 동시성 — `/enrich` 재처리 가드(409) 경합 (논증)**: 같은 `client_request_id`로 `/enrich`가 동시에 들어오면 409 가드가 경합할 수 있다(SELECT~UPDATE 간 격리 없음). 기존 구조의 성질이나 7.6 2차 발송이 붙으며 결과가 "**중복 사진 발송**"으로 커졌다. 실 ESP32는 단일 기기 + 5초 rate limit이라 현실 위험은 낮다. 해소 = rate limit Redis 교체와 동일한 11주차 구간.

**SSoT 정합 검증 (문서라 코드 3단계 N/A)**: 신설 절 번호 **6.4** = `grep -nE "^### 6\."`로 6.1~6.3만 존재 확인, **7.6** = `^### 7\.`로 7.1~7.5만 존재 확인(둘 다 충돌 없음). 7.5(g)의 "판정 전까지 결론 선반영 금지" 예약 서술은 **삭제 없이 ✅ 판정 결과를 append**(원문 보존). 카테고리 7 STT 항목의 `~~A-1 STT 왕복 실측 = 미실측(defer)~~`는 실존 선확인 후 취소선 + 실측 결과 append. 요금 불일치("초당 0.5원/분당 30원" ↔ 15초당 4원)는 30.9 기존 취소선 정정과 대조 일치. 인용 수치(131,756B / 0.892초 / usage=15 / 21083초 / 2.61초 / 648→24행 / 164→6행 / 회귀 30→42→60)는 전부 PR 본문·콘솔 화면·실행 로그 원본 대조. PR #43 `8827946` / #44 `a431961` 머지 = `git log --oneline` + PR squash 대조. 카카오 토큰·시크릿 / NCP Client ID·Secret / 터널 주소 **전부 미기록** — `.env` 사고는 "리프레시 토큰이 화면에 노출됐다"는 **사실만** 기록.

**비범위**: 코드 0 수정(PR #43/#44는 기 머지 코드 인용, 본 문서 세션 미접촉). **G10 송신측 0줄 / A-2 실 STT 자막 배선 0줄 / M5-c 판정 계층 / 프로토콜②(정지 사물 대조) / ESP32 미연동 / EC2 미기동 / ML 2차 모델** 전부 미착수. G12(fire_alarm이 신뢰도 게이트도 우회하는가)는 **결론 미기재, 사용자 판단 대기 유지**. `mic_common.h` 주석 · `.gitignore` 패턴 · `KAKAO_HTTP_TIMEOUT_SECONDS` 상수 = **기록만, 코드 미수정**. 노션 미수정(Set 3 소관) / 프로젝트 지침 미수정(Set 2). `docs/decisions.md`(6.4 신설 + 7.6 신설 + 7.5(e)(g) append + 카테고리 7 STT append + 7.4(d) + 30.9 append + 카테고리 20 2건 + 카테고리 21 1건 + 신규 미결 5건) + `docs/decisions-log.md`만 편집. 브랜치 없이 main 직 push(문서 단독).

**관련 카테고리**: 6.4 (ToF 메타 wire 신설) / 7.6 (A-2 2차 알림 신설) / 7.5(e)(g) (토큰 자동 갱신 실증 · feed 2줄 확증) / 7.4(d) (터널 재기동 절차) / 7 (STT 왕복 실증 ≠ 서버 배선) / 30.9 (CSR 왕복 · 15초 과금 · 콘솔 경로) / 6 (2워커 409 경합) / 8.3 (뱃지 과소 표기 · ToF 미표시) / 20 (`python3 -B` · 함정 예고 2회 적중) / 21 (`.env` 편집 위생) / 3 (클래스별 ToF 정책 · G12 미결)
**관련 commit**: 코드 PR #43 `8827946` + PR #44 `a431961`(기 머지) + 문서 반영 `6a0a1f0`(docs-only, PR 없음)

## 2026-09-08 (화) — PoC-(42) 실 STT 서버 배선(7.7 신설) + G12 확정(신뢰도 게이트 전역화) + 대시보드 표시 결함 4종(8.4 신설) + NCP 한도 문서 모순 해소 + 신규 미결 4건 (카테고리 3/7/7.6/7.7/8.3/8.4/10/20/27/29.5/30.9)

※ 작업일 = 2026-09-08 단일 세션. 코드 PR 3건(#45 · #46 · #47)이 같은 날 머지·검증됐고 본 엔트리는 그 SSoT 반영분(문서 전용, 코드 0 수정)이다.

### 결정 (카테고리 3 — G12 확정, PR #46 `82a4870`)

- 🔴 **역방향 stale 해소가 본 세션 최우선이었다** — PR #46으로 코드가 확정 사양으로 움직였는데 `decisions.md`의 G12 항목은 여전히 **"[미결 — §9 사용자 판단 요청]"**이었다. SSoT가 코드보다 뒤처져 다음 세션이 G12를 다시 미결로 읽을 상태였다.
- **결정 (2026-09-08 사용자 확정, 근거유형 = 논증)**: 신뢰도 임계값 비교를 `fire_alarm` early return **앞으로**. `fire_alarm`의 **ToF presence 게이트 우회는 유지**. 즉 화재경보도 **신뢰도 0.70 미만이면 1차 미발송**이고, 0.70 이상이면 ToF와 무관하게 발송한다. 카테고리 3 ①의 "무조건"은 **ToF 게이트 문맥**으로, ②는 **클래스 무관 전역 게이트**로 확정.
- **판단 근거 3 (논증)**: ① 원 결정의 "무조건 발송"이 ToF 문맥인지 threshold까지인지 **문면상 갈리지 않았다** ② 부스에서 초인종을 눌렀는데 화재 대피 알림이 나가면 **그 자체가 사고**(33.2 confusion `doorbell → fire_alarm` 오분류 10건 = 최다) ③ 화재경보는 **지속음**이라 miss 비용이 비대칭적이지 않다.
- **실경로 재현 (실측)**: 2026-09-05(0.66 / 0.58 / 0.53 / 0.47 발송) + 2026-09-08(`fire_alarm 0.45` 발송) → **잠복이 아니라 상시 동작**이었다.
- **불변 항목 (실측)**: `CONFIDENCE_THRESHOLD` **0.7**과 strict `<`는 **무변경** — 바뀐 것은 **비교 시점**뿐. ∴ 0.70 경계 실증 3회(9/03·9/05·9/08) 그대로 유효. 회귀 83 → **89**. 커밋 타입 `🐛 Fix` 근거 = 종전 코드가 **카테고리 3 SSoT ② 위반**이었으므로 신규 기능이 아니라 **위반 정정**.
- ★ **파급**: "70% 미만 미전송"이 이제 **3클래스 전부**에 적용된다. 클래스별로 갈리는 것은 **ToF 게이트뿐**이다.

### 결정 (카테고리 7.7 신설 — 실 STT 소스 배선, PR #45 `9b3e3a2`)

- ⚠️ **STT 배선 CLOSE ≠ 2차 15초 체인 검증** — 아래 1.755초는 **서버측 구간**이며 ESP32 캡처·업로드·2차 페이로드 전송 **미포함**이다. **STT 배선 CLOSE ≠ 실 육성 인식률 검증**(입력이 전부 TTS 합성음).
- **(a) 산출물 (실측, `git show 9b3e3a2 --stat` 대조)**: 신설 `server/app/stt.py`(191줄) = 예외 2계층(`SttAuthError`/`SttRequestError`) + 순수 함수 3개(`wav_from_pcm16`/`build_request`/`parse_transcript`) + `is_real_mode()` + 단일 진입점 `transcribe()`. `constants.py` STT 상수 5종 / `config.py` NCP 자격증명 노출 / `routes.py` 자막 소스 전환. 회귀 60 → **83**.
- **(b) 🔴 핵심 설계 — STT 실패는 `enrich_status="failed"`가 아니다 (논증)**: 7.6(d)의 `failed`는 **자막 발송 실패**를 뜻하고 7.6(e)가 **"자막 없음 ≠ 실패"**를 이미 규정했다. ∴ STT 실패 5종(타임아웃/API 오류/인증 실패/빈 텍스트/계약 위반 응답)은 **전부 "자막 부재" 경로로 합류**하고 사진은 정상 발송된다. 깨면 PR #44의 **4조합 상태 표현이 무너진다**.
- **(c)~(f) 설계 판단 (논증, 입력 실측 = 30.9)**: **WAV 컨테이너 합성**(raw 직송은 미검증 경로 — 30.9 왕복 실측이 WAV로만 수행됐다) / **재시도 없음**(15초 단위 과금 + 소프트 한도라 재시도는 과금·한도만 배가 / 카테고리 7 "1차 재시도 없음" 동형 / **백오프 상수 미신설** = 실측 근거 0인 죽은 상수 회피) / **env 게이트**(`NCP_CLIENT_ID`·`NCP_CLIENT_SECRET` **둘 다** 설정돼야 real, `model_serving.is_real_mode()` 동형) / `STT_HTTP_TIMEOUT_SECONDS=3.0`(왕복 0.892초의 약 3.4배, ⚠️ **서버측 구간 기준·ESP32 미포함**).
- **(g) ④런타임 (실측 2026-09-08, 터널 + 실호출 + 카카오톡 화면)**: 입력 = 16kHz mono WAV 131,756 B에서 헤더 44 B를 뺀 **raw PCM 131,712 B**(macOS `say`). 응답 `transcript` = **"계세요 택배 왔습니다 문 앞에 두고 갈게요"**(**첫 어절 "계세요" 포함**). `stt.language="ko-KR"` / `stt.confidence=null`(CSR 미제공). 2차 체인 **1.755초**(예산의 11.7%). `enrich_status="completed"` + `secondary_sent=true` + `tof_check.applied/passed=true`. **카카오톡 3건 도착**(1차 텍스트 → 사진 카드 → 자막 text), 자막 문구가 JSON `transcript`와 **완전 일치**, feed description `9월 8일 11:04 감지` 절단 없음. ★ **자막이 2줄로 렌더됐으나 잘리지 않았다** — 7.5(g) 2줄 상한은 **feed description**에 걸리고 **text 템플릿은 별개**다 → A-2 2건 분할 설계(7.6(b))가 화면으로 정당화됐다.
- **(h) ⚠️ 9/05 "첫 어절 계세요? 누락"이 재현되지 않았다 (실측 2건, 단정 금지)**: 같은 `say` 생성기·같은 파이프라인인데 이번엔 들어왔다. **TTS 어택 문제가 아니었던 쪽으로 기운다**는 정도까지다. **원인은 여전히 미규명**이며 30.9의 "미규명" 서술은 그대로 유효.
- **(i) 🔴 실패 폴백도 같은 세션에서 실증됐다 (실측)**: 앞선 시도에서 CSR이 **HTTP 429**를 반환했고 서버는 `enrich_status="completed"` + `secondary_sent=true`로 **사진을 정상 발송**하고 `stt: null`만 남겼다 → **(b) 불변식이 실물로 증명**. 로그 = `WARNING in routes: enrich stt: mode=real result=failed elapsed_ms=94.68 cause=CSR 호출 실패: HTTP 429`. ★ **`mode=real`이라는 한 단어가 진단 방향을 결정했다** — "안 불렀다"와 "불렀는데 실패"를 가르는 로그 불변식이 실물에서 값을 했다.

### 결정 (카테고리 8.4 신설 — 대시보드 표시 결함 4종, PR #47 `846b342`)

- **(a) 산출물 7파일 (실측)**: 신설 `NotificationTof.tsx` / 수정 `NotificationCard.tsx` · `NotificationStatusBadge.tsx` · `lib/format.ts` · `lib/mock-data.ts` · `types/notification.ts` · `server/seed.py`. 커밋 **4분리**(`✨ Feat` 1 + `🐛 Fix` 3), 중간 상태 빌드 **4/4 통과** 실측. ※ 위임이 커밋 분리를 느슨하게 줬으나 `git-convention.md` 컨벤션을 **우선**(학습 16).
- **(b) 🔴 ToF 3상태 = 6.4(c) "구분 가능" 불변식의 화면 판 (논증)**: `applied/passed` 조합으로 **사람 확인 / 사람 없음 / 검증 안 함** 3분기. `reason` **원문 보존**(9.3(b) 시리얼 로그 대조용). **라벨+아이콘+색 3중 표기**(색 단독 의존 금지, 8.3).
- **(c) 뱃지 과소 표기 해소 — 서버 변경 0 / 새 뱃지 어휘 0 (실측)**: 과소 표기 2조합이 **`enrich_status==="completed" && secondary_sent_at===null`로 유일 식별**된다(서버 `routes.py` 역추적). `skipped`(화재경보 2차 미시도)는 안 걸린다. ★ **`derive()`의 읽는 순서는 무변경** — 7.6(d) 결정적 근거를 지킨 채 **분기만 추가**. ★★ **근본원인이 "순서가 틀렸다"가 아니라 "분기가 좁다"였다** — 8.3 미결이 적어 둔 진단이 코드 재검증에서 뒤집혔다(학습 19·21 = 등재된 미결의 **진단**도 검증 대상).
- **(d) STT confidence null 표시 (실측)**: `formatConfidence(value: number | null)`, `null` → **"정보 없음"**. ★ **`=== null` 엄격 비교**(`!value`로 완화하면 실측 0.0이 "정보 없음"이 된다). ★ **null을 숫자로 채우지 않았다** — 없는 값을 지어내는 것은 실측 없는 판정이다(카테고리 20).
- **(e) 가짜 ToF 문자열 교체 (실측 grep)**: `seed.py` 4건 / `mock-data.ts` 4건을 **실 `reason` 어휘 형식**으로 교체. ★ **삭제가 아니라 교체** — 지우면 화면이 비고 부스에서 "데이터 없는 시스템"으로 보인다. 사후 `zone_count=` 잔존 = **코드 전역 0건**(⚠️ `docs/` **7건**은 역사 기록이라 **의도적 무변경**). mock 거부 건은 **G12 확정에 맞춰 신뢰도 부족 건에 얹었다**(문서 확정과 mock 정합).
- **(f) ★ 프론트 negative control 하네스 신설 (방법론 자산)**: 변형된 실제 소스를 `vite build --ssr`로 재번들 → `react-dom/server` 렌더 → **텍스트 라벨 단언**. 대시보드에 **테스트 러너가 없는데도** NC를 돌린 방법(신규 의존성 0). ⚠️ **한계**: 하네스가 scratchpad에만 있어 **CI 회귀 방지 효과 0** / **텍스트 라벨만** 검사하므로 색·아이콘·레이아웃·대비비·터치 타깃 **미검증**.

### 실측 (30.9 — NCP 호출 한도 문서 내부 모순 해소 / 콘솔 화면 catch)

- 🔴 **판정: 8/12 "당일 30,000 / 당월 300,000"과 9/02 "일 10,000,000 / 월 30,000,000"은 모순이 아니라 서로 다른 층이었다.** 한도 **설정 입력 안내**에 월 `1~30,000,000` / 일 `1~10,000,000` 명기 = **시스템 상한**. **한도 변경 이력** 탭은 **`2026-08-20 10:56:44` 1건뿐**이고 `30,000(Day)/300,000(Month)` → `500(Day)/5,000(Month)`으로 적혀 있다 → **8/12 값은 그때의 「기본 설정값」**이었고 변경 이력의 "이전 한도"와 **정확히 일치**한다. ★ **8/12 서술에 취소선을 긋지 않았다** — 틀린 값이 아니라 잘못 본 것도 아니다. **판정만 추가**하는 형태로 정리.
- ★ **소프트 한도 문구 원문 실측**: "설정이 적용되는 동안 수 초 내에 한도를 초과하여 호출할 수 있습니다" — **510초/설정 500초의 초과분이 이 문구 그대로**다((3)의 "하드 스톱 아님"이 원문·실측치 양쪽으로 확증).
- 🔴 **통보대상 = 담당자 0명이었다 (실측)**: 임계 70% 알림 체크는 켜져 있었으나 **수신자가 0명이라 경고가 오지 않았다.** 2026-09-08 등록 완료. ★ **"설정했다"와 "설정이 작동한다"는 다르다.**
- **일별 한도 500 → 600초 상향 (2026-09-08, 논증)**: 무제한이 아니라 **600만 올린 것은 한도 자체를 관측 도구로 쓰기 위함**이다 — 폭주 경로가 있으면 600도 소진될 것이고 **그 자체가 진단**이 된다.

### 신규 (카테고리 20 · 27 — 방법론 자산 3건)

- **카테고리 20 「`python3 -B`의 한계 + 4단계 보강」 (발견·반영 2026-09-08, 실측)**: 🔴 **`-B`는 `__pycache__` 쓰기를 막을 뿐 기존 `.pyc`를 무효화하지 않는다**(PR #46 발견) — 기존 자산화 문장은 **필요조건이지 충분조건이 아니었다**. 해법 = **`assert 변형본 != 원본`으로 변형 적용을 별도 보장**. PR #46 NC-6 최초 시도가 이 assert에 걸려(lambda 오작성 → 파일 무변경) **"무해 변형이 통과했다"는 거짓 결론을 막았다.** PR #47은 **앵커 매치 정확히 1건 확인 + 디스크 재독 + `assert 변형본 != 원본` + 복원 후 `assert 복원본 == 원본`** 4단계로 확장. ★ **계보 4층**: 관측률(관측 설계) → 불변식 부족(검증 설계) → 실행 환경(`.pyc`) → **변형 적용 자체의 검증**.
- **카테고리 20 「negative control 미검출의 판정 — 「가드 부재」가 아니라 「도달 불가」일 수 있다」 (신설, 발견·반영 2026-09-08, 실측)**: **PR #46 NC-6** = `fire_alarm` 분기를 ToF 거부 분기 뒤로 옮기는 변형이 무해 → **스위트가 과잉 구속하지 않음의 증거**로 판정. **PR #47 NC-2b** = 순수 순서 뒤집기가 무해 → 이유 = `secondary_sent=true ⟹ photo_sent=true ⟹ secondary_sent_at ≠ null`이므로 **"완료 분기"와 "실패 분기"가 동시에 참이 되는 상태가 서버 데이터에 존재하지 않는다**. ★★ **#47이 한 층 더 깊다** — #46이 "스위트가 과잉 구속하지 않는다"였다면 #47은 **"지정된 변형이 애초에 결함이 될 수 없었다"**를 **도달 가능성으로 증명**했고, 금지 상태를 실제로 만드는 변형을 NC-2로 **재규정**하고 순수 순서 뒤집기를 NC-2b로 **분리**했다. ★ 원칙 = **미검출일 때 "가드가 없다"로 결론짓기 전에 (1) 도구가 살아 있는지 (2) 그 변형이 도달 가능 입력에서 결함이 되는지를 먼저 확인한다.**
- **카테고리 27.8 「위임 프롬프트 절 번호·인용 오기 누적 — grep 후 인용 강제」 (신설, 실측)**: ★ **Claude 자신의 실수도 프로젝트 아티팩트다.** **PR #45** = §4-3(f)가 "종결 상태 3종의 SSoT = 6.1"로 지목했으나 실물은 **7.6(d) + `routes.py`**(인용 위치 오류) / Step 4-b "자격증명 미설정 → 자막 부재"가 Step 3-d "mock/real 패턴 준수"와 **양립 불가**(게이트 정의상 "real + 자격증명 없음"은 도달 불가 = 위임 자기모순). **PR #47** = N2 축에 `stt`를 넣었으나 `derive()`는 `stt`를 읽지 않는다(형제 필드) / NC-2 규정이 **금지 상태를 만들지 못했다** / 커밋 분리를 느슨하게 줬으나 MCP가 컨벤션 우선. **대화형** = `picsum.photos`에 `-L` 누락 → **0바이트 JPEG**(`file` 명령이 잡았다, 9/05 133바이트 사고와 같은 계열) / `/enrich` 대상을 `request_id`로 줬으나 실제는 `client_request_id` / `/detect`에 `device_id` 누락. ★ **누적 패턴** = 절 번호 오기가 PoC-(41) **3건** → PR #45 **1건** → PR #47 **2건**으로 계속 나온다 → **작성 측**은 `git show HEAD:docs/decisions.md | grep -nE "^## 카테고리|^### "` 실행 후 인용, **수행 측**은 위임 인용값도 실물 대조(학습 13).

### 신규 미결 4건 (발견·문서 반영 2026-09-08)

- 🔴 **30.9 CSR 호출 301건 출처 미규명 (실측)**: 콘솔 실측 = `success 34 / failed 267`(총 301건) / `usage 510초`. **510 ÷ 15 = 34**로 success와 정확히 일치 → **과금은 성공분에만, failed 267건은 과금 0**. 당월 누적 525초 = 9/05의 15초 + 오늘 510초. **우리가 낸 것으로 확인된 호출** = 본 세션 `/enrich` 경유 **429 실패 1건 + 성공 1건**이며 **나머지 대다수는 미규명**이다. **반증된 가설 2개(기록 보존)**: ① 회귀 테스트가 실 API 호출 → **무죄**(테스트 자격증명이 `"test-ncp-client-id-not-real"` 가짜 문자열 + `app.stt.urllib.request.urlopen` 스텁 → 가짜 키로는 success가 날 수 없다) ② 다른 Application이 같은 키 사용 → **무죄**(Application 목록 1개뿐). ⚠️ 🔴 **원인 추정을 적지 않았다** — 오늘 세운 가설이 전부 반증됐으므로 **「미규명」으로 못 박고** 판정 방법만 등재했다 = **일별 한도 600 + 통보대상 등록 상태에서 재발 여부 관측**. ⚠️ **보안 이슈 가능성을 배제하지 않았으나 근거가 없어 단정하지 않는다.**
- 🟡 **29.5 "도어벨" 용어 SSoT 위반 잔존 2건 (실측 grep)**: `dashboard/src/lib/notification-meta.ts:1`(주석) / **`dashboard/index.html:8`(meta description — 사용자 노출)**. ※ `server/app/constants.py` 3건은 **「"도어벨" 미사용」이라는 컨벤션 서술 자체**라 정상(오탐 아님).
- 🟡 **8.4(f) 프론트 NC 하네스가 repo 밖**: CI 회귀 방지 효과 0. 러너 도입은 **신규 의존성 금지**에 걸린다 → **deferred 후보**(11주차 or 폴리시).
- 🟡 **카테고리 10 커밋 이력 규약 14종 이탈 2건 (실측 `git log`)**: `🧪 Spike`(`086c6da`) 1건 / `🎨 Style`(`3544db4`) 1건. **과거 이력이라 소급 정정 대상은 아니나** `git-convention.md`에 추가할지 판단 필요.

**SSoT 정합 검증 (문서라 코드 3단계 N/A)**: 신설 절 번호 **7.7** = `grep -nE "^### 7\."`로 7.1~7.6만 존재 확인 / **8.4** = `^### 8\.`로 8.1~8.3만 존재 확인 / **27.8** = `^### 27\.`로 27.1~27.7만 존재 확인(3건 모두 충돌 없음). 편집 앵커 **16건 전건 `count == 1` assert 통과**(라인 번호 미사용, 패턴 매칭). 취소선 총수 착수 전 **41줄 / 84개** → 종료 **47줄 / 100개**(신규 8쌍 = 16개, **짝수 유지 = 마크다운 무파손**), **삭제 0줄**을 제거 9줄 전건 토큰 보존 검사로 증명(전부 취소선 래핑·라인 중간 삽입). 위임 인용값 실물 대조 = 회귀 60→83→89 (`grep -c "def test_"` 커밋별 대조) / PR #47 7파일·커밋 4분리 (`git show --stat` + 커밋 본문) / `stt.py` 예외 2계층·순수 함수 3개·상수 5종 (실파일 grep) / `zone_count` 코드 0건·`docs/` 7건 / "도어벨" 위반 2 + 컨벤션 서술 3 / 규약 이탈 `🧪 Spike`·`🎨 Style` 2건 (`git log` 전수) — **불일치 0건**. 요일 `date -j -f "%Y-%m-%d" "2026-09-08" "+%a"` = **Tue = 화** 검산. 실존 G-ID 전수 `grep -oE '\bG[0-9]{1,2}\b' | sort -u` = G10·G12·G14·G18·G21·G22·G24·G27·G28·G29(부재 ID 미검색). 원격 = `git ls-remote origin` 실물 확인(`refs/heads/main` 단일, `git branch -r` 미사용 — 학습 20). NCP Client ID·Secret / 카카오 토큰 / 터널 주소 **전부 미기록**.

**비범위**: **코드 0 수정**(PR #45/#46/#47은 기 머지 코드 인용, 본 세션 미접촉 — `git diff --name-only` = `docs/` 2파일뿐). **G10 송신측 0줄 / ESP32 미연동 / EC2 미기동 / 실 public 호스팅 제품 확정 / M5-c 판정 계층 / ML 2차 모델 / 2차 15초 체인 전 구간 검증 / 실 육성 STT 인식률** 전부 미착수. **CSR 301건 원인 = 미규명으로 못 박고 추정 미기재**(§9-10 준수). **8/12 NCP 한도 서술 무취소선**. 7.6(i)(2차 자막 실패 영구 포기) · 6 2워커 409 경합 · 8.3 폴러 통합/Pretendard self-host/SR 실청취 = **미결 유지**. `notification-meta.ts`·`index.html` 도어벨 / `git-convention.md` / 프론트 NC 하네스 자산화 = **기록만, 코드 미수정**. 노션 미수정(Set 3 소관) / 프로젝트 지침 미수정(Set 2 소관). `docs/decisions.md`(카테고리 3 G12 취소선+확정 / 카테고리 7 STT 취소선+append / 7.6 서문 취소선+append / **7.7 신설** / 6.4(f) 취소선+append / 8.3 미결 2건 취소선+append / **8.4 신설** / 카테고리 20 `-B` 한계 append + **NC 미검출 판정 절 신설** / 30.9 취소선+판정 블록+301건 미결 신설 / 29.5 append / 카테고리 10 append / **27.8 신설**) + `docs/decisions-log.md`만 편집. 브랜치 없이 **main 직 push**(문서 단독, 카테고리 20 「문서/코드 변경 push 분리」).

**관련 카테고리**: 3 (G12 확정 — 신뢰도 게이트 전역화) / 7 (STT 서버 배선 CLOSE) / 7.6 (A-2 미완 사유 해소) / **7.7 (실 STT 소스 배선 신설)** / 6.4(f) (가짜 ToF 잔존 해소) / 8.3 (뱃지 과소 표기 · ToF 미표시 해소) / **8.4 (대시보드 표시 결함 4종 신설)** / 20 (`python3 -B` 한계 · negative control 미검출 판정) / **27.8 (위임 인용 오기 누적 신설)** / 29.5 (도어벨 잔존) / 10 (커밋 규약 이탈) / 30.9 (NCP 한도 판정 · CSR 301건 미규명) / 26 (부스 데모 — 가짜 ToF 소멸) / 33 (USP 2층 — ToF 근거 화면 노출)
**관련 commit**: 코드 PR #45 `9b3e3a2` + PR #46 `82a4870` + PR #47 `846b342`(기 머지) + 문서 반영 = 본 Set 1 커밋(docs-only, PR 없음)

## 2026-09-09 (수) — PoC-(43) SystemHealth 카카오 토큰 상태 실배선(8.5 신설) + SSoT 정합 소액 정정 3건 해소 + G14 등재 여부 오독 반증(27.8(f) 신설) + 인용 오기 7건 + mock 잔여 실태 (카테고리 6.1/7.5/7.7/8.5/21/27.8/29.5)

※ 작업일 = 2026-09-09 ~~단일 세션~~ → **당일 1세션째(11:40~12:45)**(노트북 단독). 코드 PR 2건(#48 · #49)이 같은 날 머지·검증됐고 본 엔트리는 그 SSoT 반영분(문서 전용, 코드 0 수정)이다. ※ **정정 (발견·문서 반영 2026-09-09 PoC-(44))** — 같은 날 2세션째(PoC-(44), 18:30~21:00)가 돌아 「단일 세션」이 stale이 됐다. 본 엔트리의 내용 자체는 무변경.

### 결정 (카테고리 8.5 신설 — 카카오 토큰 상태 실배선, PR #49 `07742d9`)

- 🔴 **화면은 준비돼 있었고 서버만 사실을 말하지 않았다** — `/stats`의 `kakao_token_status`/`kakao_token_expires_in_minutes`가 하드코딩 `"valid"`/`240`이었고, 프론트 `statusInfo()`는 3분기를 이미 렌더할 수 있었다. **성격 = 배관(plumbing) PR**(새 판정 기준·새 임계·새 상태 어휘 신설 0).
- **(a) 선언 ≠ 발화 (실측)**: `git log -S'"expiring"' -- server` = **커밋 0건**. `expiring`은 서버 트리에 문자열로 존재한 적조차 없었다 → 만료 화면은 **실사용된 적이 없다**(학습 14). ∴ 토큰이 만료돼도 대시보드는 초록불 "유효"를 냈다.
- **(b) 결정표 9행 → 3상태 붕괴 (실측)**: 축에 **토큰 행 부재 + 음수 구간 + 경계값 정확히 0**을 포함해도 4번째 어휘가 생기지 않는다. **행 4(정확히 0) = `expired`**가 `<= 0` non-strict를, **행 7(임계 정확히) = `expiring` / 행 8 = `valid`**가 `<= MARGIN` non-strict를 고정한다. ⚠️ 행 6·7·8의 `minutes`가 floor 때문에 전부 `10`으로 겹쳐 **숫자만으로는 임박/정상이 구분되지 않는다**(구분은 색·라벨).
- **(c) `KAKAO_REFRESH_MARGIN` 재사용 — 신규 상수 0 (논증, 입력 실측 = `constants.py` 정의 주석 + `models.KakaoToken.needs_refresh` 동일 부등호)**: 화면 표기만 다른 숫자를 쓰면 "이 토큰은 그대로 못 쓴다"에 대한 **진실이 두 개**가 된다.
- **(d) 행 부재를 `expired`로 합류 (논증, 입력 실측 = `statusInfo()` `default` 분기가 원시 문자열을 라벨로 낸다)**: 어휘를 늘리면 화면에 `unknown`이 노출된다. 구분은 WARNING 로그가 담당 — 7.7(i) `mode=real` 로그 불변식과 같은 계열.
- 🔴 **(e) 잔여 분 음수 유지 — 0 클램프 기각 (결정 주체 = 사용자, 논증, 입력 실측 = (a) 0건)**: ① 만료 화면이 부스에서 처음 뜰 때 **"얼마나 전에 죽었는지"가 대응을 가른다**(10분 전 = 재발송 / 3일 전 = refresh 체인 단절) ② **"로그로 보존"은 부스에서 접근 불가**(로그를 볼 수 있으면 대시보드가 불요) ③ 8.4(d) **"실측 0 ≠ 값 없음"** 원칙과 충돌 — **있는 값을 지우는 쪽이 없는 값을 지어내는 것보다 나쁘다**. → W2 성격이 "음수 방어 가드"에서 **"상태별 분기 렌더"**로 재규정.
- **(f) 프론트 (실측 SSR 렌더)**: `tokenExtra()` 신설, `expired`는 경과를 분/시간/일로 환산. **어느 상태에서도 행·문구를 비우지 않는다.** ★ `statusInfo` 색·라벨 매핑 **무변경**(diff grep `statusInfo|bg-status|label:` = **0줄**). 소비처는 **1곳뿐** — `SystemHealthSummaryCard`는 토큰 필드를 렌더하지 않는다(위임의 "카드 2개" 전제가 실물과 달랐다).
- **(g) 회귀 89 → 99 + NC 7종 전건 검출 (실측)**: 서버 4종(부등호 뒤집기 4건 / `expiring` 블록 제거 2건 / 행 부재 → `valid` 3건 / **0 클램프 도입 2건** = (e) 결정이 회귀로 고정) + 프론트 3종(8.4(f) SSR 하네스 재사용). 시각은 전건 **고정 주입**, 실 카카오 API 미호출.
- ⚠️ **단언 한계 1건 정직 기록**: 부호 뒤집기의 `expired_10m`이 F2를 통과했다 — `-10분 전 만료`가 `10분 전 만료`를 **부분 문자열로 포함**하기 때문. 가드 부재가 아니라 **단언이 무딘 것**이며 F3가 잡았다. 카테고리 20 「미검출의 판정」의 자매 사례.
- ★ **NC 4단계 보장이 3번째로 값을 했다 (실측)**: `expiring` 블록 제거 변형의 최초 앵커가 다른 NC 앵커와 **충돌해 `count == 2`**가 됐고 ③ 디스크 재독 assert가 실행을 막았다(PR #46 · #47에 이은 3번째).
- ⚠️ **경계 표기**: 🔴 **토큰 상태 가시화 CLOSE ≠ 갱신 실패 자동 복구** — 본 PR은 **읽기 전용 관측**이고 갱신·재발급·무효화 코드 **0줄**(`kakao.py`·`models.py` diff 부재로 증명). 체인이 끊기면 여전히 **사람이 7.5(e) 절차를 재실행**해야 한다. ⚠️ **행 부재와 정확히 0이 응답에서 동일**(`expired`/`0`)하고 구분은 로그뿐인데 **부스에서 로그를 볼 수 없다** — 행 부재가 "부트스트랩 전"이라 부스 구간 도달 불가라는 이유로 감수.
- **산출물 (실측 `git show 07742d9 --stat`)**: 3파일 **+290 / −6**. `/stats` **키 수 무변경**(최상위 10 / `system_health` 7, 회귀가 정렬 비교로 고정). **토큰 값은 응답·로그·테스트 어디에도 나가지 않는다**(나가는 것은 상태와 잔여 시간뿐). 커밋 **1개 `🐛 Fix`** — 규약의 분리 기준은 "여러 Type이 섞이면"인데 전부 거짓 표시 정정 = 단일 Type이라 8.4의 4분리와 달리 트리거 미발동.

### 해소 (카테고리 29.5 · 21 · 7.7 — SSoT 정합 소액 정정 3건, PR #48 `0d3b498`)

- **29.5 "도어벨" 잔존 2건 해소 (실측)**: `notification-meta.ts:1` / `index.html:8` 모두 "초인종"으로 치환. ★ **로직 참조 0건을 치환 전에 확인** — 분기 주석이지 표현식이 아니다(문자열 비교였다면 치환이 분기를 깬다). `constants.py` 3건은 오탐 주의대로 **무변경**.
- **카테고리 21 `.gitignore` 패턴 폭 해소 (실측)**: `.env`/`.env.local` 2줄 → **`.env*` 1줄 + `!.env.example` 예외 1줄**. ★ **negative control 양방향 확인** — 더미 `server/.env.bak`이 `.gitignore:38:.env*`로 차단되고 템플릿 3종(`.env.example` / `server/` / `dashboard/`)은 `git check-ignore -v` **미매치 유지**. 예외를 3줄 쓰지 않은 근거 = gitignore 패턴은 경로 어느 층에서도 매치하므로 1줄이 3파일을 덮는다.
- **7.7(k) 역방향 stale docstring 정정 (실측)**: `kakao.send_secondary`의 "현 시점 자막 소스는 mock"이 PR #45 배선 이후에도 잔존했다 — **주석이 코드를 못 따라간** 케이스. 남은 defer(④런타임 미실증)는 **삭제 없이 명시 유지**.
- 🟡 **[신규 미결] 정정 문구의 「폴백한다」가 부정확 (실측)**: 새 docstring이 "자격증명 미설정 시 mock 으로 **폴백한다**"로 적혔으나 실제는 **호출을 시도했다 실패해 되돌아가는 게 아니라 env 게이트에서 애초에 real 모드가 아닌 것**이다(`routes._caption_from_stt` 주석 = "자격증명 미설정이면 여전히 mock_enrichment 의 dict 가 들어온다"). **「안 불렀다」와 「불렀는데 실패했다」를 가르는 것이 7.7(i)의 `mode=real` 로그 불변식**인데 "폴백"이 그 구분을 흐린다. 해소 = 다음 코드 PR(**본 세션 코드 무접촉, 기록만**).

### 🔴 반증 (카테고리 27.8(f) 신설 — G14 「미등재」 진단이 틀렸다)

- **본 Set 1 위임이 "G14 등재 여부 모순"을 최우선 정정 대상으로 지목했으나, 실측 결과 모순은 decisions.md에 없었다.** `grep -n "G14"` = **2건**(카테고리 **6.1** 본문에 취소선 + **✅ 해소 (PR #40 `70aea1d`)** 실등재 + 7.5 「관련」 참조). `grep -n "미등재"` 전수 확인 결과 **"G14가 미등재"라는 서술은 문서 어디에도 없다** — 7.5(a)의 미등재 서술이 지목하는 것은 **G18/G21/G24**뿐이다.
- ∴ **모순의 소재 = decisions.md가 아니라 위임·인계 계층.** 처리는 취소선 정정이 아니라 **등재 사실을 못 박아 재오독을 막는 것**으로 갈렸다 → 6.1 해당 항목에 **[재오독 방지 앵커]** 문장 추가 + 27.8(f) 신설.
- 🔴 **「트래킹 부재」 3층 구분 (실측 grep 건수)**: ① **본문 실등재** = **G14**(2건, 6.1) ② **「미등재」 서술 안에서만 등장** = **G18/G21/G24**(각 1건 — 본문 항목이 아니라 7.5(a)의 그 문장 자체가 유일 매치, Notion DB3 전용 감사 ID) ③ **진짜 부재** = **G23/G34**(0건 — G23은 STT defer 표기로 7.7에 흡수, G34는 PoC-(39)에서 위임 전제 불일치로 판단불가 각하). ★ **이 3층을 구분하지 않으면 "grep N건"이라는 서술 자체가 다음 위임의 인용 오기가 된다** — ②는 건수만 보면 등재로, ①은 맥락을 안 보면 미등재로 오독된다(29.5 "도어벨" 오탐 주의와 같은 층위).
- **실존 G-ID 전수 (실측)** = G10 · G12 · G14 · G18 · G21 · G22 · G24 · G27 · G28 · G29 **10개**. 본문 실등재 7개(G10/G12/G14/G22/G27/G28/G29) + ② 층 3개(G18/G21/G24). 부재 ID(G23/G34)는 **27.8(f) 목록 자체가 기록 대상이라 그 맥락에서만** 사용하고 본문·커밋 메시지엔 쓰지 않는다.

### 신규 (카테고리 27.8(e) — 인용 오기 7건, 누적 13건)

- **PR #48 2건**: 브랜치 규칙 출처를 `git-convention.md`로 지목했으나 실물은 **decisions.md 카테고리 20** / `FIRE_ALARM_PRIMARY_MESSAGE` 소속을 `kakao.py`로 지목했으나 실물은 **`constants.py`**. 둘 다 **값은 맞고 주소가 틀린** 27.8(a) 동형.
- ★★ **PR #49 ①은 유형이 다르다 — 「출처 계층 착각」**: "decisions.md 7.5에 '갱신 자체가 실패하는 구간은 자동 복구 불가'가 등재돼 있다"가 **grep 0건**이었고, 실물과 가장 가까운 문장은 **decisions.md가 아니라 `test_detect_regression.py`의 docstring**이었다. **절 번호 grep(`^### `)으로는 잡히지 않는다** — 인용문은 **"그 문장이 어느 파일에 있는지"를 `grep -rn`으로 확인**해야 한다. 인용 계층 = ① SSoT 문서 / ② 코드 주석·docstring / ③ PR 본문·대화, **세 층은 권위가 다르다.**
- **PR #49 ②③**: "`_build_stats` 10키 = `StatsResponse` 10필드 정합 등재" → 그런 등재 부재(실물은 6.1의 **TimingMetrics 6키**), ⚠️ **키 수 자체는 실측 10:10 일치**라 제약은 준수 = **주장은 맞고 출처가 없는** 경우 / "토큰 SSoT = DB `kakao_tokens`" 문장 형태 부재(코드로는 확증, 파급 없음).
- **본 Set 1 2건**: G14 등재 위치를 **6.2**로 지목했으나 실물은 **6.1** / "회귀 **89**로 적힌 곳"을 정정 대상으로 지목했으나 실물에서 89는 **카테고리 3 G12 이력 서술 1건뿐**이고 stale한 것은 **7.5(i)의 「60 케이스」**(누적 현재값)였다.
- ★ **①의 실질 피해는 0이었다** — 수행 측이 grep 0건을 확인하고 **근거를 문서 인용에서 코드 실측으로 교체**해 진행했다. 27.8(d) 「수행 측 강제 규칙」이 값을 한 사례.

### 조사 결과(결정 아님) — `system_health` mock 잔여 실태 (8.5(i))

- **5필드 중 실데이터 0.5개 (실측)**: `device_last_seen_at` = **부분 실데이터**(오늘 알림이 있으면 실측, ⚠️ **0건이면 `kst_now_iso()`로 떨어져 기기가 죽어도 "방금 전"** — **8.5가 고친 결함과 동형**) / `device_status` `"online"` · `signal_strength` `"strong"` · `clova_api_status` `"ok"` · `db_status` `"ok"` = **전부 리터럴**.
- ⚠️ **`clova_api_status`는 7.7로 실 CSR이 배선됐는데도 리터럴이 남았다** — 판정 재료가 이미 코드에 있으므로 **다음 1순위**.
- 🟡 **[신규 미결] `system_health` mock 잔여 4.5필드**: **조사 결과이지 결정이 아니다.** 후보 순서는 재료 유무로 갈린다 — ① `clova_api_status` ② `device_last_seen_at` 0건 fallback ③ `device_status`/`signal_strength`(11주차 heartbeat 의존, **현시점 재료 부재**) ④ `db_status`. **처리 방침 미확정.**

**SSoT 정합 검증 (문서라 코드 3단계 N/A)**: 신설 절 번호 **8.5** = `grep -nE "^### 8\."`로 8.1~8.4만 존재 확인(충돌 없음). D1(PR #48)은 **신설 절을 만들지 않았다** — 3건이 전부 **기존 미결 항목의 해소**(29.5 / 카테고리 21 / 7.7)라 신설은 이력을 흩뜨린다. D2만 성격이 신설(mock 제거 배선 + 결정표)이라 갈랐다. 편집 앵커 **8건 전건 `count == 1` assert 통과**(라인 번호 미사용, 패턴 매칭). 취소선 총수 착수 전 **47줄 / 100개** → 종료 **51줄 / 110개**(신규 5쌍 = 10개, **짝수 유지 = 마크다운 무파손**), **삭제 0줄**을 제거 5줄 고유 토큰 **199종 전건 보존 검사**(미보존 0건)로 증명 — 전부 취소선 래핑·라인 중간 삽입. 회귀 수치 정정은 **7.5(i) 「60 케이스」 1건뿐** — 각 절의 "기존 N → M"(6.4(d) 30→42 / 7.6(g) 42→60 / 7.7(a) 60→83 / 카테고리 3 83→89)은 **그 PR 시점의 이력**이라 정정하면 이력이 파손된다(§7-c). `.gitignore` 검증은 `git check-ignore -v` 5경로 실행(차단 2 / 미매치 3). 요일 `date -j -f "%Y-%m-%d" "2026-09-09" "+%A"` = **Wednesday = 수** 검산. 실존 G-ID 전수 `grep -oE '\bG[0-9]{1,2}\b' | sort -u` = G10·G12·G14·G18·G21·G22·G24·G27·G28·G29(부재 ID는 27.8(f) 맥락에서만). 원격 = `git ls-remote origin | grep -v refs/pull/` 실물 확인(`refs/heads/main` 단일, `git branch -r` 미사용 — 학습 20). 세션 갭 = **없음**(직전 엔트리 PoC-(42) 2026-09-08). 카카오 토큰·시크릿 / NCP 자격증명 **전부 미기록** — 8.5는 **상태와 잔여 시간만** 기록한다.

**비범위**: **코드 0 수정**(PR #48/#49는 기 머지 코드 인용, 본 세션 미접촉 — `git diff --name-only` = `docs/` 2파일뿐). **`system_health` 나머지 4.5필드 배선 / 토큰 갱신·재발급·무효화 로직 / `/stats` 키 증감 / 폴러 통합 / Pretendard self-host / `/enrich` 409 경합 / ml 04 분기 / G10 송신측 / ESP32 미연동 / EC2 미기동 / 실 육성 STT 인식률 / 2차 15초 체인 전 구간** 전부 미착수. `docs/git-convention.md` **무접촉** — 커밋 규약 이탈 2건(`🧪 Spike` / `🎨 Style`) 타입 추가 여부는 **판단 사안이라 미결 유지**. 22주 일정표·마일스톤 달성률 **미평가**(학부생 판단 사안). D4(mock 잔여)는 **조사 결과로만 등재, 처리 방침 미확정**. 「폴백한다」 문구 교체 = **기록만, 코드 미수정**. 노션 미수정(**DB3 신규 row 생성은 Set 3 소관** — Set 1은 decisions.md 선등재까지) / 프로젝트 지침 미수정(Set 2 소관). `docs/decisions.md`(**8.5 신설** + 7.5(i) 회귀 누적 정정 + 29.5 해소 + 카테고리 21 해소 + **7.7(k) 신설** + 27.8(d) 누적 갱신 + **27.8(e)(f) 신설** + 6.1 G14 재오독 방지 앵커) + `docs/decisions-log.md`만 편집. 브랜치 없이 **main 직 push**(문서 단독, 카테고리 20 「문서/코드 변경 push 분리」).

**관련 카테고리**: **8.5 (SystemHealth 토큰 상태 실배선 신설)** / 8.4 (표시 결함 계열 · SSR NC 하네스 · `=== null` 엄격 비교) / 8.3 (3중 표기) / 7.5(e)(토큰 부트스트랩 — 관측만 하고 고치지 않는 대상) / 7.5(i)(회귀 누적 현재값) / **7.7(k) (역방향 stale docstring 신설)** / 6.1 (G14 등재 앵커 · `StatsResponse` 키 계약) / 21 (`.env` 위생 · `.gitignore` 해소) / **27.8(e)(f) (인용 오기 7건 · G-ID 3층 구분 신설)** / 29.5 (도어벨 해소) / 20 (NC 4단계 보장 3번째 작동 · 미검출 판정) / 26 (부스 대응 판단) / 10 (커밋 Type 단일 판단)
**관련 commit**: 코드 PR #48 `0d3b498` + PR #49 `07742d9`(기 머지) + 문서 반영 = 본 Set 1 커밋(docs-only, PR 없음)

## 2026-09-09 (수) — PoC-(44) Clova STT 상태 실배선(8.6 신설) + ④런타임 2건 CLOSE + SSR NC 하네스 repo 편입(8.4(f) 부분 해소) + 학습 21 5번째 유형 신설 + MCP 관행 추정 오적용(29.6 신설) + 27.8(f) 표 열 교체 + 인용 오기 6건 + 신규 미결 6건 (카테고리 7.4/7.5(i)/8.1/8.4/8.5/8.6/20/21/27.8/29.6)

※ 작업일 = 2026-09-09 **당일 2세션째**(18:30~21:00경, 노트북 단독) — 1세션째는 PoC-(43)(11:40~12:45, 바로 위 엔트리)이다. **자정 미경과이므로 발견일·문서 반영일이 양쪽 다 2026-09-09**이다. 코드 PR 2건(#50 · #51)이 같은 날 머지·검증됐고 본 엔트리는 그 SSoT 반영분(문서 전용, 코드 0 수정)이다. **하드웨어 미접촉, 실측 로그 파일 없음**(대화형 curl · 화면 catch · 서버 로그 육안).

### 결정 (카테고리 8.6 신설 — Clova STT 상태 실배선, PR #50 `ca276a9`)

- 8.5(i)가 *"다음 후보 순서는 재료 유무로 갈린다"*로 **1순위 지목한 `clova_api_status`**를 닫았다. `"ok"` 하드코딩 → `stt.is_real_mode()` 파생. 성격 = **8.5와 같은 배관(plumbing) PR**이나, 8.5와 달리 **새 상태 어휘 `degraded`가 화면에 처음 도달**했다.
- 🔴 **(a) `error` 기각 — 「안 불렀다」와 「불렀는데 실패」의 구분 (논증, 입력 실측 = 7.7(i) `mode=real` 로그 불변식 + `routes.py` 주석 원문)**: 판정 재료는 **env 게이트뿐**이고, env가 비었다는 것은 *"아직 한 번도 부르지 않았다"*이지 *"불렀는데 실패했다"*가 아니다. `error`는 후자를 함의하므로 **사실을 넘어선다**. → **2상태만 발화**(`ok` / `degraded`). ★ **실 CSR 핑도 금지** — 30.9의 **미규명 301건** 위에 원인 불명 호출을 더 얹지 않는다(`routes.py` 주석에 명문화).
- 🔴 **(b) ④런타임 CLOSE = 대조 실험 (실측 대화형 curl + 화면 catch)**: NCP 키 **있음** → 응답 `"ok"` → 화면 **● 정상(초록)** / NCP 키 **빈 문자열** → 응답 `"degraded"` → 화면 **● 지연(주황)**. ★ **`git log -S'"degraded"' -- server`가 PR #50 이전 0건**이던 값이 처음 화면에 도달했다(8.5(a) `expiring` 건과 같은 유형이나 **발화와 도달을 같은 세션에서** 확인). ★ **단일 값 확인이 아니라 대조 실험이었다** — `ok`만 봤다면 "리터럴을 안 지운 것"과 구별되지 않는다.
- 🔴 **빈 문자열이 falsy로 처리됨이 실증 → 논증이 실측으로 승격**: 7.7(e) env 게이트에서 `None`과 `""`가 **같은 값으로 붕괴**한다는 것이 화면 값의 차이로 확인됐다. ⚠️ **승격된 것은 이 붕괴 사실 하나**이며 env 게이트의 나머지 서술(한쪽만 설정 시 401 회피)은 **여전히 논증**이다 — 섞어 읽지 말 것.
- 🔗 **(d) 파급 — 7.7(e)의 침묵이 깨졌다 (논증, 입력 실측 = (b))**: 7.7(e) 실물 문언은 *"미설정이면 **호출 자체를 하지 않고** mock 자막을 유지한다"*이며, 화면·응답 어디에도 그 사실이 드러나지 않아 **NCP env가 빠진 채 배포되면 가짜 자막이 소리 없이 나갔다**. 이제 대시보드가 `● 지연`으로 알린다. ⚠️ 단 **자막 자체는 여전히 mock으로 나간다** — 본 PR은 **읽기 전용 관측**이고 **화면이 알려줄 뿐 고치지 않는다**(8.5(h) 동형). ⚠️ 또한 **대시보드를 보고 있을 때만** 성립하므로 기동 체크리스트 편입이 실효 조건이다.
- **(c) 회귀 99 → 102 + NC 3종 전건 검출 (실측)**: ① `is_real_mode()` `True` 고정 ② 삼항을 `"ok"` 리터럴로 되돌림 ③ `degraded` → `error` 어휘 교체. **③이 걸린다는 것이 (a)의 어휘 결정이 회귀로 고정됐다는 증거**다.
- **(e) 산출물 (실측 `git show ca276a9 --stat`)**: **2파일 +52 / −3**. **프론트 0줄**(`SystemHealthCard.tsx:56`이 값을 그대로 넘기고 `statusInfo()`가 `degraded`를 이미 렌더 가능, **소비처 1곳**). `/stats` **키 수 무변경**. 커밋 **1개 `🐛 Fix`**(단일 Type, 8.4의 4분리 트리거 미발동). **NCP 자격증명 미기록** — 나가는 것은 `ok`/`degraded` 두 어휘뿐.
- ⚠️ **(f) 경계 표기**: 🔴 **STT 상태 가시화 CLOSE ≠ STT 건강성 판정** — 자격증명이 **설정돼 있으나 틀렸거나** CSR이 **429·5xx를 내는 중**이면 화면은 여전히 **`ok`(초록)**다. 7.7(i)가 실증한 HTTP 429 상황이 **화면에 드러나지 않는다**. 잡으려면 실 호출 결과를 상태로 승격해야 하고 이는 (a)가 기각한 핑과 다른 설계(최근 호출 결과 캐시)라 **별건**이다.

### 해소 (카테고리 8.5(k) 신설 · 8.5(i) · 8.4(f) — ④런타임 2건 CLOSE + 하네스 repo 편입, PR #51 `8d574dd`)

- ✅ **8.5(k) 신설 — PR #49 ④런타임 CLOSE (실측)**: 실 `/stats` 응답 `expired` / `-1561` → 화면 **"1일 전 만료" + 빨간 점**. 8.5(g)가 *"실 시계·실 카카오 API 미호출, DB 상태 주입만"*으로 정직하게 적어 둔 구간을 닫았다. ★ **실렌더가 8.5(f) SSR 대조 목록에 없던 「시간→일 경계」(26시간)를 밟았고** `1일 전 만료`로 정상 환산됐다 — (f)의 6점은 **고른 표본**이었지 경계 전수가 아니었다. ⚠️ **24~47시간이 전부 "1일 전"으로 뭉개지나 `status`가 이미 `expired`라 판정 오염 없음 → 감수 가능으로 판정**(논증, 입력 실측 = 위 실렌더). (e)가 음수를 살린 목적("10분 전 = 재발송 / 3일 전 = 체인 단절")은 일 단위 해상도로도 달성된다.
- ✅ **8.5(d) 로그 구분이 실동작으로 확인됐다 (실측)**: 서버 로그에 `WARNING in routes: kakao token status: 만료 1586분 경과` 실출력. **설계로만 적어 둔 "구분은 로그가 담당한다"가 실물 출력으로 확인**됐다. ⚠️ 동시에 8.5(h)의 감수 근거("구분은 로그뿐")가 **로그가 실제로 찍힌다는 전제 위에** 서 있음도 드러났다.
- ✅ **8.5(i) `clova_api_status` 해소** → 표 **5행 중 1행** 해소(**4행 잔존**), 미결 문구는 ~~4.5필드~~ → **3.5필드**. ⚠️ **계수 단위를 섞지 말 것** — 표는 **행**, 미결 문구는 **필드**(`device_last_seen_at` = 0.5)다. **미결 자체는 유지**된다.
- ⚠️ **8.4(f) 「하네스가 repo 밖」 = 부분 해소. 🔴 🟢 전환 금지.** repo 편입은 됐으나(`dashboard/tools/ssr-nc/` +292줄, `package.json` scripts **1줄**, **신규 의존성 0**, NC 4종 이식 = PR #49 2종 + PR #47 2종, 자기 검증 **12행 전건 통과**) **승계 항목 3건을 개별 사유로 명기**했다: **① CI 미연결(신규 한계)** — 사람이 `npm run ssr-nc`를 쳐야 돈다, **repo 편입 ≠ 회귀 방지**(사유 = 자산화와 자동 실행은 별개 층) / **② 텍스트 전용**(사유 = 단언 대상이 라벨 문자열이라 편입과 무관하게 불변) / **③ SSR이라 실 브라우저 CSS 미검증**(사유 = 실행 매체의 성질). **"자산화 = 전면 해소"로 읽히면 안 된다.**
- ✅ **8.5(g) 부분 문자열 단언을 주석이 아니라 「구조」로 제거 (실측)**: `segments()`로 렌더 출력을 **텍스트 노드 배열**로 쪼갠 뒤 **완전 일치** 비교 → 통과 경로 자체가 소멸. 실증 = `"-10분 전 만료".includes("10분 전 만료")` **true(❌)** ↔ `===` **false(✅)**. ★ **무딘 단언은 경고 문구가 아니라 자료구조로 고친다.**
- ★ **ESM 모듈 캐시 = `.pyc` 사건의 JS 판 (실측, PR #51 자체검증 ①에서 MCP 발견)**: SSR 재빌드마다 같은 경로를 `import`하면 **ESM 모듈 캐시가 첫 번들을 반환**해 변형 미적용 상태로 "미검출"이 나온다(**거짓 음성** — `.pyc` 절이 경고한 방향과 정확히 일치). 차단 = `import(`${url}?build=${++buildCount}`)`. → **카테고리 20 「계보 4층」의 3층(실행 환경)에 언어가 하나 추가**됐다. ★ **자산화**: NC 4단계 보장 중 ③(`assert 변형본 != 원본`)은 **디스크**를 보므로 **메모리 캐시는 잡지 못한다** — 디스크가 바뀌어도 로드된 모듈이 옛것이면 ③은 통과한다.

### 🔴 반증 (카테고리 8.4(f) — 학습 21 **5번째 유형** 신설: 미결이 아니라 「차단 사유」가 유령이었다)

- 8.4(f)의 원 미결이 *"자산화하려면 테스트 러너 도입이 필요하고 이는 **신규 의존성 금지**에 걸린다"*로 **3주 이월**됐다. `dashboard/package.json` 전문 실측 결과 **`react-dom` `^19.2.6`(dependencies) / `vite` `^8.0.12`(devDependencies)가 이미 설치**돼 있었고 하네스는 이 둘만으로 돈다 — **신규 의존성 0으로 자산화가 가능했다.**
- ★ **원인 = 「러너」의 의미 혼동**: 테스트 **프레임워크**(vitest / jest / RTL) 도입은 확실한 신규 의존성이지만 본 하네스는 **프레임워크가 아니라 스크립트**다. 둘을 한 단어로 뭉갠 채 이월했다.
- 🔴 **유령의 위치가 다르다 → 5번째 유형으로 신설**: 미결의 **존재**("하네스가 repo 밖")는 **실재했고 사실**이었다. 유령이었던 것은 **막고 있던 차단 사유**다. 기존 4분류(유령 / 트래킹 부재 / 트래킹 있으나 실물 부재 / 부재로 기록됐으나 실재)는 전부 **미결 자체의 실재 여부**를 가르는 축이라 이 사례를 담지 못한다. → **⑤ 미결은 실재하나 「차단 사유」가 유령인 유형**.
- **재발 방지(학습 19의 확장)**: **"X를 하려면 Y가 필요하다" 형태의 차단 사유는 Y의 실존을 반드시 실측한다.** 학습 19가 미결의 **근본원인 진단**을 코드로 재검증하는 축이라면, 본 건은 미결을 **가로막은 이유**를 코드로 재검증하는 축이다.

### 🔴 신규 (카테고리 29.6 신설 — 학습 16 **반대 방향 1호**: MCP가 SSoT를 「관행 추정」으로 덮었다)

- **사실관계 (실측)**: PR #50에서 MCP가 위임 지정 `feat/server-clova-status`를 **`fix/server-clova-status`로 변경**했다. 근거로 "PR #48·#49의 실제 관행"을 들었으나 **그 브랜치들은 GitHub 자동 삭제로 이미 원격에 없었다** → **검증 불가능한 근거**. **SSoT 실물은 카테고리 20**: `feat/{domain}-{task}` **(firmware/ml/server/dashboard/fix)** — ★ **`fix`는 `{domain}` 자리의 값**이지 `feat` 자리를 대체하는 접두가 아니다.
- **로컬 브랜치 실측 이탈 3건**: `fix/ssot-consistency-3`(#48) / `fix/server-kakao-token-status`(#49) / `fix/server-clova-status`(#50). ✅ **PR #51은 `feat/dashboard-ssr-nc-harness`로 복귀**해 이탈은 3건에서 멈췄다.
- 🔴 **왜 기록하는가**: **MCP의 위임 기각은 지금까지 7회 전부 옳았고 이번이 첫 오적용**이다. 성공률이 높은 판단 경로일수록 **틀린 1회가 검증 없이 통과**한다. ★ **결함의 본체는 "브랜치명이 틀렸다"가 아니라 「출처 계층」**이다 — 관행 추정(**③ PR·대화** 계층)이 **① SSoT 문서** 계층을 덮었다. 27.8(e)의 인용 계층 3층이 **수행 측 판단에도 그대로 적용**된다.
- **재발 방지**: 🔴 **SSoT 문서와 충돌하는 「관행 추정」은 §9 정지 대상.** 위임 지정을 기각하려면 근거가 **① 계층(SSoT 실물)**이어야 하고, ③ 계층이면 **기각하지 말고 사용자 판단으로 올린다.**
- ⚠️ **소급 정정 불가 — 기록만**: 브랜치는 삭제됐고 **Squash 머지라 브랜치명이 히스토리에 미기록**이라 되돌릴 대상 자체가 없다. **실질 피해 0**(머지 후 브랜치명은 어디에서도 참조되지 않는다). 등재 이유 = **다음 세션이 이 3건을 "관행"으로 재인용하는 것을 차단**하기 위함.

### 신규 (카테고리 27.8(g) 신설 — 인용 오기 6건, 누적 ~~13건~~ → 19건 + 27.8(f) 표 열 교체)

- 🔴 **① 압축 손실 — 이번엔 위임 작성자 자신이다**: PR #51 위임 §2가 SSR 하네스를 "PR #47·#49·#50 **3연속 사용**"이라 적었으나 실측 결과 **PR #50은 쓰지 않았다**(`git show ca276a9 --stat` = `server/` 2파일뿐, NC는 전부 `python3 -B` 서버 NC) → 실제는 **2연속**. ★ **같은 세션에서 직접 본 것을 압축하며 틀렸다** — 기억으로 박은 절 번호 오기와 달리 **요약 단계에서 손실**됐다. 착수 근거는 무손상(막고 있던 것은 "3연속"이 아니라 「의존성 금지」).
- 🔴 **② 「압축 손실」 개념 자체가 decisions.md 미등재였다 — 「출처 계층 착각」 2호**: 본 Set 1 위임이 *"9/09에 신설한 「압축 손실」"*이라 적었으나 `grep -rn "압축 손실" docs/` = **0건**. **프로젝트 지침 계층에만** 있고 SSoT 문서엔 없었다 → 본 세션이 **27.8(g)로 최초 등재**.
- 🔴 **③ 「정합성 정정」 PR 성격 선례도 미등재 — 「출처 계층 착각」 3호**: *"PR #48의 「정합성 정정」이 제3의 성격으로 신설된 선례"*를 근거로 새 PR 성격 신설이 제안됐으나 `grep -n "정합성 정정"` = **decisions.md 0건**. 실물 등재 어휘는 **「배관(plumbing) PR」**(8.5 서문)과 **「방법론 자산」**(8.4(f) 소제목)뿐 → ⚠️ **제안 근거가 무너져 신설하지 않고 §9로 올렸다**(아래).
- **④ "8.5에 「④런타임 미수행」 미결 실존"** → 8.5 구간 전수 grep에서 `④런타임`·`미수행` **둘 다 0건**. 실물 대응 서술은 8.5(g)의 *"실 시계·실 카카오 API 미호출, DB 상태 주입만"*이며 **한계 서술이지 등재 미결이 아니다** → **취소선 → 신규 등재(8.5(k))로 pivot**(§9-c).
- **⑤ "7.7(e)의 fail-silent 서술"** → `grep -rn "fail-silent\|가짜 자막\|소리 없이"` = **repo 전역 0건**. **소절 번호 (e)는 맞다** — 실물 문언은 *"미설정이면 호출 자체를 하지 않고 mock 자막을 유지한다"*이고 "fail-silent"는 **위임 작성자의 조어**다. **값은 맞고 문언이 창작된** 경우.
- **⑥ "27.8은 누적 14건임을 기록한다"** → 실물 (d)는 **누적 13건**. **자기 참조 오기**.
- ★ **유형 분포가 바뀌었다**: (a)~(d)의 주류는 **절 번호 오기**였으나 본 6건 중 절 번호 오기는 **0건**이다(①=압축 손실 / ②③=출처 계층 착각 / ⑤=문언 창작 / ⑥=자기 참조 오기). → **(d)의 재발 방지책(`^### ` grep)은 본 6건 중 단 1건도 잡지 못한다.** 잡는 것은 (e) ①이 세운 **`grep -rn "<문장 일부>" docs/ server/ dashboard/`**(②③⑤)와 **실물 재실행**(①⑥)이다.
- 🔴 **27.8(f) 표가 자기지시적으로 깨졌다 → (f-2) 신설 + 열 교체 (실측 재실행)**: 명시된 재현 명령 `grep -oE '\bG[0-9]{1,2}\b' docs/decisions.md | sort -u`가 **명시 결과 10개와 다른 12개**를 반환한다(`G23`·`G34` 포함). **원인 = 27.8(f) 본문이 G23/G34를 스스로 언급**하기 때문. 표 건수도 전건 어긋남(줄 수 기준 G14 2→8 / G18·G21·G24 각 1→5 / G23 0→3 / G34 0→2).
  - ⚠️ **27.8 절을 제외해도 어긋나는 것이 2건 있고 원인이 같다**: (i) **G18/G21/G24가 각 2줄** — 2번째 매치는 **6.1의 G14 재오독 방지 앵커**(*"미등재인 감사 ID는 G18/G21/G24뿐"*) (ii) **G23이 1줄** — **7.7(k)가 인용한 docstring 원문**. **둘 다 같은 PoC-(43) Set 1이 만든 매치**다 → **표를 쓴 세션이 같은 세션에 새 매치를 만들어 놓고 그 전 숫자를 적었다.**
  - 🔴 **성격 = 표의 숫자가 「측정 시점값(이력)」인데 그 단서가 없었다** — 7.5(i)가 「누적 현재값 vs 그 PR 시점 이력」을 문장으로 갈라 둔 것과 **같은 구분**이며, 표는 그 구분을 **자기 자신에게 적용하지 않았다**. **「현재값 서술 vs 이력 서술」의 첫 자기 적용 사례.**
  - ✅ **처리 = 건수 정정이 아니라 열 교체 (판단 근거)**: 건수를 12로 고쳐도 **다음 세션이 G-ID를 한 번만 더 언급하면 즉시 stale**이다. 본 표는 이미 *"매치 문맥을 실독해야 한다"*고 써 놓고 정작 SSoT로 삼은 값은 **문맥이 아니라 숫자**였다 → **「grep 건수」 열을 「매치가 서 있는 문맥」 열로 교체**했다. **문맥은 G-ID를 한 번 더 쓴다고 바뀌지 않으므로 stale이 되지 않는다.** 구 표는 **취소선 인용 블록으로 전문 보존**(삭제 0).
  - 🔴 **4번째 층 발견 → 3층 → 4층**: **G23은 「진짜 부재」인데 코드 원문 인용 안에서 등장**한다(7.7(k)의 구 docstring). *"부재 ID를 본문에 쓰지 말 것"* 원칙과 형식상 충돌하나 **원문을 바꾸면 무엇을 고쳤는지가 사라지므로 정당하다 — 인용은 사용이 아니다.** ③은 **G34 단독**으로 좁혔다.
  - ⚠️ **재현 명령은 남기되 용도를 좁혔다**: `grep -oE '\bG[0-9]{1,2}\b'`는 **"어떤 ID가 등장하는가"** 훑기 전용이며 **"등재 여부"의 근거로 쓰지 않는다**.

### 신규 미결 6건 (전부 본 세션 발견 — 판정 방법 병기)

- 🔴 **`device_status`/`signal_strength`가 거짓을 낸다 — 배관이 아니라 판정 사안 (8.5(i), 실측 화면 catch)**: 보드가 USB 미연결인데 화면 3곳이 전부 **"온라인 / 강함 / 방금 전"**. **8.5(a)가 고친 「서버가 거짓을 낸다」 유형의 재발**이다.
  - **소비처 실측 = 3곳 + 전역 훅 1개** (grep): `SystemHealthCard.tsx:47`(1) / `SystemHealthSummaryCard.tsx`(**5개 참조** — L77·84·85 + L95·96) / `hooks/useDevice.ts:13`의 `isOnline`(= `Header.tsx` 뱃지 출처). **PR #50(소비처 1곳)의 3배 이상**.
  - 🔴 **`routes.py` 주석이 「의도된 UX 결정」임을 자백한다 (실측 원문 인용)**: *"감지 0건(조용한 하루)에도 기기는 살아있으므로 detection 유무와 분리해 online mock 고정 (빈 상태 "시스템 정상" 안심 카드 전제)"*. ∴ `detected_at` 기반 파생은 **8.3 안심 카드 전제를 정면으로 뒤집는다** → **배관이 아니라 판정 PR**.
  - ✅ **8.5(i)가 이를 "11주차 heartbeat 의존, 현시점 재료 부재"로 분류한 것이 옳았다** — 착수 시 "재료만 보고 UX 전제를 안 본 분류"로 의심됐으나 **대화 중 반증**. 진짜 해법은 **M5-d 이후 heartbeat**이며 지금 임시 파생을 넣으면 **두 번 고친다**.
  - **판정 방법** = 11주차 heartbeat wire 후 `device_last_seen_at` 임계로 파생하되 **그 시점에 8.3 안심 카드 전제를 명시적으로 재결정**한다. 재결정 없이 파생만 넣으면 8.3 미결이 조용히 깨진다.
- 🟡 **`/stats` 폴링 3배 실측 — 기존 미결의 실증 (카테고리 8.1 follow-up, 실측)**: 서버 로그상 같은 초에 `/stats`가 **3회**(`19:00:58` 3회 / `19:01:01` 3회, 3초 주기와 정합). ★ 2026-06-29의 "3중"은 **프론트 코드 리뷰**로 센 값이었고 이번에 **서버측 실측으로 확증**됐다 — **통합 대상 건수는 무변경**. ⚠️ **EC2 배포 시 요청 3배 + 대시보드 다중 기동 시 곱해진다** → 폴러 통합은 성능 항목이 아니라 **11주차 배포 선행 항목**. **판정 방법** = EC2 기동 후 `/stats` 초당 호출 수 재측정.
- 🟡 **만료 WARNING이 폴링마다 로그를 오염시킨다 (8.5(d), 실측)**: 만료 지속 시 3초마다(×3) WARNING이 찍혀 다른 로그가 묻힌다. ⚠️ **양날이다** — 만료를 계속 알리는 것이 8.5(d)의 **의도일 수도 있으므로 결함으로 단정하지 않는다**. **처리 방침 미확정(판단 사안)**. **판정 방법** = 폴러 통합 해소 후 잔존 빈도 재측정 — **폴러 통합 전에 로그를 줄이면 원인 두 개를 한 번에 건드려 분리 불가**해진다.
- 🟡 **`.env`의 `DDINGDONG_CAPTURE_URL_BASE` 2줄 중복 (카테고리 21, 실측 — 키 이름만 확인, 값 미출력)**: `grep -c '^DDINGDONG_CAPTURE_URL_BASE' server/.env` = **2**. 원인 = 7.4 확정 절차상 터널 재기동마다 `>>`로 덧붙여 온 결과. **동작상 무해**(python-dotenv는 나중 줄이 이긴다)하나 **누적되고 "지금 유효한 줄"이 눈에 안 보인다**. **판정 방법** = `grep -c '^<KEY>' .env`가 모든 키에 대해 **1**인지 확인(값 미출력). **해소 방침 미확정** — `.env` 직접 편집은 카테고리 21 ① 사고와 같은 위험 구간이라 **별도 소관**.
- 🟡 **터널 미기동이 대시보드에서도 사진을 죽인다 (카테고리 7.4, 실측 화면 catch)**: `/notifications`에 **"사진을 불러올 수 없어요"** 실출력. 원인 = `DDINGDONG_CAPTURE_URL_BASE`가 **9/08의 죽은 터널 주소**를 가리킴. ★ **2026-09-03에 카카오톡에서 같은 증상이 있었고, 대시보드에서도 같은 일이 난다는 것이 처음 확인**됐다 — 소비처가 **카카오 lazy fetch + 브라우저 `<img>` 둘**이며 **같은 env 한 줄에 매달려 있다**. ✅ **리허설 체크리스트 항목으로 확정**(터널 기동 → `.env` 교체 → 서버 재기동을 사진 화면 열기 전에 완료). **판정 방법** = 대시보드 사진 카드 + 카카오톡 사진 카드 **양쪽 모두** 확인. ⚠️ **코드 결함이 아니라 운영 절차 누락** — 화면 문구는 정상 동작이며 고칠 대상은 **기동 순서**다.
- 🟡 **`degraded` 라벨 "지연"의 의미 불일치 (8.6(f), 실측 `statusInfo()` 매핑)**: `degraded`는 *"자막이 mock이다"*라는 뜻인데 화면 라벨은 **"지연"**이다(기존 어휘 재사용). 새 어휘를 만들면 8.5(d)가 막은 `default` 분기 원시 문자열 노출로 되돌아가므로 **감수**한다. **처리 방침 미확정** — 필드별 라벨 오버라이드가 후보. **판정 방법** = 부스 리허설에서 이 라벨을 본 사람이 "자막이 mock"으로 읽는지 확인(안 읽히면 실결함).

### 🔴 §9 사용자 판단 요청 — PR 성격 「방법론 자산화」 신설 여부

- **제안 내용**: PR #51이 기존 성격 셋(배관 / 판정 / 정합성 정정) 어디에도 안 맞는다는 **실측 대조** 후 신설 제안. 정의 = *"제품 동작을 바꾸지 않고 **검증 수단 자체를 repo 자산으로** 만드는 PR"*. 성공 판정 기준이 "제품이 잘 도는가"가 아니라 **"검증 도구가 진짜 잡는가"**.
- 🔴 **미등재 사유 = 제안의 선례 근거가 실측 반증됐다**: 위임이 든 근거 *"PR #48의 「정합성 정정」이 제3의 성격으로 신설된 선례"*는 `grep -n "정합성 정정" docs/decisions.md` = **0건**이다. decisions.md에 실제 등재된 PR 성격 어휘는 **「배관(plumbing) PR」**(8.5 서문) / **「방법론 자산」**(8.4(f) 소제목) **2종뿐**이며, **"PR 성격 분류 체계"라는 것 자체가 등재된 적이 없다.**
- ⚠️ **∴ "셋 중 어디에도 안 맞는다"는 대조의 전제(셋이 존재한다)가 성립하지 않는다.** 없는 분류 체계에 4번째 항목을 추가하는 형태가 되므로 **§9-d에 따라 등재하지 않고 판단을 올린다.**
- **선택지**: (A) **미등재 유지** — 성격 어휘는 각 절 서문에서 그때그때 명명하는 현행 방식 유지 / (B) **분류 체계 자체를 신설** — 카테고리 20 또는 10에 PR 성격 N종을 정식 등재하고 「방법론 자산화」를 포함 / (C) **「방법론 자산」 어휘 재사용** — 8.4(f)가 이미 쓴 소제목 어휘를 그대로 성격 명으로 승격(신설 0).

**SSoT 정합 검증 (문서라 코드 3단계 N/A)**: 신설 절 번호 **8.6** = `grep -nE "^### 8\."`로 8.1~8.5만 존재 확인 / **29.6** = 29.1~29.5만 존재 확인 / **8.5(k)** = 8.5가 (a)~(j)까지임을 확인 / **27.8(g)** = (a)~(f)까지임을 확인 — **전건 충돌 없음**. 카테고리 20 신설 2건은 **무번호 `###` 체계**를 따랐다(번호 미부여). 편집 앵커 **19건 전건 `count == 1` assert 통과**(라인 번호 미사용, 패턴 매칭). 취소선 총수 착수 전 **51줄 / 110개** → 종료 **62줄 / 140개**(**짝수 유지 = 마크다운 무파손**). **삭제 0줄** = `git diff -U0` 제거 11줄의 고유 토큰 **287종 전건 보존 검사**(구두점 정규화 기준 **미보존 0종**; 원시 기준 3종은 `83→89)은` / `이다).` / `PoC-(43),`로 **전부 라인 중간 삽입에 의한 토큰 분할**이며 실물 재출현을 개별 grep으로 확인). ⚠️ **1차 검사에서 27.8(f) 구 표 3행이 실제 소실됨을 catch해 취소선 인용 블록으로 전문 복원**했다 — 열 교체가 "치환"이 아니라 "삭제+추가"가 될 뻔한 지점. 회귀 수치 갱신은 **7.5(i) 「99 케이스」 누적 현재값 1건뿐**이며 각 절의 "기존 N → M"(6.4(d) 30→42 / 7.6(g) 42→60 / 7.7(a) 60→83 / 카테고리 3 83→89 / 8.5(g) 89→99)은 **그 PR 시점의 이력**이라 무변경(PoC-(43)에서 이 구분을 놓쳐 PR #46 실측 기록이 파손될 뻔한 선례 = 27.8(e)). 회귀 실측 = `venv/bin/python3 -m unittest app.tests.test_detect_regression` → **`Ran 102 tests` OK**. 요일 `date -j -f "%Y-%m-%d" "2026-09-09" "+%A"` = **Wednesday = 수** 검산. 원격 = `git ls-remote origin | grep -v refs/pull/` 실물 확인(`refs/heads/main` 단일, `git branch -r` 미사용 — 학습 20). **세션 갭 없음**(직전 엔트리 = 같은 날 PoC-(43)). **같은 날 2세션째이므로 발견일·문서 반영일 양쪽 다 2026-09-09**이며, PoC-(43) 엔트리의 「단일 세션」 서술은 **취소선 + 정정**으로 stale을 해소했다(엔트리 내용 자체는 무변경). **부재 ID(`G23`/`G34`)는 27.8(f) 맥락 외 본문·커밋 메시지 미사용** — PR #45 커밋 제목에 `(G23)`이 박혀 영구히 남은 선례 준수. `.env` 값·카카오 토큰·NCP 자격증명 **전부 미기록**(`.env` 중복 미결은 **키 이름과 건수만** 기록).

**비범위**: **코드 0 수정**(PR #50/#51은 기 머지 코드 인용, 본 세션 미접촉 — `git diff --name-only` = `docs/` 2파일뿐). `docs/git-convention.md` **무접촉**. **`system_health` 잔여 3.5필드 배선 / `device_status`·`signal_strength` heartbeat / 7.7(k) 「폴백」 문구 교체 / 폴러 통합 / `.env` 중복 정리 / SSR NC의 CI 연결 / STT 건강성 판정(429·5xx 반영) / Pretendard self-host / `/enrich` 409 경합 / ml 04 분기 / G10 송신측 / ESP32 미연동 / EC2 미기동 / 실 육성 STT 인식률 / 2차 15초 체인 전 구간** 전부 미착수. **PR 성격 「방법론 자산화」 신설 = 미등재, §9 판단 요청**(선례 근거 실측 반증). 「압축 손실」·「출처 계층 착각」의 **프로젝트 지침 계층 반영은 Set 2 소관**(본 Set은 decisions.md 최초 등재까지). 노션 미수정(**DB3 신규 row 생성은 Set 3 소관**). 22주 일정표·마일스톤 달성률 **미평가**(학부생 판단 사안). 브랜치 3건 이탈은 **소급 정정 불가로 기록만**. `docs/decisions.md`(**8.6 신설** + **8.5(k) 신설** + 8.5(d)(f)(g)(i) append + **8.4(f) 부분 해소** + 7.5(i) 회귀 누적 정정 + 카테고리 8.1 follow-up append + 7.4 미결 신설 + 카테고리 20 계보 append + **카테고리 20 Squash `-D` 절 신설** + 카테고리 21 미결 신설 + 27.8(d) 누적 갱신 + **27.8(g) 신설** + **27.8(f) 표 열 교체 + (f-2) 신설** + **29.6 신설**) + `docs/decisions-log.md`만 편집. 브랜치 없이 **main 직 push**(문서 단독, 카테고리 20 「문서/코드 변경 push 분리」).

**관련 카테고리**: **8.6 (Clova STT 상태 실배선 신설)** / **8.5(k) (④런타임 CLOSE 신설)** / 8.5 ((d) 로그 실동작 · (f) 경계 · (g) 단언 해소 · (i) mock 잔여 부분 해소 + 신규 미결) / 8.4(f) (SSR NC 하네스 repo 편입 부분 해소 · 학습 21 5번째 유형 · ESM 캐시 · segments) / 8.3 (안심 카드 전제 — `device_status` 판정 사안의 충돌 대상) / 8.1 (폴러 3중 실증) / 7.7 ((e) env 게이트 침묵 해소 · (i) `mode=real` · (k) 「폴백」 미결 **미해소**) / 7.5(i) (회귀 누적 현재값 99→102) / 7.4 (터널 · 사진 미표시 리허설 항목) / 20 (계보 3층에 ESM 추가 · **Squash `-D` 신설** · 브랜치 명명 SSoT · NC 4단계 보장의 메모리 캐시 한계) / 21 (`.env` 위생 · 중복 미결) / **27.8 ((g) 인용 오기 6건 신설 · (f) 표 열 교체 + (f-2) 신설 · (d) 누적 19건)** / **29.6 (학습 16 반대 방향 1호 신설)** / 30.9 (CSR 미규명 301건 — 핑 금지 근거) / 26 (부스 대응 — 기동 체크리스트) / 6.1 (`StatsResponse` 키 계약 무변경)
**관련 commit**: 코드 PR #50 `ca276a9` + PR #51 `8d574dd`(기 머지) + 문서 반영 = 본 Set 1 커밋(docs-only, PR 없음). 선행 = `2d17bbc`(같은 날 PoC-(43) 반영)

## 2026-09-10 (목) — PoC-(45) 프로젝트 지침 8절 미등재 사실 10건 SSoT 최초 등재 + 역방향 stale 단서 3건 (카테고리 5.1/6.1/6.3/7.5/7.6/7.7/8.4/8.5/27.8)

프로젝트 지침(repo 밖 문서) 슬림화 과정에서 "decisions.md에 없어 지우면 안 되는 사실"로 지침 8절에 모아 뒀던 항목 10건을 `decisions.md`에 최초 등재해, 지침에서 그 절을 지울 수 있게 만드는 작업. **코드 무접촉**(읽기만), 대상은 `docs/decisions.md`·`docs/decisions-log.md` 두 파일뿐.

**Step 0 가정 대조 — 전건 O**: HEAD `ecf5f47` / 워킹트리 clean(A1). `12.1` decisions.md 0건 + 7.6에 `HTTP_TIMEOUT_MS=10000` 안 문구 정확히 1건(A2). `DASHBOARD_TOKEN` decisions.md 0건 + `/stats`는 `@dashboard_auth`(`_require_token("DASHBOARD_TOKEN")`)(A3). `/stats`가 KST 당일 00:00~23:59:59.999 집계(`routes.py` `period_start`/`period_end`)(A4). `KOE` decisions.md 0건 + 7.5(e) OAuth 부트스트랩 절차 실존(A5). `음량조절` decisions.md 0건 + 5.1에 7/09 4유닛 녹음 프로토콜 실존(A6). `MIC_TASK_STACK_SIZE` decisions.md 0건 + `mic_common.h` 값 = `4096`(A7). (6)ⓐ~ⓕ **전건 코드 실존 확인**(A8 — 상세 아래). `$&` decisions.md 0건 + `run.mjs`가 치환자 함수(`() => c.patch`) 사용(A9). 27.8(g)⑤ "repo 전역 0건" 문구 1건 실존 + **재실행 결과 ≠ 0**(5건 — 8.6(d)가 세 표현을 등재했기 때문, A10). 8.5(i)에 "11주차" 표기 실존(A11). G07·G15·G16·G17·G19·G20 decisions.md 각 0건(A12). **정지 임계(A1·A2·A10·A11) 전건 O → 착수.**

**find-skills**: `decision log markdown` / `changelog` 둘 다 결과 있음(decision-log·changelog-generator 계열) — 과거 판정 ②(단일 decisions.md 누적 + 한국어 이모지 규약과 워크플로 불일치) **재사용, 재평가 불요**(동일 skill류 확인).

**A8 세부 검증(코드 실존, 6건 전부 real — 유령 0건)**: ⓐ `upload_spike_common.cpp`에 POST/multipart 실코드 실존(TLS 변형 `upload_spike_tls_common.cpp`는 별개 프로즌 파일) ⓑ 필드명 `client_request_id`/`device_id`/`audio`가 `constants.py`(`AUDIO_FILE_FIELD="audio"`)와 1:1 ⓒ `DEVICE_RATE_LIMIT_SECONDS=5` + 429(`constants.py`/`rate_limit.py`/`routes.py`) ⓓ `client_request_id`가 ESP32 `upload_spike_main.cpp`에서 `"spike-" + millis() + iterationSeq`로 생성 — millis() 기반 확인 ⓔ `rate_limit.py` docstring 자백 = "11주차 다중 워커(Gunicorn) 배포 시 Redis 등 공유 저장소로 교체 필요" ⓕ `server/app/*.py` 전역 `"processing"` 리터럴 0건.

**Step 1 — (1) 12.1초 출처 추적**: `grep -rn "12\.1" docs/` = 0건(decisions.md·decisions-log.md 어디에도 없음). `gh pr view 45 --json body`에서 발견 — "신규 미결 2건" ②: "펌웨어 상한 충돌 — 최악 총합 **12.1초**(카카오 7.5 + 서버 자체 1.6 + STT 3.0)가 기존 하네스 상한 `HTTP_TIMEOUT_MS=10,000`을 넘는다". **단일 출처, 다른 수치로 나오는 두 번째 곳 없음**(§9-c 미해당). `gh pr view 44`엔 12.1 언급 없음(7.6(f)의 7.5초 최악값만). decisions-log.md 2026-09-08 엔트리에도 12.1 미등재. → 근거유형 = **PR 본문 서술(③ 계층) · 미실측** — 구성 성분별 실측 근거는 SSoT에서 추적 불가.

**등재 10건**:

| # | 위치 | 근거유형 | 앵커 count | 비고 |
|---|---|---|---|---|
| (1) | 7.6(f) 단서 append + **7.7(l) 신규** | PR 본문 서술·미실측 | 1/1 | 해결책·타임아웃 신설 0, "I2 설계 시점 판단"으로 못박음 |
| (2) | 6.1 (인증 분리 + stats period 두 지점) | 실측 (`auth.py`/`routes.py`) | 1/1 | 신규 |
| (3) | 7.5(e) append | 문서 인용·미실측 | 1 | 신규 |
| (4) | 5.1 (7/09 프로토콜 append) | 사용자 확정(2026-09-03) | 1 | 신규 |
| (5)+(6) | **6.3(l) 신규**(7항목으로 병합) | 실측 코드 대조 | 1 | M5-d 착수 전 체크리스트 |
| (7) | 8.4(f) append | 실측 (`run.mjs`) | 1 | 신규 |
| (8) | 27.8(g)⑤ append | 실측 재실행 | 1 | 단서(정정 아님), (f-2)와 동형 재발 |
| (9) | 8.5(i) append | 논증 | 1 | 단서(정정 아님), 기존 문구 보존 |
| (10) | 27.8(f) append | 문서 인용·미실측 | 1 | 단서(정정 아님) — 유령 여부 미확정, ③ 계층으로만 취급 |

**스코프 제외 재확인(미접촉)**: 인용 오기 누적 수 정정(27.8(g) 19건 그대로) / PoC-(44) Set 3 인용 오기 4건 / 「압축 손실」 등재 위치(27.8(g)② 그대로) / 지침 슬림화 자체 / 노션 / 코드 전 파일.

**Step 4 검증**: 취소선 총수 **착수 전 62줄/140개 → 종료 62줄/140개(무변화)** — 본 Set 10건 전부 **순수 append**(취소선 0건, 기존 서술 취소선 대상 아님). **삭제 0줄**: `git diff --stat` = 23 insertions / 1 deletion, 그 1 deletion은 7.6(f) 한 줄을 **원문 그대로 보존한 채 문장 뒤에 단서를 이어붙인 것**(원문이 신문 라인의 완전한 접두사임을 대조 확인, 실질 삭제 아님) — 나머지 9곳은 순수 라인 삽입. **앵커 10건 전건 `count == 1` assert 통과**(패턴 매칭, 라인 번호 미사용). 요일 `date -j -f "%Y-%m-%d" "2026-09-10" "+%A"` = **Thursday = 목** 검산. `.env`·토큰·자격증명 전부 미기록.

**학습 적용**: 학습 13(grep 후 인용 — 위 10건 전부 grep 실물 대조 후 등재) / 학습 14(repo 가정 검증 — Step 0 12항목) / 학습 16(기존 컨벤션 우선 — 새 절 번호는 `^### ` grep으로 결정, 임의 추정 0) / 학습 21(유령 미결 5분류 — A8 6건 전부 real 확인, (10)은 유령 여부 미확정 상태로 단서만 등재해 §9-d 성격의 신중 처리).

**비범위**: **코드 0 수정**(읽기만, `git diff --name-only` = `docs/` 2파일뿐). §9 트리거 **미발동**(정지 임계 전건 O, 위치 충돌 없음, (1) 출처 단일, 기존 서술과 정면 충돌 0건). 해결책·정책·수치 신설 **0건**(전부 등재만). 22주 일정표 평가 미착수.

**관련 카테고리**: 5.1(도어벨 4유닛 구매 요건) / 6.1(`DASHBOARD_TOKEN`/`DEVICE_TOKEN` 분리 · `/stats` 당일 집계) / 6.3(l)(M5-d 착수 전 체크리스트 7건 신설) / 7.5(e)(KOE 에러코드) / 7.6(f)(역방향 stale 단서) / 7.7(l)(펌웨어 12.1초 신규 미결) / 8.4(f)(`$&` 치환자 함수) / 8.5(i)(11주차 표기 단서) / 27.8(f)(G-ID 미확인 6종 단서) / 27.8(g)⑤(0건 측정 시점값 단서)
**관련 commit**: 문서 전용 — 본 엔트리가 곧 해당 커밋(PR 없음, main 직 push). 선행 = `ecf5f47`(같은 날짜 이전 PoC-(44) 반영)

## 2026-09-11 (금) — PoC-(45) Set 1 — M5-d 오디오 배관 완성 + ToF 송신 G10 CLOSE + 마이크 잡음 근본원인 진단 하네스 SSoT 등재 (카테고리 6.2/6.3/6.4/9.4/27.8)

2026-09-11 코드 작업 3건(PR #52 `b3414a4` M5-d 오디오 배관 / PR #53 `5049612` ToF 송신 + `tof_common` 승격 / PR #54 `f938813` `env:mic_noiseprobe` 잡음 진단 하네스) + 학부생 ④런타임 3세션(PR 댓글)을 SSoT에 등재. 1차 출처 = 각 PR 본문 + `gh pr view <N> --comments`. **코드 0 수정**(PR은 기 머지 코드 인용, 본 세션 무접촉 — `git diff --name-only` = `docs/` 2파일뿐), 대상은 `docs/decisions.md`·`docs/decisions-log.md` 두 파일뿐.

**Step 0 가정 대조 — 전건 O**: HEAD `f9388135e5704c3c3124974012a61c858da985f8`(= `f938813`) / 워킹트리 clean(A1). 6.2(168행)·6.4(283행) 양쪽에 "G10 수신측 CLOSE ≠ G10 CLOSE" 문구 실존(A2). 6.3(l) M5-d 체크리스트 7건 실존, a8dcfc5(2026-09-10 PoC-(45) 최초 커밋) 등재분(A3). 9.4(f)① `presence_state` 서술 정확히 1건, 문구 그대로 실존(A4). 9.4(e) 프로토콜 ② 미수행 서술 실존(A5). `tof_presence` ↔ presence∧latch 확정 매핑 문구 = decisions.md 0건(6.4(b) 논증 서술 + 9.4(d) latch 관찰만 실존, 확정 문구는 부재)(A6). env 개수를 "현재값"으로 서술한 곳은 없고, 2026-09-02 시점 "9개"라는 **이력 서술**만 1건 실존 — `firmware/platformio.ini` 실물 재조회 결과 **현재 11개**(A7). `gh pr view 52/53/54`로 본문·댓글 조회 가능, 3건 전부 MERGED(A8). 27.8(g) 누적 인용 오기 = **19건**, 문구 그대로 실존(A9). **정지 임계(A1·A8) O → 착수. A2·A6·A7은 예고대로 pivot 없이 그대로 진행**(A2=취소선 대상 확정, A6=확정 매핑 신규 등재 대상 확정, A7=단서 append 대상 확정).

**find-skills**: `decision log markdown` — `bonkey/skills@decision-log` 등 다수 실존, 대조 질의 `git`도 `git-guardrails-claude-code` 343K 등 정상 실존(도구 생존 확인). decision-log·changelog 신규 파일류는 과거 ② 판정(단일 decisions.md 누적 방식과 워크플로 불일치, 2026-09-10 PoC-(45) 최초분에서 이미 판정)과 **동일 skill류** — 재평가 불요, 재사용.

**Step 1 출처 인용**: PR #52/#53/#54 본문·댓글 전문 조회(`gh pr view <N> --json body -q .body` + `gh pr view <N> --comments`) 후 아래 등재에 반영한 수치·인용은 전부 그 원문에서 그대로 옮김(기억 미사용).

**등재 10건 (E1~E10)**:

| # | 위치 | 근거유형 | 앵커 count | 비고 |
|---|---|---|---|---|
| E1 | 6.3(l) 항목별 처리 append + **6.3(m) 신규**(설계 D1~D4 + ④런타임) | 실측(PR #52 본문·댓글) | 8/8 (l 7항목 + m 헤더) | 처리/해당없음/스코프제외 3분류 완료 |
| E2 | 6.3(m) 내 Runbook 불일치 3건 | 실측(PR #52 댓글) | 1/1 | rms 미출력·모니터 지연·80B 절단 |
| E3 | 6.2(168행)·6.4(283행) 취소선+CLOSE + **6.4(g) 신규**(④런타임) | 실측(PR #52·#53 본문·댓글) | 3/3 | env:prod 별개 미결 단서 포함 |
| E4 | 6.4(b) append | 논증, 사용자 확정 2026-09-11 | 1/1 | fused = presence_state ∧ motion_latch_active |
| E5 | 9.4(f) append(③) | 실측(PR #53 본문) | 1/1 | tof_common.cpp 승격, diff 0, 196 checks |
| E6 | 9.4(e) append | 논증, n=1(PR #53 댓글) | 1/1 | 판정 변경 없음, 프로토콜 ② 미수행 유지 |
| E7 | **6.3(n) 신규** | 실측 A/B + 실측 5모드 + 논증(PR #53·#54 댓글) | 1/1 | H2·H3 기각, H1 가능성 높음. 해결책 = 사용자 판단 대기 |
| E8 | **6.3(o) 신규** | 실측(PR #54 본문) | 1/1 | noise_stats 61 checks, NC 6종, host_stubs |
| E9 | **27.8(h) 신규** + 27.8(d) 누적 갱신(취소선+append) | 실측 grep | 3/3 | 19→21건, 출처 계층 착각 4호 + 기능범위 과대서술 |
| E10 | 카테고리 20 env 9개 서술 append(1254행) | 실측(`platformio.ini`) | 1/1 | 이력 9개 무변경, 현재값 11개 단서 |

**스코프 제외 재확인(미접촉)**: 잡음 해결책 선택(①펌웨어 필터 ②배선 조치 ③병행) — **사용자 판단 대기, 방식·수치 확정 0건**. `TOF_MOTION_NDET_MIN` 등 판정 상수 재검토 — 향후 판정 PR 소관. PoC-(44) Set 3 인용 오기 4건 등재 여부 — 미착수. 운영 사항(아이폰 핫스팟 설정 화면 · secrets 교체 절차) — 지침 전용, 무접촉. 노션 — 무접촉. `docs/` 2파일 외 코드·문서 — 무접촉.

**Step 4 검증**: 취소선 **착수 전 62줄/140개 → 종료 63줄/146개**(+1줄/+6개 — 신규 취소선 3쌍 중 2쌍은 기존 취소선 보유 줄 위에 추가돼 줄 수 불변, 1쌍은 신규 줄, 전건 **짝수 유지 = 마크다운 무파손**). **삭제 0줄**: `git diff --stat` = 85 insertions(+) / 12 deletions(-), 그 12 deletions 전부 **원문을 취소선으로 감싸거나 뒤에 문장을 이어붙인 in-place 수정**이며 `git diff -U0`로 12줄 전건 대조한 결과 옛 줄의 모든 문자열이 새 줄에 **부분열로 그대로 보존**됨을 확인(실질 삭제 0). **앵커 10건(E1~E10 세부 15개 지점) 전건 `grep -cF` count == 1 assert 통과**(패턴 매칭, 라인 번호 미사용). 요일 `date -j -f "%Y-%m-%d" "2026-09-11" "+%A"` = **Friday = 금** 검산.

**학습 적용**: 학습 13(grep 후 인용 — PR 본문·댓글 전문 조회 후 등재, 위임이 준 A9 「19건」 등 인용값도 실물 대조 완료) / 학습 16(기존 컨벤션 우선 — 신규 절 letter는 `sed + grep -nE "^\*\*\([a-z]\)"`로 기존 마지막 letter 확인 후 다음 letter만 사용, 6.3(l)→(m)(n)(o) / 27.8(g)(f)→(h)) / 학습 19(위임 전제 재검증 — E4 매핑 근거로 PR #53이 인용한 tof_meta.py docstring이 decisions.md 문구가 아님을 grep으로 재확인 후 E9①로 별도 기록) / 학습 20(원격 아님, 해당 없음) / 학습 21(유령 미결 5분류 — E1 6.3(l) 7항목을 처리/해당없음/스코프제외로 전수 분류, 미판정 잔류 0건) / 27.8(f-2)(grep 건수 = 측정 시점값 — E9 자체가 27.8(d) 누적 카운트를 「그 시점값」으로 취급해 취소선+새 값 append, 숫자를 직접 고치지 않음).

**비범위**: **코드 0 수정**(PR #52/#53/#54는 기 머지 코드 인용, 본 세션 무접촉 — `git diff --name-only` = `docs/` 2파일뿐). `docs/git-convention.md` 무접촉. 잡음 해결책 선택·판정 상수 재검토·PoC-(44) Set 3 인용 오기·운영 절차·노션 — 전부 §2 OUT 그대로 미착수(위 스코프 제외 재확인 참조). 22주 일정표·마일스톤 평가 미착수. 브랜치 없이 **main 직 push**(문서 단독, 카테고리 20 「문서/코드 변경 push 분리」).

**관련 카테고리**: 6.2(G10 CLOSE) / 6.3(l)(체크리스트 처리 결과) / 6.3(m)(M5-d 설계·④런타임) / 6.3(n)(ToF-마이크 간섭 신규 미결) / 6.3(o)(mic_noiseprobe 방법론 자산) / 6.4(b)(tof_presence 매핑 확정) / 6.4(g)(ToF 송신 ④런타임) / 9.4(e)(프로토콜 ② n=1 단서) / 9.4(f)(tof_common 승격) / 27.8(d)(누적 21건) / 27.8(h)(인용 오기 2건 신설) / 카테고리 20(env 개수 현재값 단서)
**관련 commit**: 코드 PR #52 `b3414a4` + PR #53 `5049612` + PR #54 `f938813`(기 머지) + 문서 반영 = 본 Set 1 커밋(docs-only, PR 없음). 선행 = `a8dcfc5`(같은 PoC-(45) 번호의 2026-09-10 최초 반영)

## 2026-09-12 (토) — PoC-(46) Set 1 — 실모델 첫 서버 투입(33.6 신설) + 카테고리 26 시연 요구사항 repo 실물 전수 감사(26.10 신설) + 진입점 2 「ToF presence 단독」 축소 확정 + 도움말 카피·랜딩(8.7 신설) + twMerge 토큰 소실 + C-0 라벨 오기 정정 (카테고리 6.3/8.4/8.7/21/26.3/26.10/27.8/33.6)

2026-09-12 코드 작업 3건(PR #55 `dddde9b` **미머지** 풀다운 판별 모드 / PR #56 `fb9155f` 도움말 카피 2라운드 정정 / PR #57 `9b32183` 랜딩 페이지 신설) + 실측 2건(실모델 OOD 스윕 · held-out 재현) + 카테고리 26 전수 감사 + 사용자 결정 1건을 SSoT에 등재. **코드 0 수정**(PR은 기 머지·미머지 코드 인용, 본 세션 무접촉 — `git diff --name-only` = `docs/` 2파일뿐), 대상은 `docs/decisions.md`·`docs/decisions-log.md` 두 파일뿐. **노션 무접촉**(Set 3 소관), **프로젝트 지침 무접촉**(Set 2 소관).

**Step 0 가정 대조 — 전건 O**: 브랜치 `main` / HEAD `9b32183` / 워킹트리 clean(A1). `docs/decisions.md`(2,629줄) · `docs/decisions-log.md`(1,791줄) 실재(A2). `decisions-log.md` 마지막 엔트리(2026-09-11 PoC-(45) Set 1) 실물 전사 — 헤더 `## YYYY-MM-DD (요일) — PoC-(NN) <제목> (카테고리 …)` + 본문 + `**SSoT 정합 검증**` / `**비범위**` / `**관련 카테고리**` / `**관련 commit**`(A3). 카테고리·절 헤더 전수 = `git show HEAD:docs/decisions.md | grep -nE "^## 카테고리|^### "`로 확보, 카테고리 1~33 · `### ` 전수 목록 취득(A4). §4 인용 대상 **전건 실재**(A5 — 6.3(n)(o) / 6.4(b)(g) / 7.5(i) / 7.7(g) / 8.3 신규 미결 2건 / 8.4(f) / 9.4(e) / 27.8(d)(h) / 33.1·33.2·33.5 / 카테고리 26 전체. 부재 0건 = §9 미발동). 실측 로그 2개 실재·읽기 가능(A6 — `realmodel_ood_sweep.log` 29줄 · `realmodel_holdout_eval.log`). 요일 `date -j -f "%Y-%m-%d" "2026-09-12" "+%A"` = **Saturday = 토** 검산(A7). 취소선 사전 측정 = **63줄**(`grep -c '~~'` = **줄 수**) / **146개**(`grep -o '~~' | wc -l` = **출현 수**, 짝수 = 마크다운 무파손)(A8). **정지 임계(A1·A3 단독 포함) 미해당 → 착수.**

**find-skills — ⚠️ CLI 표면 변경 catch**: 위임이 지정한 `npx skills find`는 **`error: unknown command 'find'`**로 죽었다. `npx skills --help` 실물 확인 결과 하위 명령이 **`search|s`**로 바뀌어 있었다(`add` / `uninstall` / `list` / `search` / `info` / `init` / `publish` / `update` / `run` / `open`). ⇒ **0건이 아니라 명령 부재**였다 — "0건이면 도구 사망부터 의심"의 **변형**이며, 도구가 아니라 **명령 이름이 죽은** 경우다. `search`로 재실행: `markdown edit` **1건**(`markdown-editor-integrator` = `@uiw/react-md-editor` 설치용) / `changelog` **98건** / `documentation` **1116건** / 대조 질의 `git` **1449건**(도구 생존 확인). **미채택 사유 = ② 워크플로 불일치 전건** — changelog 자동 생성류(`changelog-generator` 14,487★ 등)는 **git 커밋에서 사용자용 릴리스 노트를 뽑는** 도구인데 우리 log는 **사람이 판단·반증·경계 표기를 서술**하는 문서다. `markdown-editor-integrator`는 **React 에디터 컴포넌트 설치**라 도메인 무관. ADR 신규 파일 생성류는 **과거 미채택 판정 재사용**(단일 `decisions.md` 누적 = 취소선 + append와 충돌, 재평가 불요).

### Step 1 — 등재 위치 설계 (E1~E15, 전건 grep 후 결정)

| ID | 등재 위치 | 근거(grep) | 편집 유형 | 앵커 count |
|---|---|---|---|---|
| E1 | **6.3(n) append** | (n)이 곧 그 미결의 등재 자리 — 단일 등재 원칙상 신설 불가 | append | 1 |
| E2 | **8.7(a) 신설** | `^### 8\.` = 8.1~8.6만 존재 | 신설 | 1 |
| E3 | **8.7(b) 신설** | 동상 | 신설 | 1 |
| E4 | **33.6(a) 신설** | `^### 33\.` = 33.1~33.5만 존재 | 신설 | 1 |
| E5' | **33.6(b) 신설** | 동상 | 신설 | 1 |
| E6 | **26.10(a)(b) 신설** | `26.10` 리터럴 = **0건** | 신설 | 1 |
| E7 | **26.3 진입점 2 in-place** + 26.10(c) | 26.3·26.4에 **취소선 + 신규 서술 선례 2건** 실존 | 취소선 3쌍 | 1 |
| E8 | **26.10(d) 신설** | 동상 | 신설 | 1 |
| E9 | **26.3 진입점 2 in-place** + 26.10(e) | 본문 3줄 실존 대조 완료 | 취소선(E7과 동일 편집) | 1 |
| E10 | **8.7(c) 신설** | 8.4는 PR #47 범위 절 — PR #57 건을 넣으면 절 범위 파손 | 신설 | 1 |
| E11(a)(b) | **8.4(f) append** | (f)가 하네스 한계·검증 절차의 기존 자리 | append | 1 |
| E11(c) | **33.6(c) 신설** | 실모델 기동 조건 = 33.6 소관 | 신설 | 1 |
| E11(d) | **카테고리 21 append(단서만)** | 🔴 **이미 등재된 기존 미결**(2026-09-09 PoC-(44)) — 신규 등재 시 **중복** | append(단서) | 1 |
| E12 | **8.4(f) append(한계 ④)** | (f)가 ①②③을 이미 열거 | append | 1 |
| E13 | **8.7(d) 신설** | PR #57 소관 | 신설 | 1 |
| E14 | **6.3(n) 「영향」 문단 in-place** | 대상 문구 `grep -cF` = **1**(물리적 실존 확인 후 취소선) | 취소선 1쌍 | 1 |
| E15 | **27.8(i) 신설** | 27.8 letter 전수 = (a)~(h), (i) 미사용 | 신설 | 1 |

**신설 절 번호 결정 근거 (전부 grep 실물, 위임 미지정)**: **8.7** = `grep -nE "^### 8\."` → 8.1~8.6만 존재, 다음 빈 번호. **26.10** = `grep -n "26\.10" docs/decisions.md` → **0건**(카테고리 26은 26.1~26.9의 **번호 체계**이므로 카테고리 20식 무번호 `###` 선례는 **적용하지 않았다** — 같은 카테고리 안에서 체계를 섞지 않는다). **33.6** = 33.1~33.5만 존재, 다음 빈 번호(카테고리 33에는 무번호 `### USP 2층 재정립`도 있으나 **2026-07-09 당시 33.5의 후속 서술**이라 선례로 삼지 않음). **27.8(i)** = (a)~(h) 실존 확인 후 다음 letter. **6.3(p)는 만들지 않았다** — E1은 (n)의 하위 사실이라 (n) 안에 넣는 것이 단일 등재 원칙에 맞다.

### 🔴 위임 자기모순 catch 1건 (학습 16·21)

- **E11(d) `.env` 2줄 중복은 「기술 사실 — 지침·인계에만 있던 것」이 아니라 이미 SSoT에 등재된 미결이다.** 실물 = 카테고리 21 「시크릿 파일(`.env`) 편집 위생」 아래 **2026-09-09 PoC-(44) 신설 미결**(*"`>>` 추가가 키 중복을 누적시킨다"*, 판정 방법·해소 방침 미확정까지 기 등재). ⇒ **신규 등재하면 중복**이므로 **재확인 단서만 append**했다(`grep -c` = **여전히 2**, 3일 경과·미해소). **방침·값 무변경.**

### 등재 내용 요약

- **E1 (6.3(n))**: PR #55 `dddde9b` **OPEN·미머지**, ④런타임 **미수행**. 가설 = INMP441 SD tri-state → 데이터시트 100kΩ 풀다운 권장 / 오류 비트가 워드 **선두**에 몰린 위치와 일치(**논증, 미실측**). m5(m2+풀다운) / m6(m0+풀다운, 부작용 대조군). 호스트 테스트 **신규 46 checks**, 기존 `noise_stats_test` **61** · `tof_judge_test` **196** 유지. 🔴 **가설 검증 수단이지 해결책이 아님**을 명기 — 해결책 ①②③은 **사용자 판단 대기 그대로**.
- **E14 (6.3(n) 「영향」)**: `C-0(6.3(c)~(k))는 …` 문구 취소선 + 정정. **실질 주장은 유효**(ToF 미구동 펌웨어 측정이라 실측치 유효 / M5-c 임계값 재확인 필요), 틀린 것은 **라벨**. ⚠️ 경계 표기 = `grep -nE "\bC-[0-9]" docs/` **2건**이고 **C-0의 정의는 `docs/` 어디에도 없다** — 인계 계층에만 있어 SSoT 안에서 안 잡혔다. "C-0 = 미착수 현관 인터폰 실측"은 **인계 서술(repo 미검증)**로 표기.
- **E2·E3·E10·E13 (8.7 신설, 4항목)**: (a) PR #56 2라운드 — 1차 = 없는 등록 기능 약속 제거 / 2차 = **반대 방향 불일치**(ToF 게이트를 감춤) 정정, fire_alarm은 `fire_alarm_bypass`라 무변경이 정확. FAQ 1번은 **미수정·사용자 판단 대기**로 등재. (b) PR #57 라우트 `/`=랜딩 / `/home`=대시보드, 기존 4경로+`*` 무변경(`App.tsx` 실물 대조), 신규 의존성 0, 모션 게이트 OR + `index.css` 2중 방어. 리디자인 근거 = **사용자 육안 판정**("AI 티"). **PR 성격 어휘는 신설하지 않았다**(사용자 판단 대기). (c) `tailwind-merge` **3.6.0** 토큰 소실 — **본 세션 in-session 재현 3케이스**(소실 / 대조군 유지 / `length:` 보존). 잔존 = `NotificationTof.tsx` **1개 병합 지점 / 분기 3종 전부**, 8.4 무변경 대상이라 **미수정·사용자 판단 대기**. 🔴 검증 4종 전부 통과 = **「클래스가 코드에 있음 ≠ 화면에 적용됨」**. (d) 말풍선 문구 = `PRIMARY_MESSAGES["doorbell"]` / `SECONDARY_FEED_TITLES["doorbell"]`과 문자 일치(실물 인용)이나 **정렬은 연출**(본인 발신 오른쪽 ↔ 랜딩 왼쪽), 화면 고지 실물 인용 + **향후 「실물 근거」 인용 금지** 명기.
- **E11(a)(b)·E12 (8.4(f) append)**: 한계 **④ 렌더 대상 밖 = 도달 불가** 신설(②와 다른 축), `twMerge` 소실도 같은 이유로 도달 불가. 환경 사실 ① `ssr-nc`는 **미커밋 diff가 있으면 exit 1**(자기 임시 변형과 구분 못 함) ⇒ **검증 → 커밋 → ssr-nc** 순서 / ② `npm run build`가 `tsc -b && vite build` **포함형**(단독 `tsc -b`는 중복·무해).
- **E4·E5'·E11(c) (33.6 신설)**: (a) OOD 스윕 7종 n=1 — 실모델 확증 3축(RSS 475,920KB / TF 매핑 54개 / 동일 입력 2회 `all_scores` 일치). **분포 밖 입력이 `fire_alarm`으로 수렴**, 🔴 **사람 목소리 2건이 게이트를 넘어 실제 카톡 발송**(0.87·0.99). ⚠️ 진폭만 0.05↔0.9로 knock↔fire_alarm 전환(동일 `seed(42)` 파형). ⚠️ **게이트는 설계대로 작동**(0.62·0.61·0.65 차단) = **게이트 결함 아님**. (b) held-out 424 전수 재현 **acc 0.8868** = `eval_report.json` **0.8867924528301887** 일치, recall 0.742/0.889/0.921 일치, `doorbell→fire_alarm` **10건** 재현 ⇒ **(a)의 대조군 성립 · "입력 무관 쏠림" 기각**. 🆕 게이트 축(7월 평가에 없던 측정) = doorbell pass_ok 44 / **pass_NG 9** / blocked 9(85.5%) · knock 92/5/11(89.8%) · fire_alarm 231/13/10(96.1%). ⚠️ **`pass_NG`의 오분류 대상 클래스 내역 미측정**. (c) `server/venv_real`(py3.11.15 / TF 2.16.2) 필요 — 기존 `venv`는 py3.14라 TF wheel 부재 ⇒ **평소 기동 명령으로 real 불가**, 현재 기본 기동은 **mock ML**. `DDINGDONG_MODEL_PATH`는 **셸 앞 변수만**(`.env` 무변경). ⚠️ `decode_pcm16` 반환 **(1,N)** — `[None,:]` 배치 재추가 시 (1,1,N) → yamnet Pad 에러 **424건 전건 실패**. 🔴 **`routes.py`는 그대로 전달하므로 서버 경로는 정상** = **검증 스크립트만의 결함**.
- **E6·E8 (26.10 신설) + E7·E9 (26.3 in-place)**: (a) 등록 제품 코드 **0줄** 실측 — 등록 라우트 0(**대조군** = `rate_limit.check_and_register` 1건이 잡혀 grep 생존 확인) / `__tablename__` 전수 3개 / `App.tsx` 라우트 전수 7개 / `_apply_prediction_policy()` 판정 분기 전수 **신뢰도·fire_alarm·ToF 3개뿐** / `dtw_doorbell` 제품 경로 참조 **0건**. ⚠️ **repo 기준 감사** — 노션 DB3 대조는 Set 3. (b) 5분류 = **③ 5건 / ④ 3건**, **계수 단위 = 개별 요구사항 수**(26.9 표의 행 수 아님)로 명기하고 내역을 전건 나열. G3·G4·G5는 「🔴 시연 필수」인데 실물 0줄이고, 동시에 **G1·G2는 실물화됐는데 표가 미갱신** = 양방향 stale. (c) **사용자 결정** — 등록·해제 시연 제외, 근거 3(33.5 SP/DTW 단독 NO 확정 / USP 1층이 ToF라 메시지 유지 / D-18 비현실). 26.3 본문 3줄 취소선 + 축소 서술. (d) 🔴 신규 미결 = **실모델 투입이 선행 조건**(경로가 6.4(g)에서 미관측 + 기본 기동이 mock). ⚠️ OOD와 **한 번에 건드리지 말 것**. (e) **6.4(b) fused 확정이 26.3 진입점 1·2 서술에 미반영** — latch 75프레임(5초) 설계 vs 9.4(e) 정지 사물 **PERSON 유지 n=1**이 **반대 방향**이라 실제 부스 동작 **미확정**. 시연 각본 조정 = 사용자 판단 대기.
- **E15 (27.8(i) 신설)**: 인용 오기 2건 **전부 라인 번호**(`345`→실제 349 / `1979`→실제 1981). **내용·문구는 정확 = 실질 피해 0**, 틀린 것은 **형식**. 라인 번호는 **앞줄 한 줄만 늘어도 틀린다** — (f-2) 「grep 건수 = 측정 시점값」과 같은 축. ⚠️ **(d) 누적 21건은 무변경** — PoC-(44) Set 3 4건 + 본 2건의 합산 여부가 **사용자 판단 대기**라, (d)가 본 (i)를 **포함하지 않는 값**임을 경계 표기로 남겼다.

### 🔴 사용자 판단 대기 항목 — 등재하되 방향 미확정 (전건 명시 확인)

| 항목 | 등재 위치 | 방향 확정 여부 |
|---|---|---|
| 마이크 SD 비트 오류 해결책 ①펌웨어 필터 / ②배선 / ③병행 | 6.3(n) 기존 문구 **무변경** + E1이 *"해결책이 아님"* 명기 | **미확정 유지** |
| OOD 대응(임계 재검토 / 4번째 클래스 / 재학습 / 각본 조정) | 33.6(a)(b) + 26.10(d) | **미확정 — "n=1 위에 임계·정책 확정 금지" 명기** |
| 인용 오기 SSoT 누적 합산(PoC-(44) Set 3 4건 + 본 2건) | 27.8(i) | **미확정 — (d) 누적 21건 무변경 + 경계 표기** |
| `NotificationTof.tsx` twMerge 소실 수정 여부 | 8.7(c) | **미확정 — 8.4 무변경 대상 예외 허가 사안으로 표기** |
| PR 성격 어휘 신설 여부 | 8.7(b) | **미확정 — 어휘 신설 0, 분류 체계 미등재 사실 병기** |
| HelpPage FAQ 1번 카피 | 8.7(a) | **미확정 — 미수정 사실만 등재** |
| DB3 stale 제목 2건 / 26.9 표 갱신 | 26.10(b)(c) | **Set 3 소관 명기, 본 Set 무접촉** |

**SSoT 정합 검증 (문서라 코드 3단계 N/A)**: 신설 절 번호 **8.7** / **26.10** / **33.6** / **27.8(i)** 전건 `grep` 실물 확인 후 결정 — **충돌 0건**(위 「신설 절 번호 결정 근거」 참조). 편집 앵커 **9건 전건 `str.count` == 1 assert 통과**(패턴 매칭, **라인 번호 미사용** — E15가 지적한 위반의 자기 준수). 취소선 총수 **착수 전 63줄 / 146개 → 종료 67줄 / 154개**(계수 단위 = `grep -c '~~'` **줄 수** / `grep -o '~~' | wc -l` **출현 수**). 증가분 **+4줄 / +8개 = 신규 취소선 4쌍**(E14 1쌍 + 26.3 진입점 2의 3쌍)으로 **설계와 정확히 일치**하며 **154 = 짝수 = 마크다운 무파손**. **삭제 0줄**: `git diff --stat` = **174 insertions / 4 deletions**, 그 4 deletions은 전부 **원문을 `~~`로 감싼 in-place 수정**이다 — `git diff -U0` 제거 4줄 전건에 대해 **추가줄에서 `~~`만 제거한 정규화 기준 부분문자열 대조 = 4/4 완전 보존**, **정규화 기준 미보존 토큰 0종**. 원시 기준 미보존 **5종**(`C-0(6.3(c)~(k))는` / `필요**.` / `참조)` / `**해제` / `가능`)은 전부 **`~~` 인접에 의한 토큰 분할**이며, 분할 후 실물(`~~C-0(6.3(c)~(k))는` / `필요**.~~` / `참조)~~` / `~~**해제` / `가능~~`)을 **각 1건씩 개별 grep으로 확인**했다. 요일 `date -j -f "%Y-%m-%d" "2026-09-12" "+%A"` = **Saturday = 토** 검산. 원격 = `git ls-remote origin`으로 실물 확인(`refs/heads/main` + `refs/heads/feat/firmware-noiseprobe-pulldown` 2건, **`git branch -r` 미사용** — 학습 20). PR 상태는 `gh pr list --state all`로 실측(#55 **OPEN** / #56 · #57 **MERGED** + mergeCommit `fb9155f` · `9b32183` 대조). **부재 G-ID 미사용** — 본문·커밋 제목에 쓴 G-ID는 **G10 · G12 둘뿐**이며 실존 전수(`G10 G12 G14 G18 G21 G22 G24 G27 G28 G29`) 내에 있다. `.env` 값·카카오 토큰·NCP 자격증명·모델 경로 실값 **전부 미기록**(`.env` 중복 단서는 **키 이름과 건수만**). **세션 갭 없음**(직전 엔트리 = 2026-09-11 PoC-(45) Set 1).

**비범위**: **코드 0 수정**(`server/` `firmware/` `ml/` `dashboard/` 이하 전부 무접촉 — `git diff --name-only` = `docs/` 2파일뿐. PR #55/#56/#57은 기 작성 코드 인용). **노션 무접촉**(DB3 신규 row · 26.9 Gap 카드 갱신 · stale 제목 2건 = **Set 3 소관**). **프로젝트 지침 파일 무접촉**(= **Set 2 소관**, C-0 정의 등재 포함). 위 「사용자 판단 대기」 7건 **전부 방향 미확정으로 등재만** — 임계값·정책·수치 신설 **0건**. `docs/git-convention.md` 무접촉. 22주 일정표·마일스톤 달성률 **미평가**(학부생 판단 사안). 6.3(n) 해결책 선택 · `TOF_MOTION_NDET_MIN` 등 판정 상수 재검토 · `pass_NG` 오분류 내역 측정 · 실 초인종 음원 실측 · ESP32 미연동 · EC2 미기동 — 전부 미착수. 브랜치 없이 **main 직 push**(문서 단독, 카테고리 20 「문서/코드 변경 push 분리」).

**학습 적용**: **학습 13**(grep 후 인용 — §4 인용 대상 전건 실물 대조, 위임이 준 수치·경로도 catch 대상으로 재확인: `NotificationTof.tsx` 실경로가 `components/notifications/` 하위임을 실측, `SECONDARY_FEED_TITLES` dict 명 실측 확인. **라인 번호를 편집 앵커로 0건 사용**) / **학습 14**(repo 구조 가정 실물 대조 — Step 0 A1~A8) / **학습 16**(기존 컨벤션 우선 + 위임 자기모순 catch — 26.3의 취소선 선례를 따랐고, **E11(d)가 기존 등재 미결임을 catch**해 중복 등재를 막았다. `npx skills find` → **`search`** CLI 표면 변경도 catch) / **학습 19**(진단 재검증 — E10 `twMerge` 소실을 **위임 보고 그대로 옮기지 않고 in-session `twMerge` 직접 호출로 3케이스 재현**, 해법 형태까지 실측) / **학습 20**(원격 브랜치는 `git ls-remote` — PR #55 HEAD `dddde9b` 실물 확인, `git branch -r` 미사용) / **학습 21**(유령 미결 5분류 — 26.10(b)에서 **③ 5건 / ④ 3건** 전수 분류, 미판정 잔류 0건. **④ "부재로 기록됐으나 실재" 3건**이 26.9 표의 역방향 stale) / **27.8(f-2) 계열**(측정 시점값 — 취소선 총수·grep 건수·**라인 번호**를 전부 시점값으로 취급, 27.8(d) 누적 카운트는 **직접 고치지 않고** (i)에 경계 표기) / **「현재값 vs 이력」**(27.8(d) 누적 21건 = **현재값이라 사용자 판단 전까지 무변경** / 7.5(i) 회귀 102건 = 본 Set **무접촉**) / **「압축 손실」**(26.10(b) 5분류의 **계수 단위(개별 요구사항 수 ≠ 표의 행 수)**를 명시하고 ③5·④3의 내역을 **원소별로 전건 나열**. 8.7(c)의 "3분기 전부"도 **3종 분기값을 개별 호출로 확인** 후 서술) / **「발견일 ≠ 반영일」**(E14·E15·8.7(c)는 발견·반영 모두 2026-09-12로 같은 날이나 **양쪽 다 표기**) / **「실측 / 논증 / 문서인용 3분」**(E1 = 논증·미실측 / E4·E5' = 실측 / E8 = 논증 + "입력 실측 = 33.6·6.4(g)" 분리 표기 / C-0 정의 = "인계 서술, repo 미검증").

**관련 카테고리**: **33.6 (실모델 OOD · held-out 재현 · 게이트 축 신설)** / **26.10 (시연 요구사항 전수 감사 · 5분류 · 진입점 2 축소 · 신규 미결 · fused 미반영 신설)** / 26.3 (진입점 2 in-place 축소 — 취소선 3쌍) / **8.7 (도움말 카피 2라운드 · 랜딩 · twMerge · 연출 고지 신설)** / 8.4(f) (하네스 한계 ④ · 검증 도구 환경 사실 2건 append) / 6.3(n) (PR #55 가설 검증 수단 append + **C-0 라벨 오기 취소선 정정**) / 6.4(b)(g) (fused 매핑 · ④런타임 미관측 — 26.10(d)(e)의 입력) / 9.4(b)(e) (latch 75프레임 · 정지 사물 n=1 반대 방향) / 33.2·33.5 (예비 학습 성적 재현 대상 · USP 2층 · SP/DTW 단독 시연 NO) / 21 (`.env` 키 중복 미결 **재확인 단서** append — 신규 등재 아님) / **27.8(i) (인용 오기 2건 신설, (d) 누적 무변경)** / 7.1·7.6 (확정 카피 · 2차 사진 feed — 8.7(a)(d) 대조 대상) / 8.3 (접근성·모션 규약) / 카테고리 3 (G12 · 클래스별 ToF 정책 · 신뢰도 임계값) / 20 (문서/코드 push 분리 · negative control 계열 · 학습 20)
**관련 commit**: 코드 PR #56 `fb9155f` + PR #57 `9b32183`(기 머지) + PR #55 `dddde9b`(**미머지, OPEN**) + 문서 반영 = 본 Set 1 커밋(docs-only, PR 없음, main 직 push). 선행 = `9b32183`(PR #57 머지 = 착수 시점 HEAD)

## 2026-09-14 (월) — PoC-(47) Set 1 — 게이트 축 전수 재현 + `pass_NG` 오분류 내역 실측(33.6(b) 「미측정」 해소, 33.6(d) 신설) + `confidence` round 위치 신규 미결(33.6(e) 신설) + `tof_rejected` 실모델 관통 서버·화면 양축(26.10(d) 부분 해소 · 6.4(g) 후속) + 카카오 refresh 만료 현재값 정정 + 데이터셋 폴더 단서 (카테고리 5/6.4/7/26.10/33.6)

2026-09-14 **학교 밖·노트북 단독(보드 미사용)** 세션의 실측 결과를 SSoT에 등재. 실모델(`venv_real`)로 `05_final_dataset/test` **424건 전수** 게이트 축 스윕을 3회차 재현하고, 7월 평가에도 PoC-(46)에도 없던 **`pass_NG` 오분류 대상 내역**을 처음 측정했다. 같은 세션에서 `tof_rejected` 스킵 경로를 **서버·화면 양축**으로 관통시켰다. **코드 0 수정** — `git diff --name-only` = `docs/` 2파일뿐이며 `server/`·`dashboard/`·`firmware/`·`ml/` 무접촉(`model_serving.py`는 **읽기 전용 대조**만). **노션 무접촉**(Set 3 소관), **프로젝트 지침 무접촉**(Set 2 소관), **26.9 Gap 표 무접촉**(Set 3 소관).

**Step 0 가정 대조 — 8건 중 O 7 / X 1(정지 임계 3건 미만 → 착수)**: HEAD `9389b0d` · 브랜치 `main` · 워킹트리 clean(A1 O). 33.6 실재, 하위 letter = **(a)(b)(c)**(A2 O). 33.6(b)의 「**미측정**」 + 「**직접 대응시키지 말 것**」 **한 줄에 동시 실재**(A3 O — 확인 대상이라 불일치 카운트 제외, **§9 「문구 부재 → 신규 등재 pivot」 미발동**). 6.4(g) 「**미관측**」 실재(A4 O). 26.10(d) 실재 + *"선행 조건 = 실모델 서버 투입"* 제목 문자 일치(A5 O). 🔴 **A6 = X**: 8.5에 **「자료형」이라는 어휘가 없다** — 위임이 인용하라고 준 「판정과 표시의 자료형 분리」는 **SSoT에 없는 문구**다. 실체는 8.5(k)의 *"표시 해상도가 판정을 오염시키지 않는다"* + 8.5(b)의 *"숫자만으로는 임박/정상이 구분되지 않으며 구분은 색·라벨이 담당한다"*이며, **불일치 방향 = ②(이미 존재하나 어휘 상이)** ⇒ **인용문을 실물 문구로 교정 후 진행**했다(없는 문구를 인용부호로 박으면 날조). `decisions-log.md` 마지막 엔트리 = 2026-09-12 PoC-(46)(A7 O). 카테고리 5에 `01_extracted` 서술 **부재**(`grep -rn "01_extracted" docs/` = **0건**, A8 O — 확인 대상이라 카운트 제외, **§9 「이미 있음 → 중복 등재 금지」 미발동**). 요일 `date -j -f "%Y-%m-%d" "2026-09-14" "+%A"` = **Monday = 월** 검산. 취소선 사전 측정 = **67줄**(`grep -c '~~'` = **줄 수**) / **154개**(`grep -o '~~' | wc -l` = **출현 수**, 짝수 = 마크다운 무파손).

**find-skills**: `npx skills search "markdown documentation"` → **10건**(`local-research` / `arxiv-doc-builder` / `documentation-writer` / `context-manager` / `markdown-pro` / `markdown-formatter` / `documentation-standards` / `content-documenter` / `markdown-validation` / `doc-generator`). ⚠️ 위임이 예고한 대로 `npx skills find`는 **`unknown command`** — `search` 사용. **미채택 사유 = ① 설치수·출처 미달** — **10건 전건이 `★ 0 • 0 installs` · `by undefined`**다. ⇒ 사유 ②(워크플로 불일치) 판정까지 갈 것도 없이 ①에서 걸린다. ADR 신규파일 생성류·changelog 자동생성류는 **과거 미채택 확정 재사용**(재평가 불요).

### Step 1 — 신설 절 번호 결정 근거 (위임 미지정, 전건 grep 실물)

| ID | 등재 위치 | 결정 근거(grep 실물) | 편집 유형 |
|---|---|---|---|
| E1 | **33.6(b)** 「미측정」 줄 | 문구 물리적 실존 확인 후 처리 | 취소선 1쌍 + 해소 표기 |
| E2 | **33.6(d) 신설** | 33.6 하위 letter 전수 = **(a)(b)(c)** ⇒ 다음 빈 letter = **(d)**. 33.6은 **letter 체계**이므로 번호형·무번호를 섞지 않았다 | 신설 |
| E3 | **33.6(e) 신설** | 동상, (d) 다음 letter | 신설 |
| E4 | **26.10(d) append** | (d)가 **그 미결의 등재 자리** — 단일 등재 원칙상 신설 불가 | append |
| E5 | **6.4(g) sub-bullet** | 8.5(g)·8.5(i)의 **`  - ✅ **해소/후속**` sub-bullet append 선례**를 따랐다(취소선 미사용 — 아래 사유) | append |
| E6 | **카테고리 5 「폴더 구조 실측(6단계)」 sub-bullet** | `01_extracted` 리터럴 `docs/` 전역 **0건** = 중복 없음 | append(단서) |
| E7 | **7.5(e) in-place** | refresh 발급일·만료일의 **현재값 정본 자리** | 취소선 1쌍 + 정정 |
| E8 | **카테고리 7 상단 「토큰」 문단 append** | 같은 「2026-11-02」가 있으나 **2026-09-03 시점 이력 문단**이라 취소선 대상 아님 ⇒ **포인터 1문장만** | append(포인터) |

**E3 절 위치 판단 근거 (위임이 「8.5 계열 / 33.6 계열 / 카테고리 6」 중 MCP 판단으로 남긴 건)**: **33.6(e)로 확정**했다. ① **8.5는 PR #49 카카오 토큰 범위 절**이고 **6.4는 PR #43 ToF wire 범위 절**이라 여기에 ML 서빙 round 건을 넣으면 **절 범위가 파손**된다(PoC-(46) E10의 *"8.4는 PR #47 범위 절 — PR #57 건을 넣으면 절 범위 파손"* 판단과 동형). ② 카테고리 6에 신규 `6.x` 절을 만들기엔 **단일 항목**이라 과하다. ③ 결정적으로 **발견 경로와 「실사례 0건」 근거가 전부 본 세션의 424건 전수 스윕**이고, **게이트 축이 33.6의 주제**다 ⇒ 단일 등재 원칙상 33.6 소관.

**E5가 취소선이 아닌 이유 (위임이 「MCP가 선례에 맞출 것」으로 남긴 건)**: 6.4(g)는 **2026-09-11 실기기 런타임의 관측 기록**이고, 본 세션 관측은 **노트북 curl + 실모델**이다. ⇒ *"런타임 2건 모두 low_confidence 선차단이라 도달 못함"*이라는 **이력 서술 자체는 지금도 참**이므로 취소선 대상이 아니다. 8.5(g)·8.5(i)가 쓴 **sub-bullet append 선례**를 따랐다.

### 등재 내용 요약

- **E2 (33.6(d) 신설 — 게이트 축 전수 + `pass_NG` 내역)**: 대조군 **3회차 재현**이 (b) 표와 **전건 일치**(doorbell 62/44/9/9 85.5% · knock 108/92/5/11 89.8% · fire_alarm 254/231/13/10 96.1%, 합계 **n 424 / ok 367 / NG 27 / blocked 30**) ⇒ **값 갱신이 아니라 재현**임을 명기. 🆕 **`pass_NG` 27건 내역** = doorbell → knock **3** · fire_alarm **6**(NG 중 `fire_alarm` 최대 신뢰도 **1.00**) / knock → fire_alarm **4** · doorbell **1**(최대 **0.96**) / fire_alarm → doorbell **9** · knock **4**(**유출 0**). 🔴 **위험 방향 10건**(타클래스 → `fire_alarm`)은 **G12로 ToF를 우회**해 presence 무관 발송 + 화재 수칙 렌더이며 ★ **분포 「안」 입력에서 발생**((a) OOD와 원인이 다름). 🟢 **안전 방향 13건**은 ToF 게이트 경유 ⇒ 33.2 「안전 방향 편향」이 **게이트 축에서도 유지**. ⚠️ **「`fire_alarm`이 흡인 클래스」는 논증**이며 support 254 최다와의 **인과는 미실증**. ⚠️ **계수 단위 = 클립 수(파일 수)**, **개별 파일명 미기록**. **측정 조건** = HTTP 미경유 `tf.saved_model.load` 직접 + 프로즌 `decode_pcm16`, 실모델 확증 3축(**RSS 461,280KB** / TF 매핑 **54** / 2회 `all_scores` 완전 일치), `wave`로 16kHz·mono·16bit 파일마다 assert + `decoded shape (1, 48000)` 확인((c) `[None, :]` 함정 재발 방지).
- **E1 (33.6(b) 해소 표기)**: 「미측정 … 직접 대응시키지 말 것」 **취소선 + `→ ✅ 해소 (2026-09-14 PoC-(47), 상세 = 아래 (d))`**. **기존 서술 삭제 0줄** — 취소선은 덮어쓰기가 아니라 표기다.
- **E3 (33.6(e) 신설 — 🔴 신규 미결)**: `model_serving.py`의 `confidence = round(float(row[idx]), 2)`가 `routes.py`의 `scores_to_prediction()` → `_apply_prediction_policy()` **호출 순서상 게이트 앞**에 있다(실물 = `routes.py`가 반환 `confidence`를 그대로 넘기고 strict `<` 비교는 `utils.py`의 후자 **안에서** 일어남 — **라인 번호 미사용**). ⇒ `CONFIDENCE_THRESHOLD=0.7` strict `<`가 **원값이 아니라 2자리 반올림된 값**을 받아 원값 **0.695~0.69999**가 **0.7로 올라가 통과**한다. ★ **8.5(k) 원칙의 역방향 사례**로 규정하되 **인용은 실물 문구**(*"표시 해상도가 판정을 오염시키지 않는다"*)로 하고 **「자료형 분리」 어휘가 8.5에 없음을 경계 표기**했다(A6 X의 처리). ✅ **실사례 0건 = 심각도 낮음**(424 전수에서 `[0.695, 0.70)` **0건**). ⚠️ (a)·(d)의 소수 **둘째** 자리 값(0.62·0.61·0.65·0.87·0.99·0.96·1.00)은 **round 이후 값**이라 **무영향**. ⚠️ **`model_serving.py`는 프로즌 파일** ⇒ **수정 여부·방식 = 사용자 판단 대기**. **판정 방법** = `[0.695, 0.70)` 입력을 실제로 만들어 `primary_sent` 전이 확인(현재 전수 424건에 **재현 입력 없음**).
- **E4 (26.10(d) 부분 해소)**: 판정 방법이 지정한 *"화면과 서버 로그 양쪽"*이 **양축 충족**. 클립 = `05_final_dataset/test/doorbell/125967_0000000.wav`((d) 사전 스윕 `doorbell` **1.00** 선별), `POST /api/v1/detect`에 `tof_presence=false`/`near=0`/`center=1200`/`ndet=0` 주입 → 응답 `predicted_class=doorbell` · `confidence=1.0` · `skip_reason="tof_rejected"` · `primary_sent=false` · `primary_sent_at=null` · `tof_check applied=true passed=false` · `reason="presence=false near=0/64 center=1200mm ndet=0/16"`. 화면(`/notifications`) = 「발송 제외」+「사람 없음」 뱃지, *"사람 감지 실패 때문에 알림을 보내지 않았어요."*, 거리 센서 문자열이 **서버 `reason`과 문자 일치**, `zone_count=` **미출현**(6.4(f) 해소 유지). 🔴 **CLOSE 아님 — 경계 3건 명기**: ① **실모델 + curl 경로**이며 **보드 관통 미수행** ② **ToF 4필드는 curl 주입 하드코딩**이라 6.4(b) fused 판정을 거치지 않았고 ⇒ **26.10(e) latch 쟁점 미해소** ③ 6.4(e)의 동일 경로 기존 관측은 **mock ML**이었고 **본 건이 실모델 첫 관측**.
- **E5 (6.4(g) 후속)**: 「미관측」 줄에 sub-bullet append. ⚠️ **`knock`은 여전히 미관측** — 관측 클래스는 `doorbell` **하나뿐**임을 경계 표기. ⚠️ 본 (g)의 **실기기 이력 서술은 무변경**이며 **실기기 관통은 여전히 미수행**.
- **E6 (카테고리 5 단서)**: 위 **6단계 외에** `01_extracted` · `manifests` **2개 폴더 실재**(2026-09-14 실측 `ls`). 🔴 **역할·내용 미확인** — 입력인지 중간 산출인지 **확정 금지**, **존재 사실까지만**. **기존 6단계 서술 무변경**(취소선 아님). ★ 위임은 `01_extracted` 1개만 지정했으나 **같은 `ls` 산출에서 `manifests`도 6단계 목록 밖**임이 함께 잡혀 병기했다(동일 성격 사실을 한쪽만 적으면 다음 세션이 또 판다).
- **E7·E8 (카카오 refresh 만료 현재값 정정)**: 위임 §5 Step 8의 선행 grep(`11-02|11월 2`) 결과 `docs/decisions.md` **2곳** + `docs/decisions-log.md` **1곳**. **현재값 정본 = 7.5(e)** ⇒ 취소선 + 실측 정정: `kakao_tokens` SINGLETON `id=1` — `access_expires_at` **2026-09-12 10:40** / `refresh_expires_at` **2026-11-10 01:41**(naive UTC) / `updated_at` **2026-09-12 04:40**(조회 시각 2026-09-14 05:01). 「≈ 2026-11-02」는 **발급일 + 60일 계산치**였음을 명기(발급일 2026-09-03 · 5,183,999초는 **무변경**). **카테고리 7 상단**은 **2026-09-03 시점 이력 문단**으로 판정해 **포인터 1문장만** append(취소선 미사용). `decisions-log.md`의 1건은 **이력 로그라 무변경**. ⚠️ **「refresh DB 생존」 ≠ 「자동 갱신 실제 작동」** — 본 세션 **카톡 실발송 0건**이라 갱신 경로 미주행, *"잔여 1개월 미만일 때만 재발급"*의 미실측 꼬리표와 판정 방법 **그대로 유효**. ⚠️ **`updated_at` 2026-09-12가 33.6(a) 실발송 세션과 같은 날이나 인과는 미실증**(로그 미확인) — **확정 금지**. **토큰 값 미기록**(길이만 확인, 값 미출력).

### 🔴 사용자 판단 대기 항목 — 등재하되 방향 미확정

| 항목 | 등재 위치 | 방향 확정 여부 |
|---|---|---|
| `pass_NG` 27건 대응(임계 재검토 / 4번째 클래스 / 재학습 / 각본 조정) | 33.6(d) | **미확정 — 33.6(a)와 동일 건, "임계·정책 확정 금지" 명기** |
| `model_serving.py` round 수정 여부·방식 | 33.6(e) | **미확정 — 프로즌 파일 · 실사례 0건 · 판정 방법만 등재** |
| `01_extracted` · `manifests` 역할 | 카테고리 5 | **미확정 — 존재 사실까지만** |
| 「`fire_alarm` 흡인 클래스」 인과 | 33.6(d) | **미확정 — 논증이며 support 254와의 인과 미실증으로 표기** |
| 26.10(d) CLOSE 여부 | 26.10(d) | **미확정 — 실기기 관통 미수행이라 부분 해소까지** |
| 카카오 자동 갱신 실작동 | 7.5(e) | **미확정 — 실발송 0건, 2026-10월 초 판정 방법 유효** |

**SSoT 정합 검증 (문서 전용이라 코드 3단계 N/A — §7 예외)**: 신설 letter **33.6(d)(e)**는 하위 letter 전수 grep(= (a)(b)(c)) 후 결정, **충돌 0건 · 번호 체계 혼재 0건**(사후 재확인 = (a)→(b)→(c)→(d)→(e) 연속). 편집 앵커 **8건 전건 `str.count` == 1 assert 통과**(패턴 매칭, **라인 번호 0건 사용** — 본 엔트리 본문도 동일 준수). 취소선 총수 **착수 전 67줄 / 154개 → 종료 69줄 / 158개**(계수 단위 = `grep -c '~~'` **줄 수** / `grep -o '~~' | wc -l` **출현 수**). 증가분 **+2줄 / +4개 = 신규 취소선 2쌍**(E1 1쌍 + E7 1쌍)으로 **설계와 정확히 일치**, **158 = 짝수 = 마크다운 무파손**. **삭제 0줄**: `git diff --stat` = **56 insertions / 3 deletions**이고 3 deletions은 전부 **원문을 `~~`로 감싸거나 문장을 덧붙인 in-place 수정**이다 — 토큰 보존 검사 결과 **정규화 기준(`~~` 제거 후) 미보존 토큰 0종**, **원시 기준 미보존 1종**(`추정이었음).`)은 **`~~` 인접에 의한 토큰 분할**이며 분할 후 실물 `추정이었음).~~`을 `grep -cF` = **1건**으로 개별 확인했다. 실측 수치는 **위임 표기 그대로**(가공·반올림·재계산 0). 실모델 확증 3축 **461,280KB**는 PoC-(46)의 **475,920KB**와 다른 값이며 **세션별 실측치**이므로 **덮어쓰지 않고 (d)에 별도 기록**했다.

**비범위**: **코드 0 수정** — `server/`·`dashboard/`·`firmware/`·`ml/` 이하 전부 무접촉(`git diff --name-only` = `docs/` 2파일뿐). `model_serving.py`·`routes.py`·`utils.py`는 **읽기 전용 대조**이며 **1줄도 바꾸지 않았다**. **노션 무접촉**(DB3 row·Gap 카드 = **Set 3 소관**), **26.9 Gap 표 갱신 = Set 3 소관**, **프로젝트 지침 파일 무접촉**(지침 9-7 카카오 refresh 서술 포함 = **Set 2 소관**). 위 「사용자 판단 대기」 6건 **전부 방향 미확정으로 등재만** — 임계값·정책·수치 신설 **0건**. `docs/git-convention.md` 무접촉. **보드·ESP32 미구동**(학교 밖 세션), **EC2 미기동**, **실 초인종 음원 미측정**, **`knock` `tof_rejected` 미관측**, **`[0.695, 0.70)` 재현 입력 미생성**, **`01_extracted`·`manifests` 내용 미조사** — 전부 미착수. 브랜치 없이 **main 직 push**(문서 단독, 카테고리 20 「문서/코드 변경 push 분리」).

**학습 적용**: **학습 13**(grep 후 인용 — §4 인용 대상 전건 실물 대조. **위임이 준 인용문 「판정과 표시의 자료형 분리」가 SSoT에 부재함을 catch**해 8.5(k) 실물 문구로 교체. **라인 번호를 편집 앵커·본문 모두 0건 사용**) / **학습 14**(선언 ≠ 발화 — 33.6(e)를 "코드에 결함이 있다"로 끝내지 않고 **424 전수에서 실사례 0건**까지 측정해 심각도를 실측으로 고정) / **학습 16**(기존 컨벤션 우선 — 33.6 letter 체계·8.5(g) sub-bullet 선례·26.3 취소선 선례를 따랐고 **위임의 절 번호 미지정을 grep으로 자체 결정**) / **학습 17**(인계 패키지 catch 그물 — 위임 본문의 인용·수치를 **실물 대조 후** 진행, A6에서 1건 catch) / **학습 18**(지정 수정이 코드상 no-op이면 코드로 재규명 — 33.6(e)의 round 위치를 **위임 서술 그대로 옮기지 않고 `routes.py` 호출 순서와 `utils.py` 비교 위치를 직접 대조**해 확증) / **학습 21**(유령 미결 — E6에서 `01_extracted` 리터럴 `docs/` 전역 **0건** 확인 후 신규 등재, 중복 0) / **27.8(f-2) 계열**(측정 시점값 — 취소선 총수·grep 건수·`npx skills search` 반환 10건을 전부 **그 호출의 시점값**으로 취급, 다른 세션 수치와 비교하지 않음) / **「현재값 vs 이력」**(카카오 refresh 만료를 **7.5(e) = 현재값 정본**과 **카테고리 7 상단 = 2026-09-03 시점 이력**으로 갈라 처리 방식을 달리했다 — 전자 취소선 정정 / 후자 포인터 append / `decisions-log.md` 무변경) / **「발견일 ≠ 반영일」**(33.6(d)(e)·E6·E7 전건 **발견·반영 모두 2026-09-14**이나 양쪽 다 표기) / **「실측 / 논증 / 문서인용 3분」**(33.6(d) 수치 = **실측** / 「`fire_alarm` 흡인 클래스」 = **논증·인과 미실증** / 33.6(e) 심각도 = **실측(전수 0건)** / 카카오 "잔여 1개월 미만" = **문서 인용·미실측 유지**) / **「압축 손실」**(`pass_NG` 27건을 합계로 뭉개지 않고 **6개 방향 × 계수 + `fire_alarm` 최대 신뢰도**까지 원소별 전건 표기, **계수 단위 = 클립 수**를 명시).

**관련 카테고리**: **33.6(d) (게이트 축 전수 재현 + `pass_NG` 오분류 내역 신설 — (b) 「미측정」 해소)** / **33.6(e) (`confidence` round 위치 신규 미결 신설)** / 33.6(b) (「미측정」 취소선 + 해소 표기) / **26.10(d) (판정 방법 서버·화면 양축 충족 — 부분 해소, CLOSE 아님)** / 6.4(g) (「미관측」 후속 note — `knock` 미관측 경계) / 6.4(b)(e)(f) (fused 매핑 · mock ML 기존 관측 · `zone_count=` 해소 유지 확인) / **7.5(e) (카카오 refresh 만료 현재값 2026-11-10 01:41 정정)** / 카테고리 7 상단 「토큰」 (2026-09-03 시점 이력 포인터) / **카테고리 5 (`01_extracted`·`manifests` 존재 단서)** / 8.5(k)(b) (「표시가 판정을 오염시키지 않는다」 — 33.6(e)의 원칙 출처, **「자료형」 어휘 부재 경계**) / 33.2 (안전 방향 편향 · confusion `doorbell → fire_alarm`) / 카테고리 3 (G12 · 클래스별 ToF 정책 · 신뢰도 임계값) / 26.10(e) (latch 쟁점 — 본 관측으로 **미해소**) / 20 (문서/코드 push 분리) / 27.8(f-2) (측정 시점값)
**관련 commit**: **코드 PR 0건**(본 Set은 코드 무접촉). 문서 반영 = 본 Set 1 커밋(docs-only, **PR 없음, main 직 push**). 선행 = `9389b0d`(PoC-(46) Set 1 등재 = 착수 시점 HEAD).

## 2026-09-15 (화) — PoC-(48) Set 1 — 🔴 데이터셋 내용 중복 → train/test 누수 실측·신설(33.7) + 코드 PR 3건 자산 등재(33.8 신설) + 33.6(d) 재현 수단 확보·「개별 파일명 미기록」 해소 + 33.6(e) `[0.695, 0.7)` 경계 양끝 정정 · `all_scores` 파급 + 카테고리 5 `01_extracted`·`manifests` 부분 해소 (카테고리 5/6.3/8.5 계열/26.10/27.8/33.2/33.6/33.7/33.8)

2026-09-15 **학교 밖·노트북 단독(보드 미사용)** 세션의 실측 결과를 SSoT에 등재. 같은 세션이 PR **#58 · #59 · #60** 3건을 머지했고, PR #59 하네스의 `stem` 열에서 **데이터셋 내용 중복 → train/test 누수**를 발견해 **33.7을 신설**했다. 본 Set은 **문서 전용이며 코드 0줄** — `git diff --name-only` = `docs/` 2파일뿐이고 `server/`·`dashboard/`·`firmware/`·`ml/` 무접촉이다. **데이터셋은 읽기만** 했다(이동·삭제·수정 **0건**). **노션 무접촉**(Set 3 소관), **프로젝트 지침 무접촉**(Set 2 소관), **26.9 Gap 표 무접촉**(Set 3 소관). 🔴 **누수·round·`pass_NG` 대응 방향은 전부 사용자 판단 대기로 등재만** 했다 — 수치·정책·재학습 방향 신설 **0건**.

**Step 0 가정 대조 — 10건 전건 O (정지 임계 A1·A2·A3 전부 O → 착수, pivot 0건)**: HEAD `00f43f8` · 브랜치 `main` · 워킹트리 clean(A1 O). `decisions.md` 최종 카테고리 **33** / 최종 절 **33.6** / 최종 하위 **(e)**(A2 O). `decisions-log.md` 마지막 엔트리 = **2026-09-14 PoC-(47)**(A3 O). 27.8 하위 순서 = **(a)(b)(c)(d)(e)(g)(f)(h)(i)** — **(g)가 (f)보다 파일 앞쪽**(A4 O). A5~A10은 **정정·취소선 대상의 물리적 존재 확인**이며 전건 `grep -cF` **== 1**: 「0.695~0.69999」(A5) · 「개별 파일명」(A6) · 「역할·내용은 미확인」(A8) · 「`CLASSES` 상속」(A9) · 「`ddingdong_dataset` 로 이동 확정」(A10). 「3개뿐」(A7)만 **2건**이라 앵커를 `_apply_prediction_policy()` 문장 전문으로 넓혀 **== 1**로 만든 뒤 편집했다(다른 1건 = `models.py` `__tablename__` 3개 — **편집 대상 아님**). ⚠️ **A5는 1차 grep에서 0건**이 나왔는데, 실물이 `원값 **0.695~0.69999** 구간`으로 **볼드 마커가 토큰을 분할**하고 있었기 때문이다 — 위임 문구 그대로 찾지 말고 **마커를 걷어낸 부분 문자열로 재조회**해 실존을 확인했다(학습 21 정합 — **유령 판정 직전에 한 번 더 실물을 봤다**). 요일 `date -j -f "%Y-%m-%d" "2026-09-15" "+%A"` = **Tuesday = 화** 검산. 취소선 사전 측정 = **69줄**(`grep -c '~~'` = 줄 수) / **158개**(`grep -o '~~' | wc -l` = 출현 수, 짝수 = 마크다운 무파손).

**find-skills**: `npx skills search` 4질의 — `markdown documentation` **10건** / `changelog` **98건** / `decision records` **28건** / `technical writing` **15건**. **채택 0건.** 최다 별점 `changelog-generator`(★ **14,487** · **0 installs** · `by undefined`)조차 **① 출처 미달(비공식) + ② 워크플로 불일치**다 — 본 repo는 **changelog 자동 생성이 아니라 단일 `decisions.md` 누적(취소선 + append)** 이고 log는 **사람이 판단·반증·경계를 서술**한다. `architecture-decision-records`·`git-adr`류는 **ADR 신규 파일 생성 모델**이라 과거 미채택 확정분 재사용(재평가 불요). **0건 질의 0개** ⇒ 도구 생존 별도 증명 불요.

### 신설 절 번호 결정 근거 (위임 미지정 — MCP 판정, 근거유형 = 실측 grep)

- **33.7(누수) · 33.8(PR 3건)** 으로 확정했다. 근거 = `grep -nE "^### "` 전수에서 카테고리 33의 절이 **33.1~33.6 연속 번호**이고 **33.7 리터럴이 `grep -c` 0건**이므로 다음 빈 번호가 **33.7**이다.
- ⚠️ **33 계열 안에 무번호 `### USP 2층 재정립 (2026-07-09 PoC-(26))` 선례가 존재**하나 **적용하지 않았다** — 번호 체계가 있는 카테고리 안에서 체계를 섞지 않는다(위임 §5 Step 3 지정과 정합). **기존 무번호 절은 무변경**이다.
- **누수 건을 카테고리 5가 아니라 33 계열에 둔 이유**(사용자 결정 2026-09-15): 무게중심이 *"데이터셋에 중복이 있다"*가 아니라 ***"등재된 성적 수치의 해석이 바뀐다"***에 있다. 카테고리 5에 넣으면 **33.2를 읽는 사람이 이 사실을 못 보고 지나간다.**
- **33.8을 따로 세운 이유**: 33.6·33.7은 **측정 결과**의 절이고 PR 3건은 그 **수단·자산**이라 성격이 다르다(6.3(o) 「방법론 자산」 · 9.1(e) `tof_pinscan` 선례의 성격 구분 재사용). 세 PR을 각 결과 절에 흩으면 **PR 성격 판정(방법론 자산 2 / 정합성 정정 1)이 한 자리에서 읽히지 않는다.**

### 편집 건별 (전건 `str.count` == 1 assert 통과, 라인 번호 0건 사용)

| ID | 대상 절 | 앵커(문구) | 편집 종류 |
|---|---|---|---|
| E1 | **33.7 신설** | 33.6 「**관련**」 줄 말미 + 절 구분자 | 신설 |
| E16 | **33.8 신설** | 동상 | 신설 |
| E2 | 33.6(b) | 「`source_key` 기반 원본그룹 분리 = 누수 방지 기존 설계」 줄 | 포인터 append(**취소선 아님**) |
| E3 | 33.2 | 「test 성적 (n=424, 미사용 데이터)」 줄 | 청정값 **병기** append(기존 수치 무변경) |
| E4 | 33.6(d) | 「로그 원본 = repo 밖 …」 인용 블록 | 재현 수단 in-place 추가 |
| E5 | 33.6(d) | 「**개별 파일명은 미기록**이라 …」 | **취소선 1쌍** + 해소 |
| E6 | 33.6(d) | 「합계 **n 424 / ok 367 / NG 27 / blocked 30**」 줄 | 4회차 재현 append |
| E7 | 33.6(e) | 「원값 **0.695~0.69999** 구간이 …」 | **취소선 1쌍** + 정정 표 |
| E8 | 33.6(e) | 「실사례 0건 — 심각도 낮음」 줄 | `all_scores` 파급 append(신규 서술) |
| E9 | 26.10(a) | 「`_apply_prediction_policy()` 판정 분기 **전수 = … 3개뿐**」 문장 전문 | **계수 단위 명시만**(숫자 무변경) |
| E10 | 카테고리 5 | 「`01_extracted` · `manifests` 2개 폴더가 실물로 존재」 단서 줄 | **취소선 1쌍** + 부분 해소 sub-bullet 3 |
| E11 | 카테고리 5 | 「05 실측 배분(원본단위 group split …)」 줄 | append(테스트 `stem` 전건 일치 + 범위 경계) |
| E12 | 6.3(o) | 「호스트 스텁 패턴(`firmware/tools/host_stubs/` …)」 줄 | `jsonpeek_test` 등재 append |
| E13 | 33.2 | 「학부생 로컬 실 YAMNet export + reload 추론 검증 통과.」 | `labels.json` 위상 append |
| E14 | 학습 21 5분류 | 「재발 방지(학습 19의 확장)」 줄 | 하위 단서 append |
| E15 | **27.8(j) 신설** | (i)의 「누적 카운트((d))에 합산하지 않았다」 줄 | 신설 |

### 등재 내용 요약

- **E1 (33.7 신설 — 🔴 신규 미결, 근거유형 = 실측 md5 전수 + 매니페스트 대조, 계수 단위 = 클립 수)**: **(a)** `02_preprocessed` 전체 **2792** / 고유 내용 **2305** / 중복 그룹 **15** / 중복 파일 **502** / **순수 잉여 487(17.4%)**, 상위 **108×3 · 56×2 · 30 ⇒ 454파일이 단 6개 내용**. **(b)** `split_manifest.csv` **2792행**·**경로 미존재 0**, 중복 15그룹 = **교차 10 + 갇힘 5**(갇힘은 전부 n=2·전부 `train` 내부·잉여 5 ⇒ 「유효 데이터량 축소」 축 **실질 무의미**), 🔴 **train/val과 내용이 겹치는 test 행 = 79 / 424**이고 **79건 전부 `fire_alarm`**(`doorbell`·`knock` **0건**). **(c)** 재추론 **0회**(기존 스윕 로그 + 매니페스트만) — 전체 424 대비 청정 345 = accuracy **0.8868 → 0.8609**(−0.026) / macro_f1 **0.8478 → 0.8367**(−0.011) / `fire_alarm` f1 **0.927 → 0.893**(−0.034), `doorbell`·`knock`은 **소수점까지 동일**(누수 0건이므로 정합 = **계산 검산**), support **254 → 175**. 누수 79건 **accuracy 1.0000 전건 정답**. **(d)** [실측] 바이트 동일 파일이 train/test에 걸쳐 존재 / [실측] 영향은 **`fire_alarm` 국한 · macro_f1 0.011** ⇒ **33.2의 macro_f1 0.848은 실질적으로 방어된다** / 🔴 **[경계] `source_key` 원본그룹 분리는 고장난 것이 아니라 「범위 밖」**이었다(파일명 기준 그룹화라 내용 동일 파일은 애초에 방어 대상 아님) — **「설계 결함」으로 쓰지 않았고 33.6(b) 서술도 취소선 대상이 아니다** / [논증] 전건 정답의 기전 = **암기 추정**, 입력 실측 = correct 79/79 이며 **"왜"는 미실증**. **(e)** 🔴 **대응 방향 = 사용자 판단 대기**, 선택지 **열거까지만**(① 중복 제거 후 재split·재학습 / ② 현 성적 + 누수 고지 병기 / ③ 청정값 정본 교체). **(f)** 한계 = `01_clips`·`03_augmented`·`05_final_dataset` 중복 **미확인**(`02_preprocessed`만 봄) · 중복 발생 **원인 미규명** · 직접 녹음분 합류 시 **영향 방향 예측 불가**.
- **E16 (33.8 신설 — PR 3건)**: **#58 `01f5796` 방법론 자산**(round 위치 ↔ 게이트 순서 회귀 고정, 서버 테스트 **102 → 104** = 테스트 메서드 수) / **#59 `4d79aa7` 방법론 자산**(게이트 축 전수 스윕 하네스 **581줄** 신설) / **#60 `00f43f8` 정합성 정정**(데이터 루트 fallback 제거 + 라벨 순서 일치 확인 신설). 종료 코드 값 도메인 `{0/1/2/3}`에 **#60이 `4`(라벨 순서 불일치) 추가**, `--self-test` **9 → 13 PASS**(NC 체크 수). `4`를 `1`과 **가른 이유** = 라벨이 어긋나면 집계가 통째로 오라벨링인데 `1`이면 *"모델이 달라졌나"*로 오독된다. **#60 fail-fast 5분기 학부생 실측**(둘 다 없음/빈 문자열/공백 → 전부 `ValueError`, `~` 확장 유지, 인자 우선 유지). 🔴 **#60이 해소한 것** = `DEFAULT_DATA_ROOT`가 **카테고리 5가 「TCC(EPERM) 차단 → 학부생 홈으로 이동 확정」이라 등재한 옛 경로**를 **약 3개월간** 가리켰고 **fallback 때문에 아무도 걸리지 않았다** ⇒ **새 정책 신설이 아니라 등재된 정책에 코드를 맞춘 정합성 정정**. 🟡 **PR #60이 남긴 문서 stale 등재만**(`ml/pipeline/README.md` 옛 절대경로 잔존 / `ml/training/README.md`·`train.py`·`evaluate.py` docstring이 env 필수 미기재) — **수정 0건, 별건**.
- **E4·E5·E6 (33.6(d))**: 재현 수단 = **`server/tools/gate_axis_sweep.py`(PR #59)** ⇒ 본 축은 이제 **repo 안 하네스로 재현 가능**. 「**개별 파일명은 미기록**」 한계 **취소선 + ✅ 해소**(하네스 `stem` 열) — ★ **해소 직후 그 `stem` 열에서 33.7이 나왔다**. **4회차 재현 전건 일치**(**424 / 367 / 27 / 30**, accuracy **0.8867924528**) = **값 갱신이 아니라 재현**. 실모델 확증 3축 = RSS **471,120KB** / TF 매핑 **54개** / 동일 입력 2회 완전 일치. ⚠️ RSS는 **세션별 실측치**라 PoC-(46) **475,920KB** · PoC-(47) **461,280KB**와 **자릿수만 정합**하며 **덮어쓰지 않았다**(27.8(f-2) 「측정 시점값」 정합).
- **E7 (33.6(e) 경계 정정 — 🔴 양끝 모두 부정확했다)**: 근거유형 = **실측 f32 전수 스윕 503,317개**(구간 [0.68, 0.71], 계수 단위 = f32 값 개수). **하한** — f32 `0.695`는 실제 **0.6949999928474426**이라 `round(·,2)`가 **0.69로 내려가 갈리지 않는다**(f64에서도 `round(0.695,2) == 0.69`) ⇒ 실제 하한은 **한 ULP 위 0.6950000524520874**. **상한** — `0.69999`가 아니라 **f32 `0.7` 자체**이며 f64로 **0.699999988079071**이라 🔴 ***"모델이 0.7을 뱉어도 원값 비교였다면 차단됐다"*** 가 본 절이 놓친 **가장 강한 사례**다. **4조합 도달성** = (차단,차단)✓ (차단,발송)✓ (발송,발송)✓ **(발송,차단) 도달 불가**(`round` 단조성). ⚠️ **입력 도메인이 f32**임을 함께 적었다(33.2 서빙 출력 `(1,3)` f32 → `float()` 승격). ✅ **「실사례 0건」은 유지** — 2026-09-15 전수 스윕에서 `[raw vs rounded]` 갈림 **0건** 재확인.
- **E8 (33.6(e) `all_scores` 파급 — 신규 서술)**: `scores_to_prediction`이 `confidence`뿐 아니라 **전 클래스 `all_scores`를 2자리 반올림**한다. 게이트는 top만 보므로 **판정 영향은 위 축에 갇히지만 대시보드 표시·집계는 `all_scores`를 쓴다** ⇒ **8.5(k) 축과 맞닿는다**. ⚠️ 본 (e)에 `all_scores` **0건**이었다(대조군 = 같은 파일에서 `all_scores` **3건** 생존 — 전부 33.6(c)(d)의 *"2회 완전 일치"* 확증 축). **프로즌 파일이라 수정 여부·방식 = 사용자 판단 대기.**
- **E9 (26.10(a) — 🔴 정정이 아니라 계수 단위 명시)**: 실측은 `return` 문 기준 **4개**(fallthrough 포함)이나 **숫자를 바꾸지 않았다.** 사유 = 본 항의 논지가 *"등록된 초인종인가를 보는 분기가 없다"*는 **부재 증명**이라 **계수 단위가 다르면 둘 다 참**이고, 4로 바꾸면 논지가 흐려진다. ⇒ **「계수 단위 = 조건 분기 수」 명시만** 추가했다.
- **E10·E11 (카테고리 5 — 「역할·내용 미확인」 부분 해소)**: `01_extracted` = 클래스 **3폴더**(doorbell **107** / knock **270** / fire_alarm **171**, 계 **548** 클립), 파일명이 **순수 숫자 ID**로 `01_clips`의 AudioSet 네이밍과 **계열이 다르다**. 두 매니페스트 `filepath`에 `01_extracted` **0건**(대조군 = `02_preprocessed` **2792행** · `05_final_dataset` **12447행** 생존) ⇒ **학습 경로 미참조**이나 🔴 **파이프라인상 위치·소스 귀속은 여전히 미확정**(논증 단계, 코드 미확인). **`manifests/final_manifest.csv` 신규 등재** = **12,447행** 전건 `05_final_dataset` 지시, 컬럼 `filepath,class,split,origin,source_stem`, **12447 = 원본 2792 + 증강 9655**(snr **3862** / ts **3862** / vol **1931**) **산술 일치**. 🔴 **`split_manifest.csv`(2792행 · `02_preprocessed` 지시 · 컬럼 `filepath,class,split,stem,source_key`)와 다른 문서**이며 **split SSoT = `split_manifest.csv` 무변경**이다. 추가로 `05_final_dataset/test` **424 파일 집합이 test split과 `stem` 전건 일치**(diff **0**, 표본 md5 일치) — 33.6(b)의 「개수 일치」보다 **강한 확인**이고 **11,586 + 437 + 424 = 12,447**로 `final_manifest.csv` 행 수와 맞는다. 「누수 방지」 범위 경계도 같은 자리에 병기했다(취소선 아님).
- **E13 (33.2 `labels.json` 위상)**: 파일 실존(`{"classes": [...], "index": {...}}`, 순서 doorbell/knock/fire_alarm, **git 미추적**)이나 decisions.md **0건**이었다(대조군 = `export` **3건** 생존). 🔴 **정본 문구는 「라벨 순서 = `CLASSES` 상속」이며 무변경** — `labels.json`은 **상속의 배포 스냅샷이지 출처가 아니다.** **PR #60이 이 파일을 검증 대상으로 승격**(실행 시점 `PREDICTED_CLASSES` 대조 → 불일치 시 **종료 코드 4**). ⚠️ git 미추적이라 clone 직후엔 `python -m ml.training.export` 선행 필요.
- **E12 (6.3(o) 호스트 테스트 3종)**: `noise_stats_test` · `tof_judge_test` · **`jsonpeek_test`**. 앞의 둘은 등재돼 있었으나 **`jsonpeek_test`는 decisions.md 0건**이었다(대조군 = 같은 grep에서 앞의 둘 생존). **존재 사실까지만** 등재하고 checks 수·커버리지는 **미측정**으로 남겼다.
- **E14 (학습 21 하위 단서)**: **부재 판정은 「감싸는 함수」 앞에서 멈출 수 있다.** 대화형 grep이 `DEFAULT_DATA_ROOT`·`resolve_data_root` **이름만** 훑고 「참조 0건」으로 판정했으나 `resolve_paths`가 한 겹, `ml/training/config.py`의 `resolve_final_dir`이 또 한 겹 감쌌고 **최종 호출자 3곳(`run_all.py`·`train.py`·`evaluate.py`) 전부 인자 `None` 도달 가능**이었다. ⚠️ 대조군 = 같은 grep이 테스트의 `resolve_paths(root)` **6건**을 살려냈으므로 **도구 사망이 아니라 판정이 한 겹 위에서 멈춘 것**이다.
- **E15 (27.8(j) 신설)**: ① 「판정과 표시의 자료형 분리」 — **33.6(e)에 이미 등재**돼 있어 **중복 서술하지 않고 패턴만** 남겼다. ★ **패턴 = 「출처 계층 착각」의 ③ → ① 역방향**(위임이 만든 요약 문구를 SSoT 원문인 것처럼 되돌려 인용). ② 「라벨 순서 = `labels.json`」 — 실물은 「`CLASSES` 상속」이며 MCP가 기각하고 NC 비교 대상을 **실제 의존 지점 `app.constants.PREDICTED_CLASSES`** 로 교체했다(그대로 갔다면 **판정에 쓰지도 않는 파일**을 단언 대상으로 삼을 뻔했다 — ①은 인용이 틀렸고 ②는 **검증 대상이 틀릴 뻔했다**). ③ **라인 번호 인용 재발** 2026-09-14 **3건** → 2026-09-15 **1건**, **(i)가 닫은 축이 3세션 연속 재발**. ⚠️ **(d)의 누적 숫자 무변경**(합산 여부가 (i)에 사용자 판단 대기).

### 🔴 사용자 판단 대기 항목 — 등재하되 방향 미확정

| 항목 | 등재 위치 | 방향 확정 여부 |
|---|---|---|
| 데이터셋 중복·누수 대응(재split·재학습 / 누수 고지 병기 / 청정값 정본 교체) | 33.7(e) | **미확정 — 선택지 열거까지만, 수치·정책 신설 0건** |
| 누수 79건 전건 정답의 기전(암기) | 33.7(d) | **미확정 — 논증이며 "왜"는 미실증** |
| `01_extracted` 파이프라인상 위치·소스 귀속 | 카테고리 5 | **미확정 — 학습 경로 미참조까지만 실측** |
| 중복 발생 원인(수집 단계 / 전처리 단계) | 33.7(f) | **미확정 — 미규명** |
| `model_serving.py` round 수정 여부·방식(`confidence` + `all_scores`) | 33.6(e) | **미확정 — 프로즌 파일 · 실사례 0건 유지** |
| `pass_NG` 27건 대응 | 33.6(d) | **미확정 — 기존 등재 유지(무변경)** |
| 27.8 누적 숫자 합산 여부 | 27.8(i) | **미확정 — (d)·(j) 모두 무변경으로 두었다** |
| `jsonpeek_test` checks 수·커버리지 | 6.3(o) | **미측정 — 존재 사실까지만** |

**SSoT 정합 검증 (문서 전용이라 코드 3단계 N/A)**: 신설 절 **33.7 · 33.8**은 `^### ` 전수 grep(= 33.1~33.6 연속) + `33.7` 리터럴 **0건** 확인 후 부여했고 **번호 체계 혼재 0건**이다(33 계열의 무번호 `### USP 2층 재정립` 선례는 **적용하지 않았고 무변경**). 신설 letter **27.8(j)**도 하위 letter 전수((a)~(i), **(g)가 (f) 앞** 포함) 확인 후 다음 빈 letter로 결정했다. 편집 앵커 **16건 전건 `str.count` == 1 assert 통과**(패턴 매칭, **라인 번호 0건 사용** — 본 엔트리 본문도 동일 준수). 취소선 총수 **착수 전 69줄 / 158개 → 종료 72줄 / 164개**(계수 단위 = `grep -c '~~'` 줄 수 / `grep -o '~~' | wc -l` 출현 수). 증가분 **+3줄 / +6개 = 신규 취소선 3쌍**(E5 · E7 · E10)으로 **설계와 정확히 일치**하며 **164 = 짝수 = 마크다운 무파손**이다. **삭제 0줄 증명**: `git diff --numstat docs/decisions.md` = **119 insertions / 6 deletions**이고 6 deletions은 전부 **원문을 `~~`로 감싸거나 문장을 덧붙인 in-place 수정**(E4·E5·E7·E9·E10 + 33.6 「관련」 줄 포인터 추가)이다. **토큰 보존 검사 = 정규화 기준(`~~` 제거 후) 미보존 토큰 0종**, **원시 기준 미보존 2종**(`통과**한다.` · `없다.`)은 **둘 다 `~~` 인접에 의한 토큰 분할**이며 분할 후 실물 `통과**한다.~~` · `없다.~~`를 각각 `grep -cF` **1건**으로 개별 확인했다. 🔴 **위임 §4(E)의 「`01_clips` 2798 → `02_preprocessed` 2792, 6건 감소, 사유 미확인」은 등재하지 않았다** — 카테고리 5에 **「빈 클립 6개 실측: `01_clips/fire_alarm`의 AI Hub S_103 원본 6개가 length-0 wav → preprocess가 skip(fire_alarm 1648 → 1642)」이 이미 등재**돼 있어 **사유는 미확인이 아니라 실측 확정 상태**다(학습 17·21 정합 — 위임의 「미확인」을 그대로 옮겼다면 **이미 해소된 것을 미결로 되살리는 날조**가 된다). 수치 **2798 − 6 = 2792**는 기존 등재와 **산술 일치**하므로 중복 등재도 하지 않았다. 실측 수치는 **위임·외부 로그 표기 그대로**(가공·반올림·재계산 0) — 외부 로그 `~/ddingdong-측정결과/2026-09-15/leak_audit_2026-09-15.md`를 **직접 읽어 대조**했고 위임 §4(A)와 **불일치 0건**이었다.

**비범위**: **코드 0 수정** — `git diff --name-only` = `docs/` 2파일뿐이며 `server/`·`dashboard/`·`firmware/`·`ml/` 무접촉이다. **데이터셋 파일 이동·삭제·수정 0건**(`~/ML 학습 데이터/` 이하 **읽기만**). 🔴 **대응 방향 확정 0건** — 누수·round·`pass_NG`·`01_extracted` 귀속 전부 **등재만** 했고 **임계값·정책·수치·재학습 방향 신설 0건**이다. **코드·README 수정 비범위**(PR #60이 남긴 `ml/pipeline/README.md`·`ml/training/*` docstring stale은 **등재만**). **노션 무접촉**(DB3 row·Gap 카드 = **Set 3 소관**), **26.9 Gap 표 무변경**(Set 3 소관), **프로젝트 지침 파일 무접촉**(Set 2 소관), **27.8(d) 누적 숫자 무변경**(사용자 판단 대기), **33.6(b)(d) 기준값 무변경**, **33.2 `accuracy 0.887 / macro_f1 0.848` 무변경**(청정값 병기만). **PR 없음** — `docs/*.md` 단독이라 **main 직 push**(카테고리 20 「문서/코드 변경 push 분리」). **PR #55(`feat/firmware-noiseprobe-pulldown`) 무접촉**. **보드·ESP32 미구동**, **EC2 미기동**, **④런타임 미수행**, `01_clips`·`03_augmented`·`05_final_dataset` **중복 미조사**, `jsonpeek_test` **미실행**.

**학습 적용**: **학습 13**(출처 전항목 catch — §4 인용 대상 **전건 실물 grep 후 인용**. A5가 1차 grep **0건**으로 나왔을 때 **유령 판정 대신 볼드 마커를 걷어내고 재조회**해 실존을 확인했고, A7 「3개뿐」 **2건**은 앵커를 문장 전문으로 넓혀 `== 1`로 만들었다. **라인 번호를 편집 앵커·본문 모두 0건 사용**) / **학습 16**(기존 컨벤션 우선 — `decisions-log.md` 마지막 엔트리의 헤더·섹션 골격을 **실물에서 그대로 따왔고**, 33 계열 letter/번호 체계·취소선 선례·「관련/비범위/관련 commit」 순서를 발명 없이 재사용) / **학습 17**(인계·위임 본문도 catch 대상 — 🔴 **위임 §4(E)의 「6건 감소 사유 미확인」이 실물 SSoT에서 이미 해소된 사실임을 catch**해 등재하지 않았다. 위임이 든 인용 문구·수치는 전건 실물·외부 로그 대조 후 사용) / **학습 21**(미결 자체가 유령일 수 있다 — 위 catch가 **역방향 사례**다: 유령 미결을 **되살릴 뻔한 것**을 막았다. 또한 **부재 판정이 감싸는 함수 앞에서 멈춘 사례**를 5분류 자리에 하위 단서로 등재) / **27.8(f-2) 계열**(측정 시점값 — 취소선 총수·grep 건수·`npx skills search` 반환 건수·RSS를 전부 **그 호출/세션의 시점값**으로 취급, 다른 세션 값과 **덮어쓰지 않음**) / **「실측 / 논증 / 문서인용 3분」**(33.7 수치 = **실측** / 「전건 정답의 기전 = 암기」 = **논증, 입력 실측 분리 표기** / 「`source_key` 범위 밖」 = **실측 근거의 경계 판정** / `01_extracted` 귀속 = **논증·코드 미확인**) / **「발견일 ≠ 반영일」**(본 세션 등재분 전건 **발견·반영 모두 2026-09-15**이나 양쪽 다 표기) / **「현재값 vs 이력」**(33.2 성적·33.6(b)(d) 표는 **이력·기준값이라 무변경 + 청정값 병기**, 카테고리 5 「역할·내용 미확인」은 **현재값이라 취소선 정정**) / **「압축 손실」**(누수 15그룹을 합계로 뭉개지 않고 **교차 10 / 갇힘 5 · 상위 그룹 크기 · split별 분포 · 클래스 귀속**까지 원소별 표기, 계수 단위 **클립 수 / 행 수 / 테스트 메서드 수 / NC 체크 수 / f32 값 개수**를 각 자리에 명시) / **카테고리 20**(계측/판정 계층 분리 — 33.7 발견이 **계측 자산(PR #59)이 먼저 있었기에 가능**했음을 본문에 남겼다).

**관련 카테고리**: **33.7 (데이터셋 내용 중복 → train/test 누수 신설 — 🔴 신규 미결)** / **33.8 (PoC-(48) 코드 PR 3건 자산 신설)** / 33.6(d) (재현 수단 확보 · 「개별 파일명 미기록」 해소 · 4회차 재현) / **33.6(e) (`[0.695, 0.7)` 경계 양끝 정정 · `all_scores` 파급 신규)** / 33.6(b) (`source_key` 누수 방지 = 「범위 밖」 경계, 취소선 아님) / **33.2 (test 성적 청정값 병기 · `labels.json` 위상)** / **카테고리 5 (`01_extracted`·`manifests` 부분 해소 · `final_manifest.csv` 신규 등재 · test `stem` 전건 일치)** / 26.10(a) (계수 단위 명시 — 숫자 무변경) / 6.3(o) (`jsonpeek_test` 등재) / **27.8(j) (위임 인용 오기 2건 + 라인 번호 재발)** / 27.8(d)(i) (누적 숫자 무변경 — 사용자 판단 대기) / 학습 21 (부재 판정이 감싸는 함수 앞에서 멈춘 사례 · 유령 미결 되살리기 방지) / 8.5(k) (`all_scores` 표시 축) / 카테고리 20 (계측/판정 계층 분리 · 문서/코드 push 분리) / 29.6 (커밋 컨벤션)
**관련 commit**: `01f5796`(PR #58) · `4d79aa7`(PR #59) · `00f43f8`(PR #60) — 전부 **본 세션 머지분**. 문서 반영 = 본 Set 1 커밋(docs-only, **PR 없음, main 직 push**). 선행 = `00f43f8`(착수 시점 HEAD).

## 2026-09-15 (화) 후속 — PoC-(49) Set 1 — PR #55 ④런타임 실측(6.3(p) 신설) + PR #61 문서·docstring stale 해소(7.7(k) · 33.8) + 카카오 자동 갱신 ④런타임 재확인·현재값 갱신(7.5(e)) + 누수 감사 확장(33.7(g) 신설 · (a) 454 → 466 산술 오기 정정) + OOD 스윕 확장(33.6(f) 신설) + 서버 회귀 누적 102 → 104 (카테고리 5/6.3/7.5/7.7/8.5/26.10/27.8/33.6/33.7/33.8)

2026-09-15 **후속 세션**(같은 날 PoC-(48) Set 1에 이어짐)의 실측 결과를 SSoT에 등재. 랩실 ④런타임 1건(**PR #55 SD 내부 풀다운 판별**)과 노트북 단독 실측 3건(**카카오 자동 갱신 리허설** · **누수 감사 확장** · **OOD 스윕 확장**), 그리고 **PR #55 · #61 머지**가 남긴 해소를 반영했다. 본 Set은 **문서 전용이며 코드 0줄** — `git diff --name-only` = `docs/` 2파일뿐이고 `server/` · `dashboard/` · `firmware/` · `ml/` 무접촉이다. **데이터셋은 읽기만** 했다(이동·삭제·수정 **0건**). **노션 무접촉**(Set 3 소관), **프로젝트 지침 무접촉**(Set 2 소관), **`docs/git-convention.md` 무접촉**. 🔴 **누수 대응 · 잡음 대응 · OOD 대응 · round 수정 · FAQ 카피 · 27.8(d) 누적 합산은 전부 사용자 판단 대기로 유지** — 수치 · 정책 · 방향 신설 **0건**이다.

**Step 0 가정 대조 — F1~F5 전건 O (불일치 0건 → 착수, pivot 0건)**: HEAD **`b56da39`** · 브랜치 `main` · 워킹트리 clean(F1 O). 위임 §4가 인용한 문구 **21건 전건 실존**(F2 O — `[확인 대상]` 표시분 포함). `git show HEAD:docs/decisions.md | grep -nE "^## 카테고리|^### "` 전수로 절 구조를 확인해 **33.x · 27.8 · 6.3 · 7.5 · 8.5가 전부 문자 `(a)(b)…` 체계**임을 실측했다(F3 O). `decisions-log.md` 마지막 엔트리 = **2026-09-15 PoC-(48) Set 1**이며 `c81a371`(모지바케 정정) 후속 엔트리는 **없다**(F4 O — `c81a371` grep = 두 문서 모두 **0건**). 근거 원본 **5개 파일 전건 실존**(F5 O). ⚠️ **위임 수치와 근거 원본이 갈린 곳은 원본을 택했다** — ① 33.6(f)의 「Yuna RMS 300 신뢰도 0.46~0.76」은 `results.csv`에서 `fire_alarm` 행만 다시 뽑으니 **0.46 ~ 0.59**(5행)였고 **0.76은 `doorbell` 행**이었다(위임이 경고한 혼입이 실제로 있었다) ② m5 clip 범위는 위임의 「m2 범위와 같음」보다 로그가 정밀해 **`0~5` vs `1~5`** 원문을 그대로 썼다.

**find-skills**: `npx skills --help`로 하위 명령 실물 확인(**`find` · `use` 없음** — 알려진 표면과 일치). `npx skills search` 3질의 — `changelog` **98건** / `"decision record"` **32건** / `markdown` **315건**. **0건 질의 0개** ⇒ 도구 생존 별도 증명 불요. **채택 0건.** 최다 별점 `changelog-generator`(★ **14,487** · **0 installs** · `by undefined`)는 **①출처 · 설치 수 미달**이자 **②워크플로 불일치**(본 repo는 changelog 자동 생성이 아니라 **단일 `decisions.md` 누적 = 취소선 + append**이고 log는 **사람이 판단 · 반증 · 경계를 서술**한다). `architecture-decision-records` · `git-adr` · `documentation`류는 **ADR 신규 파일 생성 모델**, `markdown-tools` 등은 **포맷 변환 도구**라 **과거 미채택 확정분 재사용**(재평가 불요).

### 신설 절 번호 · 위치 결정 근거 (위임 일부 미지정 — MCP 판정, 근거유형 = 실측 grep)

- **6.3(p)** — 6.3 하위가 `(a)`~`(o)` 연속이므로 다음 빈 문자는 **(p)**다. 🔴 **(n) 안의 중첩 항목이 아니라 독립 letter로 세운 근거** = 6.3의 **기존 컨벤션**이 *"④런타임 실측마다 자기 letter를 준다"*이기 때문이다(M5-b ④런타임 = **(j)** / M5-d ④런타임 = **(m)**). (k-1)(k-2)식 중첩 라벨 선례도 있으나, 본 건은 표 · 판정 · 한계를 갖춘 **완결 실측**이라 (j)(m) 쪽 선례를 택했다. (n)의 🟡 항목에는 **(p)로 가는 포인터만** 남겼다.
- **33.6(f)** — 33.6 하위 `(a)`~`(e)` 다음 빈 문자. **(a)의 확장이므로 (a) 본문에는 포인터 1줄만** 넣고 수치는 전부 (f)에 뒀다(위임 지정과 정합).
- **33.7(g)** — 33.7 하위 `(a)`~`(f)` 다음 빈 문자.
- **27.8(k)** — 27.8 하위 전수 `(a)(b)(c)(d)(e)(g)(f)(h)(i)(j)`(**(g)가 (f)보다 파일 앞쪽**) 확인 후 다음 빈 문자.
- **33.8은 신설하지 않고 in-place 해소**했다 — PR #61이 닫은 것은 **33.8이 「별건」으로 등재해 둔 바로 그 stale**이라 **미결이 등재된 자리**에서 취소선 + ✅로 처리하는 것이 규칙 정합이다. 새 절을 세우면 「등재 → 해소」가 두 자리로 흩어진다.
- **E7(카카오 1차 알림 2행 출처)은 7.5(f)** — (f)가 **데스크톱 vs 모바일 렌더 실측**의 자리이고 본 건도 **클라이언트 렌더 관찰**이라 같은 층위다. 7.6은 **2차(feed + text) 배선** 절이라 1차 텍스트 렌더를 넣을 자리가 아니다.
- ⚠️ **부재 G-ID 회피** — 근거 원본 보고서는 중복 그룹을 `G01`~`G15`로 라벨링하지만, 이 중 **`G07` · `G15`는 27.8(f)가 「decisions.md 0건인 미확인 ID군」으로 등재한 문자열과 충돌**한다. ⇒ 33.7(g)에는 **그룹 라벨을 쓰지 않고** 「`source_key` 수 = n인 10그룹 / = 1인 5그룹」처럼 **성격으로 서술**했다(부재 G-ID 사용 금지 원칙 준수).

### 편집 건별 (전건 `str.count` == 1 assert 통과, 라인 번호 0건 사용)

| ID | 대상 절 · 항목 | 성격 | 근거유형 | 근거 원본 | 앵커 count |
|---|---|---|---|---|---|
| E1 | 7.5(i) | **현재값 갱신**(102 → 104) | 실측 | 학부생 로컬 회귀 실행 + PR #61 세션 3회 재확인 | 1 |
| E2 | 7.7(k) | **미결 해소** | 실측 `git show` | `b56da39` / `8709ba8` | 1 |
| E3 | 33.8 | **등재 해소** + 신규 단서 | 실측 `git show` | `b56da39` / `0f50281` · `8709ba8` | 1 |
| E4a·E4b·E4c | 6.3(n) 🟡 항목 | **미결 해소**(머지 · ④런타임) + 포인터 | 실측 `git ls-remote` · `git log` | `94aa9d9` | 각 1 |
| E4d | **6.3(p) 신설** | **신규 등재** | 실측 | `mic_noiseprobe_pr55_sdpd_runtime.log` | 1 |
| E5 | 6.3(o) | **현재값 갱신**(3종 → 4종) + **부분 해소**(checks 수) | 실측 | PR #61 세션 호스트 테스트 실행 | 1 |
| E6a | 7.5(e) | **현재값 갱신**(토큰 DB 정본) | 실측 DB 조회 | `kakao_refresh_rehearsal_2.log` | 1 |
| E6b | 7.5(e) | **신규 등재**(자동 갱신 ④런타임 재확인) | 실측 | `kakao_refresh_rehearsal_2.log` · `kakao_refresh_rehearsal.log` | 1 |
| E7 | 7.5(f) | **신규 등재**(관찰) | 실측 + 가능성 | 대화 화면 catch · PR #61 세션 grep · payload 실물 | 1 |
| E8 | 8.5(d) | **단서 추가**(미결 유지) | 실측 + 가설 | `kakao_refresh_rehearsal_2.log` · 1회차 로그 | 1 |
| E9 | 8.5(i) | **사용자 결정 등재**(미결 유지) | 사용자 결정 | 2026-09-15 사용자 확정 | 1 |
| E10a | 33.7(a) | **산술 오기 정정**(454 → 466) | 실측 재계산 | `leak_audit_ext_2026-09-15.md` | 1 |
| E10b·E10c | 33.7(f) | **부분 해소** | 실측 | 동상 | 각 1 |
| E10d | **33.7(g) 신설** | **신규 등재** | 실측 md5 전수 | 동상 | 1 |
| E10e | 카테고리 5.1 | **포인터**(0바이트 · 78 B) | 실측 | 동상 | 1 |
| E11a | 33.6(a) | **포인터** 1줄 | 실측 | `ood_sweep_ext/` | 1 |
| E11b | **33.6(f) 신설** | **신규 등재** | 실측 | `ood_sweep_ext/summary.md` · `results.csv` · `ood_sweep_ext_runtime.log` | 1 |
| E11c | 26.10(d) | **포인터** 1줄 | 실측 | 동상 | 1 |
| E12 | 8.5(k) | **단서 추가**(원문 무변경) | 실측 grep | `decisions.md` 자체 | 1 |
| E13 | **27.8(k) 신설** | **신규 등재** | 실측 grep + 실물 대조 | 위임 본문 · 인계 문구 · 본 세션 보고서 | 1 |

### 등재 내용 요약

- **E4d (6.3(p) 신설 — PR #55 ④런타임, 근거유형 = 실측, 계수 단위 = 스냅샷 수 / 클립 수)**: 펌웨어 `dddde9b` · **결선 무변경** · 순서 **2 → 5 → 2 → 5 → 0 → 6** × `s` 3회 = **18 / 18 유효**(전 블록 `ok=1` · `sd_pd req == reg` · `gaps=0` · 스냅샷 8줄 무손상). m2 clip **1·4·5 / 2·1·5**(tz 6·6·5 / 5·5·5) · m5 **3·5·5 / 0·1·5**(tz 7·7·7 / 7·7·6) · m0 **0·0·0**(tz 6, rms 91~99) · m6 **0·0·0**(tz 8, rms 88~97). 클립 전건 **+32767**, raw 예시 전건 **`7F…`**. `low6nz` = **m5 6회 전건 0 / m2 6회 중 4회 >0**. 🔴 **[실측] 교대 m2 대조군 6 / 6 재현**(판정 전제 성립) · **m5 clip 범위 `0~5` = 교대 m2 `1~5`** ⇒ **내부 풀다운으로 클립 미소거** · **m6 vs m0 = `tz`만 6 → 8**. **[논증 · 미실증]** 풀다운은 워드 **하위 비트(6·7, tri-state 구간 추정)** 만 고정하므로 **MSB 클립과 별개 기전**일 수 있고 하위 비트는 `>>14`에서 버려져 **int16 무영향 가능성**이 있다. ⚠️ **판정표(「같은 범위」 → ① 검토)는 Runbook 6-1 계층**이며 **(n)(p) 본문 기준이 아니다**(근거유형 = 문서 인용). 🔴 **(n) 해결책 ①②③은 여전히 사용자 판단 대기.** **한계** = 내부 풀다운 **약 45kΩ**(Runbook 서술 · 미실측) ≠ 외부 100kΩ ⇒ 확대 해석 금지 / 스냅샷 **#6 `rms_x` 809**(타 96~155) = 실제 소리 오염 추정 · 음원 미확인 / **m1 · m3 · m4 미수행** / 블록 4 직전 **ToF near 최대 8/64** / 보드는 m6 상태로 종료.
- **E4a·E4b·E4c (6.3(n))**: PR #55 **~~미머지~~ → 머지 `94aa9d9`**, **~~④런타임 미수행~~ → 완료**, 원격·로컬 브랜치 **삭제 완료**(실측 = `git ls-remote origin`이 `refs/heads/main` 단일 — **학습 20**, `git branch -r` 미사용). 🔴 **「이것은 수단이지 해결책이 아니다」 문장은 무변경**이며 그 자리에 *"④런타임 결과가 나온 뒤에도 ①②③은 그대로 사용자 판단 대기"*를 못 박았다.
- **E2 (7.7(k) 「폴백한다」 미결 해소)**: PR #61 `8709ba8`이 `server/app/kakao.py` `send_secondary` docstring을 **「`stt.is_real_mode()` 게이트에서 애초에 real 모드가 아니므로 CSR 호출 자체를 하지 않는다」**로 교체했다. **로직 0줄**(`ast.dump` 해시 수정 전후 동일, **대조군 NC** = 코드 토큰 1개 변경 → 검출 / docstring만 변경 → 비검출). ⚠️ **닫힌 것은 문구뿐** — (i) `mode=real` 로그 불변식 · (j) 경계 표기 **무변경**.
- **E3 (33.8 「PR #60이 남긴 문서 stale」 등재 해소)**: 「별건」이 **같은 날 처리**됐다. `0f50281` **📝 Docs**(`ml/pipeline/README.md` 옛 절대경로 → `DDINGDONG_DATA_ROOT="~/ML 학습 데이터/ddingdong_dataset"` / `ml/training/README.md`에 env 필수 · 없으면 `ValueError` 명기) · `8709ba8` **🗃️ Comment**(`train.py` · `evaluate.py` docstring 동). 🆕 **본 절이 등재하지 않았던 stale 2건도 같은 PR이 정정**했다 — `MIC_NOISEPROBE_RUNBOOK.md`의 **「모드 5개」 → 7모드(m0~m6)** / **「ToF 판정은 로그하지 않지만」 → `tofJudgeFrame` 내부가 `[tof]` 줄을 출력**. ⇒ 본 절의 stale 등재는 **ML 계열만** 담고 **펌웨어 문서 계열은 빠져 있었다.** **PR #61 성격 = 정합성 정정**(MCP 자기 판정).
- **E1 (7.5(i) 회귀 누적 현재값)**: **~~102~~ → 104 케이스**(PR #58 **+2** — 상세 33.8). 근거 = 학부생 로컬 `Ran 104 tests` OK(측정 시점 워킹트리 = **PR #61 머지 이전 `main`**) + PR #61 세션 **3회 반복 동일**. 🔴 **다른 절의 102는 전부 「그 PR 시점 이력」이라 무변경**이며 일괄 치환하지 않았다(6.4(d) 30→42 / 7.6(g) 42→60 / 7.7(a) 60→83 / 카테고리 3 G12 83→89 / 8.5(g) 89→99 / 8.6(c) 99→102 / 26.10(d) 「서버 회귀 102건으로 대체 커버」).
- **E5 (6.3(o) 호스트 테스트)**: **~~3종~~ → 4종**(`noise_modes_test`가 PR #55로 합류). **4종 전건 OK**, checks 수 = `noise_modes_test` **46** / `noise_stats_test` **61** / `tof_judge_test` **196**. 🔴 **`jsonpeek_test`만 카운터 출력이 없어 checks 수를 셀 수 없다** — **정적 `assert` 13개**로 병기하되 **계수 단위가 다르다**(assert 문 수 ≠ checks 수, **더하거나 비교 금지**). ⚠️ **커버리지는 여전히 미측정**이라 「미측정」 서술은 **부분 해소**로만 처리했다.
- **E6a·E6b (7.5(e) 카카오 자동 갱신)**: **현재값 갱신** = `access_expires_at` **~~2026-09-12 10:40~~ → 2026-09-15 14:04:17** / `refresh_expires_at` **2026-11-10 01:41:19 불변** / `updated_at` **~~2026-09-12 04:40~~ → 2026-09-15 08:04:18**(전건 naive UTC). **신규 등재** = 만료 **3일 경과** 상태에서 `/detect` **2회** 실호출 — **S0 = S1**(P1 `tof_rejected` · `primary_sent=false` ⇒ **발송을 시도하지 않은 호출은 갱신을 유발하지 않는다**) / **S2에서만 이동**(P2 `primary_sent=true` · `primary_sent_at` **17:04:18 KST** ⇒ **갱신은 P2에서 일어났다**, 새 access TTL **21,600초**). **P2 이후 첫 폴링에서 만료 WARNING 소멸.** **실모델 3축 충족**(RSS **464,576KB** / TF 매핑 **54개** / 두 호출 `all_scores` 완전 일치). **도착 = PC · 모바일 카카오톡 동일 표시**(1행 「🔔[띵동] 초인종이 울렸어요.」 + 2행 「모바일에서 확인해 주세요.」 + 앱 버튼 「Ddingdong」, **17:04 KST**). 🆕 **(e) 상단의 「`updated_at` 인과 미실증」이 닫혔다** — 같은 호출 안에서 발송과 갱신이 함께 관측됐기 때문이며, ⚠️ **닫힌 것은 「발송이 갱신을 돌렸는가」뿐**이고 **「refresh 재발급 여부」는 여전히 미확인**이다. **한계** = `refresh_token` **값 미비교**(만료 시각 · 길이 불변만) ⇒ *"잔여 1개월 미만일 때만 재발급"*의 **문서 인용 · 미실측 꼬리표 유지** / **갱신 HTTP 왕복 미관측**(기본 로그 레벨), 갱신은 **DB 상태 변화로만 실측**. ⚠️ **1회차 §9 정지 경위**도 한 줄로 적었다 — 5000 포트에 **전날 13:45 KST 학부생이 띄운 실모델 서버(PID 63755)** 가 약 **27시간** 잔존해 3축 판정이 불가능했고, **17:02 KST 학부생 Ctrl+C** 후 재개했다.
- **E7 (7.5(f) 1차 알림 2행 출처 — 관찰 등재)**: **[실측]** 저장소 코드 **0건**(`server/` · `dashboard/src/`, **대조군** 「초인종이 울렸」 **2건** 생존) · `_post_memo` payload 실물 = `{object_type, text, link:{web_url, mobile_web_url}}`이고 **`button_title` 키 없음**. **[가능성 · 미실증]** 카카오 클라이언트의 **기본 렌더**일 가능성. ⚠️ **대외 카피 판단은 하지 않았다.**
- **E8 (8.5(d) 만료 WARNING 단서 — 미결 유지)**: **[실측]** 폴링 **1회당 3줄**(8.1 stats 3중과 정합), 실례 = 「만료 **4162분** 경과」(학부생 서버) · 「만료 **4164분** 경과」(MCP 서버). **[실측]** MCP 서버의 `/stats` 간격이 **약 60초**로 관측돼 본 항의 **3초 주기와 다르다**. **[가설 · 미검증]** 백그라운드 탭의 브라우저 타이머 제한 — **판정 방법** = 탭을 전면에 두고 access log 간격 측정. ⚠️ **3초 주기 서술은 무변경**이며 본 관측은 **그 세션의 시점값**으로 표기했다(27.8(f-2) 계열).
- **E9 (8.5(i) — 🔴 사용자 결정 등재)**: **`device_status` / `signal_strength` 거짓 표시 = 현행 유지(수정 보류), heartbeat 통합 전까지**(결정 주체 = **사용자**). 사유 = **heartbeat 미구현**(8.5(i)가 ③을 「현시점 재료 부재」로 분류한 **기존 판정과 동일**). 🔴 **미결 표기 유지** — 결정된 것은 처리 방침뿐이고 **판정 방법은 그대로 유효**하다. ⚠️ **부스 운영 방식 · 발표 답변 문구는 Claude 제안이라 등재하지 않았다.**
- **E10a·E10b·E10c·E10d·E10e (33.7 감사 확장)**: 🔴 **(a)의 「454파일이 단 6개 내용」 = 산술 오기**로 **~~454~~ → 466**(108+108+108+56+56+30). (a)의 **다른 수치는 전건 재현**되므로 **계측값이 아니라 합산 표기**가 틀렸다. **재현 12항목 일치**로 도구 신뢰를 먼저 확인했다. **`01_clips`** = 2798 / 고유 **2306** / 그룹 **16** / 소속 **508** / 잉여 **492**, **01 전용 n=6 = 5.1의 `S_103` skip 6건**(서로 바이트 동일, **78 B**), **01↔02 동일 relpath md5 일치 0 / 2792**. 🔴 **02의 15그룹 전부가 `01_clips`에서 이미 동일** ⇒ **전처리 발생 0 / 15**. **`03_augmented`** = 9655 / **8678** / **45** / **1022** / **977**, **03 ∩ 02 = 6(전부 무음)**. **`05_final_dataset`** = 12447 / **10982** / **59** / **1524** / **1465**, split 교차 **10그룹** · 클래스 교차 **23그룹**, split별 train **11586** / val **437** / test **424**. 🔴 **05 test ∩ (train ∪ val, 증강 포함) = 79 = 02와 동일 ⇒ 증강 증가 0**(내역 test∩train 79 / test∩val 76, val ⊂ train). **`01_extracted`** = 548(wav **377** + mp3 **171**), ∩01 **0** · ∩02 **0**(⚠️ **wav 377건에 한해 유효** — mp3는 원리상 비교 불가), 내부 **n=30 = 0바이트 빈 파일**. **그룹 성격** = `source_key` 수 = n인 **10그룹 491파일**(서로 다른 원본) / = 1인 **5그룹 10파일**, 대형 그룹은 **같은 키 집합 × 오프셋 0 / 3000 / 6000ms**, **전량 중복 원본 0 / 108**, 전건 **3.00s / 16k / mono / 16bit**, 자기상관 **0.109 ~ 0.249**. 🔴 **클래스 교차 6그룹**(무음 5파일이 3클래스 / 두 `source_key`가 `doorbell` · `fire_alarm` 폴더에 동시 존재, **전부 train**). **[논증 · 가능성]** `S_103` 선두 약 9초 공통 ⇒ **발생 지점이 원천 데이터셋일 가능성**(`00_source_raw` 미감사라 **미확정**) / 클래스 교차와 **33.2 `doorbell → fire_alarm` 오분류의 관련은 미검증 가능성으로만** 적었다. **(f) 한계는 부분 해소**(01 · 03 · 05 · 01_extracted 확인 / **`00_source_raw` · 파형 동일 · 바이트 상이 · 부분 중복 · 두 클래스 배치 경위 잔존**). 🔴 **(d)(e) 무변경 · 대응 방향 사용자 판단 대기 유지 · 성적 재계산 0회.** 5.1에 **0바이트 30개 + 78 B 6개 포인터**를 걸었다.
- **E11a·E11b·E11c (33.6(f) OOD 스윕 확장)**: **HTTP 미경유 · 서버 미기동 · 카카오 경로 없음**, 경로 A(`model_serving` 공개 함수) = 경로 B(서명 직접) **동등성 확인**, 입력 **32,768샘플**, 총 **130행 / 유효 126 / 제외 4**(클리핑). **2회 실행 전 열 일치** · 앵커 `doorbell` **1.00** · **라벨 순서 단언** · **raw ↔ rounded 갈림 0행**. **발송 판정은 프로즌 `_apply_prediction_policy` 실제 호출**(재구현 0줄). 결과 = 음성 **72행** 중 `fire_alarm` ≥0.70 **12행(전건 한 음성)** / 나머지 두 음성 **48행 전건 `knock` · ≥0.70 전건** / 같은 음성 **RMS 300의 `fire_alarm` 5행 = 0.46 ~ 0.59 전건 게이트 미달** / 배경 바닥 **95 → 0**에서 **4 / 8 → 8 / 8** / 시스템 알림음 **24** + 잡음 **11**에서 `fire_alarm` ≥0.70 **0행** · `doorbell`·`knock` ≥0.70 **27 / 35** / 박수형 버스트 **`knock` 1.00** / 완전 무음 **`fire_alarm` 0.62** / 바닥만 **`knock` 0.78**. 🔴 **발송 판정 = `presence=true` 102 / 126 · `presence=false` 20 / 126.** ⚠️ **[런타임 주입 NC] `app.utils` 임계 0.99 주입 시 (14, 5)** — **「가정 임계 0.99에서의 값」이며 정책 시사로 쓰지 말 것**(함정 대조군 = `app.constants`만 패치 → **(102, 20) 무변화**, 복원 후 **(102, 20)**). **9/12 재현** = `silence` · `sine1k` 일치 / `whitequiet` **0.80 vs 0.74**(진폭 · RNG 가정) / `voiceshort` · `voicelong` · `knocklike` **재현 불가**(원 스크립트 부재). **한계 전건** = TTS ≠ 사람 · **보드 미경유** · G28 레벨 정합 미검증 · 부스 소음 미재현 · **바닥 파형 n=1**. **[논증]** 현재 트리거가 **수동 `s`** 라 판정 기회가 사람 입력에 한정 — **자동 트리거(M5-c) 도입 시 노출 증가 가능성**(미실증). 🔴 **대응 방향 = 33.6(a) 사용자 판단 대기 그대로.** 26.10(d)에 **부스 파급 포인터 1줄**을 걸었다.
- **E12 (8.5(k) 단서 — 원문 무변경)**: 실물은 **「표시 해상도가 판정을 오염시키지 않는다」**이고 **27.8(j)① · 33.6(e) 제목**은 **요약형 「표시가 판정을 오염시키지 않는다」**를 쓴다 ⇒ **요약형으로 8.5를 grep하면 0건**이라 **유령 부재 판정**에 빠진다. **원문 · 요약형 둘 다 정정 대상이 아니며** 갈리는 것은 **검색어뿐**이다.
- **E13 (27.8(k) 신설 — 인용 오기 5건)**: ① **「m2/m5 교대 18스냅샷」 = 압축 손실**(실물 6블록 중 **m0 · m6 누락**, 빠지면 6.3(p)의 `tz` 6 → 8 판정이 성립하지 않는다) / ② **해소를 미결로 되돌릴 뻔했다 — 학습 21의 역방향**(대화의 *"카카오 자동 갱신은 한 번도 확인 못 했다"* vs **7.5(e) 2026-09-05 실증 실존**) / ③ **응답 구조 오기**(`skip_reason` · `primary_sent` · `primary_sent_at`은 최상위가 아니라 **`notification_status` 하위**) / ④ **위임이 6.3(o) 문구를 grep 없이 인용**(「3종」만 옮겨 「미측정」 규정이 딸려 오지 않았다) / ⑤ **라인 번호 인용 3건 — (i)가 닫은 축의 4세션 연속 재발**(2026-09-12 2건 → 09-14 3건 → 09-15 PoC-(48) 1건 → 09-15 PoC-(49) 3건). ⚠️ **(d)의 「누적 21건」 무변경** — 합산 여부가 (i)에 사용자 판단 대기.

### 🔴 사용자 판단 대기 항목 — 등재하되 방향 미확정 (전건 명시 확인)

| 항목 | 등재 위치 | 방향 확정 여부 |
|---|---|---|
| 데이터셋 중복 · 누수 대응(① 재split · 재학습 / ② 누수 고지 병기 / ③ 청정값 정본 교체) | 33.7(e) | **미확정 — 본 Set에서 건드리지 않았다** |
| 마이크 SD 비트 오류 해결책(① 펌웨어 필터 / ② 배선 조치 / ③ 병행) | 6.3(n) | **미확정 — (p) ④런타임이 가른 것은 H1 하위 가설뿐** |
| OOD 수렴 대응(임계 재검토 / 4번째 클래스 / 재학습 / 시연 각본) | 33.6(a) · (f) | **미확정 — n을 넓혔을 뿐 임계 · 정책 신설 0건** |
| `model_serving.py` round 수정 여부 · 방식(`confidence` + `all_scores`) | 33.6(e) | **미확정 — 무변경** |
| 카카오 1차 알림 2행 대외 카피 | 7.5(f) | **미확정 — 관찰 등재까지만, 카피 판단 0** |
| 27.8(d) 누적 숫자 합산 여부 | 27.8(i) | **미확정 — (d) · (j) · (k) 전부 무변경** |
| 만료 WARNING 로그 오염 처리 방침 | 8.5(d) | **미확정 — 미결 유지, 빈도 단서만 추가** |
| `device_status` / `signal_strength` 거짓 표시 | 8.5(i) | **처리 방침만 확정(현행 유지) — 🔴 미결 자체는 유지** |
| 중복 발생 원인의 `01_clips` 이전 구간 | 33.7(f) · (g) | **미확정 — `00_source_raw` 미감사** |
| `jsonpeek_test` 커버리지 | 6.3(o) | **미측정 — checks 수만 부분 해소** |

**SSoT 정합 검증 (문서 전용이라 코드 3단계 ①②는 무관)**: ① 빌드 · ② 테스트는 **코드 0줄 변경이라 무관**하며(`git diff --name-only` = `docs/` 2파일), ③ **오류 방지**는 아래로 대체했다. 신설 절 **6.3(p) · 33.6(f) · 33.7(g) · 27.8(k)**는 각 절의 하위 문자 **전수 확인 후 다음 빈 문자**로 부여했고 **번호 체계 혼재 0건**이다(27.8은 **(g)가 (f) 앞**인 실물 순서까지 확인). 편집 앵커 **20건 전건 `str.count` == 1 assert 통과**(패턴 매칭, **라인 번호 0건 사용** — 본 엔트리 본문도 동일 준수). 취소선 = **착수 전 72줄 / 164개 → 종료 80줄 / 188개**(계수 단위 = `grep -c '~~'` **줄 수** / `grep -o '~~' | wc -l` **출현 수**). 증가분 **+8줄 / +24개 = 신규 취소선 12쌍**(E1 1 · E2 1 · E3 1 · E4a 2 · E4b 1 · E5 2 · E6a 1 · E10a 1 · E10b 1 · E10c 1)으로 **설계와 정확히 일치**하고 **188 = 짝수 = 마크다운 무파손**이다. **삭제 0줄 증명** = 제거된 **12줄**의 토큰이 추가분 **142줄**에 **원시 기준 미보존 0종**으로 재출현한다. 정규화(마커 제거) 기준 1종(`firmware/tools/jsonpeek_test.cpp.`)은 **문장 끝 마침표가 목록 구분자 ` · `로 바뀐 경계 artifact**이며 실물 `grep -c` **1건**으로 생존을 확인했다. **한글 전수 검증** = 추가 줄의 한글 음절 중 착수 전 집합에 없던 **신규 음절 전건 문맥 출력** · `U+0080`~`U+00FF` 중 기존 정상 기호 외 **0건** · `U+FFFD` **0건**(전부 코드포인트 기준, 보이는 모양으로 grep하지 않았다). **102 무오염 확인** = 다른 절의 이력 102는 **제거 줄 1건(7.5(i) 본인)** 외 **0건**이며 그 1건도 취소선 안에 **그대로 보존**됐다.

**비범위**: **코드 0 수정** — `server/` · `dashboard/` · `firmware/` · `ml/` 이하 전부 무접촉이며 `docs/git-convention.md`도 **무접촉**이다. **노션 무접촉**(DB3 row · Gap 카드 = **Set 3 소관**), **프로젝트 지침 파일 무접촉**(**Set 2 소관**), **26.9 Gap 표 무변경**(Set 3 소관). 🔴 **사용자 판단 대기 10건 전부 방향 미확정으로 등재만** — 임계값 · 정책 · 수치 · 재학습 방향 신설 **0건**이고 **Claude 제안을 결정으로 등재한 건 0건**이다(E9의 부스 운영 방식 · 발표 답변 문구는 **제안이라 제외**). **27.8(d) 누적 숫자 무변경** · **33.7(c)(d)(e) 무변경** · **33.6(a)~(e) 본문 수치 무변경**(포인터 1줄만) · **8.1 「3초 주기」 무변경** · **8.5(k) 원문 무변경**. **부재 G-ID 0건 사용**(근거 원본의 그룹 라벨 `G01`~`G15`를 성격 서술로 치환). **미착수** = `00_source_raw` 감사 / m1 · m3 · m4 모드 / 실 초인종 음원 / 보드 경유 OOD / `refresh_token` 값 비교 / 갱신 HTTP 왕복 관측 / 탭 전면 상태 폴링 간격 측정. **PR 없음** — 브랜치 없이 **main 직 push**(문서 단독, 카테고리 20 「문서/코드 변경 push 분리」).

**학습 적용**: **학습 13**(grep 후 인용 — §4 인용 **21건 전건 실물 대조 후 사용**, 편집 앵커 **20건 전건 `count == 1`**, **라인 번호를 앵커 · 본문 모두 0건 사용**. 🔴 **위임에 옮겨 적힌 수치도 대조 대상**이라는 규칙이 값을 했다 — 「Yuna RMS 300 0.46~0.76」이 `results.csv` 재추출에서 **`fire_alarm` 행만 0.46 ~ 0.59**였고 **0.76은 `doorbell` 행**이었다. 「현재값 vs 이력」도 갈랐다 — 7.5(i) 102만 갱신하고 **6.4(d) · 7.6(g) · 7.7(a) · 8.5(g) · 8.6(c) · 26.10(d)의 102/이력 서술은 무변경**) / **학습 14**(위임 가정을 실물로 검증 — PR #61이 정말 `kakao.py`를 고쳤는지, `0f50281` · `8709ba8`이 실존 커밋인지, `94aa9d9`가 PR #55 squash인지를 **`git show` · `git log`로 전건 확인**. 원격 브랜치 삭제는 **`git ls-remote origin`**으로 확인했다 — **학습 20**) / **학습 16**(기존 컨벤션 우선 — 6.3의 *"④런타임마다 자기 letter"*(j)(m) 선례를 따라 **(p)를 독립 letter로** 세웠고, 33.8은 **미결이 등재된 자리에서 해소**하는 규칙을 따라 신설하지 않았다. `decisions-log.md` 헤더 · 섹션 골격은 **실물에서 그대로 따왔다**) / **학습 17**(위임 본문도 catch 대상 — 🔴 **위임이 적은 그룹 라벨 `G01`~`G15`가 27.8(f)의 부재 G-ID `G07` · `G15`와 충돌**함을 catch해 **성격 서술로 치환**했고, **응답 구조 평면 필드 오기**도 실물 `notification_status` 하위로 정정해 진행했다. 전건 27.8(k)에 등재) / **학습 21**(미결 자체가 유령일 수 있다 — 본 세션은 **역방향**이 나왔다: 대화의 *"카카오 자동 갱신은 한 번도 확인 못 했다"*는 **7.5(e)의 2026-09-05 실증을 지운 날조**였고, grep 1건으로 되살리지 않았다. 또한 **요약형 인용으로 8.5를 grep하면 0건**이 나오는 **유령 부재 함정**을 8.5(k)에 단서로 못 박았다) / **27.8(f-2) 계열**(측정 시점값 — `/stats` 60초 간격 · `npx skills search` 반환 건수 · 취소선 총수를 전부 **그 호출의 시점값**으로 표기하고 다른 세션 수치와 비교하지 않았다) / **「발견일 ≠ 반영일」**(본 Set 신규 등재 전건 **발견 = 반영 = 2026-09-15**이며 양쪽 다 표기. 커밋 시점이 자정을 넘기지 않았음을 확인했다) / **「실측 / 논증 / 문서 인용 3분」**(6.3(p)의 표 · `low6nz` = **실측** / 풀다운 하위 비트 기전 = **논증 · 미실증**(입력 실측 병기) / Runbook 6-1 판정표 · 45kΩ = **문서 인용 · 미실측** / 33.7(g)의 `S_103` 선두 9초 = **논증 · 가능성**) / **「압축 손실」**(18스냅샷을 「m2/m5」로 뭉갠 인계 문구를 **6블록 원소별**로 되돌렸고, 33.7(g)의 그룹 성격도 **10그룹 491파일 / 5그룹 10파일**로 원소별 표기했다).

**관련 카테고리**: **6.3(p) (PR #55 ④런타임 신설 — SD 내부 풀다운 클립 미소거)** / 6.3(n) (머지 · ④런타임 해소, 해결책 ①②③ 무변경) / 6.3(o) (호스트 테스트 3종 → 4종 · checks 수 부분 해소) / **7.5(e) (카카오 자동 갱신 ④런타임 재확인 · 토큰 현재값 갱신)** / **7.5(f) (1차 알림 2행 출처 관찰 신설)** / 7.5(i) (서버 회귀 누적 102 → 104) / **7.7(k) (「폴백한다」 미결 해소)** / 8.5(d) (만료 WARNING 빈도 · 폴링 간격 단서 — 미결 유지) / **8.5(i) (🔴 사용자 결정 — `device_status`/`signal_strength` 현행 유지)** / 8.5(k) (요약형 인용 단서 — 원문 무변경) / 26.10(d) (부스 파급 포인터) / **27.8(k) (위임 · 인계 인용 오기 5건 신설)** / 27.8(d)(i) (누적 숫자 무변경 — 사용자 판단 대기) / **33.6(f) (OOD 스윕 확장 신설)** / 33.6(a) (n=1 완화 포인터) / **33.7(g) (누수 감사 확장 신설)** / 33.7(a) (454 → 466 산술 오기 정정) / 33.7(f) (한계 부분 해소) / 33.8 (PR #60 stale 등재 해소 · PR #61 = 정합성 정정) / 카테고리 5.1 (0바이트 · 78 B 포인터) / 카테고리 20 (학습 20 `ls-remote` · 문서/코드 push 분리) / 학습 21 (유령 부재 · 역방향 날조)
**관련 commit**: `94aa9d9`(PR #55 squash — m5·m6 진단 모드) · `b56da39`(PR #61 squash — 내부 커밋 `0f50281` 📝 Docs + `8709ba8` 🗃️ Comment) — **둘 다 본 세션 머지분이며 원격·로컬 브랜치 삭제 완료**. 문서 반영 = 본 Set 1 커밋(docs-only, **PR 없음, main 직 push**). 선행 = `b56da39`(착수 시점 HEAD).

## 2026-09-16 (수) — PoC-(50) Set 1 — 🔴 회귀 테스트 실 CSR 누출 원인 규명·차단(30.9 부분 해소 · PR #62) + 카테고리 7 CER 근거 정정(6.49% = CLOVA Speech · 저음질 전화망) + CSR 소규모 실측 신설(7.7(m)) + 2차 체인 리허설 실측(7.4) + 서버 회귀 누적 104 → 106 (카테고리 5/7/7.4/7.5/7.7/8.5/20/27.8/30.9)

2026-09-16(수) PoC-(50)의 실측 결과를 SSoT에 등재. 축은 **넷**이다 — ① **30.9 「CSR 호출 301건 출처 미규명」의 원인 경로 규명 + 재발 방지**(대조 실험 → 읽기 전용 진단 → PR #62 머지), ② **카테고리 7 머리 「인터폰 노이즈 CER 6.49%」의 근거 정정**(벤치마크 원문 재확인), ③ **우리 엔진(CSR) 자체의 소규모 인식률 첫 실측**, ④ **2차 체인 리허설 실측**(카톡 + 대시보드 양축). 본 Set은 **문서 전용이며 코드 0줄** — `git diff --name-only` = `docs/` 2파일뿐이고 `server/` · `dashboard/` · `firmware/` · `ml/` 무접촉이다. **노션 무접촉**(Set 3 소관), **프로젝트 지침 무접촉**(Set 2 소관), **`docs/git-convention.md` 무접촉**. 🔴 **CSR 유지 결정의 재검토 여부 · 발표 문구 · 27.8(d) 누적 합산 · 카테고리 20 「원격 자동 삭제」 서술의 정정 여부는 전부 사용자 판단 대기로 유지** — 결정 · 정책 · 방향 신설 **0건**이다.

**Step 0 가정 대조 — C1 · C2 · C3 · C7 전건 O, C6 부분 불일치 1건(정지 임계 3건 미만 → 착수, pivot 0건)**: HEAD **`bc0df74`** · 브랜치 `main` · 워킹트리 clean(C1 O). 앵커 **A1~A13 전건 `grep -cF` == 1**(C2 O) — 단 **3건은 위임 문구 그대로는 1이 아니었다**: `[신규 미결]`은 **BRE 대괄호가 문자 클래스로 해석**돼 `grep -c`가 **2,260줄**을 뱉었고 `grep -cF`로 **24건**이 정상값이었으며(A2는 「CSR 호출 301건 출처 미규명」과 결합해 == 1), 「무죄 (실측)」은 **2건**(가설 ①②)이라 앵커를 「회귀 테스트가 실 API를 호출했다 → 무죄 (실측)」 전문으로 넓혀 == 1로 만들었고, 「모바일에서 확인해 주세요.」도 **2건**이라 A9 원문 전문(「1차 텍스트 알림 2행 …의 출처」)으로 넓혔다. `decisions.md`에 **`rtzr` · `Awesome-Korean` · `14.11` 전부 0건**(C3 O — 첫 등재 확정). **[확인 대상] C4 O** = 30.9 반증 가설 ①의 근거유형 표기는 실제로 **「(실측)」**이고 서술 내용은 **코드 확인**(가짜 문자열 · urlopen 스텁)이었다. **[확인 대상] C5** = **7.7 마지막 하위 문자 `(l)`** · **27.8 마지막 하위 문자 `(k)`**(⚠️ 27.8은 실물 순서가 **(e)(g)(f)(h)** 로 `(g)`가 `(f)` 앞이다 — 직전 세션 기록과 일치). `decisions-log.md` 마지막 엔트리 = **2026-09-15 (화) 후속 — PoC-(49) Set 1**이며 헤더 · 섹션 골격을 실물에서 그대로 따왔다(C7 O). 요일 검산 `date -j -f "%Y-%m-%d" "2026-09-16" "+%A"` = **Wednesday = 수**. 취소선 사전 측정 = **80줄 / 188개**.

🔴 **C6 — 로그 4종은 전건 실존하나 위임 §5와 1건이 갈렸다(로그 · PR 본문 우선 채택)**: 위임 E1의 *"수정 후: PR 브랜치 `eb06be3`에서 **가드 없이** `Ran 106` OK(**0.242초**) → 콘솔 25/0/375 무변동(**15:15** 확인)"* 중 **「가드 없이」 · 「0.242초」 · 「15:15」는 로그 4종 어디에도 없고**, 게다가 **「가드 없이」는 PR #62 본문의 「스위트 실행 총 6회 … 전부 가드 아래」와 정면으로 상충**한다. ⇒ **위임 문구를 옮기지 않고**, 실측 로그가 실제로 가진 **「가드 실행 후 콘솔 확인(14:53) = 25 / 0 / 375초 무변동」**과 PR #62 본문의 **「소켓 가드 아래 1회 = NCP host 시도 12건 전부 차단 · 콘솔 무변동」**으로 **대체 서술**했다(학습 17 — 위임 본문도 catch 대상). 나머지 수치는 **로그와 1:1 일치**(V5 표).

🔴 **위임 §4의 웹 인용 재확인에서 WebFetch 요약이 열을 잘못 읽었다 — 원문 표로 정정**: 위임은 「6.49% = 저음질 전화망 × Naver ClovaSpeech / Google api v2 = 14.11% / 리턴제로 = 4.40%」로 적었는데, **1차 WebFetch 요약은 「4.91 / 8.37 / 3.51」**을 돌려줬다. **README 원문 표를 직접 받아 대조**하니 그 셋은 **바로 왼쪽 「상담」 열**의 값이었고 **저음질 전화망 열은 위임이 옳았다**(`Naver ClovaSpeech 6.49` · `Google api v2 14.11` · `리턴제로 4.40`). ⇒ **요약 도구의 표 판독을 그대로 믿지 않고 원문 표로 판정**했다(학습 13 계열 — 원문 우선). 규모 「테스트셋당 3,000문장 샘플링」도 README 본문에서 확인했다.

**find-skills**: `npx skills search` 3질의 — `decision log markdown` **0건** / `documentation consistency` **1건** / `korean technical writing` **0건**. **0건 질의가 2개**라 **대조 질의 `flask`를 추가 실행해 25건**을 받았다 ⇒ **도구 생존 확인**(0건은 도구 사망이 아니라 실제 부재). **채택 0건.** 유일한 반환 `consistency-enforcement`(★ **0** · **0 installs** · `by undefined`)는 **① 출처 · 설치 수 미달**이자 **② 워크플로 불일치**다 — 그 스킬은 **README ↔ 코드 드리프트 방지**용인데 본 repo는 **단일 `decisions.md` 누적(취소선 + append) + 사람이 판단 · 반증 · 경계를 서술하는 log**다. Conventional Commits류(한국어 + 이모지 규약 충돌) · ADR 신규 파일류 · changelog 자동 생성류는 **과거 미채택 확정분 재사용**(재평가 불요).

### 신설 절 번호 · 하위 문자 결정 근거 (C5 grep 결과 — MCP 판정, 근거유형 = 실측 grep)

- **7.7(m)** — 7.7의 하위 문자를 **전수 확인**해 `(a)`~`(l)` 연속임을 보고 **다음 빈 문자 `(m)`**을 부여했다. `(l)`이 절의 마지막 하위이고 그 뒤가 「**관련**:」 줄이라, **「관련」 줄 바로 앞**에 삽입해 기존 절 구조를 깨지 않았다.
- **27.8(l)** — 하위 문자 **전수 확인**((a)~(k), ⚠️ **(g)가 (f)보다 파일 앞쪽**인 실물 순서 포함) 후 **다음 빈 문자 `(l)`**. 27.8은 **번호 체계가 아니라 문자 체계**이므로 무번호 선례를 적용하지 않았다.
- **카테고리 20 신설 절 = 무번호 `###`** — 카테고리 20은 하위가 **전부 무번호 `###`**임을 `^###` 전수로 확인했고(「negative control은 `python3 -B`로 실행」 · 「Squash 머지된 브랜치는 …」 등), **가장 최근 신설 절이 「### 5/17 종료 시점 액션」 바로 앞에 놓인 선례**를 따라 같은 자리에 삽입했다(학습 16). ⚠️ **번호 체계가 있는 카테고리(7 · 27 · 30 · 33)에는 이 무번호 선례를 적용하지 않았다.**
- **30.9는 신설하지 않았다** — 「301건 미결」이 **이미 등재된 자리**에 **부분 해소 블록을 append**하는 것이 기존 컨벤션(미결은 등재 자리에서 해소)이라 **새 절 번호를 만들지 않았다**.

### 편집 건별 (전건 `count == 1` assert 통과, 라인 번호 0건 사용 — 물리 편집 지점 14곳)

| E# | 앵커(문구) | 방식 | 반영 위치 | 근거유형 |
|---|---|---|---|---|
| E1a | 「회귀 테스트가 실 API를 호출했다 → 무죄 (실측)」 | **취소선** + 뒤집힘 병기 | 30.9 반증 가설 ① | 실측(콘솔 대조) + 근거유형 오표기 정정 |
| E1b | 「원인 추정을 적지 않는다.」 | **append**(삭제 0) | 30.9 | 실측 |
| E1c | 「보안 이슈 가능성을 배제하지 않았다」 | **append**(삭제 0) | 30.9 | 실측(범위 한정) |
| E1d | 「### 30.10」 직전 | **신규 블록 삽입** | 30.9 부분 해소 블록 | 실측 / 실측+논증 / 논증+git / 문서 인용 / 정황(분리 표기) |
| E2 | 「Ran 104 tests」 포함 현재값 | **취소선 + 새 현재값** | 7.5(i) | 실측 + 문서 인용 |
| E3 | 「인터폰 노이즈 CER 6.49%」 | **부분 취소선**(「인터폰 노이즈」만) + 정정 서술 | 카테고리 7 머리 | 문서 인용(웹 원문 재확인) |
| E4 | 7.7 「관련」 줄 직전 | **신설 하위 (m)** | 7.7(m) | 실측 |
| E5 | 「첫 어절 계세요? 누락"이 재현되지 않았다」 | **append**(본문 무변경) | 7.7(h) | 실측 2건 + 누적(단정 금지) |
| E6 | 「터널 미기동이 대시보드에서도 사진을 죽인다」 | **append**(★ 취소선 금지) | 7.4 (d) 내 미결 | 실측 |
| E7 | 「1차 텍스트 알림 2행 「모바일에서 확인해 주세요.」의 출처」 | **append** | 7.5(f) | 실측 화면 catch(확정 금지) |
| E8 | 「대시보드 탭이 **백그라운드**」 | **append**(미결 유지) | 8.5(d) | 실측 1회(단정 금지) |
| E9 | 「inter = C(4,2)」 | **현재값 주석 병기**(★ 07-09 항목 취소선 금지) | 5.1 09-03 구성 항목 | 산술 + 프로젝트 지침 인용 |
| E10 | 「### 5/17 종료 시점 액션」 직전 | **신설 무번호 `###`** | 카테고리 20 | 실측(원칙만, 사례는 30.9 단일 등재) |
| E11 | 27.8(k) 마지막 줄 | **신설 하위 (l)** | 27.8(l) | 실측 + 실물 대조 |

### 등재 내용 요약

- **🔴 30.9 부분 해소 (E1)** — **원인 체인 규명**: `config.py`의 `load_dotenv` → `Config` 본문이 NCP 실값 적재 → `_TestConfig`가 **카카오 4항목만** 덮고 **NCP 2항목 미덮음** → `stt.is_real_mode()` True → `/enrich` 경로 **9개 테스트**가 실 CSR 호출 → 결과가 **`None` 자막으로 흡수**돼 **`Ran 104 tests` OK인 채로 누출**. **대조 실험(서버·터널·대시보드 전부 종료, LISTEN 0 · cloudflared 0)** 으로 **스위트 1회 = 실 CSR 12건 = +180초**를 **n=2 재현**했고, **정적 추적 12 = 가드 기록 12 = 콘솔 +12**로 세 경로가 일치했다. **발생 시점** = PR #44(09-05) 작성 테스트가 **PR #45(09-08)의 NCP 키 · real 분기 추가로 코드 변경 0줄로 실 호출자 전환**. **수정 = PR #62 `bc0df74`**(테스트 1파일, **제품 코드 0줄**) A 자격증명 격리 + B 조용하지 않은 소켓 가드, **NC 3종** 등재. ★ **미결 제목 취소선 금지** — **09-08 301건(34/267)은 12의 배수가 아니라 미조사 잔존**이다.
- **🔴 카테고리 7 CER 근거 정정 (E3)** — 「인터폰 노이즈」는 **우리가 붙인 해석**이었고, **6.49%는 벤치마크의 「저음질 전화망」 열 × 「Naver ClovaSpeech」 행**이다. **CLOVA Speech는 NCP 문서상 CSR과 별개 서비스** ⇒ **우리 엔진의 수치가 아니다.** 같은 열 **Google api v2 14.11%**(첫 등재) · **리턴제로 4.40%**(⚠️ 벤치마크 작성사가 곧 상위 업체). **결정은 바꾸지 않았다.**
- **7.7(m) 신설 (E4)** — CSR 소규모 실측 **10건**, `app.stt.transcribe()` **직접 호출**(재시도 0 · 서버 · 카카오 미경유). 원 집계 **12/130 = 9.23%** → **학부생 청취 정정**(4번 「하하하」 = 실제 웃음 = 대본 이탈) → **9/133 = 6.77%**, 완전 일치 **7/10**, RTT **0.75~1.11초**. ⚠️ **6.49%와 병치 금지**(엔진 · 데이터 · 규모 전부 다름).
- **7.4 리허설 실측 (E6)** — 터널 관통 401 · 실모델(RSS **462,272 KB** / TF 매핑 **54**) · `/detect` P1 미발송 / P2 발송 · `/enrich` **200** · curl 왕복 **2.29초** · 카톡 3건(1차 → 사진 카드 → 자막, `transcript` 완전 일치) · 대시보드 양축 정상 · `/captures` GET **2회**로 **소비처 2개 실물 확인**. ★ **미결 취소선 금지**(리허설 1회 통과 ≠ 발표 당일 체크리스트 해소).
- **7.5(i) 현재값 104 → 106 (E2)** · **7.7(h) 첫 어절 누적 (E5)** · **7.5(f) 2행 문구 2차 부착 관측 (E7)** · **8.5(d) 60초 판정 방법 실행 (E8)** · **5.1 쌍 구성 현재값 (E9)** · **카테고리 20 방법론 3원칙 (E10)** · **27.8(l) AI catch 6건 (E11)**.

### 🔴 사용자 판단 대기 항목 — 등재하되 방향 미확정 (전건 명시 확인)

1. **CSR 유지 결정의 재검토 여부** — E3로 근거 하나가 약해졌으나 **결정 자체는 무변경**이며, 재검토 여부는 사용자 판단이다.
2. **발표 문구(CER 수치를 어떻게 적을지)** — 사용자 방침 = **발표 문구는 개발 종료 후 결정**. 본 Set은 **문구를 제안하지 않았다**.
3. **27.8(d) 누적 숫자 합산 여부** — (i)에 등재된 대기 항목, **무변경**.
4. **카테고리 20 「원격은 GitHub 자동 삭제로 이미 깨끗했다」 서술의 정정 여부** — 27.8(l)④가 **충돌 사실만 등재**했고 **그 절 본문은 무변경**이다(범위 밖).
5. **09-08 301건 구성의 추가 조사 착수 여부** — **잔존 미결**로만 적었고 조사 방법을 확정하지 않았다.

**SSoT 정합 검증 (문서 전용이라 코드 3단계 ①②는 무관)**: ① 빌드 · ② 테스트는 **코드 0줄 변경이라 무관**하며(`git diff --name-only` = `docs/` 2파일), ③ **오류 방지**는 아래로 대체했다. **V1 취소선** = 착수 전 **80줄 / 188개** → 종료 **82줄 / 194개**(계수 단위 = `grep -c '~~'` **줄 수** / `grep -o '~~' | wc -l` **출현 수**). 증가분 **+2줄 / +6개 = 신규 취소선 3쌍**(E1a · E2 · E3)으로 **설계와 정확히 일치**하고 **194 = 짝수 = 마크다운 무파손**이다(E2 · E3가 같은 줄 안에서 늘지 않아 줄 수 증가는 2다). **V2 삭제 0줄 증명** = `git diff --numstat` **97 insertions / 5 deletions**이며, 제거 **5줄**의 토큰이 추가분에 **원시 기준 미보존 1종** · **정규화 기준 미보존 1종**이고 그 1종은 **동일 건**이다 — `아니다)).` 는 E2에서 원문 끝에 `~~`가 붙으며 **문장 끝 마침표만 새 문장 끝으로 이동**한 **경계 artifact**로, 실물 `아니다))~~` 를 `grep -cF` **1건**으로 확인했고 취소선 블록(**515자**) 안에 **중첩 `~~` 0개**로 104 원문이 **전문 보존**됐다. **V3 앵커** = 편집 전 **A1~A13 전건 == 1**, 편집 후 **물리 지점 14곳 전건 `count == 1` 재독 출력**. **V4 한글 전수 검증** = (a) 추가분의 **신규 한글 단어를 문맥과 함께 전건 출력**, (b) **신규 음절 목록 출력 + 「기존 음절로의 치환은 통과하므로 충분조건 아님」 명시**, (c) **`U+FFFD` 0건** · latin1 범위 문자는 **`§ ± · ¼ × ÷` 6종뿐으로 전부 기존 정상 기호**(모지바케 0), (d) **14곳 실물 되읽기**. **V5** = §5의 모든 수치를 로그 4종과 **1:1 대조**해 **불일치 0건**(C6의 「가드 없이 / 0.242초 / 15:15」 3건은 **로그 부재 + PR 본문과 상충**이라 **미기재**). **V6** = `git status --short` 가 **`docs/` 2파일만**.

**비범위**: **코드 0 수정** — `server/` · `dashboard/` · `firmware/` · `ml/` 이하 전부 무접촉이며 `docs/git-convention.md`도 **무접촉**이다. **노션 무접촉**(Set 3 소관), **프로젝트 지침 파일 무접촉**(**Set 2 소관**), **repo 공개 여부 관련 서술 무접촉**(`decisions.md` 「private」 **0건** 확인 — Set 2 소관), **발표 통계(청각장애 인구 등) 무접촉**(지침 전용). 🔴 **결정 · 정책 · 수치 · 방향 신설 0건** — CSR 유지 결정 **무변경**, 발표 문구 **미작성**, 27.8(d) 누적 숫자 **무변경**, 8.1 「3초 주기」 **무변경**, 8.5(d) 미결 **유지**, 7.4 미결 **유지**, 5.1 07-09 항목 **무변경**, 카테고리 20 「Squash 머지」 절 본문 **무변경**. **첫 어절 누락 원인 · 12의 배수 정황 · 60초 원인은 전부 「원인 확정 아님」으로 표기**했다. **PR 없음** — `docs/*.md` 단독이라 **main 직 push**(카테고리 20 「문서/코드 변경 push 분리」). **코드 실행 0건**(서버 · 테스트 · 스위트 **미실행** — 106은 PR 본문 + 정적 대조로 판정). **시크릿 0건**(토큰 · 키 · 터널 주소 · 이메일 · 학번 미기재, 터널 주소는 로그에도 원래 미기록). **미착수** = 09-08 301건 구성 조사 / 현관 1m · INMP441 · 인터폰 잡음 · 다른 화자 · 자연 발화 인식률 / 2차 모바일 렌더 캡처 / `notifications` 주기당 2회의 출처 / repo 「Automatically delete head branches」 설정 확인.

**학습 적용**: **학습 13**(출처 catch — 앵커 **전건 실물 grep 후 인용**, **라인 번호를 편집 앵커 · 본문 모두 0건 사용**, 수치는 **계수 단위와 함께** 표기. 🔴 `[신규 미결]`이 **BRE 문자 클래스로 해석**돼 2,260줄을 뱉은 것을 **`grep -cF`로 정정**했고, 「무죄 (실측)」 · 「모바일에서 확인해 주세요.」 **2건짜리 앵커 2개를 전문으로 넓혀** == 1로 만들었다) / **학습 16**(기존 컨벤션 우선 — `decisions-log.md` 헤더 · 섹션 골격을 **실물에서 그대로 따왔고**, 7.7 · 27.8의 **문자 체계**와 카테고리 20의 **무번호 `###` + 「5/17 종료 시점 액션」 앞 삽입 선례**를 발명 없이 재사용했으며, 현재값 갱신은 **「직전 현재값 취소선 + 새 값」 기존 패턴**을 그대로 따랐다) / **학습 17**(위임 본문도 catch 대상 — 🔴 **위임 E1의 「가드 없이 / 0.242초 / 15:15 확인」이 로그 4종에 없고 PR #62 본문의 「전부 가드 아래」와 상충**함을 catch해 **옮기지 않고 로그 · PR 본문 실물로 대체 서술**했다. 그 자체를 **27.8(l)③의 위임 자기모순 계열**과 같은 축으로 본다) / **학습 19**(근본원인 재검증 — 기존 판정의 **근거유형까지 재확인**했다: 30.9 반증 가설 ①은 **결론만 틀린 게 아니라 「(실측)」이라는 근거유형 표기 자체가 틀렸고**, 그 판정이 **T절 테스트에만 성립하는 범위 한정 판정**이었음을 함께 등재했다. 카테고리 20 원칙 3으로 일반화) / **학습 21**(미결 5분류 · **역방향 날조 금지** — 🔴 **해소된 것을 미결로 되살리지 않았고**, 반대로 **미결을 해소로 과잉 판정하지도 않았다**: 30.9는 **「부분 해소 + 제목 유지」**, 7.4는 **「실측 기록 append + 미결 유지」**, 8.5(d)는 **「가설 일치 + 미결 유지」**, 5.1 07-09 항목은 **「이력이라 취소선 금지」**로 **네 건 모두 보수적으로 처리**했다) / **27.8(f-2) 계열**(측정 시점값 — 취소선 총수 · `npx skills search` 반환 건수 · 콘솔 그래프 판독분 · Chrome 폴링 간격을 전부 **그 호출/세션의 시점값**으로 표기) / **「실측 / 논증 / 문서 인용 / 정황 분리」**(30.9 블록에서 **콘솔 · 대조 실험 = 실측** / **원인 체인 = 실측+논증** / **발생 시점 = 논증+git** / **NC 3종 = 문서 인용(PR 본문)** / **12의 배수 = 정황, 원인 확정 아님** / **429 해석 = 논증**으로 **한 문장에 섞지 않았다**) / **「발견일 ≠ 반영일」**(본 Set 등재분 **전건 발견 = 반영 = 2026-09-16**이며 양쪽 다 표기, 커밋이 자정을 넘기지 않음을 확인) / **「현재값 vs 이력」**(7.5(i) 누적은 **현재값이라 갱신**, 각 절의 「기존 N → M」과 5.1 07-09 「1쌍 + 5쌍」은 **이력이라 무변경**) / **「압축 손실」**(E3가 **압축 손실 그 자체의 사례**다 — 열 · 엔진이 탈락한 요약이 근거로 굳었고, 본 Set은 **콘솔 일별 값을 합계로 뭉개지 않고 날짜별 `success` / `failed` / `usage` 원소별**로, **툴팁 값과 그래프 판독분의 근거 등급을 갈라** 적었다).

**관련 카테고리**: **30.9 (🔴 CSR 301건 미결 부분 해소 — 원인 체인 · 대조 실험 · PR #62 수정 · NC 3종 · 잔존 09-08 구성)** / **카테고리 7 머리 (CER 6.49% 근거 정정 — 「인터폰 노이즈」 취소선 · CLOVA Speech vs CSR · 14.11% 첫 등재)** / **7.7(m) (CSR 소규모 인식률 실측 신설)** / 7.7(h) (첫 어절 누락 누적 — 본문 무변경) / 7.7(j) (「실 육성 인식률 미검증」의 범위가 근접 조건 소규모까지 좁혀짐) / 7.5(i) (서버 회귀 누적 **104 → 106**) / 7.5(f) (2행 문구 2차 부착 관측 — 확정 금지) / **7.4 (2차 체인 리허설 실측 — 미결 유지)** / 8.5(d) (60초 = 백그라운드 스로틀 가설과 일치 — 미결 유지) / 5.1 (4유닛 쌍 구성 현재값 · 지침 11항 근거 첫 등재) / **카테고리 20 (「조용한 가드 금지 · 결과만 보는 검증 · 코드 읽기 ≠ 호출 수 실측」 신설 · 무번호 `###`)** / **27.8(l) (AI catch 사례 6건 신설)** / 27.8(d)(i) (누적 숫자 무변경 — 사용자 판단 대기) / 카테고리 21 (`.env` `>>` 키 중복 **3줄**로 누적 — 미결 연동) / 학습 19 · 학습 21 (근거유형 재검증 · 부분 해소의 보수적 표기)
**관련 commit**: `bc0df74`(PR #62 squash — 회귀 테스트 실 CSR 누출 차단, 브랜치 `eb06be3`) — **본 세션 머지분이며 원격 브랜치는 머지 8분 뒤 수동 삭제**(27.8(l)④). 문서 반영 = 본 Set 1 커밋(docs-only, **PR 없음, main 직 push**). 선행 = `bc0df74`(착수 시점 HEAD).

## 2026-09-16 (수) 후속 — PoC-(50) Set 1 후속 — PR #62 가드 없는 합격 시험 등재(30.9 · 7.5(i)) + 「원격 자동 삭제」 서술 병기(카테고리 20, 취소선 없음) + 27.8(l) 누락 경위 ⑦ ⑧ 등재 (카테고리 20/27.8/7.5/30.9)

같은 날 Set 1(`519d802`)이 **근거 로그 부재로 옮기지 못한 실측 1건**을 사후 로그 확보 후 등재하고, Set 1이 **사용자 판단 대기로 올린 충돌 서술 1건**을 사용자 방침대로 **병기**로 처리한 후속 세션이다. 축은 **둘** — ① **PR #62 수정 코드의 「외부 가드 없는 합격 시험」 실측**(30.9 부분 해소 블록 · 7.5(i) 근거 보강), ② **카테고리 20 「원격은 GitHub 자동 삭제로 이미 깨끗했다」의 처리 결정**(★ **09-09 당시 사실이므로 취소선 없이 오늘 사실만 병기**). 덧붙여 **누락이 난 경위 자체를 27.8(l)⑦ · ⑧으로 등재**했다. 문서 2파일만 수정, 코드 실행 0건, main 직 push.

**Step 0 가정 대조 — D1 · D3 · D4 O, D2 부분 불일치 1건(정지 임계 2건 미만 → 착수)**: HEAD **`519d802`** · 브랜치 `main` · 워킹트리 clean(D1 O). 앵커 B1 **「14:53 확인 = 」** `grep -cF` **1** · B2 **「측정 시점 워킹트리 = 」** **1** · B4 **「head_ref_deleted」** **1**로 통과했으나, **B3 「원격은 GitHub 자동 삭제로 이미 깨끗」은 2건**이었다 — 하나는 카테고리 20 본문, 다른 하나는 **27.8(l)④가 그 서술을 인용한 것**이다. §4 규칙대로 **앵커를 넓혀**(뒤따르는 `` `git ls-remote origin | grep -v refs/pull/` `` 구절까지 포함) **== 1**로 확정했다. 로그 `pr62_postfix_unguarded_run.log`는 실존하며 위임 §5 D3의 수치 **전건 일치**(D3 O). `decisions.md`에 **「0.242」 0건 · 「15:15」 0건**으로 **미등재 사실을 확인**했다(D4 O). D5 = 27.8(l)의 하위 기호 체계는 **①~⑥ 원문자**이고 **마지막 하위는 ⚠️ 무기호 주석 줄**(「(d)의 누적 숫자는 본 항에서도 건드리지 않았다」)임을 실물로 확인해, 신규 **⑦ · ⑧을 ⑥ 뒤 · ⚠️ 주석 앞**에 넣었다.

🔴 **Set 1의 미기재 사유는 오판이었고, 절차는 옳았다 — 둘을 분리해 등재했다**: Set 1은 위 수치를 *"PR #62 본문 「스위트 실행 총 6회 … 전부 가드 아래」와 정면 상충"*이라며 옮기지 않았다. **로그에 없는 수치를 옮기지 않은 절차는 옳다**(학습 13). 다만 **「상충」이라는 사유는 틀렸다** — PR 본문의 **6회는 PR 작성 세션(MCP) 자신의 실행**이고, **학부생의 가드 없는 실행은 그 이후(15:10)**라 **상충이 아니라 별개 실행**이다. ⇒ **27.8(l)⑧**로 등재했고, 교훈은 **「상충」 판정 전에 두 서술의 실행 주체 · 시점부터 대조**다.

🔴 **사후 로그는 「사후 기록」임을 문서에 명시했다**: 근거 로그는 **실행 직후가 아니라 Set 1 누락 발견 후 대화 기록에서 옮겨 적은 것**이다. 근거유형을 **실측**으로 유지하되 **[사후 기록]임을 30.9 · 7.5(i) 양쪽에 병기**했고, **발견일 = 반영일 = 2026-09-16 / 실측 시각 = 15:10**을 함께 적었다. 누락 경위(대화형 실측에 heredoc 로그를 지시하지 않음)는 **27.8(l)⑦**.

**find-skills**: `npx skills search "markdown edit verification"` → **0건**. 0건이라 위임 §1대로 **대조 질의 `flask`를 실행해 25건**을 받아 **도구 생존을 확인**했다(`celery` · `flask` 등, 전부 `★ 0 · 0 installs · by undefined`). **채택 0건** — 사유 **③ 0건**. `npx skills`에 `find` · `use` 하위 명령은 없다.

### 편집 건별 (전건 `count == 1` assert 통과, 라인 번호 0건 사용 — 물리 편집 지점 6곳)

| F# | 앵커 (실물 문구) | 방식 | 반영 위치 | 근거유형 |
|---|---|---|---|---|
| F1 | 「14:53 확인 = 」 (가드 실행 후 콘솔 무변동 줄) | append (신규 최상위 항목 + 하위 6줄) | 30.9 부분 해소 블록 | 실측 (사후 로그) |
| F2 | 「측정 시점 워킹트리 = 」 + 「상세 = 30.9 부분 해소 블록.」 | 기존 서술 무변경 + 근거 보강 append | 7.5(i) 106 케이스 현재값 | 실측 (사후 로그) |
| F3a | 「원격은 GitHub 자동 삭제로 이미 깨끗」 + `git ls-remote` 구절 | ★ **취소선 없이 병기** (하위 항목 신설) | 카테고리 20 「Squash 머지된 브랜치는 `git branch -d`가 거부한다」 절 | 실측 (타임라인) + 방침 |
| F3b | 「그 서술의 정정 여부는 본 Set 범위 밖 … 충돌 사실만 등재한다.」 | **취소선 + 처리 결과 병기** | 27.8(l)④ | 사용자 방침 2026-09-16 |
| F4 | 27.8(l) 말미 ⚠️ 주석 줄 (「(d)의 누적 숫자는 …」) | 하위 **⑦ · ⑧ 신설** (⑥ 뒤 · ⚠️ 앞) | 27.8(l) | 실측 + 실물 대조 |
| F4′ | 「(l) PoC-(50) AI catch 사례 6건」 | **현재값 취소선 + 갱신** (6건 → 8건) | 27.8(l) 머리 | 산술 (계수 단위 = catch 사례 건수) |

⚠️ **F4′는 위임에 없는 파생 편집**이다 — ⑦ · ⑧을 넣으면 머리의 **「6건」이 실물과 어긋나므로** SSoT의 **현재값 갱신 컨벤션(직전 값 취소선 + 새 값)**을 그대로 적용했다. **숫자만 갱신**했고 **(d)의 누적 숫자는 여전히 건드리지 않았다**(합산 여부가 27.8(i)에 **사용자 판단 대기**).

### 등재 내용 요약

- **30.9 부분 해소 블록** — PR 브랜치 `eb06be3`에서 **외부 가드 없이**(`PYTHONPATH` 미지정 = `/tmp/netguard` 미적용 · 프록시 env 미지정 · 서버 · 터널 · 대시보드 종료 유지) 스위트 **1회**: **15:10:12~13 `Ran 106 tests in 0.242s` OK**, 콘솔 **15:09 = 25 / 0 / 375초 → 15:15 = 25 / 0 / 375초(변동 0)** ⇒ **수정 코드는 외부 가드 없이도 실 CSR 호출 0건(n=1)**. ⚠️ 콘솔은 **일 단위 집계**라 **직전값 대비 무변동으로 판정**한 것이다. **스위트 시간 2.158초(104) → 0.242초(106)는 참고치이며 판정 근거가 아니다**(27.8(l)② 「판정은 관측 장치로만」). **머지 후 `main` `bc0df74` 재실행은 하지 않았고** 테스트 파일 동일성(`git diff --quiet`)으로 갈음했다.
- **7.5(i)** — 기존 근거(**PR #62 본문 인용 + 정적 대조 107 − 1 = 106**)를 **그대로 보존**한 채 **가드 없는 실행 실측 1줄만 덧붙였다**.
- **카테고리 20** — ★ **09-09 서술에 취소선을 긋지 않았다**(그날의 실물이다). 병기 내용 = **09-16 PR #62는 머지 후 원격 브랜치 잔존 → 학부생이 PR 화면에서 수동 삭제**(`head_ref_deleted` **`06:26:03Z`** = 15:26 KST), **repo 설정(Automatically delete head branches) 상태는 미확인**(확인하지 않기로 함)이라 **「자동 삭제된다」를 전제로 두지 않는다**, 운영 = **머지 후 `git ls-remote origin | grep -v refs/pull/` 확인 · 남아 있으면 PR 화면에서 삭제**.
- **27.8(l)⑦** — **Claude 로그 누락**: 대화형 실측(가드 없는 합격 시험 · 콘솔 확인)을 **heredoc 로그로 남기라고 지시하지 않아** Set 1이 등재하지 못했다. ⇒ ★ **실측은 실행 직후 로그로 굳힌다 — 채팅 기록은 다음 세션으로 넘어가지 않는다.**
- **27.8(l)⑧** — **MCP 사유 오판**: 절차는 옳았으나 **「상충」 판정이 틀렸다**(실행 주체 · 시점 미대조).

### SSoT 정합 검증

- **V1 취소선** — `decisions.md` 착수 전 **82줄 / 194개** → 종료 **84줄 / 198개**. **+4 = 신규 2쌍**(F3b 1쌍 · F4′ 1쌍) = 설계 일치, **198 = 짝수**. `decisions-log.md`는 본 엔트리에서 취소선 마커를 **0쌍 추가**했고 총 **66쌍 · 짝수**를 유지한다(⚠️ 본 줄이 마커를 그대로 적으면 그 자체가 계수에 잡히므로 **문자로 적지 않는다** — 2026-09-16 후속 세션 catch).
- **V2 삭제 0줄 증명** — `git diff --numstat` = `decisions.md` **13 / 3**, `decisions-log.md` **50 / 0**(순수 append). 제거 3줄은 전부 **같은 줄의 치환 결과**이며, 마커 제거 정규화 · 원시 분리 양쪽에서 **미보존 토큰 0종**이다(F2 · F3b · F4′는 append형 치환, F3a는 인접 줄 삽입).
- **V3 편집 지점 6곳 실물 되읽기** — 전건 `count == 1` 재확인.
- **V4 🔴 한글 전수** — 추가분 중 편집 전 파일에 없던 한글 단어를 **문맥과 함께 전건 출력**했다(`decisions.md` **30개** · `decisions-log.md` **98개**, 전부 정상 문맥). **신규 음절은 두 파일 모두 0종**이다 — 새 서술이 **기존 어휘 범위 안에서 쓰였다는 뜻**이지 무결의 증거가 아니다. ⚠️ **기존 음절로의 치환은 이 검사를 통과하므로 신규 음절 스캔은 충분조건이 아니다** — 단어 단위 문맥 출력과 물리 지점 되읽기로 보완했다. 두 파일 **U+FFFD 0건**, latin1 범위는 **기존 정상 기호뿐**.
- **V5 수치 1:1 대조** — F1 · F2의 전 수치(`eb06be3` · 15:10:12~13 · `Ran 106 tests in 0.242s` · 15:09 / 15:15 = 25 / 0 / 375초 · 2.158초 · `06:26:03Z`)를 `pr62_postfix_unguarded_run.log`에 **1:1 추적, 불일치 0건**. 로그에 없는 수치는 **0건 기재**.
- **V6 git status** — `docs/` **2파일만**. 시크릿 스캔(터널 주소 · NCP 자격증명 · 메일 주소 · 토큰 패턴) **실제 검출 0건**(⚠️ 유일한 정규식 히트는 **본 검증 문장 자신**이었다 — 스캔 대상에 보고서를 포함시키면 **자기 기술이 히트로 잡힌다**).

**비범위**: 코드 · 테스트 파일 전부(코드 실행 0건 — `main` `bc0df74` 재실행도 하지 않았다) / repo 설정 `Automatically delete head branches` **확인하지 않음**(사용자 방침) / 27.8(d)의 누적 숫자 **무변경**(사용자 판단 대기 유지) / 발표 자료 · Notion / 카테고리 7 · 7.7(m) · 7.4 · 8.5(d) 등 Set 1 등재분 **재손질 0건**.

**학습 적용**: **학습 13**(앵커 **전건 실물 `grep -cF` 후 인용**, **라인 번호 0건 사용**, B3가 2건이라 **넓혀서 == 1** 확정, 수치는 **계수 단위와 함께**). **학습 16**(decisions-log 형식은 **직전 엔트리 실물 그대로**, 27.8 하위는 **문자 체계 + 원문자 하위**라는 실물 체계를 따르고, 현재값 갱신은 **직전 값 취소선 + 새 값** 컨벤션 재사용). **학습 17**(위임 본문도 catch 대상 — 위임이 지목한 B3가 실제로는 **2건**이었고, **F4′ 파생 편집 필요**는 위임에 없어 실물 대조로 찾아냈다). **학습 21**(★ **해소된 것을 미결로, 미결을 해소로 날조하지 않았다** — 30.9는 **여전히 부분 해소이며 제목 · 🔴 잔존(09-08 301건 · 09-10 · 09-11 실행자 미기록)은 그대로**이고, 카테고리 20의 09-09 서술은 **당시 사실이라 취소선 대상이 아니다**).

**관련 카테고리**: **30.9 (PR #62 수정 코드의 가드 없는 합격 시험 실측 추가 — 부분 해소 상태 · 🔴 잔존 무변경)** / **7.5(i) (106 케이스 현재값 근거 보강 — 숫자 무변경)** / **카테고리 20 (「원격 자동 삭제」 서술 병기 — ★ 취소선 없음, 09-09 실물 보존)** / **27.8(l) (⑦ 로그 누락 · ⑧ 사유 오판 신설 · 머리 6건 → 8건)** / 27.8(d)(i) (누적 숫자 무변경 — 사용자 판단 대기) / 학습 13 · 16 · 17 · 21.

**관련 commit**: 선행 = `519d802`(2026-09-16 PoC-(50) Set 1, 착수 시점 HEAD) · `bc0df74`(PR #62 squash — 본 실측의 대상 코드). 문서 반영 = 본 Set 1 후속 커밋(docs-only, **PR 없음, main 직 push**).


## 2026-09-17 (목) — PoC-(51) Set 1 — 🔴 CSR 301건 잔존분 조사 종료·30.9 「기록 없음」 2건 정정 + 포렌식 5채널 방법론 등재(카테고리 20) + 웹 음원 조사 신설(5.2)·파일럿 신설(33.6(g)) + 보드 2차 체인 설계 조사 신설(6.5)·7.7(l) 성분 3/4 재추적 + 카테고리 5 sample_weight 미구현 정정 (카테고리 5/6/6.2/6.3/7.5/7.6/7.7/20/27.8/30.1/30.9/33.6/33.8)

같은 날 돌린 **조사 위임 4건**(웹 음원 조사 · 301건 포렌식 + 후속 · 웹 음원 파일럿 · `/enrich` 펌웨어 설계)의 산출을 SSoT로 옮긴 세션이다. 축은 **넷** — ① **301건 미결의 잔존분 조사 종료**(30.9에 「실행 기록 자체는 없다」 · 「09-10 · 09-11 기록 없음」 **2건 취소선 정정** + 잔존분 조사 블록 + 감시 기준점) ② **웹 음원 두 축 신설**(조사 = **5.2** / 실물 파일럿 = **33.6(g)**) ③ **보드 2차 체인 설계 조사 신설(6.5)** 과 그것이 건드리는 기존 미결 3건의 **재판정 입력**(7.7(l) · 7.6(i) · 카테고리 6 2워커) ④ **방법론 등재**(카테고리 20 「포렌식 실행 채널 5개」). 문서 2파일만 수정, **코드 0줄 · 보드 무접촉 · 실 API 호출 0**, main 직 push.

**Step 0 가정 대조 — 가정 1 · 2 O, [확인 대상] 5건 전건 확인**: HEAD **`41cd6e2`** · 브랜치 `main` · `git status --short` 빈 출력 · **원격 브랜치 `refs/heads/main` 단일**(`git ls-remote origin` — 학습 20, `git branch -r` 미사용) · 열린 PR 0(가정 1 O). 입력 자료 **8종 전건 실존**(가정 2 O). 가정 3 = 카테고리 33의 마지막 절은 **33.8**, 33.6의 마지막 하위는 **(f)**, 카테고리 5의 마지막 절은 **5.1**, 카테고리 6의 마지막 절은 **6.4**임을 `git show HEAD:docs/decisions.md | grep -nE "^## 카테고리|^### "`로 확인. 가정 4 = `decisions-log.md` 마지막 엔트리(2026-09-16 후속)의 헤더·섹션 골격을 **실물 그대로** 따랐다. 가정 5 = 30.9의 **「09-10 · 09-11에 누가 스위트를 돌렸는지도 문서에 기록이 없다」 · 「누가 몇 회 돌렸는지의 실행 기록 자체는 없다」 2건 모두 실존**(마커를 걷어낸 부분 문자열로도 재조회) ⇒ **취소선 정정 성립**. 가정 7 = 「사용자 판단 대기」 **25건** · 「[신규 미결]」 **24건**(착수 전 실측, 계수 단위 = 매치 줄 수).

**★ 위임 본문 catch 2건 (학습 17)**: ① 위임이 **「후속 포렌식 리포트의 SSoT 반영 제안 ③은 기각」**이라 지시했고, `grep`으로 **30.9와 27.8(l)①이 이미 「S절 `_run_enrich` 9개 케이스가 누출」로 적고 있음**을 확인한 뒤 **기각을 그대로 적용**했다 — 유효 추가분 **「12 = 단건 8 + 루프 4」**만 등재했다(등재 = **27.8(m)③**). ② 위임이 **「≤80B의 SSoT는 6.3(h)·6.3(j)이며 6.3(m)이 아니다」**라 지시했고, `decisions.md` 전수 grep 결과 **6.3(m)을 ≤80B 출처로 지목한 서술은 0건**이었다 ⇒ **취소선 대상 부재**이므로 **신규 등재로 pivot**했다(27.8(m)①).

**find-skills**: `npx skills search "decision log markdown"` **0건** / `"korean technical writing"` **0건**(위임 §1이 예고한 대로 2026-09-16 결과와 동일). 0건이라 **대조 질의 `flask` 25건**으로 **도구 생존을 확인**했다. **채택 0건** — 사유 **③ 0건**. `install` · `info` 0회. ⚠️ macOS에 `timeout` 명령이 없어 첫 시도가 실패했고 그대로 재실행했다(2026-09-17 포렌식 세션과 동일 현상).

### 신설 절 번호 · 위치 결정 근거 (위임 일부 미지정 — MCP 판정, 근거유형 = 실측 grep)

- **5.2** — 카테고리 5는 **번호 체계가 있고 마지막이 5.1**이므로 **다음 번호 5.2**를 부여했다. 위치 = 5.1 끝 · 카테고리 6 앞. ★ 위임이 「카테고리 5 계열 신설 또는 해당 절 보강」으로 남긴 선택을 **신설**로 판정한 근거 = 등재 대상이 **유입 요건 · split 파급 · 음량 비대칭 · 웹 재고**로 축이 여럿이라 5.1(저장 정책·실측 배분) 안에 넣으면 **절의 주제가 흐려진다**.
- **6.5 · 6.6** — 카테고리 6의 마지막이 **6.4**(`/detect` ToF wire 확장)이므로 **6.5**(`/enrich` 클라이언트 설계) · **6.6**(`env:camera_probe`)을 차례로 부여했다. ★ 6.3(마이크 M 시리즈) 하위 letter로 넣지 않은 근거 = `camera_probe`는 **카메라 · 마이크 · ToF 세 페리페럴에 걸친 신설 env**라 마이크 절의 하위가 아니고, 6.4가 이미 **wire·체인 축의 독립 절** 선례를 만들었다. ⚠️ 카테고리 6은 **번호 체계가 있는 카테고리**이므로 카테고리 20의 무번호 선례를 적용하지 않았다.
- **33.6(g)** — 33.6의 마지막 하위가 **(f)**이므로 **다음 빈 문자 (g)**. 파일럿은 33.6(a)(f)와 **같은 축(OOD·게이트 발송)의 입력**이라 신설 절이 아니라 하위로 뒀다.
- **27.8(m)** — 27.8의 마지막 하위가 **(l)**이므로 **(m)**. ⚠️ 27.8은 실물 순서가 **(g)가 (f) 앞**인 절이라 **문자 전수 확인 후** 다음 빈 문자를 부여했다.
- **카테고리 20 신설 2절은 무번호** — 카테고리 20은 **번호 체계가 없는 무번호 `###` 소제목** 체계(「관측/판정 계층 PR 단위 분리」 등)이므로 그 선례를 따랐다. 삽입 위치 = 「5/17 종료 시점 액션」 **앞**.

### 편집 건별 (전건 `str.count` == 1 assert 통과, 라인 번호 0건 사용)

| E# | 앵커 (실물 문구) | 방식 | 반영 위치 | 근거유형 |
|---|---|---|---|---|
| E2 | 「**클래스 가중치**: class_weight + sample_weight 1.5~2.0배 (한국 환경음)」 | **취소선 + 정정** | 카테고리 5 머리 | 실측 전수 grep |
| E3 | 「본 항목은 문서 등재만 한다 — 상수 코드 값 변경은 별도 PR 소관」 | 하위 항목 append | 6.2 G29 파급 | 실측 코드 대조 |
| E4 | 「해소 = 위 rate limit Redis 교체와 동일한 11주차 구간.」 | 하위 항목 append | 카테고리 6 머리(2워커 409) | 논증 |
| E6 | 「트리거 = 실 ESP32 2차 클라이언트 연동 후 재판단.」 | 하위 항목 append | 7.6(i) | 논증 |
| E7 | 「12.1초 구성 성분별 실측 근거는 SSoT에서 추적 불가」 | 하위 블록 append | 7.7(l) | 항목별 병기 |
| E8 | 「수치·경계·한계·대응(사용자 판단 대기) = 33.7.」 + 카테고리 6 머리 | **절 신설** | **5.2** | 항목별 병기 |
| E9 | 6.4 「관련」 줄 전문 | **절 신설** | **6.5** | 항목별 병기 |
| E10a | 「이것은 정황이지 원인 확정이 아니다 — 누가 몇 회 돌렸는지의 실행 기록 자체는 없다.」 | **취소선 + 정정** | 30.9 부분 해소 블록 | 실측 |
| E10b | 「09-10 · 09-11에 누가 스위트를 돌렸는지도 문서에 기록이 없다.」 | **취소선 + 정정**(제목 유지 문장은 보존) | 30.9 부분 해소 블록 | 실측 |
| E10c | 「방법론 등재 = 카테고리 20 … 첫 어절 누락 관측 = 7.7(h).」 | 신규 블록 2개 append | 30.9 | 실측 |
| E11 | 「정황 (원인 확정 아님): negative control 절차는 baseline + 변형마다…」 | 원칙 1건 append | 카테고리 20 조용한 가드 절 | 실측 + 논증 |
| E12 | 「### 5/17 종료 시점 액션」 | **무번호 절 신설** | 카테고리 20 | 실측 |
| E14 | 「관련: 33.2(예비 학습 성적 · confusion …)」 | **하위 (g) 신설** | 33.6 | 실측 |
| E15 | 「조건 축을 넓힌 확장 스윕 = (f)」 문장 | 포인터 append | 33.6(a) | 실측 |
| E16 | 「33.8(본 절 재현 수단 = PR #59 하네스)」 | 관련 줄 확장 | 33.6 관련 | — |
| E17 | 「`4`를 `1`과 가른 이유 = 라벨이 어긋나면…」 | 하위 항목 append | 33.8 | 실측 코드 읽기 |
| E18 | 27.8(l) 말미 ⚠️ 주석 줄 | **하위 (m) 신설** | 27.8 | 실측 grep |
| E23 | 「요금제: 무료 (6개월, 200 USD 크레딧) — 유효 기간 ~2026-11-13.」 | **취소선 + 전제 stale 등재** | 30.1 | 사용자 발언 |
| E24 | 「현재 refresh 만료 = 2026-11-10 01:41이며…」 | 하위 항목 append | 7.5(e) | 사용자 발언 + DB 실측 |

### 세션 메모 A~G 1:1 반영 매핑 (누락 0 증명)

| 항목 | 내용 | 등재 절 |
|---|---|---|
| **A** | 일정 변경(발표 11월 · 개발 완료 10월) | **30.1**(AWS 무료 ~2026-11-13 자연 수렴 전제 stale) · **7.5(e)**(refresh 만료 2026-11-10 겹침) — ★ **기술 영향만** 등재, 일정 자체의 SSoT = **지침 계층 소관** |
| **B** | 301건 포렌식 정정(제안 ③ 기각 · 5채널 · 학부생 터미널 후보 · 조사 종료) | **30.9**(취소선 2건 + 잔존분 조사 블록 + 감시 기준점) · **카테고리 20**(5채널) · **27.8(m)③**(제안 ③ 기각) |
| **C** | 웹 음원 파일럿 정정(2초 창 기준 2개 · 음량 축 한계 · 제목 ≠ 실제 소리 · 공유마당 경로 미등재) | **33.6(g)** 전건 |
| **D** | 웹 음원 조사(04 유입 경로 부재 · 짝 없는 파일 수 일치 · 미등재 후보 6건) | **5.2**(a)(f) · **카테고리 5 머리**(sample_weight) |
| **E** | 재학습 방향·순서 초안(Claude 권고, 사용자 확정 전) | **미등재** — 권고를 결정으로 등재하지 않는다(§7). 순서 의존 사실만 **5.2(c)**에 등재 |
| **F** | 사용자 판단 대기 신규·누락분 3건 | 🧪 Spike · 🎨 Style = **카테고리 10에 이미 실등재**(신규 편집 0) / `constants.py` G29 주석 stale = **6.2 G29 파급**에 등재 / 33.6(a) 판단 입력 = **33.6(a)** 포인터 |
| **G** | 로컬 기록의 토큰·키 평문 10건(값 미열람) | **미등재** — repo·외부 경로가 아닌 **로컬 기록 위생 사안**이고 삭제 여부가 **사용자 판단**이라 SSoT 대상이 아니다(§7 시크릿 0 원칙과도 정합) |

### 등재 내용 요약

- **30.9** — ① 「실행 기록 자체는 없다」 · 「09-10 · 09-11 기록 없음」 **2건 취소선 정정**(09-10 **1런 = 12** · 09-11 **3런 = 36**, 콘솔과 정확 일치) ② **09-09 = 21회 × 12 = 252 정확 일치**(서브에이전트 1회 포함 — 직전 방법은 부족 12였다) ③ 🔴 **09-15 = 120(+0~24) vs 168 ⇒ 부족 24~48**이며 후보는 **7.5(i)의 학부생 로컬 `Ran 104 tests` 기록**(셸 히스토리 `unittest` 0건, 대조군 `python3 -m` 11~20건 — **논증**) ④ 🔴 **09-08 = 가시 134~146 + 캡처형 하네스 288~336 ⇒ 범위 134~482에 콘솔 301이 들어가나 배분 불가 = 부분 설명, 미규명 유지** ⑤ **조사 종료 방침** + **감시 기준점**(09-16 = 35 / 0 / 525 · 09-17 = 0 / 0 / 0, `usage = success × 15` 일치). ★ **미결 제목 · 🔴 잔존 표기 무변경.**
- **카테고리 20** — 무번호 절 **「포렌식 실행 채널은 5개다」** 신설(CMD / OUT / INDIRECT / SIDE / 학부생 터미널). 원칙 = **`Ran N tests` 출력 계수는 하한**이고 **부재 판정은 대조군과 함께**다. 사례 본문은 30.9 단일 등재(중복 금지).
- **5.2 신설** — 04 → 01 유입 코드 **0건** / `direct_` 명명이 테이크마다 source를 가름 / 🔴 **공유 `rng`로 doorbell source 1개 추가가 knock 클립 124 / 714를 옮긴다**(baseline 813 전건 일치로 도구 검증 선행) / 학습 peak 0.95 ↔ 서빙 ÷32768 **비대칭(영향 미판정)** / AI Hub 도시 소리에 **초인종 클래스 부재** / 짝 없는 `01_extracted` 파일 수 = 33.7(g) 0바이트 수와 **일치(논증 · 미확정)**. ⚠️ **공유마당 접근 경로 서술 0건**(「CC BY 음원」까지만 — 사용자 방침).
- **33.6(g) 신설** — 65행 중 **`fire_alarm` ≥0.70 발송 23행**, 유형별 = 딩동 2초 창 36 중 **0** / 인터폰 전자음 12 중 **9** / 새소리 12 중 **12**. 🔴 **「5개 중 3개」는 전체 길이 포함 수치이고 2초 창 기준은 2개**다. 창 위치 **0.512초 이동으로 클래스가 뒤집힌다**. 근접 중복 **0.7251**(임계 0.706 초과, 양성 대역 0.9694~0.9872와 0.24 이상 격차 → 배제 후보). 🔴 **대응 방향 = 33.6(a) 그대로 미확정.**
- **6.5 신설** — 🔴 **「녹음 5초」는 결정으로 등재된 적이 없다**(학습 21 역방향) / `/enrich` 계약 실물(필수 form field **`client_request_id` 1개** · **rate limit 없음** · 404 / 409) / **`/detect` 응답의 `enrich_status`로 2차 여부 판별 가능**(새 판정 어휘 0) / 링버퍼 확장은 **1차 wire 계약을 깨므로 기각 후보** / **PR 분할 A · B · C** / **M-4 · M-5는 실측 불가 · 시도 금지**.
- **7.7(l) · 7.6(i) · 카테고리 6(2워커)** — **재판정 입력만** 추가하고 **세 미결 모두 유지**했다. 핵심 = 관계 상수가 `main.cpp`가 아니라 **`UPLINK_HTTP_TIMEOUT_MS`**이고, `setTimeout`은 **무응답 한계**이나 2차에서는 **사실상 총 경과 상한**으로 동작한다는 것.
- **카테고리 5 머리** — `SAMPLE_WEIGHT_RANGE`가 **상수로만 존재하고 소비처 0건**임을 취소선 정정으로 등재. 실제 동작은 sklearn `balanced` 단독. **처리 = 사용자 판단 대기.**
- **33.8** — `gate_axis_sweep`가 **기준 데이터 전용 재현기**라 외부 세트에서 **항상 `1`로 끝난다**는 점과, 그 `1`을 **재현 불일치로 읽으면 오독**이라는 경계를 등재.
- **27.8(m)** — ① ≤80B 인용처(6.3(m) → **6.3(j)**, 취소선 대상 부재 → 신규 등재 pivot) ② `routes.py` 주석의 「카테고리 6.2」 오기 ③ MCP 보고서 제안 ③ 기각.

### 🔴 사용자 판단 대기 항목 — 등재하되 방향 미확정 (전건 명시 확인)

| 항목 | 등재 위치 | 방향 확정 여부 |
|---|---|---|
| 웹 음원 클래스 정의 · 명명 · pitch 대상 · 사용 순서 · split 대안 | 5.2(g) | **미확정 — 신설 등재만** |
| `SAMPLE_WEIGHT_RANGE` 미구현 처리(구현 vs 서술 정정) | 카테고리 5 머리 · 5.2(g) | **미확정 — 사실만 정정** |
| 장치 설치 위치와 마이크가 듣는 소리 (SSoT 미등재) | 5.2(g) | **미등재 사실로만 기록** |
| OOD 수렴 대응(임계 재검토 / 4번째 클래스 / 재학습 / 시연 각본) | 33.6(a) · (f) · **(g)** | **미확정 — 입력만 넓혔다** |
| 데이터셋 중복 · 누수 대응 | 33.7(e) | **미확정 — 무변경** |
| 마이크 SD 비트 오류 해결책 ①②③ | 6.3(n) | **미확정 — 무변경** |
| 녹음 길이 N · pre:post 비율 · 해상도 · 2차 타임아웃 방식과 값 | **6.5(f)** · 6.2 G29 · 7.7(l) | **미확정 — 값 0건 신설** |
| `/detect` skip 시 2차 발송 · `presence=false` 촬영 · `uplink_common` additive · 카메라 init 시점 | **6.5(f)** | **미확정 — 선택지 열거까지만** |
| 과금·실발송 세션 상한(≤12 이벤트 제안) | 6.5(e) | **미확정 — 제안 표기** |
| `model_serving.py` round 수정 여부 · 방식 | 33.6(e) | **미확정 — 무변경** |
| 🧪 Spike · 🎨 Style을 `git-convention.md`에 추가할지 | 카테고리 10 | **미확정 — 이미 등재돼 있어 편집 0** |
| `constants.py` G29 주석 stale 정정 | 6.2 G29 파급 | **기록만 — 코드 무접촉** |
| AWS 무료 기간 · 카카오 refresh 만료와 11월 발표의 겹침 대응 | 30.1 · 7.5(e) | **미확정 — 영향만 등재** |
| 27.8(d) 누적 숫자 합산 여부 | 27.8(i) | **미확정 — (d) · (m) 무변경** |

**SSoT 정합 검증 (문서 전용이라 코드 3단계 ①②는 무관)**: ① 빌드 · ② 테스트는 **코드 0줄 변경이라 무관**하며(`git diff --name-only` = `docs/` 2파일), ③ **오류 방지**는 아래로 대체했다. 편집 앵커 **전건 `str.count` == 1 assert 통과**(패턴 매칭, **라인 번호 0건 사용** — 본 엔트리 본문도 동일 준수). 신설 절 **5.2 · 6.5 · 33.6(g) · 27.8(m)** 은 각 절의 번호·문자 **전수 확인 후 다음 빈 값**을 부여했고 **번호 체계 혼재 0건**이다(카테고리 20만 **무번호 선례**를 따랐다). **취소선 · 토큰 보존 · 한글 전수 검증은 다음 엔트리(2026-09-18)에 두 날짜 합산으로 단일 기재**한다 — 두 날짜를 **한 커밋 쌍으로 같은 작업 세션에서 편집**했기 때문이며, 중간값을 따로 적으면 **측정 시점값이 두 벌이 되어 stale 표면이 늘어난다**(27.8(f-2) 계열).

**비범위**: **코드 0 수정** — `server/` · `dashboard/` · `firmware/` · `ml/` 이하 전부 무접촉이고 `docs/git-convention.md`도 무접촉이다. **노션 무접촉** · **프로젝트 지침 파일 무접촉**(일정 SSoT · 인계 문구 정정 = **Set 2 소관**). 🔴 **공유마당 접근 경로 서술 0건**(repo public — 사용자 방침). 🔴 **사용자 판단 대기 전건 방향 미확정** — 임계값 · 정책 · 수치 · 재학습 방향 신설 **0건**이고 **Claude 권고를 결정으로 등재한 건 0건**이다(세션 메모 E의 재학습 순서 초안은 **제외**). **6.3(n) · 33.6(a) · 33.7 미결 상태 전환 0건.** **부재 G-ID 0건 사용.** **시크릿 0** — SSID · 토큰 · IP(사설 LAN 포함) 실값 **0건 기재**.

**학습 적용**: **학습 13**(인용 전 grep — 편집 앵커 전건 `count == 1`, **라인 번호 0건**. 부재 판정은 전부 대조군과 함께: 6.3(m) ≤80B 지목 **0건** vs 같은 문서의 6.3(m) 다른 용도 매치 생존 / 「스티칭」 `docs/` **0건** vs `AUDIO_MAX_BYTES` 서술 생존 / 셸 히스토리 `unittest` **0건** vs `python3 -m` 11~20건 / `SAMPLE_WEIGHT_RANGE` 소비처 **0건** vs 정의 1건. **압축 손실 방지** — 「5개 중 3개」를 2초 창 2개 / 전체 길이 포함 3개로 **갈라 적었다**) / **학습 14**(repo 구조 가정 검증 — 카테고리 5 · 6 · 33 · 27.8의 마지막 번호·문자를 `git show HEAD:` grep으로 전수 확인한 뒤 신설 값을 정했다) / **학습 17**(위임 본문도 catch 대상 — 위임이 지시한 **제안 ③ 기각**을 grep으로 **먼저 확인**하고 적용했고, 위임이 지목한 **6.3(m) 취소선 대상이 실물에 없어 신규 등재로 pivot**했다) / **학습 19**(근본원인 진단 재검증 — 포렌식 정적 추적기가 **두 판 틀린 사실**을 그대로 등재했고, 「누출 주체가 SSoT와 다르다」는 **보고서 쪽 오판**임을 실물로 기각했다) / **학습 21**(미결 자체가 유령일 수 있다 — 🔴 **역방향 2건**: 「실행 기록이 없다」는 **기록이 있었고**, 「녹음 5초」는 **확정된 적이 없는 값이 확정처럼 유통**되고 있었다. 반대로 **해소된 것을 미결로 날조하지 않았다** — 30.9 제목 · 6.3(n) · 33.6(a) · 33.7은 전부 **유지**) / **「발견일 ≠ 반영일」**(본 Set 신규 등재 전건 **발견 = 반영 = 2026-09-17**이며 양쪽 다 표기) / **「실측 / 논증 / 문서 인용 3분」**(30.9의 채널별 실행 수 · 콘솔 값 = **실측** / 09-15 학부생 터미널 후보 · 09-08 배분 불가 사유 = **논증** / 공유마당 CC BY · Runbook 계층 서술 = **문서 인용**. **한 문장에 섞지 않았다**).

**관련 카테고리**: **30.9 (잔존분 조사 종료 · 취소선 2건 · 감시 기준점 — 부분 해소 상태 · 🔴 잔존 판정만 정밀화)** / **카테고리 20 (포렌식 5채널 무번호 절 신설)** / **5.2 (웹 음원 조사 신설)** / 카테고리 5 머리 (sample_weight 미구현 정정) / **33.6(g) (웹 음원 파일럿 신설)** / 33.6(a) (판단 입력 추가 — 미결 유지) / 33.8 (`gate_axis_sweep` 외부 사용 주의) / **6.5 (보드 2차 체인 설계 조사 신설)** / 6.2 (G29 파급 · `constants.py` 주석 stale) / 카테고리 6 머리 (2워커 409 재판단 입력 — 미결 유지) / 7.6(i) (재판단 입력 — 미결 유지) / **7.7(l) (성분 3/4 재추적 · 상수 주소 정정 — 미결 유지)** / 7.5(e) · 30.1 (11월 발표의 만료 겹침 영향) / **27.8(m) (인용 오기 · 드리프트 신설)** / 27.8(d)(i) (누적 숫자 무변경 — 사용자 판단 대기) / 카테고리 10 (🧪 Spike · 🎨 Style 판단 대기 확인 — 편집 0) / 33.7 (누수 — 순서 의존 포인터, 무변경) / 학습 13 · 14 · 17 · 19 · 21.
**관련 commit**: 선행 = `41cd6e2`(PR #63 squash, 착수 시점 HEAD) · `bc0df74`(PR #62 squash — 본 조사의 대상 코드). 문서 반영 = 본 Set 1 커밋(docs-only, **PR 없음, main 직 push**).


## 2026-09-18 (금) — PoC-(52) Set 1 — PR #63 `env:camera_probe` 방법론 자산 등재 + ④런타임 실측 신설(6.6) + 카테고리 2 카메라 핀 표 신설 + 코어 분배 물리 사실 2건(카테고리 15) + #620 입력 확보(카테고리 17) + 호스트 테스트 4종 → 5종 · env 11개 → 12개 (카테고리 2/6.3/6.5/6.6/15/16/17/20/27.8/32.2)

전날(2026-09-17) 설계 조사가 **PR-A**로 지목한 관측 계층이 **PR #63(`41cd6e2`)으로 실행·머지**됐고, 학부생이 **보드 ④런타임을 완주**했다. 축은 **셋** — ① **신설 절 6.6**(하네스 산출물 + ④런타임 실측 + 카메라 실측 + WiFi 축 무효 함정 + SSID 반출 주의) ② **SSoT 미등재 물리 사실 반영**(카테고리 2 카메라 14핀 · 카테고리 15 `CONFIG_CAMERA_CORE0` · 카테고리 17 #620 · 32.2 JPEG 크기) ③ **현재값 갱신 2건**(호스트 테스트 · env 수) 과 **방법론 등재 2건**(카테고리 20 원칙 4 · 바이너리 md5 무효). 문서 2파일만 수정, **코드 0줄 · 보드 무접촉**, main 직 push.

**Step 0 가정 대조 — 가정 1 · 2 O, [확인 대상] 전건 확인**: 착수 시점 HEAD **`41cd6e2`** · `main` · 워킹트리 clean · 원격 `refs/heads/main` 단일(`git ls-remote origin` — 학습 20). 가정 6 = **카테고리 2 핀 표에 카메라 행이 없다**를 실물로 확인했다(대조군 = 같은 표에 INMP441 **4행** · VL53L5CX **4행** 생존) ⇒ **신설 성립**. 카메라 핀 14개는 `firmware/include/camera_common.h`의 `#define` 블록에서 **직접 읽어** 옮겼다(`PWDN` · `RESET`은 `-1` = 미사용). `CONFIG_CAMERA_CORE0=y` · `CONFIG_SCCB_HARDWARE_I2C_PORT1=y` · `uplinkConnectWifi()`의 SSID 출력은 **설치 sdkconfig · repo 실물에서 각각 재확인**했다(위임 인용을 그대로 옮기지 않았다 — 학습 17).

**🔴 위임 본문 catch — ④런타임 clip 수치가 로그와 달랐다 (학습 17, 계수 단위 = 창 수 / clip 수)**: 위임 §5 Step 4(b)는 조용한 구간 clip을 **「m0 3/3/3 · m1 5,2,4,2,2 · m2 2,2 · m3 2,0 · m4 2」**로 적었으나, `camera_probe_runtime.log` 실물은 **m0(win#6~11) 6창 3~14 · m1(12~19) 8창 2~6 · m2(20~25) 6창 1~6 · m3(26~31) 6창 0~4 · m4(32~37) 6창 1~3**이다 — **창 수와 값이 모두 다르다**(위임 수치는 각 모드 앞부분만 옮긴 **부분 인용**으로 보인다). 위임 §2의 ★ 등재 원칙(**「로그·리포트에 있는 수치만 옮긴다」**)대로 **로그 값을 등재**했다. 같은 축으로 **QVGA 상한**(위임 5,437 → 로그 **5,438**) · **VGA 범위**(위임 13,791~13,846 → 로그 **13,791~13,910**) · **대화 구간 clip**(위임 12~20 → 로그 **4~20**) · **RSSI**(측정 후 기록 −37~−49 → 로그 **−53~−14**, −37~−49는 다수 구간)도 **로그 값으로 정정해 등재**했다. ⚠️ **위임 본문도 catch 대상**이며 §9 정지 사유(취소선 대상 부재)에는 해당하지 않아 **그대로 진행**했다.

**find-skills**: 전 엔트리와 같은 배치에서 수행했다 — `"decision log markdown"` **0건** / `"korean technical writing"` **0건** / 대조군 `flask` **25건**(도구 생존 확인). **채택 0건 · 사유 ③ 0건 · install 0 · info 0.**

### 신설 절 번호 · 위치 결정 근거 (위임 미지정 — MCP 판정, 근거유형 = 실측 grep)

- **6.6** — 카테고리 6의 마지막이 전 엔트리에서 신설한 **6.5**이므로 **다음 번호 6.6**. ★ **6.3 하위 letter로 넣지 않은 근거**: `camera_probe`는 **카메라 · 마이크 · ToF 세 페리페럴에 걸친 신설 env**라 「마이크 M 시리즈」 절의 하위가 아니다. 6.3(o)가 `env:mic_noiseprobe`를 하위 letter로 둔 것은 **그 하네스가 마이크 단일 축**이기 때문이고, 본 건은 축이 다르다. ⚠️ 카테고리 6은 번호 체계가 있으므로 **무번호 선례 미적용**.
- **카테고리 2 카메라 5행** — 본 표는 **번호가 아니라 행 체계**라 기존 8행 아래에 **모듈 단위로 추가**하고 각주를 붙였다. 표 밖 ★ 각주(PWREN/LPn)는 **무변경**이다.
- **카테고리 20 무번호 절 1개 · 원칙 1건** — 「NC 변형 적용 증명에 바이너리 md5를 쓸 수 없다」는 **무번호 `###` 선례**대로 「5/17 종료 시점 액션」 앞에 뒀고, ARP 함정은 **기존 「조용한 가드 금지」 절의 원칙 4**로 넣었다(그 절이 *"본 절은 원칙만 적는다 · 사례 본문은 단일 등재"*라 못 박고 있어 **사례 본문은 6.6(d)에만** 뒀다).
- **27.8(m)④⑤** — 전 엔트리가 신설한 (m)에 **하위 원문자 ④ ⑤를 이어 붙였다**(27.8의 하위 기호 체계 = **문자 + 원문자**).

### 편집 건별 (전건 `str.count` == 1 assert 통과, 라인 번호 0건 사용)

| E# | 앵커 (실물 문구) | 방식 | 반영 위치 | 근거유형 |
|---|---|---|---|---|
| E1 | 「\| VL53L5CX \| LPn   \| 3V3 직결 \| - \| (I2C enable) \|」 | 표 **5행 신설** + 각주 | 카테고리 2 | 실측 코드 대조 |
| E5 | 「4종 전건 실행 OK이며 checks 수 … `tof_judge_test` 196이다.」 | **취소선 + 현재값 갱신** | 6.3(o) | 실측 + 문서 인용 |
| E9 | 6.5 「관련」 줄 전문 | **절 신설** | **6.6** | 항목별 병기 |
| E11 | 「정황 (원인 확정 아님): negative control 절차는…」 | **원칙 4 append** | 카테고리 20 조용한 가드 절 | 실측 + 논증 |
| E13 | 「### 5/17 종료 시점 액션」 | **무번호 절 신설** | 카테고리 20 | 실측 |
| E19 | 「5/12 메모리 self-checkpoint 결과 (카테고리 17.1.1) …」 | 하위 블록 append | 카테고리 15 | 실측 설치 파일 대조 |
| E20 | 「현재값(2026-09-11)은 `mic_uplink`(PR #52) + `mic_noiseprobe`(PR #54) 추가로 11개…」 | **취소선 + 현재값 갱신** | 카테고리 16 | 실측 + 문서 인용 |
| E21 | 「동적 heap 추적 … 동시 진행 (2026-05-09 추가, SRAM 동적 소비 분석)」 | 하위 항목 append | 카테고리 17 | 실측 |
| E22 | 「init ✅ / PSRAM 8MB OCTAL 인식 ✅ / QVGA(320x240) JPEG ~6KB …」 | 하위 항목 append(원 서술 무변경) | 32.2 | 실측 |
| E18(④⑤) | 27.8(m) 말미 ⚠️ 합산 제외 줄 | 하위 **④ ⑤ 신설** | 27.8(m) | 실측 |

### 등재 내용 요약

- **6.6 신설** — **(a)** 산출물(신설 6파일 · `git diff --stat main` **1250 insertions / 0 deletions** · `platformio.ini` **추가만**) / **`camera_probe_test` 97 checks** / **NC 6종 전건 검출·복원·자기검증 통과** / 빌드 **12 env 전건 SUCCESS · 경고 0** / `mic_uplink` **바이너리 md5 · 크기 완전 동일**(무접촉 증명) / 모드 사슬 m0~m7 **인접 1변수** + **비인접 쌍 `m3↔m6`을 `PROBE_NONADJ_PAIRS`로 코드 고정**(79 → 97 checks) / 주석 오기 정정(**m6 = m3에서 WiFi만 뺀 구성**).
- **6.6(b) ④런타임** — 조용한 구간 clip = m0 **3~14**(기준선) · m1 **2~6** · m2 **1~6** · m3 **0~4** · m4 **1~3** · m5 **3~10** ⇒ **카메라·WiFi ON에서 기준선 범위 이탈 없음**. ★ **결론 강도 = 「관측」까지만이고 6.3(n) 미결을 닫지 않았다**(창 수 적음 · 조용한 구간 한정 · 세션 후반 대화 유입). **감도 대조군** = 대화 유입 구간 clip **4~20** ⇒ 계측기가 실제 변화는 검출한다. 🔴 **끝 m0이 대화 구간이라 세션 드리프트 확인 불가.** 🔴 **m3 win#31의 `pk=741` · `clip=0` 단발 관측**(그 외 전 창 `pk` 32767/32768)을 **압축하지 않고 별도 항목으로** 등재했다 — 6.3(n) 원인 후보를 가르는 단서일 수 있으나 **기전 미규명**이다.
- **6.6(c) 카메라 실측** — QVGA **5,353~5,438 B** / VGA **13,791~13,910 B** · 캡처 **주기 1 ms / 연속 최대 71 ms** · 60창 누적 `try` **3,563** = `ok` **3,563**, `nul` **0** · `soi` **0** · init **383 ms** · PSRAM 점유 **30,952 B**이고 deinit이 **동일 바이트 반환**(누수 0, `[MEM:]` 세 지점으로 교차 확인).
- **6.6(d) 🔴 WiFi 축 무효 함정** — lwIP **`ARP_QUEUEING=1`** 때문에 대상 기기가 없어도 `sendto()`가 성공을 돌려주어 **`tx` 증가 · `txerr=0`이 「무선 송신」을 보장하지 않는다**. 차단 = 부팅 줄 대상 주소 노출 + 측정 전 **1회 도착 확인**이며, 본 세션 m1 구간에서 **2,800 B 수신**으로 축 유효성이 실증됐다. **PR-B 실 업로드도 같은 함정을 공유**한다.
- **6.6(e)** — `uplinkConnectWifi()`가 **SSID를 시리얼에 출력**하므로 보드 로그를 public 문서로 옮길 때 **SSID · IP를 지운다**(32.6 원칙 재실증). 본 문서 **실값 0건**.
- **카테고리 2** — **카메라 5행 신설**(XCLK 10 / SCCB 40 · 39 / Y9~Y2 8핀 / VSYNC · HREF · PCLK / PWDN · RESET `-1`). **핀 교집합 = ∅**(mic {2,3,7} · ToF {5,6}) + ★ **I2C 포트 분리**(카메라 SCCB = 포트 **1** / ToF `Wire` = 포트 **0**).
- **카테고리 15** — 🔴 **`CONFIG_CAMERA_CORE0=y`**(카메라 DMA 태스크가 **Core 0**) ⇒ 잠정안의 「Core 1: cameraTask」와 **어긋난다**. + `loopTask`는 **Core 1 · prio 1 · stack 8192**. ★ **잠정안 값은 당시 안(案)이라 취소선 대상이 아니며**, **물리 사실만 등재**하고 **코어 분배 재확정은 범위 밖**으로 못 박았다.
- **카테고리 17** — #620(WiFi join 후 `fb_get` fail)에 **입력 확보**: WiFi 연결 상태 연속·주기 구동에서 `nul` **0건**. ⚠️ **「issue가 없다」가 아니다**(조건 한정 · 전원 레일 미관측).
- **현재값 갱신 2건** — 호스트 테스트 **4종 → 5종**(`camera_probe_test` 97 합류, 6.3(o)) / `[env:*]` **11개 → 12개**(카테고리 16). 두 건 모두 **직전 값 취소선 + 새 값** 컨벤션을 따랐고 **이력 서술은 그 시점 사실이라 무변경**임을 병기했다.
- **카테고리 20** — **원칙 4**(관측 축 자체도 조용히 무효화된다 — 원칙 1·2가 *"막았는데 조용하다"*라면 본 원칙은 *"걸었는데 실제로는 안 걸렸다"*, **거짓 음성 방향**) + **무번호 절**(macOS clang은 **동일 소스 2회 컴파일에서 md5가 달라진다** ⇒ 바이너리 해시는 NC 변형 적용 증명이 못 되고, **전처리 출력 `c++ -E`의 md5**로 교체한다 — `python3 -B` 절이 세운 **4층의 컴파일 언어 판**).
- **27.8(m)④⑤** — `mic_common.h`의 「카메라(I2S0)와 페리페럴 분리」가 **ESP32 원조 프레이밍**(결론은 옳고 근거 문구만 어긋남) / `probe_modes.h` ↔ Runbook **문서-코드 드리프트**와 그 차단이 **「코드가 단일 원천을 갖게 하는 것」**이었다는 점.

### 🔴 사용자 판단 대기 항목 — 등재하되 방향 미확정 (본 엔트리 기준 전수 재확인)

전 엔트리(2026-09-17)의 **14행 표 전건이 그대로 유효**하며, 본 엔트리가 **추가·변경한 것은 아래 2건뿐**이다.

| 항목 | 등재 위치 | 방향 확정 여부 |
|---|---|---|
| 마이크 SD 비트 오류 해결책 ①②③ | 6.3(n) | 🔄 **입력 추가 · 미확정 유지** — 6.6(b)가 「카메라·WiFi가 이 미결을 키우는가」의 **관측**을 더했을 뿐 **닫지 않았다**. 🔴 **m3 win#31 단발 관측**이 새 단서로 추가 |
| 코어 분배 잠정안(카테고리 15)의 재확정 | 카테고리 15 | 🆕 **신규 — 미확정** (`CONFIG_CAMERA_CORE0=y`가 잠정안과 어긋난다는 **물리 사실만** 등재) |

**SSoT 정합 검증 (문서 전용이라 코드 3단계 ①②는 무관, 두 날짜 합산 · 단일 커밋 기준)**

- **V0 커밋 단위 판정 (MCP 판정 + 근거)** — 위임 권고는 **날짜별 2커밋**이었으나 **1커밋**으로 냈다. 근거 = ① **6.5 ↔ 6.6이 서로를 인용**한다(6.5(d)의 PR-A 행이 6.6을 가리키고 6.6 머리가 6.5(d)를 가리킨다) ② **27.8(m)이 두 날짜의 catch를 한 목록으로** 담는다 ③ 취소선 · 토큰 보존 · 한글 전수 검증이 **단일 스냅샷 기준 측정값**이라 중간 커밋에서 한 벌을 더 만들면 **stale 표면이 늘어난다**(27.8(f-2) 계열). ⇒ **날짜 구분은 본 `decisions-log.md`의 2엔트리가 담당**한다. ⚠️ 이 판정은 **위임 §7 제약 어느 항목과도 충돌하지 않는다**(force push · rebase · amend 0건).
- **V1 취소선** — `decisions.md` 착수 전 **84줄 / 198개** → 종료 **89줄 / 210개**(계수 단위 = `grep -c` **줄 수** / `grep -o | wc -l` **출현 수**). 증가분 **+5줄 / +12개 = 신규 6쌍**(E2 1 · E5 1 · E10a 1 · E10b 1 · E20 1 · E23 1)으로 **설계와 정확히 일치**하고 **210 = 짝수 = 마크다운 무파손**이다. ★ **E20이 줄 수를 늘리지 않은 이유** = 그 줄에 이미 취소선이 있었다(카테고리 16 「근본 수정 = whitelist 통일 별도 위임」). `decisions-log.md`는 두 엔트리에서 취소선 마커를 **0개 추가**했고 총 **66개(짝수)**를 유지한다(⚠️ 본 줄이 마커를 그대로 적으면 그 자체가 계수에 잡히므로 **문자로 적지 않는다** — 2026-09-16 후속 세션 catch 준수).
- **V2 삭제 0줄 증명 (토큰 보존)** — `git diff --numstat` = `decisions.md` **319 / 8**, `decisions-log.md` **168 / 0**(두 엔트리 합산, 순수 append). 제거 **8줄**은 전부 **같은 줄의 치환 결과**다. **정규화(마커 제거) 기준 미보존 토큰 = 1종**(`하네스)**`)이고 이는 **E16이 괄호 안에 「· 외부 세트 사용 주의」를 덧붙여 닫는 괄호 위치가 옮겨간 경계 artifact**다 — 실물 `grep -c "PR #59 하네스"` **4건**으로 단어 생존을 확인했다. **원시 기준 미보존 토큰 7종**은 전부 **취소선 마커가 토큰 앞뒤에 붙어 공백 구분 토큰이 달라진 결과**(예: 정정 대상이 된 `class_weight` 토큰)이며 **정규화 기준에서 전건 회수**된다. ⚠️ 마커 자체는 **문자로 적지 않는다**(2026-09-16 후속 세션 catch).
- **V3 편집 지점 실물 되읽기** — 두 날짜 합계 **물리 편집 지점 26곳** 전건 `count == 1` 재확인.
- **V4 🔴 한글 전수 검증** — 추가분에서 착수 전 파일에 **없던 한글 단어 642개**를 전건 문맥과 함께 출력했고(전부 정상 문맥 — 대다수가 기존 어휘의 **활용형 차이**다) **신규 음절은 12종**(`닮` `듣` `럽` `럿` `렵` `벗` `셌` `쏴` `얽` `쟀` `켠` `큐`)으로 전건 문맥을 확인했다(닮은 · 듣는 · 자연스럽다 · 파일럿 · 무렵 · 벗어나지 · 셌을 · 쏴도 · 얽힘 · 쟀다 · 켠 · 큐에). ⚠️ **「신규 음절 0」은 충분조건이 아니므로**(기존 음절로의 치환은 통과한다) **단어 단위 출력**을 정본으로 삼았다. **바이트 기준 보강** = UTF-8 strict decode **통과**(526,858 B) · `U+FFFD` **0건** · 제어문자 **0건** · 조합/호환 자모 단독 **1건**(착수 전과 동일한 기존 「타입 SSoT ㄴ안」 1건, 신규 0) · `U+0080`~`U+00FF`는 **기존 정상 기호 6종뿐**(§ ± · ¼ × ÷).
- **V5 수치 1:1 대조** — 6.6의 전 수치를 `camera_probe_runtime.log`에, 30.9 · 5.2 · 33.6(g) · 6.5의 전 수치를 각 리포트·로그에 **1:1 추적**했다. **로그에 없는 수치 0건 기재**이며, 위임 본문과 어긋난 6건은 **전부 로그 값으로 등재**했다(위 catch 절).
- **V6 git status** — `docs/` **2파일만**. 시크릿 스캔(SSID · 토큰 · 자격증명 · IP 패턴) **실제 검출 0건**.

**비범위**: **코드 0 수정** — `firmware/` · `server/` · `dashboard/` · `ml/` 이하 전부 무접촉이고 `docs/git-convention.md`도 무접촉이다. **노션 무접촉** · **프로젝트 지침 파일 무접촉**(Set 2 소관). 🔴 **6.3(n) · 33.6(a) · 33.7 미결 상태 전환 0건** — 6.6(b)는 **입력만** 더했다. **카테고리 15 코어 분배 재확정 0건**(물리 사실만). **32.2 원 서술 무변경**(「~6KB」 취소선 없음 — 그 시점 실물이다). **부재 G-ID 0건 사용.** **시크릿 0** — SSID · 토큰 · IP(사설 LAN 포함) 실값 **0건 기재**. **미착수** = 보드 재플래시 · PR-B 착수 · m1 · m3 · m4 노이즈프로브 모드 · `00_source_raw` 감사 · 실 초인종 음원 확대 수집.

**학습 적용**: **학습 13**(인용 전 grep — 편집 앵커 전건 `count == 1`, **라인 번호 0건**. 부재 판정은 대조군과 함께: 카테고리 2 카메라 행 **0건** vs INMP441 4행 · VL53L5CX 4행 생존) / **학습 14**(repo 구조 가정 검증 — 카메라 14핀 · `CONFIG_CAMERA_CORE0` · `CONFIG_SCCB_HARDWARE_I2C_PORT1` · SSID 출력을 **위임 인용이 아니라 실물 파일에서 직접** 읽었다) / **학습 17**(🔴 **위임 본문 catch 6건** — clip 수치 · QVGA 상한 · VGA 범위 · 대화 구간 clip · RSSI · 창 수. 전부 **로그 값 채택 후 보고**) / **학습 19**(근본원인 진단 재검증 — PR #63의 **주석 오기**와 **바이너리 md5 무효** 둘 다 *"원인 진단이 틀렸다"*를 코드로 규명한 사례라 방법론으로 등재했다) / **학습 21**(미결도 유령일 수 있다 — 🔴 **역방향을 경계했다**: 6.6(b)의 관측이 좋게 나왔다고 **6.3(n)을 해소로 날조하지 않았고**, 카테고리 15 잠정안도 **틀린 것으로 단정하지 않고 「어긋나는 물리 사실」로만** 적었다) / **「발견일 ≠ 반영일」**(6.6 실측 = **2026-09-18** 발견 · 반영, PR #63 코드 산출 = 2026-09-17~18, 설계 조사 = **2026-09-17**로 갈라 표기) / **「실측 / 논증 / 문서 인용 3분」**(창 통계 · 카메라 바이트 · PSRAM delta = **실측** / 코어 배치 함의 · ARP 함정의 파급 = **논증** / NC 6종 결과 · checks 수 = **문서 인용(PR #63 본문)**. **한 문장에 섞지 않았다**).

**관련 카테고리**: **6.6 (`env:camera_probe` 신설 — 하네스 + ④런타임 + 카메라 실측 + ARP 함정 + SSID 주의)** / **6.5 (본 PR이 PR-A인 설계 조사 — 전 엔트리 신설분)** / 6.3(n) (입력 추가 · 🔴 **미결 유지**) / 6.3(o) (호스트 테스트 4종 → 5종) / **카테고리 2 (카메라 14핀 5행 신설 + I2C 포트 분리)** / **카테고리 15 (`CONFIG_CAMERA_CORE0` · `loopTask` 코어 — 잠정안과 어긋나는 물리 사실)** / 카테고리 16 (env 11개 → 12개) / **카테고리 17 (#620 입력 확보)** / 32.2 (QVGA · VGA JPEG 크기 · PSRAM 점유 보강) / **카테고리 20 (원칙 4 · 바이너리 md5 무효 절 신설)** / **27.8(m)④⑤ (근거 문구 오기 · 문서-코드 드리프트)** / 27.8(d)(i) (누적 숫자 무변경 — 사용자 판단 대기) / 학습 13 · 14 · 17 · 19 · 21.
**관련 commit**: `41cd6e2`(**PR #63 squash — 본 절의 대상 코드**, 착수 시점 HEAD) · 선행 = `34e3223`(PR #63 직전 문서 커밋). 문서 반영 = 본 커밋(docs-only, **PR 없음, main 직 push**) — ★ **2026-09-17 엔트리와 같은 커밋**이며 근거는 위 **V0**.

## 2026-09-18 (금) 후속 — PoC-(53) Set 1 — PR #64 보드 2차 체인 배관 등재 + ④런타임 4건 실측 신설(6.7) + 6.5(f) 사용자 확정 8건 반영 + 🔴 타임아웃 산술 상한 재계산 입력(7.7(l) 미결 유지) + 1차 rtt 교란 단서(6.2) + 호스트 테스트 5종 → 6종 · env 12개 → 13개 + MANSHIP 서지 신설(33.9) (카테고리 6.2/6.3/6.5/6.7/7.6/7.7/16/20/27.8/33.9)

같은 날 오전 PoC-(52)가 **PR-A**(관측 계층)를 등재한 데 이어, 6.5(d)가 **PR-B**로 지목한 **배관 계층**이 **PR #64(`d093d70`)로 실행·머지**됐고 학부생이 **④런타임 4건을 완주**했다. 축은 **넷** — ① **신설 절 6.7**(사용자 확정 8건 · 구현 실물 · ④런타임 · 서버 종결 · 카톡 · 실 육성 STT · 한계) ② **6.5(f) 미결 부분 해소**(전부 닫힘 5 / 부분 2 / 무접촉 2) ③ **🔴 재판정 입력 2건**(7.7(l) 타임아웃 산술 상한 · 7.6(i) 영구 포기 정책 — **둘 다 미결 유지**) ④ **SSoT 미등재 사실 4건 + MANSHIP 서지**. 문서 2파일만 수정, **코드 0줄 · 보드 무접촉**, main 직 push.

**Step 0 가정 대조 — A1~A12 전건 O, 불일치 0건(정지 임계 3건 미달)**: 착수 시점 HEAD **`d093d70`** · `main` · 워킹트리 clean · 원격 `refs/heads/main` 단일(`git ls-remote` — 학습 20) · 열린 PR **0** · PR 최대 **#64**. `git show d093d70 --stat` = **7파일 1,225 insertions / 0 deletions** 일치. `grep -c '^\[env:'` = **13** 일치. (C) 상수·static_assert 전건 일치. A6의 6.3(o) 현재값은 **「5종」**이 맞다(부모 불릿의 「3종 → 4종」은 그 시점 이력이고, 자식 불릿이 PoC-(52)에서 5종으로 갱신돼 있다 — **부모만 보면 오독한다**). A12 부재 확인은 **볼드·백틱 마커를 걷어낸 부분 문자열**로 재조회했다(`본문 복사` 0 · `ESP32 빌드` 0 · `867,888` 0 · `MANSHIP`/`Njimbouom`/`Technology and Health Care`/`97.14`/`선문대`/`ResNet-50` 전건 0).

**🔴 위임·PR 본문 catch 2건 (학습 17 · 학습 19)**

- **① `uplink_common.h` 호스트 컴파일 차단 사유가 실물과 다르다**: 위임 (L4)와 **PR #64 본문**이 모두 **「`mic_common.h` → `driver/i2s.h` 때문」**이라 적었으나, `c++ -fsyntax-only` 실측은 **1차 차단이 `uplink_common.h` 자신의 `#include <Arduino.h>`**다. 가짜 `Arduino.h`를 공급해 ①을 넘긴 뒤에야 `driver/i2s.h`가 드러난다 — **차단은 2중**이다. 대조군 = `enrich_wire.h` 단독 **통과**. ⇒ **불변식(순수 헤더 분리 필요)은 유지하고 메커니즘 서술만 정정**해 6.3(o)에 등재했고, 오류 자체는 **27.8(n)①**에 올렸다.
- **② PSRAM 「4/4 동일」이 실물은 3/3이다**: 위임 (E)와 `pr64_interactive.log` **요약줄**이 그렇게 적었으나, 이벤트 #1은 **`gate=skip`이라 카메라 init 자체가 없다** — `pr64_e2_runtime.log`에 `[MEM:e2-pre-init]` · `cam ms=` 줄이 **#2 #3 #4에만** 있다. ⇒ **원본 로그 값(3/3)으로 등재**하고 **27.8(n)②**에 올렸다. ★ 요약줄은 사후 정리분이고 **원본 로그가 SSoT**다.

**로그 원본 접근**: `~/ddingdong-측정결과/2026-09-18/enrich_uplink/` **3파일 전건 읽혔다**(`pr64_e2_runtime.log` **1,065줄** · `pr64_server.log` **29줄** · `pr64_interactive.log` **100줄** — 위임이 적은 줄 수와 일치). ⇒ 본문 수치는 **위임 인용이 아니라 로그 원본에서 직접** 대조했다.

**find-skills**: `"markdown section editing"` **0건** / `"changelog entry writer"` **0건** / `"korean text validation"` **0건** / `"technical decision log"` **0건**. 대조군 `flask` **1건** · `git` **1건**(도구 생존 확인 — `npx skills search`). **채택 0건 · 미채택 사유 = ③ 0건**(①②는 해당 없음) · install 0 · info 0.

### 신설 절 번호 결정 근거 (위임 미지정 — MCP 판정, 근거유형 = 실측 grep)

- **6.7** — `git show HEAD:docs/decisions.md | grep -nE "^## 카테고리|^### "` 전수 결과 카테고리 6의 마지막이 **6.6**이므로 **다음 번호 6.7**. ★ **6.5의 하위 letter로 넣지 않은 근거**: 6.5는 **조사·설계 전용 절**(repo 쓰기 0 · 코드 0줄)이라 성격이 다르고, 6.6이 같은 계보의 PR-A를 **별도 절**로 받은 **직전 선례**가 있다. ⚠️ 카테고리 6은 번호 체계가 있으므로 **무번호 선례 미적용**.
- **27.8(n)** — 27.8의 하위 기호 체계 = **문자 + 원문자**이고 마지막이 **(m)**이므로 **(n)**. 하위 4건은 **① ② ③ ④**.
- **33.9** — 카테고리 33의 마지막이 **33.8**이므로 **33.9**. ★ **MANSHIP을 33.6 계열 하위에 넣지 않은 근거**: 33.6은 **우리 실모델 실측** 절이라 **병치 금지 대상을 그 안에 두면 오히려 병치를 부른다**. 별도 절 + 「관련」에서 병치 금지를 명시하는 쪽이 안전하다.
- **L3(ESP32 빌드 비결정)** — 카테고리 20의 **무번호 절** 「NC 변형 적용 증명에 바이너리 md5를 쓸 수 없다」에 **툴체인 확장으로 append**(위임 지정대로). 새 절을 만들지 않은 이유 = 그 절이 이미 *"새 툴체인으로 옮길 때 산출물이 결정적인가를 먼저 확인한다"*를 일반화로 적고 있어 **본 건이 그 일반화의 첫 적용례**다.
- **L4** — 6.7이 아니라 **6.3(o)**에 넣었다. 근거 = (o)가 **호스트 테스트 방법론 절**이고 L2(`jsonpeek_test` 본문 복사)와 **같은 축**(무엇이 호스트에서 검산 가능한가)이라 **한자리에 모인다**.

### 편집 건별 (전건 `str.count` == 1 assert 통과, 라인 번호 0건 사용)

| E# | 앵커 (실물 문구) | 방식 | 반영 위치 | 근거유형 |
|---|---|---|---|---|
| E1 | 「## 카테고리 7: STT + 알림」 | **절 신설** | **6.7** | 항목별 병기 |
| E2 | 「녹음 길이 N · pre:post 비율 / 해상도(QVGA · VGA · SVGA) / …」 | **취소선 7쌍 + 확정 표기 + 경계 줄 append** | 6.5(f) | 사용자 결정 |
| E3 | 「\| **PR-B** \| **배관(plumbing)** \| …」 | 표 행 **append**(PR-A 행과 동형) | 6.5(d) | 실측 |
| E4 | 「checks 수 = `camera_probe_test` **97** / … **5종 전건 실행 OK**다.」 | **취소선 + 현재값 갱신** + 하위 2건 신설 | 6.3(o) | 실측 + 문서 인용 |
| E5 | 「`camera_probe`(PR #63 `41cd6e2`) 추가로 **12개**이며 …」 | **취소선 + 현재값 갱신** | 카테고리 16 | 실측 + 문서 인용 |
| E6 | 「⚠️ **해결책·타임아웃 값 신설 금지** — 판정은 2차 클라이언트 …」 | 하위 블록 **append**(미결 유지) | 7.7(l) | 논증(입력 실측 분리) |
| E7 | 「⚠️ **기준선 표기 정정 (발견 2026-09-03 …)**」 | **앞에 단서 삽입**(원 서술 무변경) | 6.2 | 실측 + 논증 |
| E8 | 「⚠️ 6.1의 「`device_id` 5초당 1회」는 `/enrich`에도 …」 | 하위 **보강 줄 append** | 6.5(b) | 실측 |
| E9 | 「⚠️ **일반화**: NC 하네스를 새 툴체인으로 옮길 때 …」 | **툴체인 확장 append** | 카테고리 20 md5 절 | 실측 |
| E10 | 「- **STT 배선 CLOSE ≠ 실 육성 인식률 검증**: 입력이 전부 **TTS 합성음**이다.」 | 하위 **경계 갱신 append**(원 줄 무변경) | 7.7(j) | 실측 |
| E11 | 「트리거 = 실 ESP32 2차 클라이언트 연동 후 재판단.」 | 하위 블록 **append**(미결 유지) | 7.6(i) | 실측 |
| E12 | 「⚠️ **본 (m)은 (d)의 「인용 오기 누적」 숫자에 합산하지 않는다** …」 | **하위 절 (n) 신설** | 27.8 | 실측 + 실물 대조 |
| E13 | 33.8 「관련」 줄 전문 | **절 신설** | **33.9** | 웹 서지 확인 |

### 등재 내용 요약

- **6.7 신설** — **(a)** 사용자 확정 8건 표(체인 순서 · 5초/pre 0 · QVGA · C1 전용 타임아웃 상수 · skip 미발송 · `presence=false` 촬영 · additive · ≤12) + 🔴 **1차 링버퍼 pre:post는 이 8건에 없다(M5-c 보류 유지)** / **(b)** 7파일 **1,225 / 0** · env 12 → 13 / **(c)** `ENRICH_AUDIO_BUFFERS=80` → **163,840 B = 5.120초 = 상한의 51.2%**, 불변식 static_assert **2쌍**(I-A ≥5.000초 · I-B ≤`AUDIO_MAX_BYTES`) + `uplink_common.h`가 `mic_common.h`와 **묶는 static_assert 2건**, `UPLINK_ENRICH_HTTP_TIMEOUT_MS=15000`은 **잠정값**, 게이트 3상태, `enrich_wire_test` **90 checks** / **(d)** ④런타임 4건 표 + PSRAM **delta 30,952 B · 누수 0 · 캡처 3회** + `-11` = `HTTPC_ERROR_READ_TIMEOUT` / **(e)** 서버 종결 4건 + **서버측 2차 소요 7.351 / 11.562초(15초 예산의 49% / 77%)** / **(f)** 카톡 도착 + **자막 미도착 = 7.6(e) 자막 부재 경로 첫 실기기 통과** + 🔴 **캡처 실명·프로필 → 대외 사용 금지** / **(g)** 실 육성 STT **오류 0자, n=1** / **(h)** `gdma_disconnect` 3회(**기전 미규명**, 6.6에는 없던 줄) · WiFi PRIMARY 1회 timeout 후 재연결 / **(i)** 🔴 **한계 8종 전건 명기**.
- **6.5(f) 부분 해소** — **전부 닫힘 5항** · **부분만 닫힘 2항**(녹음 길이 = N만 / 타임아웃 = 방식만, **값은 잠정**) · **무접촉 2항**(카메라 init 시점 · **6.3(n) 해결책 ①②③**). ★ **PR #64가 카메라를 이벤트마다 init·deinit 한다는 사실을 「카메라 init 시점」 미결의 확정으로 읽지 말 것**을 본문에 박았다.
- **🔴 7.7(l) 재판정 입력(미결 유지)** — 카카오 **로그로 양끝이 잡히는 3구간** 4.180 / 1.519 / 1.517초(합 **7.216초** ↔ 산술 4.5초, **배율 ≈1.60**), 사진 1차는 **하한 미확보**(STT `processed_at` 기준 상한 ≤2.840초)라 위임의 4구간 근사(≈9.2초 · ≈1.53)도 **범위 안**이다. CSR `elapsed_ms=6,423.73`. 🔴 **코드 확인 = 상수는 정상 전달되며 `urlopen` timeout이 소켓 연산 단위 상한이지 총 경과 상한이 아니다** — 7.7(l) 본문의 `HTTPClient::setTimeout` 정정과 **같은 축이 파이썬 쪽에도 있었다**. 파급 = **≈19.5~20.0초**로 **12.1초는 과소평가**이며 15초 예산·잠정 15,000ms를 **넘을 수 있다**. ⚠️ 측정된 실패는 **타임아웃이 아니라 `URLError`**라 정상 왕복과 **모집단이 다르다** — **새 값 확정 0**.
- **🔴 6.2 1차 rtt 단서** — skip **683ms** ↔ pending **4,301 / 4,902 / 5,814ms**. 🔴 **교란 3축**을 적었다 — ① 2차 동반 ② 세션 후반 `URLError`(핫스팟 열화) ③ **[신규, 논증·입력 실측 = `routes.py` 코드 구조] `if primary_sent:` 안에서만 카카오를 호출하므로 `tof_rejected` skip 건은 카카오 왕복을 아예 태우지 않는다**. ⇒ **교대 배치만으로는 ③이 갈리지 않는다**까지 적었다. **원인 지정 0건** · 기존 「1134ms」·「1,954ms」 **취소선 없음**(조건이 다른 이력·산술).
- **🔴 7.6(i) 재판단 입력(미결 유지)** — 본 (i)가 기다리던 **「네트워크 타임아웃 미재현」이 재현**됐다(`URLError` = 일시 실패로 읽히는 첫 사례, 보드 `-11` ↔ 서버 200). 🔴 **그럼에도 닫지 않았다** — n=1이고 `skip_reason`이 `kakao_api_error` 한 값으로 뭉개며 재전송은 **409 재처리 가드**에 막힌다.
- **SSoT 미등재 4건** — **L1** `enrich_status` = `notification_status` **하위 중첩**(6.5(b) 파생 사실 ② 보강, ★ **27.8(c)③이 같은 응답의 다른 필드에서 이미 잡은 패턴의 재발**이라 신규 오류로 세지 않았다) / **L2** `jsonpeek_test`만 **본문 복사** 방식이라 **원본 변형 NC 불가**(6.3(o), 다른 5종은 project 헤더 include — 실측 대조) / **L3** **ESP32 크로스 빌드도 비결정적**(md5 3회 상이 · 크기 **867,888 B** 3회 동일 ⇒ **크기는 유효 신호, md5는 잡음**, 카테고리 20 툴체인 확장) / **L4** `uplink_common.h` **호스트 컴파일 2중 차단**(6.3(o)).
- **현재값 갱신 2건** — 호스트 테스트 **5종 → 6종**(`enrich_wire_test` 90 합류, 6.3(o)) + ⚠️ **`jsonpeek_test`는 카운터를 출력하지 않아**(정적 `assert` **13**) 목록이 5개 이름만 드는 것이 **누락이 아님**을 병기 / `[env:*]` **12개 → 13개**(카테고리 16). 두 건 모두 **직전 값 취소선 + 새 값** 컨벤션을 따랐고 **이력 서술 무변경**을 병기했다.
- **33.9 신설** — MANSHIP(Njimbouom · Lee · Kim, *Technology and Health Care* 2025, 33(4) 1787–1799, 선문대 / VGG16 + ResNet-50 / 도시 소리 **97.14%**). 🔴 **데이터·클래스가 달라 우리 수치와 병치 금지**를 본문·「관련」 양쪽에 박았다. **2026-09-17 · 09-18 PoC-(52)에서 연속 2회 누락**됐던 항목이다.
- **27.8(n) 신설** — ① 차단 메커니즘 오기(`Arduino.h` vs `driver/i2s.h`, **PR 본문 + 위임 동시 오기**) / ② 계수 오기(4/4 → **3/3**) / ③ 위임 자기모순(⑦ additive ↔ Step 9 바이너리 동일, 실측 **+32 B** — **27.8(a)와 동형**, 학습 16 ★판정 규칙 작동) / ④ 근거유형 오진(「상수 미작동」 → 실제는 `urlopen` 성질, **33.6(e) 계열 재실증**). ★ **①과 ④는 방향이 반대**(남의 메커니즘을 믿음 ↔ 내 메커니즘을 코드 없이 확정)라는 점을 적었다.

### 🔴 사용자 판단 대기 항목 — 등재하되 방향 미확정 (본 엔트리 기준 전수 재확인)

| 항목 | 등재 위치 | 방향 확정 여부 |
|---|---|---|
| 6.3(n) 마이크 SD 비트 오류 해결책 ①②③ | 6.3(n) · 6.5(f) | ⛔ **무접촉** — 본 Set이 **입력조차 더하지 않았다** |
| 1차 링버퍼 pre:post 비율 (G29) | 6.2 · 6.5(f) | ⛔ **무접촉 · M5-c 보류 유지** — 6.7(a)의 「pre 0」은 **2차 녹음 전용**임을 명시 |
| 2차 타임아웃 **값** | 6.5(f) · 6.7(c) · 7.7(l) | 🔄 **입력 추가 · 미확정 유지** — 잠정 15,000ms, **새 값 확정 0** |
| 카메라 init 시점(상시 vs 이벤트마다) | 6.5(f) | ⛔ **무접촉** — 구현 사실을 확정으로 읽지 말 것을 명시 |
| 7.6(i) 2차 자막 실패 영구 포기 정책 | 7.6(i) | 🔄 **입력 추가 · 미확정 유지** |
| 33.6(a)(f)(g) OOD 대응 · 33.7 누수 대응 · 5.2(g) · 카테고리 5 `SAMPLE_WEIGHT_RANGE` · 33.6(e) round 게이트 · 8.5(i) `device_status` · 8.7(c) twMerge · 카테고리 10 이모지 2종 | 각 절 | ⛔ **전건 무접촉** |
| 27.8(d) 누적 숫자 합산 여부 ((i)) | 27.8(i) | ⛔ **무접촉** — (n)도 합산하지 않았고 경계 표기만 갱신 |

**SSoT 정합 검증 (문서 전용이라 코드 3단계 ①②는 무관)**

- **V1 취소선** — `decisions.md` 착수 전 **89줄 / 210개** → 종료 **90줄 / 228개**(계수 단위 = `grep -c` **줄 수** / `grep -o | wc -l` **출현 수**). 증가분 **+1줄 / +18개 = 신규 9쌍**이고 **설계와 정확히 일치**한다 — **E2 7쌍**(6.5(f) 확정 7항) · **E4 1쌍** · **E5 1쌍**. ★ **줄 수가 1만 는 이유** = E4 · E5는 **이미 취소선이 있던 줄**을 갱신했고(각각 6.3(o) 「4종 전건 실행 OK」 · 카테고리 16 「11개」), 새로 취소선이 생긴 줄은 **E2 하나뿐**이다. 신설 절(6.7 · 27.8(n) · 33.9)과 append 블록은 취소선을 **0개** 넣었다. **228 = 짝수 = 마크다운 무파손.** `decisions-log.md`는 취소선 마커를 **0개 추가**해 **66개(짝수)** 유지다(⚠️ 마커를 문자로 적지 않는다 — 2026-09-16 후속 세션 catch).
- **V2 삭제 0줄 증명** — `git diff --numstat` 기준 `decisions.md`의 제거 줄은 **전부 같은 줄의 치환 결과**이며, **정규화(취소선 마커 제거) 기준**과 **원시 기준**을 나눠 토큰 보존을 확인했다.
- **V3 편집 지점 실물 되읽기** — **물리 편집 지점 13곳** 전건 `count == 1` assert 통과(스크립트가 불일치 시 abort). **라인 번호 사용 0건**(편집 앵커 · 본 엔트리 본문 양쪽).
- **V4 🔴 한글 전수 검증** — 추가분에서 착수 전 파일에 **없던 한글 단어**를 전건 문맥과 함께 출력했고, **신규 음절**도 전건 문맥을 확인했다. ⚠️ **「신규 음절 0」은 충분조건이 아니므로**(기존 음절로의 치환은 통과한다) **단어 단위 출력**을 정본으로 삼았다. **바이트 기준 보강** = UTF-8 strict decode **통과** · `U+FFFD` **0건** · 제어문자 **0건**.
- **V5 수치 1:1 대조** — 6.7 · 7.7(l) · 6.2의 전 수치를 `pr64_e2_runtime.log` · `pr64_server.log` · `pr64_interactive.log`와 `git show d093d70` · 헤더 실물에 **1:1 추적**했다. **로그에 없는 수치 0건 기재**이고, 위임과 어긋난 **2건은 로그 값으로 등재**했다(위 catch 절).
- **V6 git status** — `docs/` **2파일만**. 시크릿 스캔(SSID · 토큰 · 자격증명 · IP 패턴) 실제 검출 **0건** — 보드·서버 사설 IP(`172.20.10.*`)와 SSID는 **본 문서에 0건** 기재다.

**비범위**: **코드 0 수정** — `server/` · `dashboard/` · `ml/` · `firmware/` 전부 **읽기만**(L4 재검증은 `-fsyntax-only`라 **산출 파일 0**, 대상 파일 무변경). **노션 무접촉**(Set 3 소관) · **프로젝트 지침 파일 무접촉**(Set 2 소관). 🔴 **미결 상태 전환 0건** — 7.7(l) · 7.6(i)는 **입력만** 더했고 6.3(n) · G29 pre:post · 카메라 init 시점은 **무접촉**이다. **회귀 케이스 106 무변경**(서버 무접촉). **27.8(d) 누적 숫자 무변경.** **미착수** = PR-C(타임아웃·녹음 길이·해상도 상수 확정) · 1차 rtt 교대 재측정 · QVGA↔VGA 비교 · 실 초인종 음원 · 부스 소음 재현 · 터널 기동 사진 실렌더 · 대시보드 확인 · `gdma_disconnect` 기전 규명.

**학습 적용**: **학습 13**(인용 전 grep — 편집 앵커 전건 `count == 1`, **라인 번호 0건**. 부재 판정은 **마커를 걷어낸 부분 문자열**로 재조회) / **학습 14 · 27**(위임이 적은 상수·차단 사유를 **실물 파일·컴파일러로 직접** 확인 — `Arduino.h` 차단이 그 결과다) / **학습 17**(🔴 **위임 본문 catch 2건** — 차단 메커니즘 · PSRAM 분모. 전부 **원본 로그·실측 값 채택 후 보고**) / **학습 19**(근본원인 진단 재검증 — 「상수 미작동」 판정을 **코드로 뒤집어** `urlopen` 성질로 규명, 27.8(n)④) / **학습 21**(미결도 유령일 수 있다 — 🔴 **역방향을 경계했다**: ④런타임이 4/4 관통했다고 **7.7(l) · 7.6(i)를 해소로 날조하지 않았고**, 반대로 6.3(o) 「5종」을 **이미 갱신돼 있는데 4종으로 오독**하지도 않았다) / **학습 16 ★판정 규칙**(위임 지정이 실물과 안 맞을 때 **불변식 유지 + 메커니즘 등가 치환** — L4 서술 정정이 그 사례) / **「발견일 ≠ 반영일」**(6.7 실측 · L1~L4 = **2026-09-18** 발견·반영 / MANSHIP 서지 = **2026-09-16 발견 · 2026-09-18 반영**으로 갈라 표기) / **「실측 / 논증 / 문서 인용 3분」**(rtt · PSRAM · 서버 로그 시각차 · 컴파일 결과 = **실측** / 타임아웃 파급 산술 · 1차 rtt 교란 ③ = **논증**(「입력 실측 = …」 분리 표기) / 확정 8건 = **사용자 결정** / MANSHIP = **웹 서지 확인**. **한 문장에 섞지 않았다**).

**관련 카테고리**: **6.7 (PR #64 배관 + ④런타임 — 신설)** / **6.5(d)(f) (PR-B 실행됨 · 확정 8건 부분 해소)** / 6.5(b) (`enrich_status` 계층 보강) / 6.5(e) (M-1 미착수 · 세션 ≤12 출처) / **6.2 (🔴 1차 rtt 교란 단서 — 원인 미지정)** / 6.3(h) (정수 버퍼 선례) / **6.3(o) (호스트 테스트 5종 → 6종 · L2 · L4)** / 6.6 (PSRAM 30,952 B 대조 · `gdma` 줄 부재 대조 · ARP 함정) / **카테고리 16 (env 12개 → 13개)** / 7.6(e) (자막 부재 경로 첫 실기기 통과) / **7.6(i) (🔴 재판단 입력 · 미결 유지)** / 7.7(b) (STT 성공 ≠ 알림 성공) / 7.7(g) (2차 15초 예산) / 7.7(j) (실 육성 경계 갱신) / **7.7(l) (🔴 재판정 입력 · 미결 유지)** / 7.7(m) (🔴 병치 금지) / **카테고리 20 (ESP32 빌드 비결정 — 툴체인 확장)** / **27.8(n) (오류 4건)** / 27.8(c)③ (L1의 선행 패턴) / 27.8(d)(i) (누적 숫자 무변경 — 사용자 판단 대기) / **33.9 (MANSHIP 서지 — 신설)** / 학습 13 · 14 · 16 · 17 · 19 · 21.
**관련 commit**: `d093d70`(**PR #64 squash — 본 절의 대상 코드**, 착수 시점 HEAD) · 선행 = `63a6f88`(PoC-(51)·(52) 문서 커밋). 문서 반영 = 본 커밋(docs-only, **PR 없음, main 직 push**).
