"""Step 5 — 누수 가드: train stem 집합 ∩ (val ∪ test) stem 집합 = 공집합 검증."""

from __future__ import annotations

from .augment import base_stem


class LeakageError(AssertionError):
    """train 원본 stem 이 val/test 에도 존재 → data leakage."""


def assert_no_leakage(final_rows: list[dict[str, str]]) -> dict[str, int]:
    """final manifest 행들로 split 간 stem 겹침 검사. 위반 시 즉시 LeakageError."""
    by_split: dict[str, set[str]] = {"train": set(), "val": set(), "test": set()}
    for r in final_rows:
        by_split[r["split"]].add(base_stem(r["filepath"]))

    holdout = by_split["val"] | by_split["test"]
    leaked = by_split["train"] & holdout
    if leaked:
        sample = sorted(leaked)[:10]
        raise LeakageError(
            f"data leakage: {len(leaked)}개 stem 이 train 과 val/test 에 동시 존재. 예: {sample}"
        )
    val_test_overlap = by_split["val"] & by_split["test"]
    if val_test_overlap:
        sample = sorted(val_test_overlap)[:10]
        raise LeakageError(
            f"val/test stem 겹침 {len(val_test_overlap)}개. 예: {sample}"
        )
    return {k: len(v) for k, v in by_split.items()}
