"""Zeroth-Korean 한국어 말소리 → `other` 네거티브 — 선별(select) + 3초 조각내기(slice).

  python -m ml.curation.zeroth_negatives select \
      --audio-info  "~/ML 학습 데이터/zeroth_korean/AUDIO_INFO" \
      --corpus-root "~/ML 학습 데이터/zeroth_korean" \
      --out-dir     "~/ddingdong-측정결과/<날짜>/zeroth" \
      --per-speaker <N>

  python -m ml.curation.zeroth_negatives slice \
      --candidates  "~/ddingdong-측정결과/<날짜>/zeroth/zeroth_candidates.csv" \
      --corpus-root "~/ML 학습 데이터/zeroth_korean" \
      --out-dir     "~/ddingdong-측정결과/<날짜>/negative_clips" \
      --max-clips-per-utterance <N> [--dry-run]

출처 = Zeroth-Korean(OpenSLR SLR40, CC BY 4.0) — 사용자 결정 2026-09-25(33.14(f)).
🔴 AUDIO_INFO 의 NAME 칸은 실명이다 — 읽지도 출력하지도 않는다. 화자는 SPEAKERID 로만 다룬다.
선별 = 화자별 sha256 결정적 순서 앞 N 발화(Zeroth 자체 train/test 구분은 열로만 기록).
조각 = slice_negatives 네거티브 모드 규칙 · ffmpeg 인자 그대로(함수 import 재사용).
그룹 키 = `zeroth_{화자}` (config.source_key 의 zeroth_ 분기) — 같은 화자는 같은 split.
모든 경로와 N · 상한은 필수 인자다(기본값 없음). 산출은 repo 밖 `--out-dir` 에만 쓴다.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from ..pipeline.config import MIN_DURATION_SEC, ZEROTH_PREFIX, source_key
from .slice_negatives import (CLASS_DIR, CLIP_SEC, MANIFEST_FIELDS, check_out_dir,
                              ffmpeg_version, plan, probe_duration, write_clip)

SALT = "ddingdong-zeroth-negatives-v1"  # sha256 salt. 내장 hash() 는 프로세스마다 달라져 쓰지 않는다.
# AUDIO_INFO 에서 읽는 칸 — NAME 은 일부러 없다.
INFO_COLUMNS = ("SPEAKERID", "SEX", "SCRIPTID", "DATASET")
CANDIDATE_FIELDS = ("speaker_id", "sex", "script_id", "utt_id", "rel_path", "zeroth_set",
                    "duration_sec", "text")
UTT_PATTERN = re.compile(r"^(\d+)_(\d+)_(\d+)$")   # {화자}_{대본}_{발화}
CANDIDATES_NAME = "zeroth_candidates.csv"
SELECT_SUMMARY_NAME = "zeroth_select_summary.md"
MANIFEST_NAME = "zeroth_slice_manifest.csv"
SLICE_SUMMARY_NAME = "zeroth_slice_summary.md"


def order_key(utt_id: str) -> str:
    return hashlib.sha256(f"{SALT}|{utt_id}".encode("utf-8")).hexdigest()


def read_audio_info(path: Path) -> dict[str, dict[str, str]]:
    """SPEAKERID → {sex, script_id, zeroth_set}. NAME 칸은 인덱스조차 잡지 않는다."""
    lines = path.read_text(encoding="utf-8").splitlines()
    header = lines[0].split("|")
    missing = [c for c in INFO_COLUMNS if c not in header]
    if missing:
        raise SystemExit(f"AUDIO_INFO 헤더에 {missing} 칸이 없다.")
    idx = [header.index(c) for c in INFO_COLUMNS]
    info: dict[str, dict[str, str]] = {}
    for ln in lines[1:]:
        if not ln.strip():
            continue
        spk, sex, script, dataset = (ln.split("|")[i] for i in idx)
        info[spk] = {"sex": sex, "script_id": script, "zeroth_set": dataset}
    return info


def scan_corpus(root: Path, info: dict) -> tuple[dict[str, list[dict]], list[tuple[str, str]]]:
    """{set}/{대본}/{화자}/{화자}_{대본}_{발화}.flac → (화자별 발화, 거부 [(rel_path, 사유)])."""
    by_spk: dict[str, list[dict]] = defaultdict(list)
    rejected: list[tuple[str, str]] = []
    texts: dict[Path, dict[str, str]] = {}
    for flac in sorted(root.glob("*/*/*/*.flac")):
        rel = flac.relative_to(root)
        zset, script_dir, spk_dir = rel.parts[:3]
        m = UTT_PATTERN.match(flac.stem)
        if not m:
            rejected.append((str(rel), "파일명이 {화자}_{대본}_{발화} 가 아님"))
            continue
        spk, script, _ = m.groups()
        if (spk, script) != (spk_dir, script_dir):
            rejected.append((str(rel), "파일명의 화자·대본이 폴더와 다름"))
            continue
        if spk not in info:
            rejected.append((str(rel), "AUDIO_INFO 에 없는 화자"))
            continue
        if flac.parent not in texts:
            texts[flac.parent] = {}
            for t in flac.parent.glob("*.trans.txt"):
                for ln in t.read_text(encoding="utf-8").splitlines():
                    uid, _, sentence = ln.partition(" ")
                    texts[flac.parent][uid] = sentence.strip()
        by_spk[spk].append({
            "speaker_id": spk, "sex": info[spk]["sex"], "script_id": script,
            "utt_id": flac.stem, "rel_path": rel.as_posix(), "zeroth_set": zset,
            "duration_sec": "", "text": texts[flac.parent].get(flac.stem, ""),
        })
    return by_spk, rejected


def select(by_spk: dict[str, list[dict]], n: int) -> list[dict]:
    """화자마다 sha256 순서 앞 n 발화. 결정적 — 같은 입력이면 같은 목록."""
    out: list[dict] = []
    for spk in sorted(by_spk, key=int):
        out += sorted(by_spk[spk], key=lambda r: order_key(r["utt_id"]))[:n]
    return out


def select_summary(info: dict, by_spk: dict, rows: list[dict], rejected: list, n: int) -> str:
    short = {s: len(v) for s, v in by_spk.items() if len(v) < n}
    no_flac = sorted(set(info) - set(by_spk), key=int)
    durs = [float(r["duration_sec"]) for r in rows if r["duration_sec"]]
    sexes = Counter(r["sex"] for r in rows)
    out = [
        "# Zeroth-Korean 네거티브 선별 요약",
        "",
        "- 출처: Zeroth-Korean (OpenSLR SLR40, CC BY 4.0)",
        f"- AUDIO_INFO 화자 {len(info)} · 발화 있는 화자 {len(by_spk)} · 화자당 N {n}",
        f"- 후보 {len(rows)} 발화 (" + " · ".join(f"{k} {v}" for k, v in sorted(sexes.items())) + ")",
        f"- 길이 못 읽음 {sum(1 for r in rows if not r['duration_sec'])}",
    ]
    if durs:
        out.append(f"- 길이(초) 평균 {statistics.mean(durs):.2f} · 중앙값 "
                   f"{statistics.median(durs):.2f} · 최소 {min(durs):.2f} · 최대 {max(durs):.2f}")
    if short:
        out += ["", "## 발화가 N 미만인 화자(있는 만큼만 선별)", ""]
        out += [f"- {s}: {c}" for s, c in sorted(short.items(), key=lambda x: int(x[0]))]
    if no_flac:
        out += ["", "## AUDIO_INFO 에만 있고 발화가 없는 화자", "", f"- {', '.join(no_flac)}"]
    if rejected:
        out += ["", "## 거부 목록", ""]
        out += [f"- {p}: {why}" for p, why in rejected]
    return "\n".join(out) + "\n"


def run_select(args: argparse.Namespace) -> int:
    out_dir = check_out_dir(args.out_dir)
    if args.per_speaker < 1:
        raise SystemExit("--per-speaker 는 1 이상이어야 한다.")
    if not args.corpus_root.is_dir():
        raise SystemExit(f"--corpus-root 가 폴더가 아니다: {args.corpus_root}")
    info = read_audio_info(args.audio_info)
    by_spk, rejected = scan_corpus(args.corpus_root, info)
    rows = select(by_spk, args.per_speaker)
    for r in rows:   # 길이는 뽑힌 발화만 잰다(22,720 전수 ffprobe 회피)
        d = probe_duration(args.corpus_root / r["rel_path"])
        r["duration_sec"] = "" if d is None else f"{d:.3f}"
    text = select_summary(info, by_spk, rows, rejected, args.per_speaker)
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / CANDIDATES_NAME).open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CANDIDATE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    (out_dir / SELECT_SUMMARY_NAME).write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


def read_candidates(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if tuple(reader.fieldnames or ()) != CANDIDATE_FIELDS:
            raise SystemExit(f"candidates 열이 다르다: {reader.fieldnames} ≠ {CANDIDATE_FIELDS}")
        return list(reader)


def slice_all(candidates: list[dict], root: Path, out_dir: Path, cap: int,
              dry_run: bool, version: str) -> list[dict]:
    """발화마다 판정·조각내기(slice_negatives.slice_all 과 같은 상태 · 사유 체계)."""
    class_dir = out_dir / CLASS_DIR
    if not dry_run:
        class_dir.mkdir(parents=True, exist_ok=True)
    root = root.resolve()
    rows: list[dict] = []
    for cand in candidates:
        utt, spk = cand["utt_id"], cand["speaker_id"]
        src = (root / cand["rel_path"]).resolve()
        group = f"{ZEROTH_PREFIX}{spk}"
        base = {"source_path": str(src), "group": group, "duration_sec": "",
                "out_rel_path": "", "start_ms": "", "padded": "", "reason": "",
                "ffmpeg_version": version}

        def reject(status: str, reason: str) -> None:
            rows.append({**base, "status": status, "reason": f"{utt}: {reason}"})

        m = UTT_PATTERN.match(utt)
        if not m or m.group(1) != spk:
            reject("rejected_id", "utt_id 가 {speaker_id}_{대본}_{발화} 형식이 아님")
            continue
        if not src.is_relative_to(root):
            reject("rejected_path", "rel_path 가 corpus-root 밖을 가리킴")
            continue
        if not src.is_file():
            reject("rejected_missing", "원본 없음")
            continue
        if src.stat().st_size == 0:
            reject("rejected_empty", "0바이트")
            continue
        duration = probe_duration(src)
        if duration is None:
            reject("rejected_decode", "ffprobe 가 길이를 읽지 못함")
            continue
        base["duration_sec"] = f"{duration:.3f}"
        if duration < MIN_DURATION_SEC:
            reject("rejected_too_short", f"{duration:.3f}s < MIN_DURATION_SEC {MIN_DURATION_SEC}")
            continue

        padded = duration < CLIP_SEC
        starts, dropped = plan(duration, cap)
        for start_ms in dropped:
            rows.append({**base, "start_ms": start_ms, "padded": int(padded),
                         "status": "dropped_cap", "reason": f"{utt}: 발화당 상한 {cap} 초과"})
        for start_ms in starts:
            name = f"{ZEROTH_PREFIX}{utt}_{start_ms:07d}.wav"
            assert source_key(Path(name).stem) == group, name   # 그룹 키 불변식(화자 단위)
            row = {**base, "out_rel_path": f"{CLASS_DIR}/{name}", "start_ms": start_ms,
                   "padded": int(padded)}
            dst = class_dir / name
            if dry_run:
                row["status"] = "planned"
            elif dst.exists():
                row.update(status="skipped_exists", reason="같은 이름이 이미 있음(덮어쓰지 않음)")
            else:
                err = write_clip(src, start_ms, padded, dst)
                row.update(status="written" if err is None else "rejected_ffmpeg",
                           reason=err or "")
            rows.append(row)
    return rows


def slice_summary(rows: list[dict], n_utts: int, cap: int, dry_run: bool, version: str) -> str:
    status = Counter(r["status"] for r in rows)
    clips = [r for r in rows if r["out_rel_path"]]
    per_spk = Counter(r["group"] for r in clips)
    out = [
        "# Zeroth-Korean 네거티브 조각내기 요약" + (" (dry-run — wav 0개)" if dry_run else ""),
        "",
        "- 출처: Zeroth-Korean (OpenSLR SLR40, CC BY 4.0)",
        f"- ffmpeg: {version}",
        f"- 발화 {n_utts} · 발화당 상한 {cap} · 화자(그룹) {len(per_spk)}",
        f"- 조각 {len(clips)} (pad {sum(1 for r in clips if r['padded'] == 1)}) · "
        f"상한으로 버림 {status['dropped_cap']}",
        "",
        "## 상태별",
        "",
    ]
    out += [f"- {k}: {v}" for k, v in sorted(status.items())]
    out += ["", "## 화자당 조각 수", ""]
    out += [f"- {k}조각: 화자 {v}" for k, v in sorted(Counter(per_spk.values()).items())]
    rejected = [r for r in rows if r["status"].startswith("rejected_")]
    if rejected:
        out += ["", "## 거부 목록", ""]
        out += [f"- {r['group']} {r['status']}: {r['reason']}" for r in rejected]
    return "\n".join(out) + "\n"


def run_slice(args: argparse.Namespace) -> int:
    out_dir = check_out_dir(args.out_dir)
    if args.max_clips_per_utterance < 1:
        raise SystemExit("--max-clips-per-utterance 는 1 이상이어야 한다.")
    if not args.corpus_root.is_dir():
        raise SystemExit(f"--corpus-root 가 폴더가 아니다: {args.corpus_root}")
    version = ffmpeg_version()
    candidates = read_candidates(args.candidates)
    cap = args.max_clips_per_utterance
    rows = slice_all(candidates, args.corpus_root, out_dir, cap, args.dry_run, version)
    text = slice_summary(rows, len(candidates), cap, args.dry_run, version)
    if not args.dry_run:
        with (out_dir / MANIFEST_NAME).open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=MANIFEST_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        (out_dir / SLICE_SUMMARY_NAME).write_text(text, encoding="utf-8")
    print(text, end="")
    return 1 if any(r["status"] == "rejected_ffmpeg" for r in rows) else 0


def _path(value: str) -> Path:
    return Path(value).expanduser()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Zeroth-Korean 한국어 말소리 → other 네거티브 (선별 · 3초 조각내기)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sel = sub.add_parser("select", help="AUDIO_INFO + 코퍼스 → 화자당 N 발화 후보 CSV")
    sel.add_argument("--audio-info", required=True, type=_path, help="Zeroth AUDIO_INFO 파일")
    sel.add_argument("--corpus-root", required=True, type=_path,
                     help="train_data_01 · test_data_01 이 있는 폴더")
    sel.add_argument("--out-dir", required=True, type=_path, help="산출 폴더 — repo · 데이터셋 폴더 밖")
    sel.add_argument("--per-speaker", required=True, type=int,
                     help="화자당 발화 수 N(기본값 없음 — 값 미정)")
    sl = sub.add_parser("slice", help="후보 CSV → 3초 · 16kHz · mono · PCM16 조각")
    sl.add_argument("--candidates", required=True, type=_path, help=f"select 산출 {CANDIDATES_NAME}")
    sl.add_argument("--corpus-root", required=True, type=_path,
                    help="후보 CSV rel_path 의 기준 폴더")
    sl.add_argument("--out-dir", required=True, type=_path, help="산출 폴더 — repo · 데이터셋 폴더 밖")
    sl.add_argument("--max-clips-per-utterance", required=True, type=int,
                    help="발화당 조각 상한(기본값 없음 — 값 미정)")
    sl.add_argument("--dry-run", action="store_true", help="wav 를 만들지 않고 예상 조각 수만 요약")
    args = parser.parse_args(argv)
    return run_select(args) if args.cmd == "select" else run_slice(args)


if __name__ == "__main__":
    raise SystemExit(main())
