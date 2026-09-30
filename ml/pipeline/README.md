# ddingdong ML 데이터 파이프라인

`01_clips` → `02_preprocessed` → **내용 중복 제거 + 원본단위 split** → `03_augmented`(train만) → `05_final_dataset`
재현 가능한 waveform 전처리·증강·분할 파이프라인. (decisions.md 카테고리 4·5 SSoT)

- 출력은 **waveform(16kHz mono Int16) 유지** — 멜스펙트로그램/SpecAugment 변환은 학습 스크립트 몫(카테고리 4).
- 분할은 **증강 이전, 원본(source) 단위 그룹 분할** — data leakage 방지(카테고리 5). train에만 증강, val/test는 원본만.
- split 직전에 **디지털 무음 → AI Hub 앞머리 멘트 → 클래스 교차 → 내용(md5) 중복** 순서로 split 대상에서 제외한다(D1 · decisions.md 33.15(d) — 순서가 규칙의 일부). 멘트 = AI Hub `S_103` `fire_alarm` 조각 중 시작 9000ms 미만(녹음당 3조각), 사유 `aihub_intro_speech`. 제외 내역 = `manifests/dedup_manifest.csv`. **`02_preprocessed`의 파일은 지우지 않는다**(원본 보존).
- source 배정은 **셔플이 아니라 그룹 키 해시 고정**(D2) — **새 source가 들어와도 기존 source 배정이 바뀌지 않는다**.
- 향후 `04_direct_recording` 녹음이 `01_clips`로 유입돼도 **코드 수정 0**, 재실행만. 직접녹음은 **테이크가 아니라 유닛**이 한 그룹이다(D3).

> ⚠️ 실제 데이터셋은 repo **밖 형제 폴더**에 있고 Claude Code는 OS 접근 차단(EPERM)이라 실행 불가.
> 실제 풀 실행은 **학부생이 자기 셸에서** 수행. (repo 안에서는 합성 더미로만 로직 검증됨.)

## 데이터 루트 규격

`DATA_ROOT`(= `01_clips` 상위 폴더) 아래에 스테이지 폴더가 존재해야 함:

```
<DATA_ROOT>/
  01_clips/{doorbell,knock,fire_alarm}/*.wav   # 입력 (2,798 클립, 16k mono Int16)
  02_preprocessed/                             # ← 파이프라인 출력
  03_augmented/                                # ← 파이프라인 출력 (train 파생만)
  05_final_dataset/{train,val,test}/{class}/   # ← 최종 출력
  manifests/split_manifest.csv, dedup_manifest.csv, final_manifest.csv
```

파이프라인은 `00_source_raw` / `01_extracted` / `04_direct_recording`을 **건드리지 않음**.

## 원커맨드 실행 (학부생용)

repo 루트에서:

```bash
# 실제 데이터 루트 지정 (경로에 공백·한글 → 반드시 따옴표)
DDINGDONG_DATA_ROOT="~/ML 학습 데이터/ddingdong_dataset" \
  python -m ml.pipeline.run_all
```

또는:

```bash
python -m ml.pipeline.run_all --data-root "…/ddingdong_dataset"
```

실행 시 Step1~5가 순서대로 돌고 끝에 `05_final_dataset` split×class 개수 + 누수 가드 통과 요약이 출력됨.

### 04 직접 녹음 유입 시 재실행

녹음 클립을 `01_clips/{class}/`에 추가한 뒤 **위 원커맨드 재실행**만 하면 됨.
분할은 `sha256(f"{SEED}:{class}:{group_key}")`를 `SPLIT_RATIO` 누적 경계에 사상하는 **순수 함수**(`split.assign_split`)라
결정적이고, **새 source가 늘어도 기존 source의 배정은 그대로**다(기각된 설계 = 클래스 공유 `random.Random(SEED)` + 셔플.
doorbell source 1개 추가만으로 knock 클립 124/714가 흔들렸다 — decisions.md 5.2(c) 실측).
⚠️ 비율은 **기대값**이다 — 그룹 수가 적으면(직접녹음 4유닛 등) 배분이 거칠고 특정 split이 0일 수 있다.
🔴 내용이 바뀐 클립이 들어오면 dedup 결과와 그에 딸린 수치(33.2·33.6·33.7)는 **새 test set 위의 값**이 된다.

## 의존성

```bash
pip install numpy soundfile librosa scipy
```

## 설정 (`config.py`)

| 항목 | 값 (카테고리 5) |
|---|---|
| `CLASSES` | `("doorbell","knock","fire_alarm","other")` (코드 식별자 = 영문 고정, 순서 = 라벨 인덱스) |
| `SAMPLE_RATE` / `CHANNELS` | 16000 / mono, 저장 `PCM_16` |
| `TIME_STRETCH_RATES` | `(0.85, 1.15)` |
| `BG_NOISE_SNR_DB` | doorbell·knock·other `(10,20)` / fire_alarm `(25,35)` dB |
| `VOLUME_GAIN_DB` | `-6.0` |
| `PITCH_SHIFT_SEMITONES` | `(-2, +2)` — **한국 환경음만** (`PITCH_SHIFT_MODE`) |
| `SPECAUGMENT` | freq=10/time=5 — **기록만**, 학습 시점 적용(waveform 단계 아님) |
| `SPLIT_RATIO` / `SEED` | `(0.70,0.15,0.15)` / `42` |

### pitch shift 적용 대상

카테고리 5의 pitch ±2semitone은 **한국 환경음 소스만** 대상. 클립 파일명만으론 소스 태그를
판별할 수 없어 `PITCH_SHIFT_MODE`로 분리:

- `"korean_only"`(기본): `KOREAN_SOURCE_MARKERS`에 든 부분문자열이 파일명에 포함된 클립에만 적용.
  값 = `("direct_doorbell_", "direct_knock_")` — 초인종·노크 직접녹음만(decisions.md 33.3① · 5.3(b)).
  부분 문자열 매칭이라 `("direct_",)`로 두면 직접녹음 화재경보까지 걸린다(규격 화재음 왜곡 회피와 충돌).
  AI Hub `S_103`는 대상이 아니다. train 에 직접녹음 클립이 없으면 대상 0 + 안내 로그.
- `"all"`: 전 클립 적용 · `"none"`: 미적용.

## 검증 (실제 데이터 없이)

합성 더미(클래스당 6개 16k mono wav)로 Step1~5 전관통 + 누수 가드를 확인:

```bash
python -m ml.pipeline.tests.test_pipeline      # 단독 실행
# 또는
pytest ml/pipeline/tests/
```

## 파이프라인 단계

| Step | 모듈 | 내용 |
|---|---|---|
| 1 | `preprocess.py` | 16k mono 검증(위반 스킵) + peak 정규화 → `02_preprocessed` |
| 2 | `split.py` | 무음 · 멘트 · 교차 · 중복 제거 → 원본(source) 단위 해시 고정 배정(증강 前) → `split_manifest.csv` + `dedup_manifest.csv` |
| 3 | `augment.py` | **train만** waveform 증강(time-stretch/BG noise SNR/volume/pitch) → `03_augmented` |
| 4 | `assemble.py` | train=원본+증강 / val·test=원본만 → `05_final_dataset` + `final_manifest.csv` |
| 5 | `guards.py` | 누수 가드 2층: ① train stem ∩ (val∪test) = ∅ ② 같은 내용 해시가 2개 이상 split에 존재하면 즉시 실패 |
