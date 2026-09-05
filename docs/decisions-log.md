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
