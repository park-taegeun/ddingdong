# 🔴 Decisions (SSoT — Single Source of Truth)

> 본 문서는 띵동 프로젝트의 **모든 결정**의 단일 진실 원천(SSoT)이다.
> 코드/펌웨어 작업 전 반드시 git pull로 최신본을 받은 후 작업할 것.
> 결정 변경 시 본 채팅방(전략) → 본 문서 갱신 → 채팅방 2(구현) 순서.
>
> 변경 이력은 `decisions-log.md` 참조.

---

## 카테고리 1: 하드웨어

- **메인**: XIAO ESP32-S3 Sense Pre-Soldered (8MB PSRAM, OV3660, USB-C)
  - ※ OV3660 → `xclk_freq_hz=20000000` 분기 필수
- **마이크**: INMP441 (THC-AS01 호환 칩, SNR 61dBA) — `I2S_NUM_1`
- **사람 감지**: VL53L5CX-SATEL (8x8 ToF, I2C)
- **핀 페리페럴**: I2S0(카메라) ↔ I2S1(마이크) 분리, strapping 핀(D0/D3/D6/D7) 회피

---

## 카테고리 2: 핀 표 (변경 시 반드시 갱신)

| 모듈 | 신호 | XIAO | GPIO | 페리페럴 |
|------|------|------|------|---------|
| INMP441 | SCK | D1 | 2 | I2S1 |
| INMP441 | WS  | D2 | 3 | I2S1 |
| INMP441 | SD  | D8 | 7 | I2S1 |
| INMP441 | VDD/GND/L_R | 3V3/GND/GND | - | - |
| VL53L5CX | SDA | D4 | 5 | I2C |
| VL53L5CX | SCL | D5 | 6 | I2C |

---

## 카테고리 3: 시스템 흐름

- **ToF**: 상시 ON (8x8 그리드 15Hz), ESP32에서 차단 X, 메타데이터로 첨부
- **음향 트리거**: 단순 RMS 임계값 (옵션 A), PoC 1주차 자체 측정 후 80% 지점 확정
- **클래스별 ToF 정책 분기 (서버)**:
  - 화재경보: ToF 우회 (무조건 발송)
  - 노크: ToF 사람 검증
  - 초인종: ToF + (등록 시) SP/DTW + cosine
- **신뢰도 임계값**: 70% 미만 미전송
- **카메라 캡처**: Lokch777 패턴 멀티코어 (Core 1 병렬)
- **1차 알림 목표**: ≤5초 (텍스트), **2차 알림 목표**: ≤15초 (사진+STT)

---

## 카테고리 4: ML

- **YAMNet Fine-tuning**: raw waveform(16kHz mono) → 1024-dim → Dense(3)
- librosa는 16kHz mono 변환 전용 (멜스펙트로그램 직접 입력 X)
- **초인종 개인 등록**: 멜스펙트로그램 2D 템플릿 + FastDTW SP/DTW + cosine distance
- **train/val/test 분할**: 파일 단위 필수 (data leakage 방지)
- **predicted_class 3종 (enum, 2026-05-28 PoC-(14) 확정)**: 초인종(`doorbell`) / 노크(`knock`) / 화재경보(`fire_alarm`) — Dense(3) 출력 매핑. 서버/대시보드 API 전역 enum (코드: `dashboard/src/types/notification.ts` `PredictedClass`). 한글 표기 = **"초인종"** (카테고리 3/5 SSoT 컨벤션, "도어벨" 미사용 — 카테고리 29.5 참조)

---

## 카테고리 5: ML 데이터

- **확보량(01_clips)**: 초인종 436 / 노크 714 / 화재경보 1648 = **2,798클립**
- **분할 결과**: train 1954 / val 434 / test 410
- **직접 녹음 계획(필수)**: 초인종 90 / 노크 180 / 화재경보 240
- **Augmentation**:
  - time-stretching ×0.85/1.15
  - BG noise SNR(초인종·노크 10/20dB / 화재 25/35dB)
  - volume -6dB
  - pitch ±2semitone (한국 환경음만)
  - SpecAugment freq=10/time=5
- **클래스 가중치**: class_weight + sample_weight 1.5~2.0배 (한국 환경음)
- **제외**: FSD50K Alarm 435, AudioSet fire_alarm 100 (대부분 차량 사이렌)
- **저장 정책**: 8주차 진입 시 재정의 (현재 `ml/` 폴더는 `.gitkeep`만)

---

## 카테고리 6: 서버

- AWS EC2 t3.small (서울, 2GB RAM)
- Nginx + Gunicorn(워커 2개, `preload_app=True`) + Flask
- SQLite + Flask-SQLAlchemy
- TLS: Let's Encrypt + ESP32는 `setInsecure()` (PoC 한계)
- **API**: `/api/v1/*` 버저닝 (2026-05-28 확정 — 기존 `POST /api/detect`·`POST /api/enrich`에서 버저닝 전환, decisions-log 2026-05-28 참조)

### 6.1 API 명세 1차 확정 (2026-05-28 PoC-(14), Phase 1 대시보드 셋업 연동)

> 상세 요청/응답 JSON 구조 = `dashboard/src/types/` (`api.ts` / `notification.ts` / `stats.ts`) + PoC-(14) 채팅방. 본 카테고리엔 **결정 + 근거만** (JSON 미박음).

