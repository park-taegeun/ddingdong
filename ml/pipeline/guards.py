"""Step 5 — 누수 가드. 두 층으로 본다.

  · stem 층  : train stem 집합 ∩ (val ∪ test) stem 집합 = 공집합 (assert_no_leakage)
  · 내용 층  : 같은 내용 해시가 2개 이상 split 에 존재하면 즉시 실패
               (assert_no_content_leakage)

내용 층이 따로 필요한 이유 = 파일명 기준 그룹화는 **내용이 같은 다른 이름**을 막지
못한다(decisions.md 33.7(d) 「설계 결함이 아니라 범위 밖」). split 단계의 dedup(D1)이
그 내용을 이미 걷어내지만, dedup 이 꺼지거나 규칙이 좁아져도 불변식(「같은 내용은 두
split 에 없다」)이 지켜지도록 **가드를 따로 세워 이중 검사**한다.
"""

from __future__ import annotations

from pathlib import Path

from .augment import base_stem
from .split import file_md5


class LeakageError(AssertionError):
    """train 원본 stem 이 val/test 에도 존재 → data leakage."""


class ContentLeakageError(LeakageError):
    """같은 **내용**(바이트 해시)이 2개 이상 split 에 존재 → 내용 기준 data leakage."""


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


def assert_no_content_leakage(final_rows: list[dict[str, str]]) -> dict[str, int]:
    """같은 내용 해시가 2개 이상 split 에 걸치면 즉시 ContentLeakageError.

    반환: {split: 고유 내용 해시 개수}. 비용 = final manifest 전 파일 1회 md5.
    """
    seen: dict[str, tuple[str, str]] = {}   # md5 → (split, stem)
    by_split: dict[str, set[str]] = {"train": set(), "val": set(), "test": set()}
    for r in final_rows:
        path = Path(r["filepath"])
        md5 = file_md5(path)
        split = r["split"]
        by_split[split].add(md5)
        prev = seen.setdefault(md5, (split, path.stem))
        if prev[0] != split:
            raise ContentLeakageError(
                f"내용 기준 data leakage: md5 {md5} 가 "
                f"'{prev[0]}'(stem={prev[1]}) 와 '{split}'(stem={path.stem}) 에 동시 존재 — "
                "같은 내용이 split 경계를 넘었다."
            )
    return {k: len(v) for k, v in by_split.items()}
