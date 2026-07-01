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
