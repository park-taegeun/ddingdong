# ddingdong ML 학습 — YAMNet transfer learning

`05_final_dataset`(파이프라인 출력) → **YAMNet 임베딩 위 분류 head 학습**.
학습할 클래스는 실행마다 `--classes` 로 준다(기본값 없음). 허용 집합 = `ml.pipeline.config.CLASSES`
= 초인종(doorbell) / 노크(knock) / 화재경보(fire_alarm). (decisions.md 카테고리 4·5 SSoT)

- **backbone = YAMNet (16kHz mono waveform → 1024-d embedding), frozen.** 원본 2,798개는
  backbone 재학습에 부족 → transfer learning 정석(Hershey 2017 / Piczak 2015). **head 만 학습.**
- **head = Dense(128)+Dropout → Dense(클래스 수) softmax (trainable).**
- 라벨 인덱스 = `--classes` 를 `ml.pipeline.config.CLASSES` 순서로 정규화한 위치(입력 순서 무관).
  3클래스면 `doorbell=0, knock=1, fire_alarm=2`(서버 `PREDICTED_CLASSES` 와 같음).
- 그 실행이 실제로 학습한 클래스·인덱스는 **run 폴더 `labels.json` 이 단일 출처**. `evaluate` ·
  `export` 는 이 파일을 읽고, `--classes` 가 이와 다르면 거부한다.

> ⚠️ 실제 데이터셋은 학부생 홈 `~/ML 학습 데이터/ddingdong_dataset` 에 있다(decisions.md 5.1 —
> repo 밖 형제 폴더의 OS TCC 차단으로 이동). **실제 학습은 학부생이 자기 셸에서** 수행.
> repo 안에서는 합성 더미로 로직 관통만 검증됨.

## 파일

| 파일 | 역할 |
|---|---|
| `config.py` | 하이퍼파라미터·경로·SpecAugment. 파이프라인 config 를 SSoT 로 상속(매직넘버 0). |
| `data.py` | `05_final_dataset/{split}/{class}` 폴더 스캔 → tf.data 임베딩 데이터셋 + class_weight 자동 산출. |
| `model.py` | frozen YAMNet backbone(hub) + trainable head + 배포용 추론 모델 합성. |
| `spec_augment.py` | SpecAugment Keras 레이어(train 배치만 마스킹, val/test 항등). |
| `frontend.py` | tf.signal 로그멜 프론트엔드(YAMNet 규격) — SpecAugment logmel 모드용. |
| `train.py` | head fit + class_weight + EarlyStopping + best 체크포인트 + history. |
| `evaluate.py` | test accuracy + 클래스별 P/R/F1 + confusion matrix. |
| `export.py` | best.keras + YAMNet → 서빙 SavedModel(`inference_savedmodel/`). |
| `tests/test_training_smoke.py` | 합성 더미 전관통(파이프라인→학습→평가) + clean 가드 + SpecAugment 검증. |
| `tests/test_export_smoke.py` | 더미 YAMNet 으로 export 관통(미추적 리소스 회귀 가드). |
| `tests/test_class_subset.py` | 클래스 인자 정규화 · 산출 폴더 필수 · 덮어쓰기 거부 · 빈 클래스 실패 · 2/3/4클래스 관통. |

## 의존성

```bash
pip install "tensorflow==2.16.*" tensorflow_hub scikit-learn soundfile librosa
```

> **Python 3.11 / 3.12 권장.** TensorFlow 는 아직 **Python 3.14 미지원**(wheel 없음).
> 시스템 python 이 3.14 면 `python3.11 -m venv` 로 가상환경을 따로 만들어 설치할 것.

## 원커맨드 (학부생 로컬)

repo 루트에서. 필수 입력 3가지 — 없으면 기본값 fallback 없이 즉시 실패한다:

