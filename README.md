# 띵동 (DdingDong)

> **English summary** — DdingDong is a door-mounted sound-alert system for Deaf and hard-of-hearing people (a university capstone project).
> An ESP32-S3 board listens at the front door, sends a short audio snapshot to a Flask server, and a YAMNet-based classifier sorts it into doorbell / knock / fire alarm / other.
> The user gets a KakaoTalk text first, then a follow-up with a door camera photo and a speech-to-text caption of what the visitor said.
> A ToF sensor (VL53L5CX) checks whether someone is actually at the door, an optional doorbell sound registration filters out different-sounding bells, and a single-knock check skips one-off thuds.
> Status: end-to-end runs have been observed on the real board, but this is not a validated product. Features are frozen as of 2026-11-02.
> Documentation is in Korean; `docs/decisions.md` is the single source of truth for every decision.

청각장애인을 위한 현관 부착형 소리 분류 알림 시스템. 졸업작품이다.

기존 초인종 알림이 「띵동」 한 번으로 끝났다면, 띵동은 **누가 왔고 뭐라고 말했는지**까지 알려 주는 것을 목표로 한다.

---

## 동작 흐름

```
현관 보드 (ESP32-S3)                 서버 (Flask)                     사용자
───────────────────                 ────────────                     ──────
소리 감지 (자동 감지 또는 수동 's')
  └─ 오디오 스냅샷 + ToF ──▶ 1차 /api/v1/detect
                               소리 분류 → 판정 규칙 ──────▶ 카카오톡 텍스트
  ◀── request_id · enrich_status
카메라 1장 + 5.12초 녹음
  └──────────────────────▶ 2차 /api/v1/enrich
                               사진 저장 · STT 자막 ──────▶ 카카오톡 사진 카드 + 자막
```

- **1차 ≤ 5초 · 2차 ≤ 15초**는 설계 목표 예산이다(카테고리 3). 보장 수치가 아니다.
- 2차는 1차 판정이 발송일 때만 진행한다. `fire_alarm`은 1차 텍스트만 보내고 2차는 없다(8.7(a)).
- 카카오 「나에게 보내기」(memo) API에는 이미지 업로드가 없다. 그래서 서버가 사진을 직접 public 주소로 서빙하고, 카드는 그 주소를 가리킨다.
- 보드 요청은 기기당 2.5초에 1회로 제한하고, 넘으면 429를 돌려준다(잠정 · 6.1 · 33.48(i)). 보드는 불응기 때문에 원래 그보다 자주 보내지 못하고, 서버 제한은 고장 난 기기의 연타를 막는 안전장치다.

## 구성

