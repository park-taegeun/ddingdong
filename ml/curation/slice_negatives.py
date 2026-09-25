"""`other` 네거티브 후보(candidates.csv)를 학습 입력 규격 3초 조각으로 자른다 — 네거티브 모드.

  python -m ml.curation.slice_negatives \
      --candidates "~/ddingdong-측정결과/2026-09-21/negatives/candidates.csv" \
      --audio-root "~/ML 학습 데이터/ddingdong_dataset/00_source_raw/fsd50k/dev_audio/FSD50K.dev_audio" \
      --out-dir    "~/ddingdong-측정결과/<날짜>/negative_clips" \
      --max-clips-per-source <N> [--dry-run]

규칙 = pretest `fsd50k_preprocess` 규칙 계승(33.7(i) · 33.10(b)) — 코드는 이식하지 않았다.
  - 3초 미만 → 16kHz 리샘플 후 `apad` zero-pad 1클립(`_0000000`)
  - 3초 이상 → 비중첩 3초 분할, 잔여 버림
  - 출력명 `{fsd_id}_{start_ms:07d}.wav`, 같은 이름이 있으면 skip(멱등)
🔴 변환기는 ffmpeg, 인자는 pretest 와 같다. 같은 FSD50K 에서 pretest 로 만든 doorbell · knock
조각과 리샘플러 · pad 방식이 다르면 그 차이가 「other 냐 아니냐」의 가짜 단서가 된다.
피크 정규화는 하지 않는다(preprocess 몫).

모든 경로와 상한은 필수 인자다(기본값 없음). 산출은 repo 밖 `--out-dir` 에만 쓴다.
"""

from __future__ import annotations

import argparse
import csv
import os
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

from ..pipeline.config import MIN_DURATION_SEC, SAMPLE_RATE, source_key
from .select_negatives import CANDIDATE_FIELDS

CLASS_DIR = "other"   # 🔴 config.CLASSES 에는 아직 넣지 않는다(33.13(d) 머지 순서)
CLIP_SEC = 3.0
CLIP_SAMPLES = int(CLIP_SEC * SAMPLE_RATE)  # 48000
REPO_ROOT = Path(__file__).resolve().parents[2]
# 데이터셋 스테이지 폴더 — out-dir 이 이 중 하나의 안이면 거부(01_clips 투입은 수동 단계).
DATASET_DIRS = ("00_source_raw", "01_extracted", "01_clips", "02_preprocessed",
                "03_augmented", "04_direct_recording", "05_final_dataset", "manifests")
MANIFEST_FIELDS = ("source_path", "group", "duration_sec", "out_rel_path", "start_ms",
                   "padded", "status", "reason", "ffmpeg_version")
# 인자는 pretest fsd50k_preprocess 와 동일(-ss · -t 는 -i 앞 = 입력 옵션).
FFMPEG = ("ffmpeg", "-y", "-loglevel", "error")
OUT_FMT = ("-ar", str(SAMPLE_RATE), "-ac", "1", "-sample_fmt", "s16")


def pick_indices(n: int, cap: int) -> list[int]:
    """조각 0..n-1 중 cap 개를 균등 간격으로. round(i·(n−1)/(cap−1)), cap=1 이면 0번."""
    if n <= cap:
        return list(range(n))
    if cap == 1:
        return [0]
    return [round(i * (n - 1) / (cap - 1)) for i in range(cap)]


def plan(duration: float, cap: int) -> tuple[list[int], list[int]]:
    """→ (쓸 start_ms, 상한으로 버린 start_ms). 3초 미만은 pad 1클립, 잔여는 버린다."""
    n = 1 if duration < CLIP_SEC else int(duration // CLIP_SEC)
    keep = set(pick_indices(n, cap))
    starts = [int(i * CLIP_SEC * 1000) for i in range(n)]
    return ([s for i, s in enumerate(starts) if i in keep],
            [s for i, s in enumerate(starts) if i not in keep])


def check_out_dir(raw: Path) -> Path:
    out = raw.expanduser().resolve()
    if out == REPO_ROOT or out.is_relative_to(REPO_ROOT):
        raise SystemExit(f"--out-dir 가 repo 안이다({out}) — 오디오 커밋 방지를 위해 거부.")
    hit = [p for p in out.parts if p in DATASET_DIRS]
    if hit:
        raise SystemExit(f"--out-dir 가 데이터셋 폴더({hit[0]}) 안이다({out}) — 거부. "
                         "01_clips 투입은 재학습 당일 수동 단계다.")
    return out


def ffmpeg_version() -> str:
    try:
        r = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
    except FileNotFoundError:
        raise SystemExit("ffmpeg 가 없다 — 시스템에 설치한 뒤 다시 실행한다.")
    return r.stdout.splitlines()[0] if r.returncode == 0 and r.stdout else "unknown"


def probe_duration(path: Path) -> float | None:
    """ffprobe format=duration(pretest get_duration 과 같은 질의). 실패하면 None."""
    r = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip()) if r.returncode == 0 else None
    except ValueError:
        return None


def _ffmpeg(args: list[str]) -> str | None:
    """ffmpeg 실행 → 실패면 stderr 요약, 성공이면 None."""
    r = subprocess.run([*FFMPEG, *args], capture_output=True, text=True)
    return None if r.returncode == 0 else (r.stderr.strip().splitlines() or ["?"])[-1]