| 입력 | 인자 | env 대체 | 없을 때 |
|---|---|---|---|
| 데이터 루트 | `--data-root` | `DDINGDONG_DATA_ROOT` | `ValueError`(PR #60) |
| 클래스 집합 | `--classes a,b,c` | 없음 | argparse 오류 |
| run 폴더 | `--out-dir` | `DDINGDONG_MODEL_DIR` | `ValueError` |

- `--classes` 는 `ml.pipeline.config.CLASSES` 의 부분집합. 모르는 이름 · 중복 · 빈 집합은 거부.
- **run 폴더는 학습 1회당 새 폴더.** `train` 은 거기에 `best.keras` · `labels.json` ·
  `inference_savedmodel` 중 하나라도 있으면 거부한다(덮어쓰기 0 — 서빙 중인
  `ml/models/yamnet/` 보호. repo 기본 경로 fallback 은 없다).
- `evaluate` · `export` 의 `--out-dir` 은 **학습이 끝난 run 폴더**(labels.json · best.keras 필수).
  `eval_report.json` · `confusion_matrix.csv` · `inference_savedmodel` 이 이미 있으면 거부.
  `--checkpoint` 로 준 head 의 출력 수가 labels.json 클래스 수와 다르면 거부.
- 요청 클래스가 train · val · test 중 쓰는 split 에서 0개면 split · 클래스 · 경로를 적은
  `ValueError` 로 즉시 실패(조용히 건너뛰지 않음 · class_weight 균등 폴백 없음).

```bash
DATA="$HOME/ML 학습 데이터/ddingdong_dataset"   # 공백·한글 → 따옴표 필수
RUN=~/ddingdong_runs/r3_YYYYMMDD                # 매번 새 폴더

# 0) (선행) 데이터 파이프라인으로 05_final_dataset 생성 — 재실행 시 auto-clean 으로 stale 방지
#    ⚠️ 재학습 준비 PR 이 다 들어오기 전에는 실데이터로 돌리지 말 것(decisions.md 33.12(e))
DDINGDONG_DATA_ROOT="$DATA" python -m ml.pipeline.run_all

# 1) 학습 (best val 체크포인트 + history + labels.json + inference_savedmodel)
python -m ml.training.train    --data-root "$DATA" --classes doorbell,knock,fire_alarm --out-dir "$RUN"

# 2) 평가 (test accuracy + per-class P/R/F1 + confusion matrix)
python -m ml.training.evaluate --data-root "$DATA" --classes doorbell,knock,fire_alarm --out-dir "$RUN"
```

- run 폴더 산출물: `best.keras`(head 가중치) · `history.json` · `labels.json`(이 run 의 클래스 ·
  인덱스) · `eval_report.json` · `confusion_matrix.csv` · `inference_savedmodel/`(waveform→확률 배포용).
- `train` 은 hub YAMNet 으로 `inference_savedmodel/` 까지 만든다. head 만 있을 때 따로 만들려면
  `python -m ml.training.export --classes … --out-dir "$RUN"`.
- YAMNet hub 핸들은 `DDINGDONG_YAMNET_HANDLE` 로 오버라이드(오프라인 로컬 경로 등).

### 예상 소요 / CPU 주의

- **CPU 만으로 충분.** 학습은 frozen backbone 임베딩 위 **작은 head(≈13만 파라미터)** 만
  돌아 가볍다. 병목은 YAMNet 임베딩 추출(클립당 1회 forward). train ≈11.6k 클립 기준
  CPU 에서 임베딩 1회 순회가 수 분~십수 분(머신 편차). 임베딩을 캐시하면 epoch 반복은 빠름.
- 첫 실행은 **YAMNet hub 다운로드**(수십 MB) 시간이 추가. 오프라인이면 로컬 핸들 지정.
- `EPOCHS=30` 기본이나 EarlyStopping(patience=6)이 대개 더 일찍 멈춘다.

### 3클래스 · 4클래스 비교 학습 (decisions.md 33.17(c) · 33.13(d))

같은 새 split 에서 3클래스와 4클래스(`other`)를 **각자의 run 폴더**로 학습해 비교한다.
라벨은 run 마다 `labels.json` 에 기록되므로 `CLASSES` 를 4로 바꾼 뒤에도 3클래스 run 의 라벨은
어긋나지 않는다.

```bash
# 3클래스 (지금 바로 가능)
python -m ml.training.train    --data-root "$DATA" --classes doorbell,knock,fire_alarm --out-dir ~/ddingdong_runs/cmp_3cls
python -m ml.training.evaluate --data-root "$DATA" --classes doorbell,knock,fire_alarm --out-dir ~/ddingdong_runs/cmp_3cls

# 4클래스 — ml.pipeline.config.CLASSES 에 other 가 들어온 뒤(다음 PR). other 인덱스 = 3.
python -m ml.training.train    --data-root "$DATA" --classes doorbell,knock,fire_alarm,other --out-dir ~/ddingdong_runs/cmp_4cls
python -m ml.training.evaluate --data-root "$DATA" --classes doorbell,knock,fire_alarm,other --out-dir ~/ddingdong_runs/cmp_4cls
```

- 두 run 의 `eval_report.json` 을 비교한다. 4클래스 run 의 `other` 기준선 칸은 `null`
  (사전테스트 기준선이 없는 클래스).

## 기준선 (개선 확인용)

사전테스트 pre-trained YAMNet Top-1: **doorbell≈30% / knock≈40% / fire_alarm≈20%**.
head 학습 후 `evaluate` 결과가 이 대비 개선되는지 확인(리포트에 baseline 병기).

## 합성 더미 관통 검증 (repo 안, 실데이터 불필요)

```bash
python -m ml.training.tests.test_training_smoke      # 또는 pytest ml/training/tests/
```

더미 backbone(결정적 임베딩)을 주입해 파이프라인→학습(2ep)→체크포인트→평가까지 오프라인 관통.
clean 가드 stale 방지 + SpecAugment train-only 도 함께 검증.

## 설계 노트 — SpecAugment × frozen hub YAMNet (결정 확정: decisions.md 33.3②)

decisions.md 카테고리 5 는 SpecAugment(freq=10/time=5)를 **학습 시점 로그멜 마스킹**으로
규정한다. 그런데 **hub YAMNet 은 waveform-in / embedding-out 블랙박스**라, 내부에서 계산되는
로그멜에 마스킹을 주입할 수 없다. 그래서:

- **`embedding` 모드(기본, 학부생 즉시 실행)**: waveform → frozen hub YAMNet → 임베딩 → head.
  이 경로에서 SpecAugment 는 backbone 내부에 도달 불가 → **미적용**. train 시점 정규화는
  shuffle + 파이프라인 03 증강(time-stretch/noise/…) + Dropout 이 담당.
- **`logmel` 모드(카테고리 5 충실 경로)**: waveform → `frontend.py` 로그멜(YAMNet 규격)
  → **SpecAugment(train-only)** → frozen YAMNet **core**(로컬 `yamnet.py`, tensorflow/models)
  → 임베딩 → head. `SpecAugment` 레이어는 이미 구현·검증됨(더미 테스트). YAMNet core 를
  로컬로 분리 로드하는 배선만 남았다.

**→ 결정 확정(2026-07-07, decisions.md 33.3②)**: **embedding 모드 유지 / logmel 배선 defer**.
`SpecAugment` 레이어는 보존(삭제·비활성 X)하고, 직접녹음 유입 후 A/B 비교로 배선을 결정한다.

## 참고 (upstream)

- **pitch shift 대상 = 초인종 · 노크 직접녹음만**: `ml.pipeline.config.KOREAN_SOURCE_MARKERS`
  = `("direct_doorbell_", "direct_knock_")`(decisions.md 5.3(b) · 33.3①). 직접녹음 클립이
  train 에 아직 없으면 적용 대상 0 이다.