- **엔드포인트 버저닝**: `/api/v1/*` — `detect`(ESP32→서버 1차) / `enrich`(ESP32→서버 2차 사진+음성) / `notifications`(대시보드 폴링) / `stats`(대시보드 폴링). 근거: 향후 API 변경 시 v1/v2 병행 + 대시보드 폴링 엔드포인트 확장
- **인증 분리**: Device Bearer Token (ESP32, `firmware/include/secrets.h`) ↔ Dashboard Bearer Token (React, `.env`) — 디바이스/대시보드 권한 도메인 분리
- **통신**: HTTPS 강제 (Let's Encrypt + ESP32 `setInsecure()`, 본 카테고리 TLS 항목 일치)
- **요청 추적 분리**: `client_request_id` (ESP32 자체 생성, 재시도 멱등 키) + `request_id` (서버 ULID 발급) — 디바이스/서버 추적 ID 분리 (코드: `notification.ts`)
- **HTTP Status 8종 + rate limit**: `device_id` 5초당 1회, 초과 시 `Retry-After` 헤더
- **Idempotency**: `idempotency_keys` 테이블 (24시간 TTL) — `client_request_id` 기반 재시도 중복 차단
- **stats period**: `today` 단일 (Phase 1, 코드 `stats.ts` `StatsPeriod`)

---

## 카테고리 7: STT + 알림

- **STT**: Naver Clova Speech (CSR) — 인터폰 노이즈 CER 6.49%
- **카카오톡**: '나에게 보내기' (memo) — 비즈 앱 심사 회피
- **이미지**: 카카오 이미지 업로드 API (S3 불필요)
- **토큰**: 액세스 6시간 + 리프레시 60일, SQLite 저장
- **토큰 상태 API (2026-05-28 확정)**: 대시보드 응답은 절대 만료시각 대신 **상대값** `kakao_token_expires_in_minutes` + `status` enum(`valid`/`expiring`/`expired`) 노출 — 클라이언트 시계 오차 무관 + 대시보드 "토큰 만료 임박" 경고 UI 직결 (코드: `dashboard/src/types/stats.ts` `SystemHealth`)
- **2차 알림**: best-effort + 1회 재시도
- **화재경보 알림 형식** (2026-05-09 추가, 카테고리 26 시연 시나리오 연동): 강조 표현 + 정부 지정 대응 수칙 동시 발송. 1차 알림만 (2차 사진 + 자막 미발송). ToF 사람 검증 우회 (카테고리 3과 동일 정책)

---

## 카테고리 8: 대시보드

- Vite + React + shadcn/ui (Tailwind)
- REST 폴링 3초
- 접근성 UI: 단계별 온보딩 + 물음표 모달

### 8.1 5/26~6/14 chunk 단계별 진행 결정 (2026-05-26 신설, 메이크잇펀 일시품절 chunk 활용)

**배경**:
- 메이크잇펀 일시품절 catch (2026-05-26 14:20, decisions.md 카테고리 22.7 도착 정정) → 부품 도착 약 6/17~6/19 예상
- 5/26~6/14 약 20일 chunk = 부품 무관 작업 진행 영역 → 학부생 제안 (5/26): "부품은 15일까지 대기하고 그 전에 다른 작업을 하는 건 어때 예를 들어 뭐 웹 대시보드를 개발한다던가 (ui 등) 부품 없이도 뭐 할 게 있지 않을까?"
- 학습 17 유도리 마인드 정합 — 외부 의존 chunk 슬립 시 부품 무관 작업 자유 재배치 가능

**결정**: 단계별 진행 (Phase 1 React 단독 → Phase 2 React + Flask)

**근거**:
- 학부생 React 익숙 + Flask 처음 (학부생 직접 catch, 5/26)
- 동시 진행 (A + B) 시 학습 부담 매우 높음 + catch 그물 작동 위험 ↑
- 단계별 진행 = 학부생 익숙 영역 (React) 먼저 진행 → Phase 2 진입 시 Flask 1차 학습 + React 익숙 상태 = 학습 시간 분산 + 9월 발표 안정성 ↑

**Phase 1: React 웹 대시보드 단독**:
- 작업 범위: Vite + React + shadcn/ui + Tailwind 셋업 + UI 골격 + 핵심 컴포넌트 (알림 카드 / 통계 / 설정 / 접근성 UI) + mock JSON 데이터 (카테고리 4 API 명세 1차 안 기반) + REST 폴링 3초 구조
- 위임 프롬프트 진행 방식: 카테고리 4 + 8 cross-reference catch 강제 (API 명세 1차 결정) + find-skills MCP 활용 강제 (frontend / react / vite / shadcn-ui) + 코드 작성 자체 검증 3단계 강제
- **✅ 완료 (2026-05-28 PoC-(14), PR #1 머지)**: 69파일 / 9180줄. Playwright 실동작 검증 통과 (5종 알림 카드 분기 + 다크모드 + Pretendard 실로드 + 콘솔 0 에러). 확정 기술 스택 / 컴포넌트 17개 / 디자인 토큰 = 카테고리 8.2 / API 명세 = 카테고리 6.1·4·7. ※ Phase 2 전환 = 학부생 자율 (날짜 미고정, 학습 17 정합)

**Phase 2: React + Flask 동시 (Flask 학습 진입)**:
- 작업 범위: Flask + SQLAlchemy 모델 + API 엔드포인트 (학부생 MacBook M4 로컬 진행) + POST /api/detect + POST /api/enrich 1차 구현 (카테고리 4) + React mock → 실제 API 전환 + REST 폴링 실제 동작 검증 + 미니 E2E 통합 1차
- 위임 프롬프트 진행 방식: Flask 학습 곡선 catch 강제 (학부생 첫 진입 = Claude Code MCP가 본문 설명 + 코드 작성 + 학습 영역 분리 강제) + 자체 검증 3단계 강제
- AWS EC2 인스턴스 띄우는 시점 = 11~12주차 (7/27 이후) 진입 시 (Phase 2는 로컬 단독, AWS 비용 0원)

**Phase 1 → Phase 2 전환 트리거** (학부생 자율, 학습 17 정합 — 날짜 박지 X):
- Phase 1 React UI 골격 + mock 데이터 완성도 학부생 자체 평가 후
- 학부생 컨디션 + 학교 일정 + Flask 학습 진입 의지 catch 후
- 메이크잇펀 도착 catch 결과 (6/15 이전 / 이후) 무관

**SSoT 영역 vs 학부생 자율 영역**:
- SSoT 박음: Phase 1 / Phase 2 작업 범위 + Phase 2 로컬 진행 강제 (AWS 비용 0원)
- 학부생 자율 (날짜 X): Phase 1 → Phase 2 전환 시점 + 일별 작업 강도 + 휴식 chunk + Phase 2 완료 시점 + 메이크잇펀 도착 후 PoC 진입 시점

**학습 17 본문 강화 사례 (5/26 본 결정 진행 중 발굴)**:
- Claude (AI) 초기 박은 추천 본문에 세부 날짜 (Phase 1 5/26~6/3 / Phase 2 6/4~6/14) 박음
- 학부생 push back "단계별로 세부 날짜까지는 확정짓지마" → 학습 17 유도리 마인드 직접 위반 catch
- 정정 = chunk 단위 작업 범위만 SSoT, 세부 날짜 박지 X = AI 본인도 학습 17 catch 그물 작동 대상
- decisions-log 2026-05-26 entry로 영구 반영

### 8.2 Phase 1 확정 기술 스택 + 컴포넌트 + 디자인 토큰 (2026-05-28 PoC-(14))

**기술 스택**:
- Vite + React 19 + TypeScript + Tailwind v4 (CSS-first, `@theme inline` — `tailwind.config.js` 없음) + shadcn/ui
- 라우팅: React Router (v7 설치, v6 호환 API) — 5페이지 + 404
- 데이터 fetching: `fetch` + `useEffect` custom hook (`usePolling`) — TanStack Query 미채택 (Phase 1 단순성)
- 상태: Context API + `useState` (`OnboardingContext` / `SettingsContext`) — Zustand 미채택
- 아이콘: Lucide React / 차트: shadcn/ui Chart (recharts, lazy 분할)
- 폰트: Pretendard Variable

**컴포넌트 17개 (4계층) + StatsCardsSection**:
- 레이아웃 3: AppShell / Header / Sidebar
- 통계카드 4: TotalDetectionsCard / ClassDistributionCard / TimingMetricsCard / SystemHealthCard (+ StatsCardsSection 묶음)
- 알림 5: NotificationCard / List / Image / STT / StatusBadge
- 보조 5: EmptyState / ErrorBoundary / HelpTooltip / LoadingSkeleton / OnboardingModal

**페이지 5종 (+404)**: Home / Notifications / Stats / Settings / Help

**디자인 토큰**:
- 컬러 / 타이포 (Pretendard 정량) / 터치 타겟 (44 / 48 / 52 / 56px 단계)
- 화재경보 강조: `shake` + `pulse-border` 애니메이션 (+ `prefers-reduced-motion` 대응)
- 디자인 영감: 한국 대중 앱 (카카오톡 / 토스 / 당근) 우선

---

## 카테고리 9: VL53L5CX 사람 검증 단계

- **Stage A (필수)**: zone count 임계값 (1m 이내 ≥8 zone)
- **Stage B (필수)**: Motion Indicator + per-zone threshold
- **Stage C/D (선택)**: NanoEdge AI / Passing-by filter

---

## 카테고리 10: Git Convention

- 모든 commit 메시지는 **한국어**로 작성
- 형식: `{이모지} {Type}: {한국어 설명}`
- 사용 가능한 Type 14종은 `docs/git-convention.md` 참조
- 예시: `✨ Feat: camera_test.cpp 골격 추가`

---

## 카테고리 11: 사전 준비 일정 (5/7~5/17, 11일, 옵션 A)

- 5/7 (목): 사전 검증 ①② + monorepo 셋업 ✅
- 5/8 (금): WiFi 더미 테스트 (Day 2 우선, 가장 위험)
- 5/9 (토): 카메라 단독
- 5/10 (일): 마이크 단독
- 5/11 (월): ToF 단독 + 최종 점검 + 5/15 검증 체크리스트
- 5/12 (화): 외부 계정 + self-checkpoint (코어 분배 재검토)
- 5/13 (수, Day 7): 졸작 중간 발표 (데모 시나리오 v1, 피드백 0건 → 카테고리 26 v1 확정) + AWS 가입 + 보안 4종 (35분) + 카카오 디벨로퍼스 셋업 (5/14 오전 11분, Day 7 통합 — 학부생 의도) → 외부 계정 셋업 완료, 카테고리 30 신설
- 5/14 (목): 호환성 추가 검증
- 5/15 (금): 부품 수령 + 결선
- 5/16 (토): 결선 마무리 + 1차 부팅
- 5/17 (일): 1차 부팅 + 5/18 준비

> 변경 사유: 사전 검증 ①②를 5/7 오전에 우선 배치 (코드 작성 전제조건). WiFi를 Day 2 우선 처리로 변경 (가장 위험한 작업 회복 시간 확보).

**5/17 이후 Day N 명명 폐기** (2026-05-25 학습 17 신규 발굴 근거):
- 사전 준비 11일 Day 1~Day 11 명명은 본 카테고리 11 본문에 한정 보존 (학습 8 원본 보존 패턴)
- 5/17 이후 외부 의존 가변 chunk 진입 시 Day N 명명 폐기 결정 (학부생 의도, 2026-05-25 PoC-(12) 본 작업)
- 폐기 사유: 학교 일정 / 부품 도착 / 외부 의존 chunk는 정량 일정 트래킹 불가능 → 학습 17 유도리 마인드 정합
- 신규 명명 패턴: 날짜 기반 ("5/25 (월)") + 학습 9 chunk 경계 정렬 + 학습 17 유도리 마인드
- 노션 DB1 row 제목 패턴 동시 전환 (Day 1~Day 8 보존, 5/25 row부터 날짜 명명)
- decisions-log.md entry 헤더 패턴 동시 전환 (2026-05-25 entry부터 날짜 명명)

---

## 카테고리 12: 사전 검증 결과

### ① VL53L5CX SparkFun lib + ESP32-S3 — 조건부 GO
- **4가지 워크어라운드**: I2C 1MHz / SATEL 모듈 / 단일 센서 / Adafruit_VL53L5 폴백
- **참고 코드**: https://github.com/susesKaninchen/OnlyFeet (XIAO Sense + 8x8/15Hz, 2026-05 활성)
- Arduino-ESP32 core 3.x + SparkFun lib 1.0.3 호환성 확인됨 (monorepo 셋업 시 자동 검증, 카테고리 16 참조)
- 시간 영향: +1h (5/11 ToF 코드)

### ② Lokch777 패턴 OV3660 멀티코어 — OV2640 포팅 추정 GO
- 실질 OV3660 멀티코어 사례 5건 (OnlyFeet 80% 매칭 + 4건)
- 5/9 카메라 코드 7가지 + build_flags 사전 반영 (카테고리 13)
- 5/21 코어 분배 잠정 안 (5/12 재검토, 카테고리 15)
- 시간 영향: +1h (5/21 PoC 통합)

---

## 카테고리 13: 5/9 카메라 코드 사전 반영 사항

```c
.xclk_freq_hz = 20000000          // Medium 권장
.fb_count = 2                     // dual buffer 필수
.fb_location = CAMERA_FB_IN_PSRAM
.grab_mode = CAMERA_GRAB_LATEST
.jpeg_quality = 12                // Medium 권장값, 화질-용량 균형
.pixel_format = PIXFORMAT_JPEG
.frame_size = FRAMESIZE_QVGA      // 또는 VGA
```

- `esp_camera_fb_return()` 후 `vTaskDelay(pdMS_TO_TICKS(30))` 필수
- 추가: 메모리 진단 코드 (PSRAM total/free, heap free, assertion)
- 참고: https://github.com/susesKaninchen/OnlyFeet/blob/main/src/main.cpp + Manjot Khangura Medium 글

---

## 카테고리 14: 5/11 ToF 코드 사전 반영 사항

1. `platformio.ini` `lib_deps` (이미 카테고리 16에 반영됨):
   - `sparkfun/SparkFun VL53L5CX Arduino Library` (메인)
   - `https://github.com/adafruit/Adafruit_VL53L5.git` (폴백)
2. `setup()`에 `Wire.setClock(1000000)` 명시
3. 단일 센서 구성 (issue #5 회피)
4. SATEL 모듈 사용 (제네릭 모듈 init fail 회피)
5. 빌드 단계 즉시 검증: Arduino-ESP32 core 3.x 호환성 (이미 확인됨)

참고: https://github.com/susesKaninchen/OnlyFeet/blob/main/src/main.cpp

---

## 카테고리 15: 5/21 PoC 통합 코어 분배 잠정 안 (5/12 재검토)

```
Core 0:
  - micTask     (priority 4)
  - tofTask     (priority 3)

Core 1:
  - cameraTask  (priority 4)
  - wifiTask    (priority 3)   ← 별도 task로 분리 (cameraTask blocking 회피)
```

### 5/12 재검토 항목 (단독 테스트 결과 기반)
1. mic priority 5 vs 4 비교 (RMS 손실 발생 여부)
2. cameraTask 단독 vs writerTask 분리 시 fb_get 안정성
3. ToF 15Hz 유지율 (다른 task에 의해 누락되는지)

> **5/12 메모리 self-checkpoint 결과 (카테고리 17.1.1)**: 정적 SRAM 18.2% / Flash 31.6%, Plan B 미발동 → **메모리 측면 잠정안 유지 가능**. 타이밍 self-checkpoint (17.1.2) 결과 대기 (5/15+ 부품 도착 후).

---

## 카테고리 16: monorepo + PlatformIO 셋업 결과 (2026-05-07)

- **컴파일**: SUCCESS (14.25초, RAM 5.6% / Flash 7.6%)
- **platform**: `espressif32@7.0.0`
- **framework-arduinoespressif32**: `3.20017.241212` (Arduino-ESP32 core 3.x)
- **SparkFun VL53L5CX 1.0.3**: 호환성 확인 완료
- **Adafruit_VL53L5**: PlatformIO Registry 미등록 → GitHub URL 직접 사용 (master 브랜치)
- **PlatformIO CLI**: `/tmp/pio-venv` (PEP 668 호환 venv)
- **Commit**: `6f1cecf` + `dd55759`
- **5/11 ToF 코드 작성 시 결정 사항**: Adafruit_VL53L5 master 추적 vs commit pin (master 추적 불안정 시 commit pin)

### 16.1 더미 테스트 누적 RAM/Flash 측정 결과 (2026-05-11 갱신)

PlatformIO env 분리 구조로 5/8~5/11 더미 테스트 결과 누적:

| 일자 | env | 작업 | RAM | Flash | 핵심 commit |
|------|-----|------|-----|-------|-------------|
| 2026-05-07 | (단일) | monorepo 초기 셋업 | 5.6% | 7.6% | `6f1cecf`, `dd55759` |
| 2026-05-08 | poc | WiFi + HTTPS 더미 | 13.8% | 25.8% | `3ec17d4` |
| 2026-05-09 | camera_v1 | 카메라 단독 (cameraTask) | 7.0% | 9.4% | `aa6116d`, `8ce56ed` |
| 2026-05-09 | camera_v2 | 카메라 분리 (writerTask) | 7.0% | 9.4% | `aa6116d`, `8ce56ed` |
| 2026-05-10 | mic_dummy | 마이크 단독 (INMP441 + I2S1) | 8.1% | 8.1% | `ff3f46b`, `eb1b451` |
| 2026-05-11 | tof_dummy | ToF 단독 (VL53L5CX + I2C) | 6.1% | 11.1% | `b2434af`, `dd8ed66` |

**5/10 mic_dummy 부연**:
- 라이브러리: legacy `driver/i2s.h` (arduino-esp32 v3.20017 SDK packaging 제약, 카테고리 28 학습 15 참조)
- 정적 메모리: `audio_buffer` + `scratch` = 8 KiB BSS (DMA 32-bit mono × 1024 frames × 2 buffer 정적 할당, 카테고리 29 학습 16 참조)
- INMP441 250ms 파워업 노이즈 처리 + 14 DMA buffers 폐기 (datasheet 2^18 SCK cycles ≈ 256ms 일치)

**5/11 tof_dummy 부연**:
- 라이브러리: SparkFun_VL53L5CX_Arduino_Library 1.0.3 (1차) + Adafruit_VL53L5 master (폴백, lib_deps만 등록 dead code elimination)
- 메모리: mic 대비 RAM ↓ (I2S DMA 4 KiB 부재) / Flash ↑ (VL53L5CX FW upload buffer ~86KB 포함)
- I2C 1MHz / 8x8 64 zones / 15Hz (datasheet 8x8 mode max, SparkFun Example3 검증 패턴)
- graceful: `initToF()` 실패 시 task spawn 생략 → `loop()` idle 진단만 (mic_test 패턴 100% 일치)
- 학습 13 catch 33개 / 학습 14 mic 컨벤션 100% 일치 / 학습 15 단계 4 (런타임) 5/15+ 보류

**env 분리 구조 (build_src_filter)**:
- `env:poc` — WiFi 더미 테스트 (5/8 본 작업)
- `env:camera_v1` — Version A (cameraTask 단독)
- `env:camera_v2` — Version B (writerTask 분리)
- `env:mic_dummy` — 마이크 단독 (5/10 신규)
- `env:tof_dummy` — ToF 단독 (5/11 신규)

**5/12 메모리 self-checkpoint 입력 데이터 (정적 budget)**:
- 320KB SRAM 한계 / 3.34MB Flash 한계 / 8MB PSRAM 한계
- 5/8 사전 추정: SRAM 22% / Flash 42% / PSRAM 50KB (~0.6%) — **5/12 실측으로 정정됨**
- 5/12 실측 (방법 1 delta sum, 카테고리 17.1.1.1): SRAM **18.2%** / Flash **31.6%** / PSRAM 50KB — Plan B 미발동 (카테고리 17.1.1.2 Stage 1 임계값 25%/40% 안전 여유)
- **동적 heap 측정 (`ESP.getMinFreeHeap()` + stack high-water mark)** 은 **11주차 통합 테스트로 분리** (카테고리 17 별도 검증 항목 참조)

---

## 카테고리 17: 별도 검증 항목

- **11주차 진입 전** esp32-camera issue #620 (WiFi join 후 fb_get fail) 재현 시도
  - 워크어라운드 후보: `fb_count=3` / WiFi power save 비활성화 / init 순서 변경
  - URL: https://github.com/espressif/esp32-camera/issues/620
  - **동적 heap 추적 (`ESP.getMinFreeHeap()` + stack high-water mark) 동시 진행** (2026-05-09 추가, SRAM 동적 소비 분석)
- **5/12 self-checkpoint**: 단독 테스트 4개 종합 → 5/21 통합 코어 분배 최종 확정 (카테고리 15)
  - **2026-05-08 갱신**: 자성리얼 부품 배송 일정 변경(카테고리 22.6, commit `847c599`) 카스케이드로 self-checkpoint 분리. 17.1 참조.

### 17.1 self-checkpoint 분리 (2026-05-08 갱신)

자성리얼 부품 배송 일정 변경(5/15~5/28)으로 5/9~5/11 실측 데이터 수집 불가. 단, 5/8 WiFi 테스트와 동일한 "더미 테스트" 패턴(컴파일 + 메모리 사용량)은 부품 없이 진행 가능. self-checkpoint 입력 데이터를 메모리(부품 X 가능) + 타이밍(부품 필요)으로 분리.

#### 17.1.1 메모리 self-checkpoint (5/12 진행, 부품 X)

- **진행 시점**: 5/12 (5/9~5/11 더미 테스트 직후)
- **입력 데이터**: 5/9~5/11 더미 테스트 컴파일 결과
  - WiFi 더미 테스트 (5/8 commit `3ec17d4`): RAM 13.8% / Flash 25.8% ✅
  - 카메라 더미 테스트 v1/v2 (5/9 commit `aa6116d` + `8ce56ed`): RAM 7.0% / Flash 9.4% ✅
  - 마이크 더미 테스트 (5/10 commit `eb1b451`): RAM 8.1% / Flash 8.1% ✅
  - ToF 더미 테스트 (5/11 commit `dd8ed66`): RAM 6.1% / Flash 11.1% ✅
- **검증 범위**: **정적 budget 검증 한정** (컴파일 시점 측정값)
- **동적 heap 측정 (런타임)** 은 11주차 통합 테스트로 분리 (카테고리 17 참조)
- **검증 항목**:
  - PSRAM 8MB 한계 안에 들어오는지
  - 통합 시 메모리 fragmentation 위험 평가
  - 카메라 frame buffer + I2S DMA 버퍼 + ToF zone 데이터 동시 보유 가능성
- **산출물**: 통합 메모리 budget 표 (카메라 + 마이크 + ToF + WiFi 합산)

##### 17.1.1.1 통합 budget 추정 결과 (2026-05-12 갱신)

**산출 방법** — 방법 1 (delta sum, 채택) + 방법 2 (단순 합산, 참고):

| 일자 | env | RAM | Flash | RAM delta (vs baseline) | Flash delta (vs baseline) |
|------|-----|-----|-------|-------------------------|----------------------------|
| 2026-05-07 | (단일 baseline) | 5.6% | 7.6% | — | — |
| 2026-05-08 | poc (WiFi+HTTPS) | 13.8% | 25.8% | +8.2pp | +18.2pp |
| 2026-05-09 | camera_v2 | 7.0% | 9.4% | +1.4pp | +1.8pp |
| 2026-05-10 | mic_dummy | 8.1% | 8.1% | +2.5pp | +0.5pp |
| 2026-05-11 | tof_dummy | 6.1% | 11.1% | +0.5pp | +3.5pp |

> 베이스라인 정의: 5/7 monorepo 셋업 시 단일 env (Arduino core + FreeRTOS + Serial + USB CDC + nvs_flash 등 공통 부분)

**방법 1 — delta sum (정적 추정 채택)**:
- RAM = baseline + Σ(delta) = 5.6 + 8.2 + 1.4 + 2.5 + 0.5 = **18.2%** (~59,640 bytes / 320 KiB)
- Flash = baseline + Σ(delta) = 7.6 + 18.2 + 1.8 + 0.5 + 3.5 = **31.6%** (~1,056,178 bytes / 3.34 MB)
- 근거: 베이스라인은 모든 env에 공통 포함 → 1회만 카운트, 페리페럴별 delta는 중복 없이 가산

**방법 2 — 단순 합산 (참고용, 베이스라인 4× 중복)**:
- RAM: 13.8 + 7.0 + 8.1 + 6.1 = **35.0%** (Σ env, 베이스라인 4중 카운트)
- Flash: 25.8 + 9.4 + 8.1 + 11.1 = **54.4%** (Σ env, 베이스라인 4중 카운트)
- 한계: 통합 binary는 단일 baseline + 페리페럴별 코드 → 방법 2는 over-count

**페리페럴별 정적 contribution (방법 1 delta 분해)**:

| 페리페럴 | RAM delta | Flash delta | PSRAM | 출처 / 근거 |
|---------|-----------|-------------|-------|-------------|
| WiFi/HTTPS | +8.2pp (~26.9 KB) | +18.2pp (~608 KB) | 0 | esp_wifi.a + lwIP + wpa_supplicant + mbedtls (HTTPS) + WiFiClientSecure + HTTPClient + ArduinoJson. arduino-esp32 v3.20017 issue #5990·#9741 (WIFI_STA 진입 시 ~45KB heap 점유 패턴 일치) |
| 카메라 OV2640/OV3660 | +1.4pp (~4.6 KB) | +1.8pp (~60 KB) | runtime fb (별도) | esp_camera v2.1.2 driver + 센서 테이블. frame buffer는 `fb_location=CAMERA_FB_IN_PSRAM`으로 PSRAM 점유 (카테고리 13) |
| 마이크 INMP441 | +2.5pp (~8.2 KB) | +0.5pp (~17 KB) | 0 | legacy `driver/i2s.h` (카테고리 28 학습 15) + `audio_buffer + scratch = 8 KiB BSS` (32-bit × 1024 frames × 2 buffer 정적 할당, 카테고리 16.1 5/10 부연 일치) |
| ToF VL53L5CX | +0.5pp (~1.6 KB) | +3.5pp (~117 KB) | 0 | SparkFun_VL53L5CX_Arduino_Library 1.0.3 + Wire. RAM = `VL53L5CX_ResultsData ~1356B BSS` (카테고리 16.1 5/11 부연 일치). Flash 117KB ⊃ FW upload buffer ~84KB (UM2884 — 매 power-on 마다 host MCU가 I2C로 upload, RAM-based sensor) |

**PSRAM 활용 분석**:
- 카메라 frame buffer 한정: QVGA JPEG `fb_count=2` × `jpeg_quality=12` + line buffer + DMA descriptor → 약 50 KB 추정 (5/8 사전 추정 보존)
- 다른 페리페럴(WiFi/Mic/ToF): PSRAM 점유 0
- PSRAM 점유율: 50/8192 = **0.6%** — 8MB 한계 대비 매우 여유

**통합 추정값 (정적, 동적 별도)**:

| 자원 | 정적 추정 (5/12) | 동적 한계 (11주차 측정 예정, 추정치) | ESP32-S3 한계 |
|------|-----------------|----------------------------------|----------------|
| SRAM (BSS+DATA) | 18.2% (~59.6 KB) | + α (런타임 heap, 추정 +30~50% peak) | **320 KB** (arduino-esp32 user-available, datasheet 512KB 중 ROM/cache 점유 제외) |
| Flash | 31.6% (~1.06 MB) | (정적 한정, 동적 Flash X) | **3.34 MB** (default partition table) / 8 MB physical |
| PSRAM | ~50 KB (0.6%) | + α (카메라 동적 alloc 시 frame queue 변동) | **8 MB** (XIAO ESP32-S3 Sense) |

**5/8 PoC-(5) 사전 추정과의 차이 (정정 분석)**:

| 자원 | 사전 추정 (5/8) | 갱신 결과 (5/12) | 차이 | 정정 사유 |
|------|----------------|-----------------|------|-----------|
| SRAM | 22% | 18.2% | **-3.8pp** | mic delta 사전 +5% 가정 → 실측 +2.5pp / tof delta 사전 +3% 가정 → 실측 +0.5pp |
| Flash | 42% | 31.6% | **-10.4pp** | tof FW image 사전 +6%(~200KB) 가정 → 실측 +3.5pp(~117KB, FW 84KB + driver) |
| PSRAM | 50 KB | 50 KB | 0 | 카메라 frame buffer만 PSRAM 점유, 사전 추정 일치 |

→ **실측 결과 모두 사전 추정 안에 안전 수렴**. Plan B 트리거 미발동.

##### 17.1.1.2 Plan B 트리거 정량화 (2026-05-12 신설)

**임계값 산정 근거** (학습 16 적용 — 위임 프롬프트 일반론 30/50/70% 대신 ESP32-S3 한계 + 동적 마진 기반 재산정):

- ESP32-S3 user-available SRAM 320 KB (datasheet 출처)
- 정적 18.2% + 동적 typical 30~50% peak = peak 50~70% (WiFi + Camera 동시 활성 사례 기준)
- WiFi peak 동적 점유 ~80 KB (TLS handshake + lwIP TX/RX + HTTPClient body, arduino-esp32 issue #5990·#5630 패턴 인용)
- Camera I2S DMA + line buffer ~16 KB IRAM (frame buffer는 PSRAM)
- 4 task stacks ~16-32 KB
- Heap fragmentation 안전 마진 ~30-40 KB

| Stage | 트리거 조건 (정적 분석 기반) | 대응 |
|-------|------------------------------|------|
| **Stage 1** (알람) | 정적 SRAM ≥ **25%** OR 정적 Flash ≥ **40%** | 알람만, 작업 계속. `ESP.getMinFreeHeap()` + stack high-water mark 동적 측정 권장 (11주차 정식 항목, 카테고리 17) |
| **Stage 2** (최적화) | 정적 SRAM ≥ **35%** OR 정적 Flash ≥ **60%** | 최적화 검토. 후보: mic DMA buffer 8→4 (4 KiB BSS 절감) / VL53L5CX FW를 PSRAM 이전 (Flash ~84KB 절감) / WiFi sdkconfig minimal / HTTPS RX buffer 축소 |
| **Stage 3** (Plan B) | 정적 SRAM ≥ **50%** OR 정적 Flash ≥ **75%** | Plan B 발동. 후보: 카메라 QVGA → CIF / ToF 8x8 → 4x4 모드 (RAM ¼ 절감) / Adafruit_VL53L5 폴백 제거 / WiFi → ESP-NOW 대체 (lwIP/mbedtls 제외) |

> **현 상태 (5/12)**: 정적 SRAM 18.2% / Flash 31.6% — **모든 Stage 미발동** (Stage 1 임계값 25% / 40% 안전 여유)

##### 17.1.1.3 분석 근거 출처 (catch 24개 항목)

1. **ESP32-S3 datasheet** (5개): 512 KB on-chip SRAM (user-available 320 KB) / 8MB·16MB·32MB Flash 옵션 / 8MB·16MB PSRAM 옵션 / dual-core LX7 @ 240MHz / WiFi 802.11 b/g/n + BT 5 LE 통합 — Espressif ESP32-S3 Datasheet v2.2 (`espressif.com`)
2. **arduino-esp32 v3.20017** (4개): WIFI_STA 진입 시 ~45KB heap 점유 (issue #5990) / WiFi.h include만 ~500KB Flash (issue #9741) / MIN free heap 60-90KB peak / framework-arduinoespressif32@3.20017.241212 (카테고리 16)
3. **ESP-IDF heap_caps** (3개): `MALLOC_CAP_8BIT` / `MALLOC_CAP_DMA` (internal SRAM 한정) / `MALLOC_CAP_SPIRAM` 분리 — `heap_caps_get_free_size()` API 노출 (학습 15 검증)
4. **esp_camera 패턴** (4개): `fb_count` 다중 시 continuous mode (double-speed) / `CAMERA_FB_IN_PSRAM` (default high-res) / `CAMERA_FB_IN_DRAM` 옵션 (PSRAM 부재 시) / esp32-camera v2.1.2 ESP Component Registry / WiFi join 후 fb_get fail (issue #620, 카테고리 17 11주차 항목)
5. **legacy driver/i2s.h DMA** (3개): arduino-esp32 v3.20017 packaging `i2s_std.h` 미노출 (카테고리 28 학습 15 일치) / DMA buffer 정적 할당 패턴 (mic_dummy 8 KiB BSS) / I2S0/I2S1 controller 분리 (ESP32-S3 dual)
6. **VL53L5CX** (5개): FW upload ~84 KB (UM2884) / 매 power-on마다 I2C upload / RAM-based sensor (internal flash 없음) / I2C max 1 Mbits/s (datasheet) / ULD driver `/VL53L5CX_ULD_API` (SparkFun 1.0.3 = ULD 1.3.x 기반)

##### 17.1.1.4 한계

- **정적 분석 한정**: BSS + DATA + Flash 컴파일 시점 측정. 동적 heap fragmentation / 런타임 peak / task stack high-water mark 미반영
- **동적 heap 측정** (`ESP.getMinFreeHeap()` + `uxTaskGetStackHighWaterMark()`): 부품 도착 후(5/15+) 또는 11주차 통합 테스트로 분리 (카테고리 17)
- **페리페럴 동시 활성 fragmentation**: PoC 1주차 통합 시 실측 (5/21 시점, 카테고리 15·17.1.3)
- **Plan B 임계값**: 정적 분석 기반 1차 추정 — 동적 측정 후 (11주차) 재조정 가능
- **WiFi 동적 추정 80 KB**: arduino-esp32 일반 패턴 인용, 본 프로젝트 HTTPClient + ArduinoJson 7.x 조합 실측 미진행

#### 17.1.2 타이밍 self-checkpoint (부품 도착 + 실측 후)

- **진행 시점**: 부품 도착 + 단독 실측 완료 후 (잠정 5/18+, 부품 도착 시점 따라 가변)
- **입력 데이터**: 실측 데이터 3종 (카테고리 15 "5/12 재검토 항목" 원본 보존)
  1. mic priority 5 vs 4 비교 (RMS 손실 발생 여부)
  2. cameraTask 단독 vs writerTask 분리 시 fb_get 안정성
  3. ToF 15Hz 유지율 (다른 task에 의해 누락되는지)
- **검증 항목**: 코어 분배 잠정안(Core 0 = mic + tof / Core 1 = camera + wifi) 유효성
- **산출물**: 코어 분배 최종안 (또는 잠정안 수정안)

#### 17.1.3 5/21 통합 코어 분배 최종 확정 시점 영향

- 메모리 self-checkpoint(5/12) + 타이밍 self-checkpoint(부품 도착 후) 모두 완료 후 진행
- **5/12 메모리 self-checkpoint 결과 (카테고리 17.1.1)**: SRAM 18.2% / Flash 31.6%, Plan B 미발동 → 메모리 측면 잠정안 유지 가능
- 부품 도착 시점에 따라 자연 연기 가능성:
  - **최단 (5/15 도착)**: 5/18 타이밍 self-checkpoint → 5/21 가능 (PoC 1주차 진행 중)
  - **중간/최장 (5/22~5/28 도착)**: PoC 1주차 진입 후 처리 → Plan B 다단계 트리거 검토와 연결
- PoC 1주차 진행 상황 보면서 재평가 (5/21 시점 변경 X, 시점은 잠정 유지)

> 학부생 의사결정: **옵션 A** (PoC-(5), 2026-05-08). 카테고리 15 "5/12 재검토 항목" 원본 보존, 본 17.1이 분리 정의로 추가.

---

## 카테고리 18: 채팅방 운영 구조

### SSoT 우선순위
1. **GitHub repo (decisions.md / decisions-log.md)** — 최상위
2. 의사결정 채팅방 (PoC-(2) / 후속 채팅방, 도메인별 분리)
3. 도메인 위임 프롬프트 생성기 채팅방 (직접 코드 X)
4. Claude Code MCP (실제 작업 수행)
5. 노션 PoC 트래킹 (사람용 VIEW)

### 작업 체인
```
[의사결정 채팅방] ↔ [도메인 위임 생성기] → [Claude Code MCP] → [GitHub + 노션]
```

### Claude Code MCP 활용 원칙
1. `find-skills` MCP로 적합 skill 탐색 먼저 (강제)
2. skill 발견 시 → skill + 관련 MCP 조합
3. skill 없으면 → MCP 단독 수행 (검색 절차 절대 생략 X)
4. 활용 MCP: `github` / `context7` / `firecrawl-mcp` / `playwright` / `notion`

### 채팅방 분리 트리거
- **시점 기반**: chunk 종료 시점
- **컨텍스트 무게 기반**: 응답 느려지거나 헷갈림
- **사건 기반**: 큰 의사결정 후

### 인계 패키지 형식
```
# [채팅방 이름] 인계 패키지
## 🔗 SSoT
## ✅ 직전 채팅방 완료 사항 (5~7개)
## 🚧 진행 중 / 미결 사항 (3~5개)
## ⏸️ 다음 채팅방의 첫 액션 (1~3개)
## 🚨 미결정 / 보류 사항
## 📌 작업 원칙
```

### 컨텍스트 무게 자체 모니터링 (2026-05-07 추가)

클로드(의사결정 채팅방)가 학부생이 먼저 묻기 전에 능동적으로 채팅방 분리 제안.

**무거움 신호 6가지:**
1. 응답 텀 길어짐
2. 이전 결정 재확인 빈도 증가
3. 동일 주제 반복 질문
4. 컨텍스트 윈도우 한계 근접 추정
5. 한 채팅방에 도메인 4개+ 누적
6. 큰 의사결정 후 chunk 종료 시점 도래

**알림 형식:**
```
⚠️ 컨텍스트 무게 알림
🔍 감지 신호: [구체적 신호]
📊 현재 무게 추정: [경량/중간/무거움/매우 무거움]
🎯 분리 추천 시점: [지금 즉시 / 특정 시점 / 모니터링 지속]
📦 인계 패키지 준비 가능: YES/NO
💬 학부생 결정 필요
```

학부생 결정: 분리 진행 / 분리 보류 / 무시 (보류·무시 시에도 신호 누적 추적 계속)

---

## 카테고리 19: 노션 PoC 트래킹

- **위치**: 노션 워크스페이스 "청각 장애인용 초인종" → "킥" 하위에 "띵동(Ddingdong) PoC 트래킹" 페이지
- **도입 일자**: 2026-05-07
- **갱신 주기**: 매일 작업 종료 시
- **갱신 방식**: Claude Code MCP에 위임 프롬프트 제공
- **SSoT 아님** (VIEW), GitHub `decisions.md`와 충돌 시 **GitHub 우선**
- **의사결정은 절대 노션에서 X**

### 셋업 완료 결과 (2026-05-07)

- 페이지 1개 + 데이터베이스 3개 (가독성 6원칙 통과)
- 노션 페이지 ID: `359d8df0-3cab-816a-aedb-ec6341cc135e`
- DB1 (일자별 진행 로그) ID: `62a11105-c858-4eff-a151-268f3ffc4c9f`
- DB2 (사전 검증 결과) ID: `e9697017-4372-4253-8aac-ae4b4f391fd6`
- DB3 (미결정 항목) ID: `a319c04a-9201-417f-8552-7d6e99b2958f`

### Velog 분리 운영 (2026-05-07 추가)

- Velog 발행 기록은 학부생이 별도 노션 페이지에서 관리
- PoC 트래킹의 외부 링크에 Velog 시리즈 URL은 참고용으로 유지
- 매일 밤 루틴의 노션 갱신 위임 프롬프트 작성 시 Velog 관련 갱신 (발행 사실, Entry 번호, URL) 포함 금지
- PoC 트래킹은 개발 진행 트래킹 전용

---

## 카테고리 20: Git 워크플로우 (5/18 도입 예정)

### 사전 준비 단계 (~5/17)
- main 직 push 유지

### PoC 1주차 ~ 본격 개발 (5/18~)
- **GitHub Flow 단순화 모델** 도입
- **브랜치 명명**: `feat/{domain}-{task}` (firmware/ml/server/dashboard/fix)
- **main 보호 룰**: PR을 통해서만 머지
- **Squash merge** 기본
- **PR 머지 조건**: 컴파일 통과 + 한국어/이모지 commit + 금지 파일 미수정 + self-approve
- **Claude Code MCP 자동 처리**: 브랜치 생성 + 작업 + push + PR 생성
- **학부생**: PR 리뷰 + 머지

### 문서/코드 변경 push 분리 (2026-05-28 명문화)
- **문서 단독 변경** (`docs/*.md` — decisions.md / decisions-log.md / git-convention.md 등): **main 직접 push 허용** (PR 불필요)
- **코드 변경** (`firmware/` / `dashboard/` / `ml/` / `server/`): **feat 브랜치 + PR 강제**
- 근거: PR 목적 = 코드 품질 catch (컴파일 / 리뷰). 문서는 충돌·리뷰 불필요 → SSoT 갱신 지연 방지
- **Squash merge 기본 유지** (완화 X). ※ PR #1(2026-05-28)은 merge commit으로 머지된 1회성 예외 — repo Settings에서 Squash merging 활성화 후 복구 예정 (decisions-log 2026-05-28 참조)

### 5/17 종료 시점 액션
- 본 카테고리 세부 룰 최종 확정
- PoC-(2) 인계 패키지에 포함

---

## 카테고리 21: 매일 밤 작업 종료 루틴

의사결정 채팅방에서 다음 3가지 동시 출력:
1. `decisions.md` 갱신 위임 프롬프트 → Claude Code MCP에 던지기
2. 프로젝트 지침 수정본 → 학부생이 직접 갱신 (정적 변경 시만)
3. 노션 갱신 위임 프롬프트 → Claude Code MCP에 던지기

**우선순위**: GitHub `decisions.md` > 프로젝트 지침 > 노션 (충돌 시 GitHub 우선)

### Claude Code MCP 위임 시 자체 검증 3단계 강제 (코드 작성 관련, 2026-05-07 추가)

코드 작성/수정/라이브러리 통합/빌드 설정 변경 등 코드 관련 모든 위임 프롬프트에 다음 섹션 항시 포함:

**자체 검증 3단계:**
- ① 효율성 검토 (시간/메모리/CPU 점유율 / 불필요한 연산 / 알고리즘 복잡도)
- ② 리팩토링 검토 (가독성 / DRY 원칙 / 함수 분리 / 매직 넘버 const화 / 네이밍 일관성)
- ③ 오류 방지 검토 (엣지 케이스 / null·undefined / 메모리 누수 / 동시성 / 보안 취약점 / 컴파일 경고)

각 단계별 발견 사항 + 수정 사항을 출력 끝에 별도 섹션으로 명시 (통과/수정/무관 표시).

**적용 범위**: 신규 코드 / 기존 코드 수정 / 라이브러리 통합 / 빌드 설정 변경
**예외**: 단순 문서 작성 / 노션 갱신 / 리서치

### 노션 매일 갱신 5단계 표준 워크플로우 (2026-05-07 추가)

3번 노션 갱신 위임 프롬프트 작성 시 다음 5단계 그대로 적용:

1. **DB1 일자별 진행 로그**에 새 row 추가
   - 형식: "Day N (M/D)" + 단계 + 상태 + 핵심 결정 + commits

2. **페이지 상단 📌 메타 콜아웃 overwrite**
   - 마지막 갱신 시각 / 현재 단계 / 다음 마일스톤

3. **📋 오늘의 작업 체크박스 갱신**

4. **일정 vs 실제 표** 해당 날짜 행에 실제 결과 입력

5. **DB3 미결정 항목 상태 자동 전환**
   - 트리거 일자 임박 시 🟡 보류 → 🔴 트리거 임박

ID 참조:
- 노션 페이지: `359d8df0-3cab-816a-aedb-ec6341cc135e`
- DB1: `62a11105-c858-4eff-a151-268f3ffc4c9f`
- DB2: `e9697017-4372-4253-8aac-ae4b4f391fd6`
- DB3: `a319c04a-9201-417f-8552-7d6e99b2958f`

---

## 카테고리 22: 부품 발주 변경 (2026-05-07)

### 22.1 디바이스마트 발주 취소
- **사유**: XIAO ESP32-S3 Sense Pre-Soldered (102010635) 품절 통보
- **취소 처리**: 5/8(금) 17시 자동 취소 → 23,870원 환불 예정
- **영향**: 다른 발주 부품 5개 (INMP441, VL53L5CX-SATEL, KEYES 점퍼선 3종)는 정상 진행

### 22.2 자성리얼 네이버 스마트스토어 대체 발주
- **판매처**: 자성리얼 (smartstore.naver.com/jasungreal)
- **상품**: Seeed Studio XIAO ESP32 S3 Sense - 2.4GHz Wi-Fi, BLE 5.0, OV2640 카메라 센서
- **주문번호**: 2026050753038371
- **결제일**: 2026-05-07
- **결제 금액**: 36,540원 (원가 51,300원 - 할인 14,760원)
- **결제 수단**: 네이버페이 포인트 2,668원 + 머니 33,872원
- **옵션**: Size: Pre-Soldered / Color: ESP32C3 (옵션 강제 묶음)
- **배송 형태**: 국내 일시 품절 → 미국 본사 해외 직발송 (자성리얼 SMS 통보, 2026-05-08)
- **배송 일정**: 5/15~5/28 도착 (영업일 5~14일, 해외 직배송 통관 변동 포함)
- **마지막 갱신 일자**: 2026-05-08
- **갱신 사유**: 판매자 SMS 회신(2026-05-08) — 통관정보 회신 완료 (개인통관고유번호 P210018836994 + 박태근 + 휴대폰)
- **신뢰성**: 자성리얼 누적 판매 8,974건, 별점 4.98, 정품 인증 + 2년 보증

### 22.3 의사결정 근거
- **후보 비교**: 자성리얼 (36,540원, Pre-Soldered 확정) vs 메이크잇펀 (31,600원, "부착" 표기 모호)
- **선택 이유**:
  - Pre-Soldered 옵션 명시 확정 → 납땜 작업 0
  - 5/8 발송 → 5/15 데드라인 안전
  - 누적 판매 8,974건 + 별점 4.98로 신뢰성 검증
  - 메이크잇펀 톡톡 답변 5/8 17시 데드라인 전 도착 어려움 → 시간 안전성 우선
- **트레이드오프**: 4,940원 추가 비용 vs 시간 안전성 + 납땜 작업 0 + 신뢰성 → 시간 안전성 선택

### 22.4 잉여 ESP32-C3 보드 활용 계획
- **상황**: 자성리얼 옵션 강제 묶음으로 ESP32-C3 보드 1개 잉여 동봉
- **활용 1 (백업)**: 메인 ESP32-S3 펌웨어 작업 중 부팅 실패/벽돌 시 ESP32-C3로 WiFi/HTTP 더미 테스트 임시 진행 (5/8 WiFi 더미 테스트 일정 백업)
- **활용 2 (시연 백업)**: 졸작 발표 시연 직전 메인 보드 고장 시 임시 대체 (단, 카메라 없음 → 1차 알림 텍스트만 시연 가능, 화재경보 분류 OK)
- **활용 3 (졸작 후)**: 다른 IoT 토이 프로젝트 (홈오토메이션, BLE 비콘 등)
- **결론**: 잉여 부품 = 비용 손해 X, 백업 가치 있음

### 22.5 즉시 액션 항목 갱신
- 🟢 디바이스마트 자동 취소 + 환불 23,870원 정상 처리 완료 (2026-05-09 확인)
- 🟡 자성리얼 배송 추적 (5/15~5/28 도착 예상, 해외 직발송)
- 🟢 도착 후 ESP32-S3 Sense + ESP32-C3 보드 검수 (도착 시점 기준)

### 22.6 사전 준비 11일 영향 평가 (2026-05-08 동적 갱신)

자성리얼 배송 일정 변경(5/9~5/11 → 5/15~5/28)에 따른 사전 준비 11일(5/7~5/17) 영향:

- **5/9~5/14 (6일)**: 부품 부재 → 외부 계정 셋업 전진 + 호환성 추가 검증으로 활용 (5/14~5/15 학교 축제 휴식, 5/16 NCP 통합)
  - AWS EC2 t3.small 셋업 ✅ (5/13, 카테고리 30.1)
  - 카카오 디벨로퍼스 앱 등록 ✅ (5/13~5/14, 카테고리 30.2)
  - Naver Cloud Platform 계정 생성 ✅ (5/16, 카테고리 30.7)
  - VL53L5CX SparkFun lib 추가 검증 ✅ (5/7 monorepo 셋업)
  - Adafruit_VL53L5 폴백 lib_deps 사전 작성 ✅ (5/7 monorepo 셋업)
- **5/15~5/17 (3일)**: 부품 도착 시 결선 + 1차 부팅 (최단 5/15 도착 가정)
- **5/18 PoC 1주차 진입**: 정상 (부품 도착 후)
- **최악 시나리오 (5/28 도착)**: PoC 1주차 진입 후 부품 도착 → Plan B 다단계 트리거 검토 필요 (별도 미결정 사항)

큰 틀 변동 X — 5/15 최단 도착이 기존 11일 안에 포함되며, 5/9~5/14 공백은 외부 계정/호환성 검증으로 자연 활용.

> 22.3 의사결정 근거의 "5/8 발송 → 5/15 데드라인 안전" 문구는 의사결정 시점의 가정이므로 보존(이력성). 본 22.6이 사후 갱신된 실제 일정.

### 22.7 자성리얼 발주 결과 catch + 메이크잇펀 재발주 (2026-05-23)

**자성리얼 부품 도착 후 학부생 직접 화면 catch 결과 (학습 13)**:
- 도착 부품: ESP32-C3 (22.4 잉여 동봉분 그대로 도착)
- **메인 보드 = XIAO ESP32 S3 Sense Pre-Soldered 미동봉** (22.2 명시 메인 보드 부재)
- 발주 시점 가정 (22.2 + 22.3) vs 도착 실제 결과 mismatch

**대체 발주 (학부생 5/23 즉시 처리)**:
- 판매처: 메이크잇펀 (네이버 스마트스토어)
- 상품: 시드 스튜디오 샤오 ESP32-S3 센스 - Seeed Studio XIAO ESP32-S3 Sense
- 옵션: 핀헤더 부착 (Pre-Soldered)
- 주문번호: 2026052312703221
- 결제일: 2026-05-23 14:44:10
- 결제 금액: 28,600원 (상품 25,600원 + 배송비 3,000원)
- 도착 예상 (5/23 시점 가정): 2026-05-26 (화) ~ 2026-05-29 (금), 영업일 3~5일 기준 (5/23 토 발주 → 주말 끼고 영업일 계산)
- **도착 예상 정정 (5/26 학부생 직접 화면 catch 결과, 학습 13)**: 메이크잇펀 김정열 판매자 발송일 변경 통보 (5/26 14:20 카카오톡) — **2026-06-15까지 입고 후 발송 예정** (일시품절, 상품준비중). 학습 14 catch 그물 작동 사례 (외부 환경 가정 검증 강제 — 발주 시점 catch만으로 부족, 발송 시점 별도 catch 강제)

**학습 14 catch 그물 작동 사례 (외부 환경 가정 검증 강제)**:
- 22.3 의사결정 근거 = 의사결정 시점 가정 (자성리얼 = Pre-Soldered 확정, 메이크잇펀 = "부착" 표기 모호)
- 22.7 = 도착 후 실제 화면 catch 결과 (자성리얼 = 메인 보드 부재, 메이크잇펀 = 핀헤더 부착 확실)
- 가정만으로 부족 → 도착 후 화면 직접 catch 강제 패턴 영구 반영

**22.6 사전 준비 11일 영향 재평가 (2026-05-25 동적 갱신)**:
- 사전 준비 11일 (5/7~5/17)은 학부생 5/14~5/15 학교 축제 휴식 + 5/16 Day 8 NCP 셋업으로 사실상 5/16 종료
- 5/17~5/22 (6일) 작업 0건 (학습 9 chunk 경계 정렬 6일 확장) → 22.6 "5/15~5/17 부품 도착 시 결선 + 1차 부팅" 자연 슬립
- 22.7 메이크잇펀 도착 5/26~5/29 예상 (5/23 시점 가정) → PoC 1주차 5/18 진입 자연 슬립
- **22.7 도착 정정 (5/26 catch, 학습 14)**: 메이크잇펀 일시품절 → 2026-06-15까지 입고 후 발송 → 도착 약 6/17~6/19 예상. 5/26~6/14 약 20일 chunk 자연 슬립
- 5/26~6/14 chunk 작업 방향 = 카테고리 8 (대시보드) Phase 1 / Phase 2 단계별 진행 (별도 카테고리 8 본문 + decisions-log 2026-05-26 entry 참조)
- 학습 17 유도리 마인드 정합 — 22주 마스터 가이드라인 정량 데드라인 X, 본 약 1개월 슬립도 가이드라인 안에서 흡수 가능 (졸업 발표 9/30 기준 약 18주 남음)
- 학습 17 (유도리 마인드, 22주 일정 = 가이드라인) 정합

---

## 카테고리 23: 시연 네트워크 환경 = 모바일 핫스팟 (2026-05-08 결정)

### 배경
- 시연 장소: 학과 발표장
- 학과 발표장 학교 WiFi 신호 약함 (기존 WiFi 환경 의존 위험)
- 학교 WiFi는 802.1X (WPA2-Enterprise) 인증 필요

### 결정
- production 시연 환경 = WPA2-Personal (모바일 핫스팟)
- 개발 환경 = WPA2-Personal (집 WiFi)
- 학교 WiFi (802.1X / WPA2-Enterprise) 지원 통째로 폐기

### 영향
- 5/8 WiFi 더미 테스트 (commit 3ec17d4): WPA2-Personal 통합 환경
  - 빌드 환경 분리 (school/home) 폐기 → 단일 환경 유지
  - esp_wpa2.h / WPA2_ENT 코드 전부 미작성
  - 런타임 SSID fallback (PRIMARY → FALLBACK) 도입
  - secrets.h: PRIMARY (집) + FALLBACK (핫스팟) 2쌍 슬롯
- 사전 준비 11일 중 가장 큰 리스크 요인 (esp_wpa2.h 호환성) 제거
- WiFi 본 작업 시간 약 40% 단축 (1h~2h → 30분~1h)

### 폐기 옵션
- core 2.x 다운그레이드 (검토 안 함)
- 학교 WiFi 시연 (PoC 5주차 이후 연기 검토 안 함)

### 후속 영향
- 시연 당일: 핫스팟 SSID/비번 바뀌어도 secrets.h만 수정 후 재업로드 (재빌드 X)
- 발표장 환경 변경 시: 즉시 적응 가능 (런타임 fallback)

---

## 카테고리 24: IDE 환경 — clangd IntelliSense 시도 + 한계 + 우회 (2026-05-08 결정)

### 배경
- 학부생 IDE: Antigravity (VS Code fork)
- WiFi 본 작업 (commit 3ec17d4) 후 IDE에서 빨간 줄 21건 발생
- pio run -t compiledb 실행 후 15건으로 감소 (Arduino.h not found 해결)
- 그러나 ESP32 전용 컴파일러 플래그 (xtensa GCC) clangd 인식 못 함

### 시도 작업 (3 commits)

**시도 1 (commit 70c0664): .clangd 설정 추가**
- ESP32 전용 컴파일러 플래그 4종 clangd 무시 처리:
  - -mfix-esp32-psram-cache-issue (Xtensa GCC 전용)
  - -mlongcalls (Xtensa GCC 전용, LLVM은 ARM/MIPS/Hexagon만 지원)
  - -fstrict-volatile-bitfields (Xtensa GCC 전용)
  - -fno-tree-switch-conversion (GCC 전용)
- -ferror-limit=0 (clang 진단 표시 개수 제한 해제)
- 효과: Unknown argument 4종 사라짐 (15건 → 11건)

**시도 2 (commit d801e01): CompilationDatabase 경로 명시**
- 원인 분석: compile_commands.json이 firmware/ 안에 있어 clangd 매칭 실패
- 해결: CompileFlags 하위 `CompilationDatabase: firmware` 1줄 추가
- 효과: 효과 미달 (11건 → 11건, 변화 없음)

**시도 3 (보강, commit db38da0): compile_commands.json gitignore 차단**
- 부산물 파일 1.9MB + 절대경로 포함 → push 위험
- .gitignore에 단일 패턴 추가 (모든 하위 디렉토리 자동 매칭)
- 효과: push 위험 차단 완료 (`git check-ignore -v` 검증 통과)

### 잔존 진단 (11건)
- hal.h not found 1건 (헤더 경로 일부 인식 실패)
- JsonDocument operator[] 7건 (ArduinoJson 7.x C++17 features 인식 한계)
- serializeJson 1건 (cascading)
- HTTPClient::begin() 1건 (WiFiClientSecure 변환 인식 한계)
- WiFi.onEvent 1건 + template 1건 (core 3.x 시그니처 인식 한계)

### 결론
- ESP32 + clangd + ArduinoJson 7.x + Arduino-ESP32 core 3.x 조합에서 IDE 인식 한계 존재
- 펌웨어 동작 영향 0 (컴파일 SUCCESS 유지, RAM/Flash 변동 0%)
- 결정: **잔존 11건 무시, 작업 진행에 영향 없음**

### 향후 옵션 (필요 시)
- 옵션 A (현재 채택): 무시 (개발 시 살짝 거슬리지만 동작 영향 0)
- 옵션 B: clangd 끄고 VS Code 기본 IntelliSense 사용 (Cmd+, → `clangd.disable`)
- 옵션 C: ArduinoJson 7.x → 6.x 다운그레이드 (firmware/platformio.ini 수정 필요, 5/8 본 작업 영향 — 비추천)

### 5/9~5/11 작업 영향
- 카메라 / 마이크 / ToF 라이브러리 추가 시 동일 패턴 빨간 줄 가능
- 5/9~5/11 작업 시 빨간 줄 보여도 추가 트러블슈팅 X (이미 IDE 한계 판정)
- 라이브러리 추가 후 `cd firmware && pio run -t compiledb` 재실행은 권장 (compile_commands.json 갱신, 그러나 commit 안 됨)

---

## 카테고리 25: Khangura 함정 6개 코드 반영 표 (2026-05-09 신설)

출처: https://medium.com/@manjotkhangura/getting-esp32-s3-sense-ov3660-camera-working-a-weekend-deep-dive-941d9c1a05d8

| # | 함정 | 코드 반영 | 분류 | 반영 위치 / 미반영 사유 |
|---|------|-----------|------|--------------------------|
| #1 | OCTAL PSRAM | ✅ | 적절 | `camera_common.cpp:59-62` `psramFound()` + `platformio.ini:30` `BOARD_HAS_PSRAM` |
| #2 | Frame Buffer Overflows | 🟡 부분 | B (부품 도착 후) | `fb_count=2` ✅ `camera_common.h:43` / DMA mode sdkconfig 미반영 — OV3660 검출 + FB-OVF 관찰 시 보강 |
| #3 | Ran Out of PSRAM | ❌ | C (QVGA scope 무관) | HD frame buffer 한정. QVGA 0.25% 점유 → PSRAM 고갈 불가 |
| #4 | JPEG timeout | ✅ | 적절 | `camera_common.h:51` `vTaskDelay(30ms)` + `camera_common.h:41` xclk=20MHz + jpeg_quality=12 |
| #5 | Kconfig WiFi | ❌ | C (framework 차이) | ESP-IDF menuconfig 한정. Arduino + secrets.h가 등가 (5/8 main.cpp 반영) |
| #6 | Dark Images | 🟡 부분 | B (indoor footage 검증) | brightness 보정 ✅ `camera_common.cpp:81` (Khangura 직접 인용) / saturation은 Arduino-ESP32/Seeed 예제 출처 — 부품 도착 후 추가 gain tuning 결정 |

**요약**: ✅ 완전 반영 2개 (#1, #4), 🟡 부분 반영 2개 (#2, #6 → B 분류, 부품 도착 후), ❌ 미반영 2개 (#3 C scope 무관, #5 C framework 차이).

**부품 도착 후 (5/15~5/28) 처리 항목**:
- #2: OV3660 검출 + FB-OVF serial 로그 관찰 시 sdkconfig 패치 (PlatformIO `board_build.partitions` 또는 `platform_packages`로)
- #6: indoor footage 어두움 육안 판정 후 추가 gain/AEC tuning

**5/9 후속 질의 commit hash**: 검토만, 코드 보강 0건 (HEAD `8ce56ed` 유지)

---

## 카테고리 26: 시연 시나리오 틀 (2026-05-09 신설)

> 본 카테고리는 5/13 졸작 중간 발표 스크립트 기준으로 시연 시나리오 **확정 틀** 정착.
> 5/13 발표 후 추가 피드백 발생 시 갱신 가능 (학습 8 원본 보존 + 갱신 추적 패턴).
> **2026-05-13 발표 결과**: 교수님 반응 좋음, 추가 피드백 0건 → v1 그대로 확정 (DB1 v2 row 신설 불필요, DB3 미결정 "5/13 발표 후 카테고리 26 갱신 가능성" 🟢 해결 처리).
> 세부 디벨롭은 노션 "데모 시나리오" 페이지에서 트래킹 + Demo-Verify-(N) 채팅방 검증.
> 발표 스크립트 원본: `docs/presentation/2026-05-13-script.md`

### 26.1 USP 2개 (4/29 중간 발표 1순위 피드백 반영)

1. **도어캠 기능**: 카메라로 방문자 사진 → 카카오톡 알림 첨부 ("누가 왔는지" 시각화)
2. **음성 자막화 기능**: 마이크 추가 녹음 → STT 텍스트화 → 자막 첨부 ("뭐라고 했는지" 텍스트 전달)

기존 시스템 흐름(소리 감지 → ML 분류 → 카카오톡)에 위 2개 기능 얹는 방식. 시스템 방향 변경 X.

### 26.2 부스 환경 (3영역 구성)

- **왼쪽**: 폼보드 가벽 현관문 모형 + 인터폰 박스 (ESP32 + 카메라 + 마이크 + ToF 통합) + 노크면 + 손잡이
- **가운데**: 책상 (시연용 도어벨 4개 + 카카오톡 수신 스마트폰 + 대시보드 노트북)
- **오른쪽**: 가이드 보드 + 포스터

인터폰 박스 → 폼보드 뒤 케이블 → 노트북 연결 구조.

### 26.3 진입점 3개 (학생 자유 선택)

#### 진입점 1: 노크 + 발화 시연
- **학생 액션**: 폼보드 가벽 노크 + 인사말 ("안녕하세요 택배입니다")
- **시스템 흐름**: ESP32 트리거 → ML 분류 (노크) → ToF 사람 검증 → 5초 1차 알림 ("누군가 노크했어요") → 15초 2차 알림 (사진 + 자막)
- **USP 메시지**: "진동만으로 누가 와서 뭐라고 했는지 한 번에 파악"
- **준비 사항**: 폼보드 노크 면 구역 + 보강재 (충격이 마이크에 잘 전달되도록)

#### 진입점 2: 초인종 등록 + 분리 시연
- **등록 액션**: 학생이 4개 도어벨 중 1개 선택 → 3~5회 누름 → 시스템이 우리집 초인종 템플릿 저장 (SP/DTW + cosine, 카테고리 4 참조)
- **분리 액션**: 미등록 초인종 → 알림 X / 등록 초인종 → 1차 + 2차 알림
- **해제 액션**: 대시보드에서 등록 해제 + 다른 초인종 재등록 가능
- **USP 메시지**: "옆집 초인종 잘못 반응 X" (SP/DTW)

#### 진입점 3: 화재경보 시연
- **학부생 액션**: 핸드폰으로 화재경보 음원 부스 마이크 근처 재생
- **시스템 흐름**: ESP32 트리거 → ML 분류 (화재경보) → ToF 사람 검증 우회 → **즉시 1차 알림** (강조 표현) + **정부 지정 화재 대응 수칙 동시 발송**
- **2차 알림 X** (사진 + 자막 미발송, 카테고리 7 참조)
- **USP 메시지**: "위급 상황 안전 최우선 + 대응 가이드 전달"

### 26.4 시연 메시지 3가지 (부스 마무리 시점)

1. 누가 와서 뭐라고 했는지 사진 + 자막으로 한 번에 알림 (USP 1 + 2)
2. 우리집과 옆집 초인종 구분 (SP/DTW)
3. 화재 시 안전 최우선 + 대응 가이드 동시 전달

### 26.5 부스 외 보완 (시연 백업 영상)

- 시연 전 별도 백업 영상 촬영 계획
- 활용 1: 현장 네트워크 문제 발생 시 대비
- 활용 2: 부스에서 보여줄 수 없는 실제 사용 환경 영상 (집안 실사용)
- 촬영 시점: 18주차 통합 테스트 이후

### 26.6 디벨롭 추적 항목 (시연 시나리오 → 시스템 결정 매핑)

본 카테고리는 시연 시나리오 **틀 확정**만 담당. 세부 디벨롭은 본 개발 진행하며 단계적 처리:

| 디벨롭 항목 | 영향 도메인 | 처리 시점 |
|-------------|-------------|-----------|
| 폼보드 노크 면 구역 + 보강재 설계 | 부스 환경 | PoC 5~6주차 |
| 시연용 도어벨 4종 선별 | ML | PoC 5주차 (ML 학습 데이터 기준) |
| 초인종 등록 응답 시간 정량 결정 | ML + Server | 11~12주차 |
| 초인종 4종 분리 정확도 측정 | ML | 8~10주차 (ML 학습 후) |
| 대시보드 등록 해제 UI / ToF 통과 표시 UI | Dashboard | 15~16주차 |
| 화재 대응 수칙 메시지 템플릿 / 정부 출처 검증 | Server (카카오톡) | 13~14주차 |
| 시연 백업 영상 촬영 | 시연 자체 | 18주차 이전 |

### 26.7 발표 스크립트 출처

- **원본 파일**: `docs/presentation/2026-05-13-script.md`
- **발표 일자**: 2026-05-13 졸작 중간 발표
- **반영 피드백**:
  - 4/29 1순위 = 데모 시나리오 구체화 + 청각장애인 킥
  - 4/29 2순위 = 시연 단순함 vs 시스템 복잡도 갭 해소

### 26.8 검증 채널 (Demo-Verify-(N) 채팅방)

- **신설 시점**: 5월 중 (시점 자유, 학부생 결정)
- **임무**: 시연 시나리오 → 시스템 기능 매핑 + 구현 가능성 평가 + Gap 카드 작성
- **Gap 카드 누적 위치**: 노션 "데모 시나리오" 페이지 DB3
- **Gap 처리 분기**:
  - 분기 A: 관련 도메인 채팅방 인계 (PoC / ML / Server / Dashboard)
  - 분기 B: 데모 시나리오 채팅방 인계 (시나리오 수정으로 회피)
  - 분기 C: decisions.md 카테고리 26 갱신 + 다른 카테고리 갱신
  - 분기 D: 무시 (Gap 영향 미미)

### 26.9 PoC-(6) 1회 검증 결과 (Gap 5건 catch)

5/9 PoC-(6)에서 본 카테고리 신설 직전 1회 검증 시 catch한 Gap 5건:

| Gap | 시나리오 위치 | 우선순위 | 영향 도메인 |
|-----|---------------|----------|-------------|
| 1 | 진입점 1 ToF 통과 표시 | 🟡 시연 품질 | Dashboard |
| 2 | 진입점 1 자막 형태 (메시지 vs 이미지) | 🟡 시연 품질 | Server + Dashboard |
| 3 | 진입점 2 등록 응답 시간 | 🔴 시연 필수 | ML + Server |
| 4 | 진입점 2 초인종 4종 분리 정확도 | 🔴 시연 필수 | ML |
| 5 | 진입점 2 등록 해제 UI | 🔴 시연 필수 | Dashboard |

상세 카드는 노션 "데모 시나리오" 페이지 DB3에 누적 (위임 2 작업 결과).

---

## 카테고리 27: 위임 프롬프트 repo 구조 가정 검증 강제 (2026-05-10 신설)

**학습 14 — 5/10 마이크 더미 테스트 (PoC-(7)) 작업 시 catch한 패턴.**

### 27.1 패턴

위임 프롬프트 작성 시 인계 패키지의 추상 표현 ("camera_dummy 컨벤션 일치", "기존 패턴 따라" 등)을 신뢰하지 말고, **실제 파일 경로 + build 설정 패턴 catch 검증**을 사전 단계로 강제.

### 27.2 5/10 catch 사례

- **위임 프롬프트 가정**: `firmware/dummy_tests/camera_dummy/` 디렉토리 + 동일 패턴으로 `firmware/dummy_tests/mic_dummy/` 신설
- **실제 5/9 카메라 컨벤션**: `firmware/src/camera_*.cpp` 직접 배치 + `firmware/include/camera_common.h` + `firmware/platformio.ini`의 `build_src_filter`로 환경 격리
- **catch 주체**: Claude Code MCP가 첫 단계 `git status` / `ls firmware/` 실행 시 디렉토리 부재 발견 → "임의 결정 금지" 원칙으로 학부생에게 옵션 제시 (`AskUserQuestion`)
- **학부생 결정**: 옵션 1 "실제 카메라 패턴 일치" 채택 → `firmware/src/mic_*.cpp` + `firmware/include/mic_common.h` + `[env:mic_dummy]` 추가

### 27.3 firmware/ 컨벤션 (5/10 catch 결과 명문화)

**디렉토리 구조**:
```
firmware/
├── include/
│   ├── camera_common.h     (5/9 신설)
│   ├── mic_common.h        (5/10 신설)
│   ├── tof_common.h        (5/11 예정)
│   └── secrets.h           (gitignore)
├── src/
│   ├── main.cpp            (env:poc 본 작업, WiFi)
│   ├── camera_common.cpp   (5/9)
│   ├── camera_test_v1.cpp  (5/9, env:camera_v1)
│   ├── camera_test_v2.cpp  (5/9, env:camera_v2)
│   ├── mic_common.cpp      (5/10, env:mic_dummy)
│   ├── mic_test.cpp        (5/10, env:mic_dummy)
│   ├── tof_common.cpp      (5/11 예정)
│   └── tof_test.cpp        (5/11 예정)
└── platformio.ini
```

**환경 격리 패턴**:
```ini
[env:{module}_{version}]
build_src_filter =
  -<*>
  +<{module}_common.cpp>
  +<{module}_test{_version}.cpp>
```

### 27.4 예방책

- 위임 프롬프트 작성 전 `git log -p [관련 commit]` 또는 GitHub 직접 확인하여 실제 컨벤션 catch
- 위임 프롬프트의 첫 작업 단계에 "현재 상태 확인 (`git status` + `ls [관련 폴더]`)" 강제 명시
- 자체 검증 ② 리팩토링의 "기존 컨벤션 일치" 항목이 자동 catch 그물 역할 (mic_test.cpp의 `setup()` graceful return 패턴이 카메라 v1/v2와 1:1 매칭됨을 검증한 사례)

### 27.5 5/28 사례 — 라이브러리 설정 방식/버전 가정 검증 (Phase 1 대시보드)

- **위임 프롬프트 가정**: Tailwind 디자인 토큰을 `tailwind.config.js`에 박음 (= Tailwind v3 멘탈모델)
- **실제 (현재 공식 기본값)**: shadcn/ui + Vite 공식 경로 = **Tailwind v4 (CSS-first, 설정파일 없음, `@theme inline`)**
- **catch 주체**: Claude Code MCP가 context7 공식 문서 + `dashboard/package.json` 실제 설치 대조 → v4 기본값 catch. 토대(전체 디자인 토큰)라 되돌리기 비용 큼 → surface 후 진행, 학부생이 v4 채택 + `@custom-variant dark` / `tw-animate-css` 정정 스펙 직접 제시
- **명문화**: 위임 프롬프트가 박은 **라이브러리 설정 방식/버전 가정**도 SSoT(현재 설치 `package.json` + 공식 문서) 대조 대상. 학습 14(가정 검증)를 "repo 구조" → "툴링 버전/설정 기본값"으로 확장 (학습 15·17 정합)

---

## 카테고리 28: packaging 제약 vs 공식 권장 분리 검증 (2026-05-10 신설)

**학습 15 — 학습 13 (전제 검증) 보강 형태. 5/10 마이크 작업 시 첫 컴파일 실패 → 즉시 검증 → fallback 결정 사례.**

### 28.1 패턴

외부 출처(공식 문서)의 권장값 인용만으로는 부족. **실제 환경(SDK / 패키지) 노출 여부**까지 함께 검증해야 채택 결정 가능.

### 28.2 5/10 catch 사례

- **공식 권장 (ESP-IDF 5.x context7 docs)**: `driver/i2s_std.h` (new API). legacy `driver/i2s.h`는 deprecated, 5.0부터 redesign
- **실제 SDK (arduino-esp32 v3.20017 = framework-arduinoespressif32@3.20017)**: 새 API 헤더 미노출
  - 첫 컴파일 시도: `fatal error: driver/i2s_std.h: No such file or directory`
  - 직접 검증: `find ~/.platformio/packages/framework-arduinoespressif32/tools/sdk/esp32s3/include/driver/include/driver/` 결과 = `i2s.h`만, `i2s_std.h` 부재
- **채택 결정**: legacy `driver/i2s.h` fallback (deprecation warning 0건 컴파일 출력 직접 확인 — `pio run -e mic_dummy` 출력에 `warning:` / `deprecated` 문자열 0건)

### 28.3 4단계 검증 절차 (학습 13 보강)

모든 라이브러리/API 채택 결정 시 다음 4단계 순차 검증:

1. **공식 권장**: 공식 문서 / 출처 인용
2. **실제 패키지 헤더 노출**: SDK 설치 경로에서 `find` / `ls`로 헤더 파일 직접 확인
3. **컴파일 통과**: 더미 코드라도 `pio run -e [env]` SUCCESS 검증
4. **런타임 동작**: 부품 도착 후 실측 (5/15~5/28 자성리얼 부품 도착 후)

### 28.4 마이그레이션 트리거

- arduino-esp32가 새 API 헤더(`driver/i2s_std.h`) 노출 시 → legacy → new API 마이그레이션 검토
- 또는 ESP-IDF 직접 사용으로 전환 시 동일 마이그레이션
- 마이그레이션 전: legacy API 유지 (현재 동작 중인 코드 깨지 X)

---

## 카테고리 29: 위임 프롬프트와 실제 컨벤션 충돌 시 기존 컨벤션 우선 (2026-05-10 신설)

**학습 16 — 5/10 마이크 작업 시 위임 프롬프트의 구체 코드 패턴과 카메라 v1/v2 기존 컨벤션 충돌 catch.**

### 29.1 패턴

위임 프롬프트의 구체 코드 패턴 vs 기존 repo 컨벤션 충돌 시 → **기존 컨벤션 우선**. 위임 프롬프트는 일반론, 기존 컨벤션은 실제 검증된 패턴.

### 29.2 5/10 catch 사례

- **위임 프롬프트 (PoC-(7))**: `while (!Serial && millis() < 2000) { delay(10); }` (Serial race 방지 패턴 A, 일반 Arduino 컨벤션)
- **실제 카메라 v1/v2 컨벤션**: `Serial.begin(115200); delay(SERIAL_BOOT_DELAY_MS=200);` (패턴 B, 단순 delay 기반)
- **Claude Code MCP 채택**: 패턴 B (camera v1/v2 컨벤션 일치 원칙 우선 적용)
  - mic_test.cpp:42~43 `Serial.begin(115200); delay(MIC_SERIAL_BOOT_DELAY_MS);` (=200ms)
  - 카메라 v1/v2의 `delay(SERIAL_BOOT_DELAY_MS=200)`와 동일 구조

### 29.3 정책

- **원칙**: 일관성 우선. 위임 프롬프트는 일반론을 제시하지만, 기존 컨벤션은 이미 검증된 실측 패턴.
- **예외**: 기존 컨벤션이 명백한 오류일 때만 위임 프롬프트 패턴 채택 + decisions-log entry로 명시 변경 사유 기록
- **자동 catch**: 자체 검증 ② 리팩토링 항목 "camera v1/v2 컨벤션 일치"가 이 catch 그물 역할

### 29.4 위임 프롬프트 작성 시 반영

- 위임 프롬프트 작성 시 일반 패턴이 아닌 **"기존 [관련 모듈] 컨벤션 우선" 원칙을 명시**
- 예: "Serial init은 기존 카메라 v1/v2 컨벤션 (`delay(SERIAL_BOOT_DELAY_MS)`) 일치"
- 충돌 발생 시 Claude Code MCP가 기존 컨벤션 자동 채택할 수 있도록 명시 우선순위 부여

### 29.5 5/28 사례 — 용어 컨벤션 (도어벨 → 초인종)

- **위임 프롬프트 용어**: "도어벨" (일반 용어)
- **기존 SSoT 컨벤션**: predicted_class 한글 표기 = **"초인종"** (카테고리 3/4/5). "도어벨"은 카테고리 26 시연용 물리 장치 한정 용어
- **catch + 채택**: Claude Code MCP가 decisions.md SSoT 대조 → predicted_class 한글 표기 = "초인종" 채택 (`doorbell` 영문 enum은 코드 유지). 위임 프롬프트 **일반 용어 < 기존 SSoT 컨벤션** (학습 16 원칙 적용, 학습 17 catch 그물 연동)

---

## 카테고리 30: 외부 계정 셋업 SSoT (2026-05-13 신설, 2026-05-16 NCP 추가)

> Day 7 (5/13~5/14 오전 통합) AWS + 카카오 디벨로퍼스 + Day 8 (5/16) NCP 셋업 결과 SSoT. 카테고리 22.6의 "5/9~5/14 외부 계정 셋업 전진 활용" 실제 완료 결과.
> **자격증명(액세스 키 / 시크릿 / 토큰 / 카드번호 / 휴대폰번호)은 본 문서 절대 미기록** — `firmware/include/secrets.h` (.gitignore) / 환경변수로만 관리.

### 30.1 AWS (2026-05-13 23:06~23:41, 35분)

- **계정**: 메일 `bagtaegeun278@gmail.com` / Account ID `953926452053` / 별칭 `xorms` / 리전 `ap-northeast-2` (서울)
- **요금제**: 무료 (6개월, 200 USD 크레딧) — 유효 기간 ~2026-11-13. 졸작 9/30 종료가 무료 기간 안에 자연 수렴 (30.4 정책 변경 catch 근거)
- **2026-11-13 의사결정 트리거**: 졸업 후 AWS 자격증/취업/사이드 프로젝트 활용 계획 있으면 유료 전환, 없으면 자동 해지 수용
- **MFA**: 루트 사용자 ON, Google Authenticator (`xorms-iphone` 디바이스), 시크릿 키 iPhone 메모 잠금 저장
- **IAM 사용자**: `ddingdong-admin` (AdministratorAccess + 콘솔 액세스)
- **결제 알람 2종**:
  - `My Zero-Spend Budget` — 실 비용 $0.01 임계값 (무료 한도 초과 즉시 catch)
  - `My Monthly Cost Budget` — 월 $100 한도 (85% / 100% / 예상 100% 알림)

### 30.2 카카오 디벨로퍼스 (2026-05-14 10:26~10:37, 11분, Day 7 통합)

> 학부생 의도: 5/14 오전 작업이지만 Day 7 외부 계정 셋업 연속선상 통합 처리 (학습 9 chunk 경계 정렬 예외, decisions-log 2026-05-13 entry에 명시).

- **계정**: 기존 카카오 계정 재사용 (앱 3개 기존 운영 중: PICKL / PICKL 개발용 / 13기 중앙해커톤 피클)
- **신규 앱**: `Ddingdong` (앱 ID `1456718`) / 회사명 `xorms` / 카테고리 `라이프스타일`
- **카카오 로그인**: 활성화 (ON)
- **talk_message scope**: **선택 동의** 채택 (이용 중 동의 X) — 카테고리 7 "memo API + 비즈 앱 회피" 일치

### 30.3 카카오 비즈 앱 회피 결정 근거

- **채택**: 개인 개발자 계정 + talk_message "선택 동의" / **회피**: 비즈 앱 심사 (사업자 등록증 필요)
- **근거**:
  1. 시스템 흐름상 "나에게 보내기" (memo API)만 사용 → 비즈 앱 불필요 (카테고리 7 일치)
  2. 본인이 본인 계정에 동의하는 구조 → "선택 동의"로 충분
  3. "이용 중 동의" 대비 "선택 동의"가 더 단순 (카카오 로그인 시 동의 받음)
- **출처**: 카카오 디벨로퍼스 공식 문서 (talk_message scope 동의 항목 정책)

### 30.4 AWS 신규 가입자 정책 변경 catch (2024-07~)

- **변경 내용**: 신규 가입자 디폴트 = "무료 (6개월)" 또는 "유료" 플랜 선택 강제 (이전 무제한 free tier 디폴트 폐기)
- **무료 플랜**: 200 USD 크레딧 + 6개월 무료 + 6개월 후 또는 크레딧 소진 시 자동 해지
- **본 프로젝트 영향**: 졸작 9/30 종료가 무료 기간(~2026-11-13) 안에 자연 수렴 → 30.1 유효 기간 명시 근거
- **출처**: AWS 가입 화면 직접 catch (2026-05-13, `bagtaegeun278@gmail.com` 계정 생성 시)

### 30.5 11~14주차 카카오 진입 시 추가 작업 placeholder

본 5/14 셋업은 앱 생성 + 카카오 로그인 ON + scope 선택까지. 11~14주차 카카오톡 메시지 작업 진입 시 추가: 플랫폼 등록(Web) / Redirect URI 등록(EC2 도메인 기반) / 토큰 발급(액세스 6h + 리프레시 60d, 카테고리 7 일치) / 메시지 발송 테스트(memo API).

### 30.6 미진행 항목 (카테고리 22.6 대비)

- ~~**Naver Cloud Platform** (STT용, 카테고리 7) — 5/13 시점 미진행~~ → **5/16 완료** (30.7 신설, 카테고리 22.6 NCP 항목 ✅ 처리)
- 카테고리 22.6 5/9~5/14 외부 계정 셋업 항목: AWS ✅ (30.1) / 카카오 ✅ (30.2) / **NCP ✅ (30.7, Day 8)** → 3건 모두 완료

### 30.7 NCP (2026-05-16 14:36~15:00 통합, Day 8)

> 학부생 의도: 5/14~5/15 학교 축제 휴식 후 5/16 (Day 8) 재개. AWS / 카카오와 동일 패턴 직접 진행. 그린루키 사전 catch 강제 (MCP 위임 12분) → 미제휴 확정 → 옵션 B (메일 발송 X) 채택.

- **계정**: ID `2021304034@skuniv.ac.kr` (학교 이메일, 그린루키 신청 가능성 catch 위해 강제) / 회원 유형 개인 / 별칭 `xorms` (AWS 동일)
- **요금제**: 무료 (기본 크레딧 100,000원, 유효기간 3개월) — 유효 기간 ~2026-08-16. 졸작 9/30 종료 시점 도달 시 자동 과금 발생 가능
- **2026-08-16 의사결정 트리거**: 졸작 9월 진입 시 STT 사용 시점 (11~12주차 7/27~8/9) 안에 사용량 catch 후 결제수단 자동 과금 수용 OR 추가 크레딧 신청 결정
- **2차 인증**: SMS (휴대 전화번호) — AWS OTP (Google Authenticator)와 다른 방식, 학부생 의도 분리. 휴대폰 분실 시 lock-out 위험 인지 강제
- **결제수단**: 신용카드 등록 (회원가입 절차 중 자동), 자동 과금 활성화. **카드 번호 본 문서 미기록**
- **IP 보안 설정**: OFF (학부생 환경 IP 자주 변경 — 집/학교/카페/모바일 핫스팟)
- **Idle Time**: 3시간 (개발 작업 흐름 우선)

### 30.8 그린루키 사전 catch 결과 (MCP 위임, 학습 14 catch 그물 7건째 작동)

- **catch 시점**: 2026-05-16 14:55, Claude Code MCP 위임 12분 (예상 20~30분 대비 단축)
- **catch 결과**: **서경대 미제휴 사실상 확정**
- **3중 출처 일관 catch**:
  1. NCP 공식 그린루키 페이지 (https://www.ncloud.com/support/greenRookie) — playwright 동적 로딩 + 스크린샷 32개 기관 시각적 catch → 서경대 미포함
  2. 서경대 산학협력단 (https://sanhak.skuniv.ac.kr/) + 서경대 메인 (https://www.skuniv.ac.kr/) — 네이버 클라우드 / 그린루키 안내 0건
  3. 비공식 출처 (블로그 / Velog / Tistory) — 서경대 학생 그린루키 신청 사례 0건
- **대조군 사례**: 아주대 (https://www.ajou.ac.kr/kr/ajou/notice.do?mode=view&articleNo=103728), 서울대 (https://www.ncloud.com/intro/cases/SNU) 등 제휴 학교는 학교 공지 / 학생 후기 다수 존재
- **NCP 공식 블로그 (2021-09)** 인용: 11개 대학 제휴 (https://blog.naver.com/n_cloudplatform/222302707216) → 2026년 5월 시점 32개로 확장, 서경대 여전히 미포함
- **결정 (5/16)**: **옵션 B (메일 발송 X)** + 옵션 D 연기 (산학협력단 NCP 제휴 추진 메일, 5/18 이후 평일 진입 후 결정)
- **결정 정정 (2026-05-27, 학부생 직접)**: **옵션 D 폐기** — 학부생 작품 기간 (~2026-09-30) 안에서 NCP 제휴 추진 불가 + 후배 가치 창출 기회 폐기 수용. DB3 옵션 D row 🟢 해결됨 전환 강제.
- **헛수고 회피**: 메일 발송 + 5/18~5/19 거절 답변 회피 (단기 손실 5분, 단기 이득 0)
- **장기 가치**: 옵션 D 진행 시 후배 가치 창출 (학기 끝나기 전 처리 시 OK) — 5/27 폐기로 미실현

### 30.9 11~14주차 카카오 + NCP 진입 시 추가 작업 placeholder

본 5/16 NCP 셋업은 회원가입 + 결제수단 + 2차 인증 + 사전 catch까지. 11~14주차 카테고리 7 STT 작업 진입 시 추가:
- Clova Speech 서비스 활성화 (NCP 콘솔 → AI Services → CLOVA Speech)
- Application 등록 (Client ID + Client Secret 발급)
- API Gateway 연동 (REST API 호출용)
- 단가 catch: 초당 0.5원 (분당 30원), 띵동 추정 월 1,000~3,000원 → 기본 크레딧 100,000원 안전 수렴
- 만료 일자 catch: 2026-08-16 (3개월) → 11~12주차 진입 후 자동 과금 발생 시점 catch 강제

### 30.10 학습 catch 사례 누적 (5/16 추가)

- **학습 13 catch 그물 작동 사례 (5/16)**: NCP 회원가입 화면 catch 시 "기본 크레딧 100,000원 / 3개월" 학부생 직접 catch → 사전 박았던 "100,000원 / 100일" 정정 사례. AI 일반 패턴 박기 X, 학부생 화면 catch 우선 강제
- **학습 14 catch 그물 작동 사례 7건째 (5/16)**: 그린루키 신청 메일 발송 전 학부생 사전 검증 강제 요구 → MCP 위임 catch → 미제휴 확정 → 헛수고 회피
- **위임 프롬프트 형식 SSoT 강제 작동 사례 (5/16)**: 그린루키 사전 catch 위임 프롬프트 9개 섹션 구조 준수 → MCP 12분 단축 완료 (효율 검증)

---

## 카테고리 31: Claude 박음 본문 사전 자가검증 3단계 강제 룰 (2026-05-27 신설)

> 2026-05-27 PoC-(13) 본 채팅방 학부생 push back catch 결과 SSoT 영구 반영. AI 본인도 학습 17 catch 그물 작동 대상 정직 영구 반영 (3차 강화 11건째 정직 작동 결정적 증거).

### 31.1 패턴

Claude가 학부생에게 코드 관련 제안 시 사전 자가검증 3단계 통과 후 박기 강제. 자가검증 누락 본문 = 학부생 push back catch 그물 작동 강제.

### 31.2 자가검증 3단계 (기존 코드 작성 위임 자체 검증 3단계와 동일)

**1단계: 효율성 검토** — 시간 / 메모리 / CPU / 알고리즘 복잡도 / 불필요한 연산 catch
**2단계: 리팩토링 검토** — 가독성 / DRY 원칙 / 함수 분리 / 매직 넘버 const화 / 네이밍 일관성 / 데이터 구조 일관성 / 기존 컨벤션 일치 (학습 16 정합)
**3단계: 오류 방지 검토** — 엣지 케이스 / null / 누락 데이터 / 충돌 / 타임스탬프 정확도 / 보안 / 동시성 / 컴파일 경고

### 31.3 적용 범위

- 코드 관련 제안 = API 명세 / 데이터 구조 / 아키텍처 / 컴포넌트 설계 / 라이브러리 선택 / 폴더 구조 / 명명 규칙 등 코드 영향 모든 결정
- **적용 제외**: 단순 의사결정 (옵션 D 폐기 / 매일 밤 루틴 / Phase 1 진입 시점 등)

### 31.4 백그라운드 진행 강제 (2026-05-27 학부생 push back 추가)

- 자가검증 3단계 = Claude 머릿속 진행, 응답 본문에 박지 X
- 응답 본문 = 자가검증 통과 결과만 박음 (가독성 ↑)
- 단, 학부생 요청 시 자가검증 본문 박음 가능 (디버깅 영역)

### 31.5 표시별 강제 출력 룰 (Claude 박음 본문 직접 적용 시 한정)

- **"통과"** → 검증 방법 1줄 강제 (백그라운드 진행 시 생략 가능)
- **"수정"** → Claude 박음 본문 정정 강제 (수정 전 → 수정 후 diff)
- **"무관"** → 근거 1줄 강제 (백그라운드 진행 시 생략 가능)

### 31.6 학습 17 3차 강화 정직 작동 11건째 (5/27 catch 결정적 증거)

- catch 사례: 결정 1 (`POST /api/detect` request body) Claude 박음 자가검증 누락 → 학부생 push back으로 강제 자가검증 적용 → 정직 정정 7건 catch (네이밍 / 데이터 구조 / 보안 / 타임스탬프 / NTP / device_id UUID / ToF 보강)
- catch 결과: Claude 박음 본문 자가검증 누락 패턴 = 학부생 push back catch 그물 정직 작동 = 학습 17 3차 강화 정직 영구 반영 강제

### 31.7 위임 프롬프트 9개 섹션 SSoT와의 관계

- 위임 프롬프트 9개 섹션 (PoC-(9) 5/13 영구 반영) = Claude Code MCP에 위임할 때 작동 룰
- 본 카테고리 31 = Claude (PoC 의사결정 채팅방 / 위임 프롬프트 생성기 채팅방) 박음 본문 직접 적용 룰
- 동일 자가검증 3단계 패턴 = 적용 영역 차이만 (위임 = MCP, 본 카테고리 = Claude 직접 박음)
