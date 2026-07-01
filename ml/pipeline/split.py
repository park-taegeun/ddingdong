"""Step 2 — train/val/test 분할 (증강 이전, leakage 방지).

★ 원본(source) 단위 그룹 분할: 한 원본 오디오를 3초 간격으로 자른 조각(piece)
클립들(파일 stem 끝 `_`+7자리 인덱스)은 반드시 같은 split 에 통째 배정한다.
같은 원본의 조각이 train 과 val/test 로 흩어지면 data leakage → 이를 원천 차단.

절차(클래스별 = stratify 유지):
  (a) 전 클립 stem 을 config.source_key 로 그룹핑
  (b) source key 목록을 재현 seed 로 셔플 후 SPLIT_RATIO 로 train/val/test 배정
  (c) 각 source 의 모든 조각을 해당 split 으로 전개
결과는 split manifest CSV(filepath,class,split,stem,source_key)로 기록.
분할 최소 단위 = source(원본) 이며, stem(조각)은 추적/증강 키로만 사용.
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
_FIELDS = ["filepath", "class", "split", "stem", "source_key"]


class SourceSplitError(AssertionError):
    """같은 원본(source)의 조각이 2개 이상 split 에 흩어짐 → 조기 leakage 검출.

    guards.py 의 최종 stem 누수가드 도달 이전에, split 단계에서 원본 단위 무결성을
    직접 확인하는 1차(조기) 가드. (guards 는 stem 단위 backstop 으로 이중 검사.)
    """


def _allocate(n: int, ratio: tuple[float, float, float]) -> tuple[int, int, int]:
    """n개(=source 개수)를 train/val/test 로 배분. val/test 는 round, train 은 나머지.

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


def assert_source_integrity(rows: list[dict[str, str]]) -> dict[tuple[str, str], str]:
    """(class, source_key) 하나당 정확히 한 split 인지 검증. 위반 시 SourceSplitError.

    = Step 4 조기 누수 자체검증: 각 클래스에서 train source 집합 ∩ (val∪test source
    집합) = 공집합. 반환: {(class, source_key): split}.
    """
    split_of: dict[tuple[str, str], str] = {}
    for r in rows:
        key = (r["class"], r["source_key"])
        prev = split_of.setdefault(key, r["split"])
        if prev != r["split"]:
            raise SourceSplitError(
                f"원본 단위 분할 위반: source '{r['source_key']}'"
                f"(class={r['class']}) 가 '{prev}' 와 '{r['split']}' 에 동시 배정 — "
                f"같은 원본 조각이 흩어짐(leakage)."
            )
    return split_of


def split_dataset(paths: Paths) -> dict[str, dict[str, int]]:
    """분할 실행 → split manifest 기록. 반환: {class: {split: 조각(clip) 개수}}."""
    rng = random.Random(config.SEED)
    rows: list[dict[str, str]] = []
    counts: dict[str, dict[str, int]] = {}

    for cls in config.CLASSES:
        files = list(audio_io.iter_audio_files(paths.preprocessed / cls))
        by_stem = {p.stem: p for p in files}

        # (a) 조각 stem → 원본(source) key 그룹핑. stem 정렬로 그룹 내부도 결정적.
        sources: dict[str, list[str]] = {}
        for stem in sorted(by_stem):
            sources.setdefault(config.source_key(stem), []).append(stem)

        # (b) source key 목록을 정렬(결정적 기저) 후 seed 셔플 → 비율 배분.
        source_keys = sorted(sources)
        rng.shuffle(source_keys)
        n_train, n_val, n_test = _allocate(len(source_keys), config.SPLIT_RATIO)
        assigned_src = (
            [("train", k) for k in source_keys[:n_train]]
            + [("val", k) for k in source_keys[n_train : n_train + n_val]]
            + [("test", k) for k in source_keys[n_train + n_val :]]
        )

        # (c) 각 source 의 모든 조각을 해당 split 으로 전개.
        clip_counts = {"train": 0, "val": 0, "test": 0}
        for split, skey in assigned_src:
            for stem in sources[skey]:
                rows.append(
                    {
                        "filepath": str(by_stem[stem]),
                        "class": cls,
                        "split": split,
                        "stem": stem,
                        "source_key": skey,
                    }
                )
                clip_counts[split] += 1
        counts[cls] = clip_counts

        # Step 3 로그: 클래스별 source 개수 / 조각 총 개수 / split별(source·조각) 배분.
        log.info(
            "split %-11s | sources %d (t/v/te=%d/%d/%d) | clips %d "
            "(t/v/te=%d/%d/%d)",
            cls, len(source_keys), n_train, n_val, n_test,
            sum(clip_counts.values()),
            clip_counts["train"], clip_counts["val"], clip_counts["test"],
        )

    # Step 4: guards 도달 전, split 단계 조기 누수 자체검증(원본 미분할 assert).
    assert_source_integrity(rows)

    paths.manifests.mkdir(parents=True, exist_ok=True)
    out = paths.manifests / SPLIT_MANIFEST
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    log.info("split manifest → %s (%d clips, 원본 단위 무결성 OK)", out, len(rows))
    return counts


def load_split_manifest(paths: Paths) -> list[dict[str, str]]:
    path = paths.manifests / SPLIT_MANIFEST
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))