def write_clip(src: Path, start_ms: int, padded: bool, dst: Path) -> str | None:
    """임시 폴더에 만든 뒤 옮긴다 — 실패한 반쪽 파일이 다음 실행에서 skip 되지 않게."""
    with tempfile.TemporaryDirectory(dir=dst.parent) as tmp:
        part = Path(tmp) / dst.name
        if padded:   # pretest resample_and_pad: 리샘플 → apad 로 정확히 3초
            mid = Path(tmp) / "resampled.wav"
            err = (_ffmpeg(["-i", str(src), *OUT_FMT, str(mid)])
                   or _ffmpeg(["-i", str(mid), "-af", f"apad=whole_len={CLIP_SAMPLES}",
                               "-t", f"{CLIP_SEC:.3f}", *OUT_FMT, str(part)]))
        else:        # pretest split_to_clip
            err = _ffmpeg(["-ss", f"{start_ms / 1000:.3f}", "-t", f"{CLIP_SEC:.3f}",
                           "-i", str(src), *OUT_FMT, str(part)])
        if err is None:
            os.replace(part, dst)
        return err


def read_candidates(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if tuple(reader.fieldnames or ()) != CANDIDATE_FIELDS:
            raise SystemExit(f"candidates 열이 다르다: {reader.fieldnames} ≠ {CANDIDATE_FIELDS}")
        return list(reader)


def slice_all(candidates: list[dict], audio_root: Path, out_dir: Path, cap: int,
              dry_run: bool, version: str) -> list[dict]:
    """원본마다 판정·조각내기. dry_run 이면 디스크에 아무것도 쓰지 않는다."""
    class_dir = out_dir / CLASS_DIR
    if not dry_run:
        class_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for cand in candidates:
        fsd_id = cand["fsd_id"]
        src = audio_root / f"{fsd_id}.wav"
        base = {"source_path": str(src), "group": fsd_id, "duration_sec": "",
                "out_rel_path": "", "start_ms": "", "padded": "", "reason": "",
                "ffmpeg_version": version}

        def reject(status: str, reason: str) -> None:
            rows.append({**base, "status": status, "reason": reason})

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
                         "status": "dropped_cap", "reason": f"원본당 상한 {cap} 초과"})
        for start_ms in starts:
            name = f"{fsd_id}_{start_ms:07d}.wav"
            assert source_key(Path(name).stem) == fsd_id, name   # 그룹 키 불변식
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


def summarize(rows: list[dict], n_sources: int, cap: int, dry_run: bool, version: str) -> str:
    status = Counter(r["status"] for r in rows)
    clips = [r for r in rows if r["out_rel_path"]]
    per_source = Counter(Counter(r["group"] for r in clips).values())
    out = [
        "# other 네거티브 조각내기 요약" + (" (dry-run — wav 0개)" if dry_run else ""),
        "",
        f"- ffmpeg: {version}",
        f"- 원본 {n_sources} · 원본당 상한 {cap}",
        f"- 조각 {len(clips)} (pad {sum(1 for r in clips if r['padded'] == 1)}) · "
        f"상한으로 버림 {status['dropped_cap']}",
        "",
        "## 상태별",
        "",
    ]
    out += [f"- {k}: {v}" for k, v in sorted(status.items())]
    out += ["", "## 원본당 조각 수", ""]
    out += [f"- {k}조각: 원본 {v}" for k, v in sorted(per_source.items())]
    rejected = [r for r in rows if r["status"].startswith("rejected_")]
    if rejected:
        out += ["", "## 거부 목록", ""]
        out += [f"- {r['group']} {r['status']}: {r['reason']}" for r in rejected]
    return "\n".join(out) + "\n"


def run(args: argparse.Namespace) -> int:
    out_dir = check_out_dir(args.out_dir)
    if args.max_clips_per_source < 1:
        raise SystemExit("--max-clips-per-source 는 1 이상이어야 한다.")
    if not args.audio_root.is_dir():
        raise SystemExit(f"--audio-root 가 폴더가 아니다: {args.audio_root}")
    version = ffmpeg_version()
    candidates = read_candidates(args.candidates)
    rows = slice_all(candidates, args.audio_root, out_dir, args.max_clips_per_source,
                     args.dry_run, version)
    text = summarize(rows, len(candidates), args.max_clips_per_source, args.dry_run, version)
    if not args.dry_run:
        with (out_dir / "slice_manifest.csv").open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=MANIFEST_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        (out_dir / "slice_summary.md").write_text(text, encoding="utf-8")
    print(text, end="")
    return 1 if any(r["status"] == "rejected_ffmpeg" for r in rows) else 0


def _path(value: str) -> Path:
    return Path(value).expanduser()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="other 네거티브 후보 → 3초 · 16kHz · mono · PCM16 조각(네거티브 모드)")
    parser.add_argument("--candidates", required=True, type=_path,
                        help="select_negatives 산출 candidates.csv")
    parser.add_argument("--audio-root", required=True, type=_path,
                        help="FSD50K dev wav 폴더({fsd_id}.wav)")
    parser.add_argument("--out-dir", required=True, type=_path,
                        help="산출 폴더 — repo · 데이터셋 폴더 밖")
    parser.add_argument("--max-clips-per-source", required=True, type=int,
                        help="원본당 조각 상한(기본값 없음 — 33.7(i) 값 미정)")
    parser.add_argument("--dry-run", action="store_true",
                        help="wav 를 만들지 않고 예상 조각 수만 요약")
    return run(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
