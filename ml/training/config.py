"""학습 전역 설정 — 매직넘버 금지, 파이프라인 config 를 SSoT 로 재사용.

★ 클래스 순서/오디오 규격/시드/경로는 ml.pipeline.config 가 단일 출처.
  라벨 인덱스( doorbell=0, knock=1, fire_alarm=2 )는 여기서 재정의하지 않고 그대로 상속한다.
  (추론·평가·배포가 학습과 동일한 인덱스를 쓰도록 강제 — decisions.md 카테고리 4.)
"""

from __future__ import annotations

import os
from pathlib import Path

from ml.pipeline import config as pipe

# --------------------------------------------------------------------------
# 파이프라인에서 상속하는 SSoT 값 (재정의 금지)
# --------------------------------------------------------------------------
CLASSES: tuple[str, ...] = pipe.CLASSES        # ("doorbell", "knock", "fire_alarm")
NUM_CLASSES: int = len(CLASSES)
CLASS_TO_INDEX: dict[str, int] = {c: i for i, c in enumerate(CLASSES)}
SAMPLE_RATE: int = pipe.SAMPLE_RATE            # 16_000
SEED: int = pipe.SEED                          # 42
SPLITS: tuple[str, ...] = ("train", "val", "test")

# --------------------------------------------------------------------------
# YAMNet backbone (카테고리 4) — hub 핸들은 env 로 오버라이드 가능(오프라인 로컬 경로 등).
# --------------------------------------------------------------------------
YAMNET_HUB_HANDLE: str = os.environ.get(
    "DDINGDONG_YAMNET_HANDLE", "https://tfhub.dev/google/yamnet/1"
)
EMBED_DIM: int = 1024                           # YAMNet embedding 차원(모델 스펙 고정)

# YAMNet frontend(log-mel) 규격 — SpecAugment(logmel 모드)용 tf.signal 프론트엔드가 사용.
# 값은 YAMNet 공개 파라미터(params.py)와 일치.
MEL_BANDS: int = 64
STFT_WINDOW_SEC: float = 0.025                  # 25 ms
STFT_HOP_SEC: float = 0.010                     # 10 ms
MEL_MIN_HZ: float = 125.0
MEL_MAX_HZ: float = 7_500.0

# --------------------------------------------------------------------------
# 분류 head (trainable) — 중간층은 정규화용, 없으면 Dense(3) 단독도 가능.
# --------------------------------------------------------------------------
HEAD_HIDDEN_UNITS: int = 128
HEAD_DROPOUT: float = 0.5

# --------------------------------------------------------------------------
# 학습 하이퍼파라미터 (전부 상수 — 매직넘버 금지)
# --------------------------------------------------------------------------
BATCH_SIZE: int = 32
EPOCHS: int = 30                                # early stopping 이 대개 더 일찍 멈춤
LEARNING_RATE: float = 1e-3
EARLY_STOP_PATIENCE: int = 6                    # val_loss 개선 없으면 조기 종료
REDUCE_LR_PATIENCE: int = 3
REDUCE_LR_FACTOR: float = 0.5
SHUFFLE_BUFFER: int = 2_048

# --------------------------------------------------------------------------
# SpecAugment (카테고리 5) — freq_mask=10 / time_mask=5. ★ train 배치에만, 학습 시점.
#   값은 파이프라인 config.SPECAUGMENT(SSoT)에서 상속. val/test 절대 미적용.
# --------------------------------------------------------------------------
SPECAUG_FREQ_MASK_PARAM: int = int(pipe.SPECAUGMENT["freq_mask_param"])  # 10
SPECAUG_TIME_MASK_PARAM: int = int(pipe.SPECAUGMENT["time_mask_param"])  # 5
SPECAUG_N_FREQ_MASKS: int = 1
SPECAUG_N_TIME_MASKS: int = 1

# --------------------------------------------------------------------------
# 산출물 경로 — 체크포인트/히스토리/평가는 repo 안 gitignore 폴더(ml/models/) 기본.
#   (오디오·모델 git 커밋 0. env DDINGDONG_MODEL_DIR 로 학부생이 외부 경로 지정 가능.)
# --------------------------------------------------------------------------
CHECKPOINT_NAME: str = "best.keras"             # 최적 val 헤드 가중치
HISTORY_NAME: str = "history.json"              # fit history
EVAL_REPORT_NAME: str = "eval_report.json"      # test accuracy + per-class P/R/F1
CONFUSION_NAME: str = "confusion_matrix.csv"    # test confusion matrix
LABELS_NAME: str = "labels.json"                # 라벨 인덱스 SSoT 스냅샷(배포 동봉)


def repo_root() -> Path:
    """ml/training/config.py → repo 루트(= parents[2])."""
    return Path(__file__).resolve().parents[2]


def model_dir() -> Path:
    """학습 산출물 디렉토리. env DDINGDONG_MODEL_DIR 우선, 없으면 repo 내 ml/models/yamnet."""
    raw = os.environ.get("DDINGDONG_MODEL_DIR")
    return Path(raw).expanduser() if raw else repo_root() / "ml" / "models" / "yamnet"


def resolve_final_dir(data_root: str | os.PathLike | None = None) -> Path:
    """05_final_dataset 경로(파이프라인 config 재사용)."""
    return pipe.resolve_paths(data_root).final
