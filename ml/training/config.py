"""학습 전역 설정 — 매직넘버 금지, 파이프라인 config 를 SSoT 로 재사용.

★ 클래스 순서/오디오 규격/시드/경로는 ml.pipeline.config 가 단일 출처.
  실행마다 학습할 클래스 집합은 인자로 받되(기본값 없음), resolve_classes 가 CLASSES 순서로
  정규화한다 → 라벨 인덱스는 재정의 없이 CLASSES 순서를 상속(doorbell=0, knock=1, fire_alarm=2).
  그 실행이 실제로 쓴 클래스·인덱스는 run 폴더 labels.json 이 단일 출처(평가·배포가 읽는다).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from ml.pipeline import config as pipe

# --------------------------------------------------------------------------
# 파이프라인에서 상속하는 SSoT 값 (재정의 금지)
# --------------------------------------------------------------------------
CLASSES: tuple[str, ...] = pipe.CLASSES        # ("doorbell", "knock", "fire_alarm") — 허용 집합·순서
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
# 분류 head (trainable) — 중간층은 정규화용, 없으면 Dense(클래스 수) 단독도 가능.
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
# 산출물 — run 폴더(학습 1회 = 폴더 1개). 오디오·모델 git 커밋 0.
#   --out-dir 또는 env DDINGDONG_MODEL_DIR 필수(repo 기본 경로 fallback 없음 — 서빙 모델 보호).
# --------------------------------------------------------------------------
CHECKPOINT_NAME: str = "best.keras"             # 최적 val 헤드 가중치
HISTORY_NAME: str = "history.json"              # fit history
EVAL_REPORT_NAME: str = "eval_report.json"      # test accuracy + per-class P/R/F1
CONFUSION_NAME: str = "confusion_matrix.csv"    # test confusion matrix
LABELS_NAME: str = "labels.json"                # 이 run 의 클래스·인덱스(배포 동봉)
SAVEDMODEL_NAME: str = "inference_savedmodel"   # 배포 아티팩트 디렉토리명
TRAIN_ARTIFACTS: tuple[str, ...] = (CHECKPOINT_NAME, LABELS_NAME, SAVEDMODEL_NAME)


def resolve_classes(names, allowed: tuple[str, ...] = CLASSES) -> tuple[str, ...]:
    """클래스 집합(쉼표 문자열 또는 iterable) → allowed 순서로 정규화한 튜플.

    빈 집합 · 모르는 이름 · 중복은 거부. 입력 순서는 무시 — 라벨 인덱스 = allowed 순서.
    """
    items = [n.strip() for n in names.split(",")] if isinstance(names, str) else list(names)
    if not items or any(not n for n in items):
        raise ValueError(f"클래스 집합이 비었거나 빈 이름 포함: {names!r} (허용: {allowed})")
    unknown = [n for n in items if n not in allowed]
    if unknown:
        raise ValueError(f"모르는 클래스 {unknown} (허용: {allowed})")
    if len(set(items)) != len(items):
        raise ValueError(f"클래스 중복: {items}")
    return tuple(c for c in allowed if c in items)


def resolve_run_dir(arg: str | os.PathLike | None) -> Path:
    """run 폴더 = 인자 우선, 없으면 env DDINGDONG_MODEL_DIR. 둘 다 없으면 즉시 실패."""
    raw = str(arg) if arg else os.environ.get("DDINGDONG_MODEL_DIR", "").strip()
    if not raw:
        raise ValueError(
            "산출 폴더 미지정: --out-dir 또는 env DDINGDONG_MODEL_DIR 가 필요하다"
            "(기본 경로 없음 — 서빙 모델 폴더 덮어쓰기 방지)."
        )
    return Path(raw).expanduser()


def refuse_existing(out_dir: Path, names: tuple[str, ...]) -> None:
    """out_dir 에 names 중 하나라도 있으면 거부(덮어쓰기 0). 쓰기 전에 부른다."""
    found = [n for n in names if (out_dir / n).exists()]
    if found:
        raise FileExistsError(f"덮어쓰기 거부: {out_dir} 에 이미 {found} 존재 → 새 폴더를 지정할 것.")


def write_labels(out_dir: Path, classes: tuple[str, ...]) -> Path:
    """이 run 이 학습한 클래스·인덱스를 labels.json 으로 기록."""
    path = out_dir / LABELS_NAME
    path.write_text(
        json.dumps({"classes": list(classes), "index": {c: i for i, c in enumerate(classes)}},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def read_labels(run_dir: Path, classes, allowed: tuple[str, ...] = CLASSES) -> tuple[str, ...]:
    """run 폴더 labels.json 의 클래스 목록. 인자 classes 와 다르면 거부."""
    path = run_dir / LABELS_NAME
    if not path.is_file():
        raise FileNotFoundError(f"labels.json 없음: {path} → 학습된 run 폴더를 지정할 것.")
    got = tuple(json.loads(path.read_text(encoding="utf-8"))["classes"])
    want = resolve_classes(classes, allowed)
    if got != want:
        raise ValueError(f"클래스 불일치: 인자 {list(want)} ≠ {path} {list(got)}")
    return got


def check_head(head, classes: tuple[str, ...], ckpt: Path) -> None:
    """체크포인트 head 출력 수 == run labels.json 클래스 수(--checkpoint 로 남의 head 를 준 경우 차단)."""
    if head.output_shape[-1] != len(classes):
        raise ValueError(f"head 출력 {head.output_shape[-1]} ≠ 클래스 {len(classes)}개 {list(classes)} @ {ckpt}")


def resolve_final_dir(data_root: str | os.PathLike | None = None) -> Path:
    """05_final_dataset 경로(파이프라인 config 재사용)."""
    return pipe.resolve_paths(data_root).final
