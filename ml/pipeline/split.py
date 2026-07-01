"""Step 2 — 파일단위 train/val/test 분할 (증강 이전, leakage 방지).

각 원본 클립 = stem 하나 = 분할 최소 단위. 클래스별로 stem을 재현 seed 로
셔플 후 비율 배분. 결과는 split manifest CSV(filepath,class,split,stem)로 기록.
"""

from __future__ import annotations

import csv
import logging
import random

from . import audio_io, config
from .config import Paths

log = logging.getLogger("ml.pipeline.split")

SPLIT_MANIFEST = "split_manifest.csv"
SPLITS = ("train", "val", "test")


def _allocate(n: int, ratio: tuple[float, float, float]) -> tuple[int, int, int]:
    """n개를 train/val/test 로 배분. val/test 는 round, train 은 나머지(합 보존).

    작은 n 에서도 안전: val/test 가 0으로 눌리면 train 이 흡수(빈 split 허용).
    """
    r_train, r_val, r_test = ratio
    n_val = int(round(n * r_val))
    n_test = int(round(n * r_test))
    n_train = n - n_val - n_test
    if n_train < 0:  # 과배분 방어(극소 n)
        n_train = 0
        n_test = min(n_test, n)
        n_val = n - n_test
    return n_train, n_val, n_test


def split_dataset(paths: Paths) -> dict[str, dict[str, int]]:
    """분할 실행 → split manifest 기록. 반환: {class: {split: count}}."""
    rng = random.Random(config.SEED)
    rows: list[dict[str, str]] = []
    counts: dict[str, dict[str, int]] = {}

    for cls in config.CLASSES:
        files = list(audio_io.iter_audio_files(paths.preprocessed / cls))
        stems = sorted(p.stem for p in files)  # 정렬 후 셔플 → 재현성
        rng.shuffle(stems)
        n_train, n_val, n_test = _allocate(len(stems), config.SPLIT_RATIO)
        assigned = (
            [("train", s) for s in stems[:n_train]]
            + [("val", s) for s in stems[n_train : n_train + n_val]]
            + [("test", s) for s in stems[n_train + n_val :]]
        )
        by_stem = {p.stem: p for p in files}
        for split, stem in assigned:
            rows.append(
                {
                    "filepath": str(by_stem[stem]),
                    "class": cls,
                    "split": split,
                    "stem": stem,
                }
            )
        counts[cls] = {"train": n_train, "val": n_val, "test": n_test}
        log.info("split %-11s train=%d val=%d test=%d", cls, n_train, n_val, n_test)

    paths.manifests.mkdir(parents=True, exist_ok=True)
    out = paths.manifests / SPLIT_MANIFEST
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["filepath", "class", "split", "stem"])
        writer.writeheader()
        writer.writerows(rows)
    log.info("split manifest → %s (%d rows)", out, len(rows))
    return counts


def load_split_manifest(paths: Paths) -> list[dict[str, str]]:
    path = paths.manifests / SPLIT_MANIFEST
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))
