# ddingdong ML 학습 — YAMNet transfer learning

`05_final_dataset`(파이프라인 출력) → **YAMNet 임베딩 위 3-class 분류 head 학습**.
초인종(doorbell) / 노크(knock) / 화재경보(fire_alarm) 3종. (decisions.md 카테고리 4·5 SSoT)

- **backbone = YAMNet (16kHz mono waveform → 1024-d embedding), frozen.** 원본 2,798개는
  backbone 재학습에 부족 → transfer learning 정석(Hershey 2017 / Piczak 2015). **head 만 학습.**
- **head = Dense(128)+Dropout → Dense(3) softmax (trainable).**
- 라벨 인덱스 순서는 `ml.pipeline.config.CLASSES` **단일 출처**(`doorbell=0, knock=1, fire_alarm=2`).
  학습·평가·배포가 같은 인덱스를 쓰도록 강제(추론 불일치 방지).

> ⚠️ 실제 데이터셋은 repo **밖 형제 폴더**(EPERM)라 Claude Code 는 실행 불가.
> **실제 학습은 학부생이 자기 셸에서** 수행. repo 안에서는 합성 더미로 로직 관통만 검증됨.

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
| `tests/test_training_smoke.py` | 합성 더미 전관통(파이프라인→학습→평가) + clean 가드 + SpecAugment 검증. |

## 의존성

```bash
pip install "tensorflow==2.16.*" tensorflow_hub scikit-learn soundfile librosa
```

> **Python 3.11 / 3.12 권장.** TensorFlow 는 아직 **Python 3.14 미지원**(wheel 없음).
> 시스템 python 이 3.14 면 `python3.11 -m venv` 로 가상환경을 따로 만들어 설치할 것.

## 원커맨드 (학부생 로컬)

repo 루트에서. 데이터 루트는 파이프라인과 동일하게 지정(공백·한글 → 따옴표 필수):

```bash
# 0) (선행) 데이터 파이프라인으로 05_final_dataset 생성 — 재실행 시 auto-clean 으로 stale 방지
DDINGDONG_DATA_ROOT="/…/ddingdong_dataset" python -m ml.pipeline.run_all

# 1) 학습 (best val 체크포인트 + history 저장)
DDINGDONG_DATA_ROOT="/…/ddingdong_dataset" python -m ml.training.train

# 2) 평가 (test accuracy + per-class P/R/F1 + confusion matrix)
DDINGDONG_DATA_ROOT="/…/ddingdong_dataset" python -m ml.training.evaluate
```

- 산출물 기본 위치: `ml/models/yamnet/`(gitignore). `DDINGDONG_MODEL_DIR` 로 변경 가능.
  - `best.keras`(head 가중치) · `history.json` · `labels.json` · `eval_report.json`
    · `confusion_matrix.csv` · `inference_savedmodel/`(waveform→확률 배포용).
- YAMNet hub 핸들은 `DDINGDONG_YAMNET_HANDLE` 로 오버라이드(오프라인 로컬 경로 등).

### 예상 소요 / CPU 주의

- **CPU 만으로 충분.** 학습은 frozen backbone 임베딩 위 **작은 head(≈13만 파라미터)** 만
  돌아 가볍다. 병목은 YAMNet 임베딩 추출(클립당 1회 forward). train ≈11.6k 클립 기준
  CPU 에서 임베딩 1회 순회가 수 분~십수 분(머신 편차). 임베딩을 캐시하면 epoch 반복은 빠름.
- 첫 실행은 **YAMNet hub 다운로드**(수십 MB) 시간이 추가. 오프라인이면 로컬 핸들 지정.
- `EPOCHS=30` 기본이나 EarlyStopping(patience=6)이 대개 더 일찍 멈춘다.

## 기준선 (개선 확인용)

사전테스트 pre-trained YAMNet Top-1: **doorbell≈30% / knock≈40% / fire_alarm≈20%**.
head 학습 후 `evaluate` 결과가 이 대비 개선되는지 확인(리포트에 baseline 병기).

## 합성 더미 관통 검증 (repo 안, 실데이터 불필요)

```bash
python -m ml.training.tests.test_training_smoke      # 또는 pytest ml/training/tests/
```

더미 backbone(결정적 임베딩)을 주입해 파이프라인→학습(2ep)→체크포인트→평가까지 오프라인 관통.
clean 가드 stale 방지 + SpecAugment train-only 도 함께 검증.

## 설계 노트 — SpecAugment × frozen hub YAMNet (발표 전 결정 항목)

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

**→ 발표 전 결정**: SpecAugment 를 실제로 켤지( `logmel` 모드 + 로컬 YAMNet ), 아니면
`embedding` 모드 + 03 증강으로 충분한지. `KOREAN_SOURCE_MARKERS`(pitch shift 대상 미결)와
함께 데이터 규모·성능 보고 확정. `SpecAugment` 자체는 언제든 활성화 가능하도록 준비돼 있음.

## 미결 (upstream)

- **pitch shift 대상 미정**: `ml.pipeline.config.KOREAN_SOURCE_MARKERS` 가 빈 상태 →
  현재 pitch shift 적용 대상 0. 한국 환경음 소스 명명 규칙 확인 후 채워야 적용됨(발표 전 결정).