| 영역 | 내용 |
|---|---|
| 하드웨어 | XIAO ESP32-S3 Sense(OV3660 카메라 · 8MB PSRAM) · INMP441 마이크(I2S) · VL53L5CX 8x8 ToF(I2C) — 카테고리 1 · 핀 표 = 카테고리 2 |
| 펌웨어 | PlatformIO · Arduino-ESP32 2.0.17. 제품 경로 = `env:enrich_uplink`(수동 트리거) · `env:enrich_autotrig`(같은 소스 + 자동 감지). 나머지 env는 단계별 계측 · 진단용 |
| 서버 | Flask + Flask-SQLAlchemy + SQLite. 실모델 · STT · 카카오는 환경변수가 없으면 mock으로 동작한다 |
| ML | YAMNet frozen 임베딩 + 분류 head. 4클래스 `doorbell` · `knock` · `fire_alarm` · `other`(33.13). `other`의 화면 표시 이름 = 「생활 소음」(PR #154 · 33.48(f)) |
| 대시보드 | Vite + React + TypeScript + Tailwind. 알림 목록 · 통계 · 시스템 상태 · 초인종 소리 등록 · 도움말 |
| 알림 · STT | 카카오톡 「나에게 보내기」(memo) · Naver CSR(Clova Speech Recognition) |
| 발표 서빙 | Cloudflare 터널. EC2는 이번 개발 범위에서 제외했다(33.18(g)) |

## 판정 규칙 요약

서버는 아래 순서로 게이트를 통과시킨다(33.30(c) · PR #100 · 노크 단일 타격 = 33.47 · PR #152). 하나라도 막히면 그 뒤는 보지 않는다.

1. **`other`** → 알리지 않는다(`not_target` · 33.13 · PR #83).
2. **신뢰도 0.7 미만** → 알리지 않는다. 클래스와 무관해서 `fire_alarm`도 이 게이트를 받는다(8.7(a)).
3. **`fire_alarm`** → ToF 확인을 건너뛰고 바로 알린다(1차만).
4. **ToF** → 현관 앞에 사람이 없으면 알리지 않는다. ToF 값이 없으면(센서 초기화 실패 등) 게이트를 적용하지 않고 통과시킨다(fail-open · 6.4).
5. **초인종 소리 등록**(선택) → 예측이 `doorbell`일 때만 본다. 소리를 모으는 중이면 알리지 않는다(`registration_collecting`). 등록돼 있으면 등록한 소리와 거리를 재서 기준을 넘으면 막는다(`registration_mismatch`). 기준값 0.20은 잠정이다. 거리 계산이 실패하면 막지 않고 통과시킨다(fail-open · 33.30(c)).
6. **노크 단일 타격** → 예측이 `knock`이고 앞 단계까지 알릴 상황이면, 녹음 속 뚜렷한 타격이 2번 미만일 때 막는다(`knock_single_hit`). 폰을 내려놓는 「툭」 소리가 노크로 분류돼도 알리지 않기 위해서다. 기준값 3개(높이 비율 0.5 · 간격 150 ms · 최소 2번)는 잠정이다. 타격 계산이 실패하면 막지 않고 통과시킨다(fail-open · 33.47(f)).

소리 등록은 **종류가 다른 소리를 거르는 2차 층**이다. 같은 제품의 옆집 벨은 칩 · 멜로디가 같아 소리로 가르기 어렵고, 옆집 구분의 1차는 ToF가 맡는다(33.19(c)).

## 현황

기능 동결 = 2026-11-02(사용자 결정). 지금부터는 버그 수정 · 문구 확정 · 문서 · 발표 준비만 한다. 동결 뒤 예외 1건 = 노크 단일 타격 차단(PR #152 · 33.46 현재값 줄).

| 구분 | 내용 |
|---|---|
| 관통 확인 | 2026-10-26 랩실 보드 세션에서 시연 기동 도구(`demo_up` live) · 자동 감지 · 카카오 실발송 · 대시보드 육안 확인이 한 세션에 함께 관통했다(경로당 n 1 ~ 2 · 1세션 · 1인 — 26.12 · 33.45(j)) |
| 그 뒤 관측 | 2026-11-02 랩실 리허설 1회차 · 11-03 미팅 시연(자동 감지 `/detect` 336요청 · 화재 예측 0) · 11-04 소음 속 등록 시험(유튜브 소음 2종). 각각 1세션 관측이고 판정 기준은 없다(33.47(d) · 33.48(b)(d)) |
| 검증 예정 | 부스 리허설(날짜 미정 · 33.48(n)). 위 관통과 관측은 검증이 아니다 |
| 서빙 모델 | p15(4차 재학습 · patience 15). 데이터셋 4차 상태 test 703건 한 세트의 오프라인 평가에서 acc 644 / 703 · macro F1 0.8204(33.2 현재값 줄). 현장 성능 수치가 아니다 |

## 알려진 한계

- **학습 분포 밖 입력** — 학습에 없던 소리가 엉뚱한 클래스로 높게 나올 수 있다. 3클래스 시절 실측(조건마다 n 1)에서 분포 밖 입력이 `fire_alarm`으로 쏠렸고(33.6(a)(f)), `other` 클래스로 대응했지만(33.13) 모든 생활 소리를 막는다는 보장은 없다. 4클래스 서빙 모델(p15)에서도 2026-11-04 보드 근처 스피커로 튼 카페 소음이 `fire_alarm` 0.83으로 나와 화재 알림이 실제로 발송됐다(관측 n 1 · 33.48(d)). 화재는 ToF 확인을 건너뛰므로 신뢰도 0.7만 넘으면 그대로 보낸다.
- **자막 잘림** — 방문자가 말하다 쉬면 자막이 앞 구절만 나올 수 있다. 원인 해석 = CSR이 쉼에서 인식을 끝낸다(유력 · 미확정 — 7.7(n)).
- **ToF 초기화 실패 부팅** — 보드 R 버튼 리셋 뒤 ToF 초기화가 실패하는 부팅이 관측됐다(원인 미규명 · 33.31(f)). 이때는 ToF 게이트 없이 통과한다(fail-open). 운영 대응 = R 버튼 대신 USB 재연결(33.33(b)). 펌웨어 보강은 하지 않기로 했다(33.47(a)).
- **잠금 화면 배너** — 「나에게 보내기」 경로는 아이폰 잠금 화면에 배너가 뜨지 않았다(대리 시험 n 1 · 33.42(c)). 실서비스 알림 경로는 미정이다.
- **2차 사진 카드 중복 도착** — 카카오 응답이 타임아웃으로 처리된 뒤 재시도하면 카드가 두 번 올 수 있었다(재현 6 · 장소 2). 사진 카드만 대기 시간을 따로 두고(2.9초 · 잠정), 응답 대기 시간 초과는 재시도하지 않게 고쳤다(PR #151). 고친 뒤 확인은 1세션(14 / 14회 1장)뿐이고 그 세션엔 시간 초과가 없어 고친 분기가 현장에서 돈 적은 없다 — 부분만 닫힘(7.6(j)).

## 폴더 구조

```
ddingdong/
├── firmware/   # ESP32-S3 펌웨어 (PlatformIO) · 장비 절차 = *_RUNBOOK.md
├── server/     # Flask API 서버 · server/inference/ = 오디오 디코드 · SavedModel 로더
├── dashboard/  # React 대시보드
├── ml/         # 데이터 파이프라인(pipeline) · 학습(training) · 네거티브 선별(curation) · 실험(experiments)
├── tools/
│   └── decisions-rag/  # decisions.md 검색 도구 (개발용 · 제품과 무관)
├── docs/       # decisions.md(SSoT) · decisions-log.md · git-convention.md · presentation(발표 대본) · poc-week1-plan.md(초기 1주 계획)
└── CLAUDE.md   # 코딩 에이전트용 작업 안내
```

데이터셋 · 학습된 모델 파일은 repo에 없다(오디오 미커밋 = 5.1 · 모델 파일도 커밋하지 않았다). 학습은 데이터 경로를 `--data-root` 또는 `DDINGDONG_DATA_ROOT`로 지정해야 돈다.

## 실행

영역마다 하위 README를 따른다.

- 서버 — [`server/README.md`](server/README.md)
- 펌웨어 — [`firmware/README.md`](firmware/README.md)
- 대시보드 — [`dashboard/README.md`](dashboard/README.md)
- ML — [`ml/pipeline/README.md`](ml/pipeline/README.md) · [`ml/training/README.md`](ml/training/README.md) · [`ml/curation/README.md`](ml/curation/README.md)
- decisions 검색 도구 — [`tools/decisions-rag/README.md`](tools/decisions-rag/README.md)

⚠️ 서버를 debug 모드(`--debug` · `FLASK_DEBUG=1` · `python run.py`)로 띄우지 않는다. debug 모드는 JSON 응답에 들여쓰기를 붙여, `/detect` 응답이 보드 수신 한도 767 B를 넘을 수 있다(33.37(e)).

## 문서

- [`docs/decisions.md`](docs/decisions.md) — 모든 결정의 단일 출처(SSoT). 코드 주석과 PR은 「카테고리 N.M」으로 이 문서를 인용한다.
- [`docs/decisions-log.md`](docs/decisions-log.md) — decisions.md 변경 이력.
- [`docs/git-convention.md`](docs/git-convention.md) — 커밋 규칙(한국어 + 이모지, `{이모지} {Type}: {설명}`).

## 데이터 출처 · 라이선스

학습 데이터는 repo에 포함하지 않는다. 사용한 공개 데이터와 표기는 다음과 같다.

- **FSD50K** — 데이터셋 = CC BY 4.0(Zenodo record 4060432). 인용 = Eduardo Fonseca, Xavier Favory, Jordi Pons, Frederic Font, Xavier Serra, "FSD50K: an open dataset of human-labeled sound events", IEEE/ACM Transactions on Audio, Speech, and Language Processing, vol. 30, pp. 829–852, 2022. 클립마다 라이선스가 다르다(예: 추가 네거티브 160클립 = CC0 · CC BY 3.0 · CC BY-NC 3.0 · Sampling+ 1.0 — 33.32). 인용할 때는 클립별 라이선스를 표기한다.
- **Zeroth-Korean** — 「Zeroth-Korean (OpenSLR SLR40, https://www.openslr.org/40/) — Lucas Jo (Atlas Guide Inc.) · Wonkyum Lee (Gridspace Inc.), CC BY 4.0 — 3초 조각 · PCM16 wav 변환 등 가공함」(표기문 원문 = [`ml/curation/README.md`](ml/curation/README.md)).
- **AI Hub · AudioSet** — 이용 조건 = 각 배포처 약관.

코드 라이선스는 아직 정하지 않았다.

---

작성: [park-taegeun](https://github.com/park-taegeun) · 프로젝트 소개: [포트폴리오](https://park-taegeun.github.io/projects/ddingdong)
