# ddingdong ML 데이터 파이프라인

`01_clips` → `02_preprocessed` → **파일단위 split** → `03_augmented`(train만) → `05_final_dataset`
재현 가능한 waveform 전처리·증강·분할 파이프라인. (decisions.md 카테고리 4·5 SSoT)

- 출력은 **waveform(16kHz mono Int16) 유지** — 멜스펙트로그램/SpecAugment 변환은 학습 스크립트 몫(카테고리 4).
- 분할은 **증강 이전, 파일(stem) 단위** — data leakage 방지(카테고리 5). train에만 증강, val/test는 원본만.
- 향후 `04_direct_recording` 녹음이 `01_clips`로 유입돼도 **코드 수정 0**, 재실행만.

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
  manifests/split_manifest.csv, final_manifest.csv
```

파이프라인은 `00_source_raw` / `01_extracted` / `04_direct_recording`을 **건드리지 않음**.

## 원커맨드 실행 (학부생용)

repo 루트에서:

```bash
# 실제 데이터 루트 지정 (경로에 공백·한글 → 반드시 따옴표)
DDINGDONG_DATA_ROOT="/Users/xorms/Desktop/서경대학교/시험 준비/26-1/공학종합설계1/ML 학습 데이터/ddingdong_dataset" \
  python -m ml.pipeline.run_all
```

또는:

```bash
python -m ml.pipeline.run_all --data-root "…/ddingdong_dataset"
```

실행 시 Step1~5가 순서대로 돌고 끝에 `05_final_dataset` split×class 개수 + 누수 가드 통과 요약이 출력됨.

### 04 직접 녹음 유입 시 재실행

녹음 클립을 `01_clips/{class}/`에 추가한 뒤 **위 원커맨드 재실행**만 하면 됨.
분할은 재현 seed(`config.SEED`)로 결정적 — 단, 클립 집합이 바뀌면 배정도 바뀌므로,
기존 split을 고정하려면 `manifests/split_manifest.csv`를 보존/재사용하도록 확장할 것(현재는 매 실행 재생성).

## 의존성

```bash
pip install numpy soundfile librosa scipy
```

## 설정 (`config.py`)

| 항목 | 값 (카테고리 5) |
|---|---|
| `CLASSES` | `("doorbell","knock","fire_alarm")` (코드 식별자 = 영문 고정) |
| `SAMPLE_RATE` / `CHANNELS` | 16000 / mono, 저장 `PCM_16` |
| `TIME_STRETCH_RATES` | `(0.85, 1.15)` |
| `BG_NOISE_SNR_DB` | doorbell·knock `(10,20)` / fire_alarm `(25,35)` dB |
| `VOLUME_GAIN_DB` | `-6.0` |
| `PITCH_SHIFT_SEMITONES` | `(-2, +2)` — **한국 환경음만** (`PITCH_SHIFT_MODE`) |
| `SPECAUGMENT` | freq=10/time=5 — **기록만**, 학습 시점 적용(waveform 단계 아님) |
| `SAMPLE_WEIGHT_RANGE` | `(1.5, 2.0)` — 학습 스크립트가 소비 |
| `SPLIT_RATIO` / `SEED` | `(0.70,0.15,0.15)` / `42` |

### pitch shift 적용 대상 (학부생 결정 필요)

카테고리 5의 pitch ±2semitone은 **한국 환경음 소스만** 대상. 클립 파일명만으론 소스 태그를
판별할 수 없어 `PITCH_SHIFT_MODE`로 분리:

- `"korean_only"`(기본): `KOREAN_SOURCE_MARKERS`에 든 부분문자열이 파일명에 포함된 클립에만 적용.
  **마커가 비어 있으면 적용 대상 0 + 경고 로그** → 한국 환경음(예: AI Hub S_103) 명명 규칙 확인 후
  `config.KOREAN_SOURCE_MARKERS = ("S_103", …)` 설정.
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
| 2 | `split.py` | 파일(stem) 단위 train/val/test 분할(증강 前) → `split_manifest.csv` |
| 3 | `augment.py` | **train만** waveform 증강(time-stretch/BG noise SNR/volume/pitch) → `03_augmented` |
| 4 | `assemble.py` | train=원본+증강 / val·test=원본만 → `05_final_dataset` + `final_manifest.csv` |
| 5 | `guards.py` | 누수 가드: train stem ∩ (val∪test) = ∅ assert |
