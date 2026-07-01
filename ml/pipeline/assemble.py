"""Step 4 — 05 조립: 최종 데이터셋 구성 + final manifest.

train = 02 train 원본 + 03 train 증강본
val   = 02 val 원본만          (증강 X)
test  = 02 test 원본만         (증강 X)
클래스 하위폴더 유지. 최종 manifest(csv) + split×class 개수 요약.
"""

from __future__ import annotations

import csv
import logging
import shutil
from pathlib import Path

from . import audio_io, config
from .augment import AUG_SEP, base_stem
from .config import Paths
from .split import load_split_manifest

log = logging.getLogger("ml.pipeline.assemble")

FINAL_MANIFEST = "final_manifest.csv"


def _copy(src: Path, dst_dir: Path) -> Path:
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    shutil.copy2(src, dst)
    return dst


def assemble(paths: Paths) -> dict[str, dict[str, int]]:
    """05_final_dataset 구성 → final manifest. 반환: {split: {class: count}}."""
    split_rows = load_split_manifest(paths)
    # stem → split 매핑(클래스별). 증강본을 train 으로 귀속시킬 때 사용.
    split_of: dict[tuple[str, str], str] = {
        (r["class"], r["stem"]): r["split"] for r in split_rows
    }

    rows: list[dict[str, str]] = []
    counts: dict[str, dict[str, int]] = {
        s: {c: 0 for c in config.CLASSES} for s in ("train", "val", "test")
    }

    # 1) 02 원본 → 각 split 로 복사
    for r in split_rows:
        cls, split = r["class"], r["split"]
        dst = _copy(Path(r["filepath"]), paths.split_dir(split) / cls)
        rows.append(
            {"filepath": str(dst), "class": cls, "split": split,
             "origin": "original", "source_stem": r["stem"]}
        )
        counts[split][cls] += 1

    # 2) 03 증강본 → train 로만 복사 (증강은 train 파생이므로 전부 train)
    for cls in config.CLASSES:
        for aug in audio_io.iter_audio_files(paths.augmented / cls):
            stem = base_stem(aug.name)
            if split_of.get((cls, stem)) != "train":
                # 방어: train 이 아닌 stem 의 증강본이 있으면 스킵(정상 파이프라인엔 없음)
                log.warning("증강본 %s 의 원본이 train 아님 → 스킵", aug.name)
                continue
            dst = _copy(aug, paths.split_dir("train") / cls)
            rows.append(
                {"filepath": str(dst), "class": cls, "split": "train",
                 "origin": "augmented", "source_stem": stem}
            )
            counts["train"][cls] += 1

    paths.manifests.mkdir(parents=True, exist_ok=True)
    out = paths.manifests / FINAL_MANIFEST
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["filepath", "class", "split", "origin", "source_stem"]
        )
        writer.writeheader()
        writer.writerows(rows)
    log.info("final manifest → %s (%d rows)", out, len(rows))
    return counts


def load_final_manifest(paths: Paths) -> list[dict[str, str]]:
    path = paths.manifests / FINAL_MANIFEST
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))
