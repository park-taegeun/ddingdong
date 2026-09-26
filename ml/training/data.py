"""데이터 로더 — 05_final_dataset → tf.data.Dataset (embedding 모드).

입력 인덱싱(택1): **폴더 직접 스캔** `05_final_dataset/{split}/{class}/*.wav`.
  근거: final_manifest.csv 의 filepath 는 학습 시점 절대경로라 이동에 취약. 폴더 스캔은
  파이프라인 출력 구조(클래스 하위폴더)만 의존해 견고. (manifest 로 바꾸려면 load_manifest
  헬퍼 참조 — 컬럼 filepath/class/split/origin/source_stem.)

파이프라인 audio_io(soundfile 기반)를 재사용해 wav → float32 [-1,1] mono 16kHz 로 로드.
YAMNet 임베딩은 backbone(embed_fn)에 위임 — 실학습은 hub YAMNet, 테스트는 더미 주입.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from ml.pipeline import audio_io
from . import config


# --------------------------------------------------------------------------
# 1) 인덱싱 (TF 불필요 — 단독 테스트 가능)
# --------------------------------------------------------------------------
def list_examples(
    final_dir: Path, split: str, classes: tuple[str, ...]
) -> list[tuple[Path, int]]:
    """05_final_dataset/{split}/{class}/*.wav → [(path, label_index)] (정렬 = 재현성).

    라벨 인덱스 = classes 안의 위치(resolve_classes 로 정규화된 튜플을 넘길 것).
    요청 클래스가 이 split 에서 0개면 즉시 ValueError(조용히 건너뛰지 않음).
    """
    if split not in config.SPLITS:
        raise ValueError(f"알 수 없는 split: {split!r} (허용: {config.SPLITS})")
    examples: list[tuple[Path, int]] = []
    split_dir = final_dir / split
    for label, cls in enumerate(classes):
        wavs = list(audio_io.iter_audio_files(split_dir / cls))
        if not wavs:
            raise ValueError(
                f"빈 클래스: split={split} class={cls} 클립 0개 @ {split_dir / cls}\n"
                f"  → 05_final_dataset 을 확인하거나 이 클래스를 --classes 에서 뺄 것."
            )
        examples.extend((wav, label) for wav in wavs)
    return examples


def load_manifest(
    manifests_dir: Path, split: str, classes: tuple[str, ...]
) -> list[tuple[Path, int]]:
    """대안 인덱싱: final_manifest.csv 에서 split·classes 행만 → [(path, label)].

    (기본은 list_examples 폴더 스캔. manifest 를 쓰고 싶을 때만 호출.)
    """
    path = manifests_dir / "final_manifest.csv"
    index = {c: i for i, c in enumerate(classes)}
    with path.open(newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["split"] == split and r["class"] in index]
    empty = [c for c in classes if not any(r["class"] == c for r in rows)]
    if empty:
        raise ValueError(f"빈 클래스: split={split} class={empty} 행 0개 @ {path}")
    return [(Path(r["filepath"]), index[r["class"]]) for r in rows]


def compute_class_weights(labels: list[int], num_classes: int) -> dict[int, float]:
    """sklearn 'balanced' 방식으로 실측 배분에서 class_weight 자동 산출(하드코딩 금지).

    balanced: w_c = n_total / (n_classes * n_c). 소수 클래스에 큰 가중.
    어떤 클래스가 0개면 balanced 가 정의되지 않으므로 즉시 ValueError(균등 폴백 없음).
    """
    from sklearn.utils.class_weight import compute_class_weight

    classes = np.arange(num_classes)
    missing = sorted(set(classes.tolist()) - set(labels))
    if missing:
        raise ValueError(f"class_weight 산출 불가: 라벨 인덱스 {missing} 가 0개")
    weights = compute_class_weight("balanced", classes=classes, y=np.asarray(labels))
    return {int(c): float(w) for c, w in zip(classes, weights)}


# --------------------------------------------------------------------------
# 2) tf.data 임베딩 데이터셋 (TF 지연 import)
# --------------------------------------------------------------------------
def _embed_one(path_bytes: bytes, embed_fn) -> np.ndarray:
    """단일 클립 경로 → mean-pool 임베딩 [EMBED_DIM] float32. (numpy_function 내부용)"""
    path = Path(path_bytes.decode("utf-8"))
    wav = audio_io.load_mono(path)                        # float32 [-1,1] mono 16k
    if wav.size == 0:                                     # 빈 클립 가드(초단파/손상)
        raise ValueError(f"빈 waveform: {path}")
    emb = np.asarray(embed_fn(wav), dtype=np.float32)
    if emb.shape != (config.EMBED_DIM,):                  # shape 불일치 가드
        raise ValueError(f"임베딩 shape 불일치: {emb.shape} != ({config.EMBED_DIM},) @ {path}")
    return emb


def make_embedding_dataset(
    examples: list[tuple[Path, int]],
    embed_fn,
    *,
    training: bool,
    batch_size: int = config.BATCH_SIZE,
    shuffle_buffer: int = config.SHUFFLE_BUFFER,
    seed: int = config.SEED,
):
    """[(path,label)] + backbone(embed_fn) → 배치 (embedding[EMBED_DIM], label) 데이터셋.

    training=True 만 shuffle. 증강(SpecAugment)은 embedding 모드에서 미적용
    (backbone 블랙박스 — README 설계 노트). val/test 는 training=False 로 셔플·증강 없음.
    """
    import tensorflow as tf

    if not examples:
        raise ValueError("빈 예제 리스트 → 빈 배치 방지 위해 중단")

    paths = [str(p) for p, _ in examples]
    labels = [int(y) for _, y in examples]
    ds = tf.data.Dataset.from_tensor_slices((paths, labels))
    if training:
        ds = ds.shuffle(
            min(len(examples), shuffle_buffer), seed=seed, reshuffle_each_iteration=True
        )

    def _map(path, label):
        emb = tf.numpy_function(
            func=lambda p: _embed_one(p, embed_fn), inp=[path], Tout=tf.float32,
        )
        emb.set_shape([config.EMBED_DIM])                 # 정적 shape 명시(하류 Dense 필수)
        return emb, label

    ds = ds.map(_map, num_parallel_calls=tf.data.AUTOTUNE)
    ds = ds.batch(batch_size)
    return ds.prefetch(tf.data.AUTOTUNE)
