"""Step 2 — train/val/test 분할 (증강 이전, leakage 방지).

★ 원본(source) 단위 그룹 분할: 한 원본 오디오를 3초 간격으로 자른 조각(piece)
클립들(파일 stem 끝 `_`+7자리 인덱스)은 반드시 같은 split 에 통째 배정한다.
같은 원본의 조각이 train 과 val/test 로 흩어지면 data leakage → 이를 원천 차단.
직접녹음(`direct_`)은 테이크가 아니라 **유닛**까지가 한 그룹이다(config.source_key).

절차(클래스별 = stratify 유지):
  (a) 02 클립에서 무음·AI Hub 앞머리 멘트·클래스 교차·중복을 걷어낸다(select_clips).
      제거 내역은 dedup manifest CSV 로 남기고, **02 의 파일 자체는 지우지 않는다**
      (split 대상에서만 제외 — 원본 보존·재현 가능).
  (b) 남은 클립 stem 을 config.source_key 로 그룹핑
  (c) 각 그룹 키를 sha256(f"{SEED}:{class}:{group_key}") 으로 [0,1) 에 사상해
      SPLIT_RATIO 누적 경계로 train/val/test 를 정한다(assign_split).
      ★ 셔플이 아니다 — 새 source 가 들어와도 기존 source 의 배정이 바뀌지 않는다.
      (기각된 설계 = 클래스 루프 밖 공유 random.Random(SEED) + shuffle. doorbell
       source 1개만 늘어도 knock 클립 124/714 의 소속이 바뀌었다 = decisions.md 5.2(c).)
  (d) 각 source 의 모든 조각을 해당 split 으로 전개
결과는 split manifest CSV(filepath,class,split,stem,source_key)로 기록.
분할 최소 단위 = source(원본) 이며, stem(조각)은 추적/증강 키로만 사용.
"""

from __future__ import annotations

import csv
import hashlib
import logging
from pathlib import Path

from . import audio_io, config
from .config import Paths

log = logging.getLogger("ml.pipeline.split")

SPLIT_MANIFEST = "split_manifest.csv"
SPLITS = ("train", "val", "test")
_FIELDS = ["filepath", "class", "split", "stem", "source_key"]

# 내용 중복 제거(D1) 내역 기록 — split manifest 와 같은 폴더/관용구(행 = 클립 1개).
DEDUP_MANIFEST = "dedup_manifest.csv"
_DEDUP_FIELDS = ["filepath", "class", "stem", "md5", "reason", "kept_stem"]

REASON_SILENCE = "digital_silence"      # 디코딩 샘플 전부 0
REASON_CLASS_CROSS = "class_cross"      # 같은 md5 가 2개 이상 클래스 폴더에 → 양쪽 모두 제거
REASON_SAME_CLASS_DUP = "same_class_dup"  # 한 클래스 안 반복 → 정렬상 첫 stem 만 유지
REASON_AIHUB_INTRO = "aihub_intro_speech"  # AI Hub 화재 녹음 앞머리 멘트 조각(33.15(d))


class SourceSplitError(AssertionError):
    """같은 원본(source)의 조각이 2개 이상 split 에 흩어짐 → 조기 leakage 검출.

    guards.py 의 최종 stem 누수가드 도달 이전에, split 단계에서 원본 단위 무결성을
    직접 확인하는 1차(조기) 가드. (guards 는 stem 단위 backstop 으로 이중 검사.)
    """


def file_md5(path: Path) -> str:
    """파일 바이트 md5. 33.7 감사(내용 중복 실측)와 같은 기준으로 맞춘다."""
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def is_digital_silence(path: Path) -> bool:
    """디코딩 샘플이 전부 0(길이 0 포함) = 디지털 무음."""
    return not audio_io.load_mono(path).any()


def is_aihub_intro(cls: str, stem: str) -> bool:
    """AI Hub 화재 녹음 앞머리 멘트 조각인가(33.15(d)). 조각 suffix 가 없으면 시작 시각을
    모르므로 빼지 않는다(False)."""
    m = config.PIECE_SUFFIX_PATTERN.search(stem)
    return (
        cls == config.AIHUB_INTRO_CLASS
        and config.AIHUB_INTRO_MARKER in stem
        and m is not None
        and int(m.group()[1:]) < config.AIHUB_INTRO_END_MS
    )


