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


def clean_final(paths: Paths) -> list[Path]:
    """05_final_dataset/{train,val,test} 를 재생성 전 비운다(stale 중첩 방지).

    배경: assemble 은 _copy(shutil.copy2)로 덮어쓸 뿐 기존 파일을 지우지 않는다. 클립
    집합이 줄어든 채 재실행하면 이전 실행의 잔여 클립이 남아 05 개수가 부풀어 오른다
    (실측: 정상 12453 대비 stale 16797 잔여물 발견 → 이 함수로 수동 rm 위험 제거).

    ★ 안전 가드(카테고리 7: 상위/원본/manifest 절대 삭제 금지):
      - paths.final 폴더명이 정확히 DIR_FINAL('05_final_dataset')일 때만 동작.
      - 삭제 대상은 paths.final 직하위 train/val/test 딱 3개 뿐. 00/01_clips/manifests 불가.
      - 각 대상을 resolve 해 정말 paths.final 직하위인지 재확인(심볼릭/트래버설 차단).
    반환: 실제로 제거된 split 경로 목록.
    """
    final = paths.final
    if final.name != config.DIR_FINAL:
        raise ValueError(f"clean 거부: final 경로명이 {config.DIR_FINAL!r} 아님 → {final}")
    final_resolved = final.resolve()
    removed: list[Path] = []
    for split in ("train", "val", "test"):
        target = final / split
        if target.resolve().parent != final_resolved:
            raise ValueError(f"clean 거부: {target} 가 {final} 직하위가 아님")
        if target.exists():
            shutil.rmtree(target)
            removed.append(target)
    if removed:
        log.info("05 auto-clean: %s 제거(stale 방지)", [p.name for p in removed])
    return removed


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
