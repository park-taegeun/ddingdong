"""로컬 FSD50K dev 덤프에서 `other`(OOD 네거티브) 후보 목록을 뽑는다 — E3 1단계.

읽기 전용이다. 오디오를 복사·변환·조각내지 않고 목록(CSV)만 만든다.
조각내기·재학습은 별도 작업 소관이다.

  python -m ml.curation.select_negatives \
      --dev-csv        "~/ML 학습 데이터/fsd50k_meta/FSD50K.ground_truth/dev.csv" \
      --vocabulary-csv "~/ML 학습 데이터/fsd50k_meta/FSD50K.ground_truth/vocabulary.csv" \
      --clips-info     "~/ML 학습 데이터/fsd50k_meta/FSD50K.metadata/dev_clips_info_FSD50K.json" \
      --pp-pnp         "~/ML 학습 데이터/fsd50k_meta/FSD50K.metadata/pp_pnp_ratings_FSD50K.json" \
      --audio-root     "~/ML 학습 데이터/ddingdong_dataset/00_source_raw/fsd50k/dev_audio/FSD50K.dev_audio" \
      --positive-clips "~/ML 학습 데이터/ddingdong_dataset/01_clips" \
      --out-dir        "~/ddingdong-측정결과/2026-09-21/negatives"

모든 경로는 인자로만 받는다(기본값 없음). 산출은 repo 밖 `--out-dir` 에만 쓴다.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import wave
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from ..pipeline.config import MIN_DURATION_SEC, source_key
from .taxonomy import (
    ASSIGNMENT,
    CATEGORY_LABEL,
    CATEGORY_PRIORITY,
    MISSING_HARD_NEGATIVES,
    PARENT_RULES,
)

TARGET_SIZE = 1_100          # §5 규모 시작값
LISTEN_SAMPLE_SIZE = 30      # 청취 검수 표본
MIN_CANDIDATES = 600         # 이보다 적으면 §9 정지
SALT = "ddingdong-other-negatives-v1"  # sha256 salt. 내장 hash() 는 프로세스마다 달라져 쓰지 않는다.

CANDIDATE_FIELDS = (
    "fsd_id", "rel_path", "selected_label", "all_labels", "category",
    "split", "duration_sec", "license", "rating", "rating_value",
)


def stable_key(fsd_id: str) -> str:
    """결정적 정렬 키. 내장 hash() 는 PYTHONHASHSEED 에 흔들려 금지."""
    return hashlib.sha256(f"{SALT}:{fsd_id}".encode()).hexdigest()


@dataclass
class Clip:
    fsd_id: str
    labels: tuple[str, ...]
    mids: dict[str, str]
    split: str


@dataclass
class Rejections:
    target: list[str] = field(default_factory=list)      # 제외 ①
    positive: list[str] = field(default_factory=list)    # 제외 ②
    too_short: list[str] = field(default_factory=list)   # 제외 ③
    unusable: list[str] = field(default_factory=list)    # 제외 ③ — 0바이트·헤더 손상
    hold: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))


# ── 입력 로드 ────────────────────────────────────────────────────────────────

def load_vocabulary(path: Path) -> dict[str, str]:
    """vocabulary.csv(헤더 없음, `index,display_name,mid`) → {라벨명: mid}."""
    out: dict[str, str] = {}
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.reader(fh):
            if len(row) < 3:
                continue
            out[row[1]] = row[2]
    if not out:
        raise ValueError(f"vocabulary 를 읽지 못했다: {path}")
    unknown = sorted(set(out) - set(ASSIGNMENT))
    if unknown:
        raise ValueError(f"배정표에 없는 라벨 {len(unknown)}건: {unknown[:5]}")
    return out


def load_clips(path: Path) -> list[Clip]:
    """dev.csv → Clip 목록. `fname,labels,mids,split`."""
    clips: list[Clip] = []
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            labels = tuple(row["labels"].split(","))
            mids = tuple(row["mids"].split(","))
            clips.append(Clip(row["fname"], labels, dict(zip(labels, mids)), row["split"]))
    if not clips:
        raise ValueError(f"dev.csv 를 읽지 못했다: {path}")
    return clips


def load_positive_source_ids(clips_dir: Path) -> set[str]:
    """01_clips 양성에 쓰인 FSD50K 유래 source ID(순수 숫자 stem)."""
    ids: set[str] = set()
    for wav in clips_dir.rglob("*.wav"):
        key = source_key(wav.stem)
        if key.isdigit():
            ids.add(key)
    return ids


def duration_sec(path: Path) -> float | None:
    """wav 헤더만 읽어 길이(초). 오디오 본문은 건드리지 않는다."""
    try:
        with wave.open(str(path), "rb") as wf:
            rate = wf.getframerate()
            return wf.getnframes() / rate if rate else None
    except (OSError, EOFError, wave.Error):
        return None


# ── 선별 ─────────────────────────────────────────────────────────────────────

def classify(labels: tuple[str, ...],
             df: dict[str, int] | None = None) -> tuple[str, str | None, str | None]:
    """클립 라벨 집합 → (판정, 선택 라벨, 사유).

    판정 = "target"(제외 ①) | "hold"(보류) | "keep".
    부모 라벨은 제외 기준으로 쓰지 않는다 — 자식이 하나도 없는 「미분화」일 때만
    그 부모의 규칙을 적용한다.

    선택 라벨은 hard negative 우선, 같은 범주면 **희소한 쪽**(= 번짐으로 올라붙은
    상위 노드가 아니라 잎에 가까운 쪽)을 고른다. df 가 없으면 이름순으로 떨어진다.
    """
    present = set(labels)
    # target > hold. 라벨 나열 순서로 판정이 흔들리면 안 되고, 미분화 Alarm 처럼
    # 부모 규칙에서 나온 target 도 hold 라벨보다 앞선다(제외 ① 은 확정, 보류는 재검토).
    verdicts = [(ASSIGNMENT[label], label) for label in labels
                if ASSIGNMENT[label] in ("target", "hold")]
    verdicts += [(verdict, f"{parent}(미분화)")
                 for parent, (children, verdict) in PARENT_RULES.items()
                 if parent in present and not (present & children)]
    for kind in ("target", "hold"):
        for verdict, reason in verdicts:
            if verdict == kind:
                return kind, None, reason
    scored = [
        (CATEGORY_PRIORITY[ASSIGNMENT[label]], (df or {}).get(label, 0), label)
        for label in labels
        if ASSIGNMENT[label] in CATEGORY_PRIORITY
    ]
    if not scored:
        return "hold", None, "범주 라벨 없음(부모만)"
    scored.sort()
    return "keep", scored[0][2], None


def rating_of(ratings: dict, fsd_id: str, mid: str) -> tuple[str, str]:
    """pp_pnp_ratings → (등급, 값). -1(unsure)은 평균에서 뺀다.

    1.0 = PP(주 음원) / 0.5 = PNP(있지만 주가 아님) / 0 = NP.
    """
    raw = ratings.get(fsd_id, {}).get(mid)
    if not raw:
        return "NA", ""
    usable = [r for r in raw if r >= 0]
    if not usable:
        return "U", ""
    value = sum(usable) / len(usable)
    grade = "PP" if value >= 1.0 else ("PNP" if value > 0 else "NP")
    return grade, f"{value:.3f}"


def _quota(sizes: dict[str, int], target: int) -> dict[str, int]:
    """라벨당 상한을 균등하게 최대로 잡고, 남는 자리를 결정적으로 배분한다.

    상한 근거: 어느 한 라벨이 후보를 독식하지 않게 「모든 라벨에 같은 상한」을
    두고, 목표 규모를 넘지 않는 최대 상한을 고른다. 상한에 못 미치는 희소 라벨은
    가진 만큼만 들어가고, 그렇게 남은 자리는 여유 있는 라벨에 한 칸씩 돌린다.
    """
    if not sizes:
        return {}
    cap = 0
    for candidate in range(1, max(sizes.values()) + 1):
        if sum(min(candidate, n) for n in sizes.values()) > target:
            break
        cap = candidate
    quota = {label: min(cap, n) for label, n in sizes.items()}
    order = sorted(sizes, key=lambda label: (-(sizes[label] - quota[label]), label))
    while sum(quota.values()) < target and any(quota[l] < sizes[l] for l in order):
        for label in order:
            if sum(quota.values()) >= target:
                break
            if quota[label] < sizes[label]:
                quota[label] += 1
    return quota


def select(clips: list[Clip], positives: set[str],
           ratings: dict, audio_root: Path, target_size: int = TARGET_SIZE,
           min_duration: float = MIN_DURATION_SEC) -> tuple[list[dict], Rejections]:
    rej = Rejections()
    # 로컬 덤프에 0바이트 wav 가 섞여 있다(다부분 zip 해제 잔재로 보인다). 후보에
    # 넣으면 재학습이 그대로 깨지므로 먼저 걷어낸다.
    broken = {p.stem for p in audio_root.glob("*.wav") if p.stat().st_size == 0}
    df = Counter(label for clip in clips for label in clip.labels)
    pools: dict[str, list[tuple]] = defaultdict(list)
    for clip in clips:
        verdict, label, reason = classify(clip.labels, df)
        if verdict == "target":
            rej.target.append(clip.fsd_id)
            continue
        if verdict == "hold":
            rej.hold[reason].append(clip.fsd_id)
            continue
        if clip.fsd_id in positives:          # 제외 ② — 양성으로 이미 쓴 원본
            rej.positive.append(clip.fsd_id)
            continue
        if clip.fsd_id in broken:             # 제외 ③ — 오디오 실물이 비어 있다
            rej.unusable.append(clip.fsd_id)
            continue
        grade, value = rating_of(ratings, clip.fsd_id, clip.mids.get(label, ""))
        # PP(주 음원) 우선 → 같은 등급 안에서는 sha256 순. 라벨 불완전성 대응.
        pools[label].append((0 if grade == "PP" else 1, stable_key(clip.fsd_id),
                             clip, grade, value))
    for pool in pools.values():
        pool.sort(key=lambda row: (row[0], row[1]))

    quota = _quota({label: len(p) for label, p in pools.items()}, target_size)
    rows: list[dict] = []
    for label in sorted(pools):
        taken = 0
        for _, _, clip, grade, value in pools[label]:
            if taken >= quota[label]:
                break
            path = audio_root / f"{clip.fsd_id}.wav"
            seconds = duration_sec(path)
            if seconds is None:                             # 제외 ③ — 헤더 손상
                rej.unusable.append(clip.fsd_id)
                continue
            if seconds < min_duration:                      # 제외 ③ — 길이 미달
                rej.too_short.append(clip.fsd_id)
                continue
            rows.append({
                "fsd_id": clip.fsd_id,
                "rel_path": f"{audio_root.name}/{clip.fsd_id}.wav",
                "selected_label": label,
                "all_labels": ",".join(clip.labels),
                "category": ASSIGNMENT[label],
                "split": clip.split,
                "duration_sec": f"{seconds:.3f}",
                "license": "",
                "rating": grade,
                "rating_value": value,
            })
            taken += 1
    rows.sort(key=lambda r: stable_key(r["fsd_id"]))
    return rows, rej


def pick_listen_sample(rows: list[dict], size: int = LISTEN_SAMPLE_SIZE) -> list[dict]:
    """범주 층화 무작위(=sha256 결정적) 표본. 범주 비율에 비례해 최대잔여법으로 배분."""
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_cat[row["category"]].append(row)
    total = len(rows)
    if total <= size:
        return sorted(rows, key=lambda r: stable_key(r["fsd_id"]))
    exact = {cat: len(items) * size / total for cat, items in by_cat.items()}
    alloc = {cat: int(value) for cat, value in exact.items()}
    for cat in sorted(exact, key=lambda c: (-(exact[c] - alloc[c]), c)):
        if sum(alloc.values()) >= size:
            break
        alloc[cat] += 1
    picked: list[dict] = []
    for cat in sorted(by_cat):
        ordered = sorted(by_cat[cat], key=lambda r: stable_key(r["fsd_id"]))
        picked.extend(ordered[: alloc[cat]])
    return sorted(picked, key=lambda r: stable_key(r["fsd_id"]))


# ── 산출 ─────────────────────────────────────────────────────────────────────

def _write_csv(path: Path, fields: tuple[str, ...], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows: list[dict], rej: Rejections, total_clips: int) -> str:
    cat = Counter(r["category"] for r in rows)
    grade = Counter(r["rating"] for r in rows)
    lab = Counter(r["selected_label"] for r in rows)
    split = Counter(r["split"] for r in rows)
    out = [
        "# other 네거티브 후보 집계",
        "",
        f"- dev 전체: {total_clips} 클립",
        f"- 후보: {len(rows)} 클립",
        f"- 제외 ① target 계열: {len(rej.target)}",
        f"- 제외 ② 양성 원본 중복: {len(rej.positive)}",
        f"- 제외 ③ 길이 미달(< {MIN_DURATION_SEC}s): {len(rej.too_short)}",
        f"- 제외 ③ 오디오 사용 불가(0바이트·헤더 손상): {len(rej.unusable)}",
        f"- 보류: {sum(len(v) for v in rej.hold.values())}",
        "",
        "## 범주별",
        "",
        "| 범주 | 건수 | 비율 |",
        "| --- | ---: | ---: |",
    ]
    for code in ("d", "a", "b", "c"):
        n = cat.get(code, 0)
        out.append(f"| {CATEGORY_LABEL[code]} | {n} | {n / max(len(rows), 1):.1%} |")
    out += ["", "## PP / PNP 비율", "", "| 등급 | 건수 | 비율 |", "| --- | ---: | ---: |"]
    for g in ("PP", "PNP", "NP", "U", "NA"):
        n = grade.get(g, 0)
        if n:
            out.append(f"| {g} | {n} | {n / max(len(rows), 1):.1%} |")
    out += ["", "## split(dev 내부 train/val 보존)", ""]
    out += [f"- {k}: {v}" for k, v in sorted(split.items())]
    out += ["", "## 보류 사유별", ""]
    out += [f"- {k}: {len(v)}" for k, v in sorted(rej.hold.items())]
    out += ["", "## 선택 라벨별 후보 수", "", "| 라벨 | 범주 | 건수 |", "| --- | --- | ---: |"]
    for label, n in sorted(lab.items(), key=lambda kv: (-kv[1], kv[0])):
        out.append(f"| {label} | {ASSIGNMENT[label]} | {n} |")
    out += ["", "## FSD50K 어휘에 없는 지정 hard negative(대체 라벨로 흡수)", ""]
    out += [f"- {k} → {', '.join(v)}" for k, v in MISSING_HARD_NEGATIVES.items()]
    return "\n".join(out) + "\n"


def run(args: argparse.Namespace) -> int:
    load_vocabulary(args.vocabulary_csv)   # 배정표가 어휘 200건을 전건 덮는지 검증
    clips = load_clips(args.dev_csv)
    positives = load_positive_source_ids(args.positive_clips)
    ratings = json.loads(args.pp_pnp.read_text(encoding="utf-8"))
    rows, rej = select(clips, positives, ratings, args.audio_root,
                       target_size=args.target_size)

    if args.clips_info is not None:
        info = json.loads(args.clips_info.read_text(encoding="utf-8"))
        for row in rows:
            row["license"] = info.get(row["fsd_id"], {}).get("license", "")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(args.out_dir / "candidates.csv", CANDIDATE_FIELDS, rows)
    _write_csv(args.out_dir / "listen_sample.csv", CANDIDATE_FIELDS,
               pick_listen_sample(rows))
    (args.out_dir / "summary.md").write_text(
        summarize(rows, rej, len(clips)), encoding="utf-8")

    print(f"후보 {len(rows)} 클립 → {args.out_dir}")
    print(f"  제외 ① target {len(rej.target)} / ② 양성중복 {len(rej.positive)} "
          f"/ ③ 길이미달 {len(rej.too_short)} · 사용불가 {len(rej.unusable)} "
          f"/ 보류 {sum(len(v) for v in rej.hold.values())}")
    if args.target_size >= TARGET_SIZE and len(rows) < MIN_CANDIDATES:
        print(f"🔴 후보가 {MIN_CANDIDATES} 미만이다 — 위임 §9 정지 트리거.", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="FSD50K dev 덤프 → other 네거티브 후보 목록(읽기 전용)")
    for flag, help_text in (
        ("--dev-csv", "FSD50K.ground_truth/dev.csv"),
        ("--vocabulary-csv", "FSD50K.ground_truth/vocabulary.csv"),
        ("--pp-pnp", "FSD50K.metadata/pp_pnp_ratings_FSD50K.json"),
        ("--audio-root", "dev wav 가 있는 디렉터리"),
        ("--positive-clips", "01_clips (양성으로 이미 쓴 원본 대조용)"),
        ("--out-dir", "산출 디렉터리 — repo 밖"),
    ):
        parser.add_argument(flag, required=True, type=_path, help=help_text)
    parser.add_argument("--clips-info", type=_path,
                        help="FSD50K.metadata/dev_clips_info_FSD50K.json (license 열)")
    parser.add_argument("--target-size", type=int, default=TARGET_SIZE,
                        help=f"후보 목표 규모 (기본 {TARGET_SIZE})")
    return run(parser.parse_args(argv))


def _path(value: str) -> Path:
    return Path(value).expanduser()


if __name__ == "__main__":
    raise SystemExit(main())