def select_clips(
    by_class: dict[str, dict[str, Path]]
) -> tuple[dict[str, dict[str, Path]], list[dict[str, str]]]:
    """split 대상 클립을 고른다(D1 + 33.15(d)). 반환: (유지분, 제거 기록 행).

    규칙 — ★ 적용 순서가 규칙의 일부다(무음 → 멘트 → 클래스 교차 → 같은 클래스 중복):
      1. 디지털 무음 = 디코딩 샘플 전부 0 → 제거.
      1-b. AI Hub 앞머리 멘트 = is_aihub_intro → 제거(33.15(d), `other` 로 재활용하지 않는다).
      2. 클래스 교차 = 같은 md5 가 2개 이상 클래스 폴더에 존재 → 그 md5 의 **모든** 파일 제거
         (어느 쪽이 정답 라벨인지 알 수 없으므로 한쪽만 남기지 않는다).
      3. 같은 클래스 중복 = 같은 md5 가 한 클래스 안에서만 반복 → 정렬상 첫 stem 1개만 유지.
    🔴 중복 제거(3)를 먼저 돌리면 교차 그룹에 한 클래스만 남아 규칙 2가 무력화된다
    (Step 1 실측: 순서를 뒤집으면 잔존 2299 → 2304). 무음(1)과 교차(2)는 서로 순서를
    바꿔도 잔존 집합이 같고 사유 라벨만 달라진다 — 그래서 순서를 상수처럼 고정한다.
    멘트(1-b)는 33.15(d) 결정 순서대로 무음 다음 · 교차 앞이다. 멘트 조각끼리 바이트가 같은
    그룹(33.7(g))은 중복(3)보다 먼저 멘트 사유로 빠진다.
    🔴 02 의 파일은 지우지 않는다 — split 대상에서만 빠진다(원본 보존·재현 가능).
    """
    md5_of: dict[tuple[str, str], str] = {}
    silent: set[tuple[str, str]] = set()
    for cls, stems in by_class.items():
        for stem, path in stems.items():
            md5_of[(cls, stem)] = file_md5(path)
            if is_digital_silence(path):
                silent.add((cls, stem))

    alive = set(md5_of)
    reason_of: dict[tuple[str, str], str] = {}
    kept_of: dict[tuple[str, str], str] = {}

    # 1. 무음
    for key in sorted(alive & silent):
        reason_of[key] = REASON_SILENCE
    alive -= set(reason_of)

    # 1-b. AI Hub 앞머리 멘트
    for key in sorted(alive):
        if is_aihub_intro(*key):
            reason_of[key] = REASON_AIHUB_INTRO
    alive -= set(reason_of)

    # 2. 클래스 교차 (살아남은 것 기준으로 다시 묶는다)
    for keys in _group_by_md5(alive, md5_of).values():
        if len({cls for cls, _ in keys}) > 1:
            for key in keys:
                reason_of[key] = REASON_CLASS_CROSS
    alive -= set(reason_of)

    # 3. 같은 클래스 중복 — 정렬상 첫 stem 만 유지
    for keys in _group_by_md5(alive, md5_of).values():
        if len(keys) > 1:
            survivor, *rest = sorted(keys)
            for key in rest:
                reason_of[key] = REASON_SAME_CLASS_DUP
                kept_of[key] = survivor[1]
    alive -= set(reason_of)

    kept = {cls: {st: p for st, p in stems.items() if (cls, st) in alive}
            for cls, stems in by_class.items()}
    dropped = [
        {
            "filepath": str(by_class[cls][stem]),
            "class": cls,
            "stem": stem,
            "md5": md5_of[(cls, stem)],
            "reason": reason_of[(cls, stem)],
            "kept_stem": kept_of.get((cls, stem), ""),
        }
        for cls, stem in sorted(reason_of)
    ]
    return kept, dropped


def _group_by_md5(
    keys, md5_of: dict[tuple[str, str], str]
) -> dict[str, list[tuple[str, str]]]:
    groups: dict[str, list[tuple[str, str]]] = {}
    for key in sorted(keys):
        groups.setdefault(md5_of[key], []).append(key)
    return groups


def assign_split(
    cls: str,
    group_key: str,
    seed: int = config.SEED,
    ratio: tuple[float, float, float] = config.SPLIT_RATIO,
) -> str:
    """(class, group key) → split. **순수 함수 — 새 source 추가가 기존 배정을 바꾸지 않는다.**

    sha256(f"{seed}:{class}:{group_key}") 앞 8바이트를 [0,1) 로 사상해 ratio 누적 경계
    (train < r_train ≤ val < r_train+r_val ≤ test)와 비교한다. 입력이 그 셋뿐이므로
    **다른 source 의 존재·개수·순서가 결과에 영향을 줄 수 없다** — 기각된 설계(클래스
    루프 밖 공유 random.Random(SEED) + shuffle)가 doorbell source 1개 추가만으로 knock
    클립 124/714 를 흔들던 원인(decisions.md 5.2(c) 실측)을 구조적으로 제거한다.
    ★ 파이썬 내장 hash() 금지 — 프로세스마다 salt 가 달라 재현되지 않는다.
    ⚠️ 비율은 **기대값**이다. 그룹 수가 적으면(예: 직접녹음 4유닛) 실제 배분이 거칠고
    특정 split 이 0이 될 수 있다 — 개수를 맞춰 자르던 기존 _allocate 와의 맞바꿈이다.
    """
    digest = hashlib.sha256(f"{seed}:{cls}:{group_key}".encode("utf-8")).digest()
    u = int.from_bytes(digest[:8], "big") / 2.0 ** 64
    if u < ratio[0]:
        return "train"
    if u < ratio[0] + ratio[1]:
        return "val"
    return "test"


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
    """분할 실행 → split·dedup manifest 기록. 반환: {class: {split: 조각(clip) 개수}}."""
    rows: list[dict[str, str]] = []
    counts: dict[str, dict[str, int]] = {}

    # (a) 내용 해시 기준 선별(D1). 02 파일은 보존 — split 대상에서만 제외한다.
    by_class = {
        cls: {p.stem: p for p in audio_io.iter_audio_files(paths.preprocessed / cls)}
        for cls in config.CLASSES
    }
    kept, dropped = select_clips(by_class)
    _write_dedup_manifest(paths, dropped)

    for cls in config.CLASSES:
        by_stem = kept[cls]

        # (b) 조각 stem → 원본(source) key 그룹핑. stem 정렬로 그룹 내부도 결정적.
        sources: dict[str, list[str]] = {}
        for stem in sorted(by_stem):
            sources.setdefault(config.source_key(stem), []).append(stem)

        # (c) 그룹 키 해시로 고정 배정 — 셔플 없음(새 source 가 기존 배정을 흔들지 않음).
        src_counts = {"train": 0, "val": 0, "test": 0}
        clip_counts = {"train": 0, "val": 0, "test": 0}
        for skey in sorted(sources):
            split = assign_split(cls, skey)
            src_counts[split] += 1
            # (d) 각 source 의 모든 조각을 해당 split 으로 전개.
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
            cls, len(sources), src_counts["train"], src_counts["val"], src_counts["test"],
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


def _write_dedup_manifest(paths: Paths, dropped: list[dict[str, str]]) -> None:
    """제거 내역 기록. 제거 0건이어도 헤더만 있는 파일을 남긴다(「돌았고 0건」 ≠ 「안 돌았다」)."""
    paths.manifests.mkdir(parents=True, exist_ok=True)
    out = paths.manifests / DEDUP_MANIFEST
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_DEDUP_FIELDS)
        writer.writeheader()
        writer.writerows(dropped)
    tally: dict[str, int] = {}
    for r in dropped:
        tally[r["reason"]] = tally.get(r["reason"], 0) + 1
    log.info("dedup manifest → %s (제거 %d clips %s)", out, len(dropped), tally or "{}")


def load_dedup_manifest(paths: Paths) -> list[dict[str, str]]:
    path = paths.manifests / DEDUP_MANIFEST
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_split_manifest(paths: Paths) -> list[dict[str, str]]:
    path = paths.manifests / SPLIT_MANIFEST
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))
