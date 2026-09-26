"""녹음 전용 수신기(server/tools/record_receiver.py) post/ WAV → 소리 시작점 기준 3초 조각 — 직접녹음 모드.

  python -m ml.curation.slice_direct \
      --recording-dir "~/ddingdong-측정결과/<날짜>/direct_rec" \
      --out-dir       "~/ddingdong-측정결과/<날짜>/direct_clips" \
      --baseline-ms <ms> --onset-ratio <배수> --onset-floor <|x|> [--dry-run]

규칙(33.7(i) 「소리 시작점 기준 3초」 · 5.3(d) 설계 입력 — 창 당기기 · 미검출 사유 기록)
  - 입력 = `--recording-dir/post/direct_{label}_{unit}_{take}.wav` 만. pre/ 는 읽지 않는다.
  - onset = 분석 스크립트 take_check.py 정의 그대로, 차이는 하나 — |x| ≥ 32767(클램프) 샘플을
    기준 계산과 탐색에서 건너뛴다(6.3(q) 고립 1샘플 글리치가 onset 이 되지 않게).
      기준 = 첫 baseline_ms 구간 |x| 의 median_high(= take_check `sorted(a[:n])[n // 2]`, 0 이면 1)
      onset = 0번부터 처음으로 |x| > ratio × 기준 이고 |x| > floor 인 샘플
  - 창 = onset 을 ms 로 내림한 지점부터 정확히 48000 샘플. 파일 끝을 넘으면 끝에 맞춰 앞으로 당긴다.
    리샘플 · 정규화 · pad 0 — 원본 샘플 그대로.
  - 미검출 · 규격 밖은 조각 0 + 사유를 manifest 에 남긴다. onset 을 다른 값으로 대체하지 않는다.
  - 멱등 = 테이크 단위: 같은 입력 stem 의 기존 조각이 같은 PCM 이면 skip, 다르면 conflict(무접촉).
    대소문자만 다른 stem 도 conflict(macOS 기본 FS 에서는 같은 파일이다). ⇒ 한 테이크 = 조각 ≤ 1.
  - 출력 `{out-dir}/{label}/{stem}_{start_ms:07d}.wav` — source_key = `direct_{label}_{unit}`(D3).

값 3개와 경로는 필수 인자다(기본값 없음 — 재학습 당일 결정). 산출은 repo · 데이터셋 폴더 ·
recording-dir 밖에만 쓴다. 01_clips 투입은 재학습 당일 수동 단계다.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import statistics
import tempfile
import wave
from array import array
from collections import Counter
from pathlib import Path

from ..pipeline.config import SAMPLE_RATE, source_key
from .slice_negatives import CLIP_SAMPLES, CLIP_SEC, check_out_dir

LABELS = ("doorbell", "knock")   # 5.3(b) 화재경보 학습용 녹음 보류 — fire_alarm 은 거부
CLAMP = 32767                    # |x| ≥ CLAMP = 클램프(take_check 정의, −32767 포함)
MS = SAMPLE_RATE // 1000         # 1ms 샘플 수
# label 에 밑줄이 있어도(fire_alarm) 이름 규칙은 통과시키고 label 판정에서 거부한다.
NAME_RE = re.compile(r"^direct_([a-z][a-z_]*)_([A-Za-z0-9]+)_(\d+)$")
OUT_RE = re.compile(r"^(.+)_\d{7}\.wav$")
MANIFEST = "direct_slice_manifest.csv"
SUMMARY = "direct_slice_summary.md"
MANIFEST_FIELDS = ("recording_dir", "source_path", "label", "unit", "take", "n_samples",
                   "onset_ms", "start_ms", "shifted", "clip_clamp_count", "out_rel_path",
                   "status", "reason", "baseline_ms", "onset_ratio", "onset_floor")


def find_onset(a: list[int], base_n: int, ratio: float, floor: float) -> tuple[int | None, str]:
    """a = |x| 목록 → (onset 샘플 | None, 미검출 사유)."""
    base = [v for v in a[:base_n] if v < CLAMP]
    if not base:
        return None, f"기준 구간 {base_n}샘플이 전부 클램프"
    thr = max(ratio * (statistics.median_high(base) or 1), floor)
    onset = next((i for i, v in enumerate(a) if v < CLAMP and v > thr), None)
    if onset is None:
        peak = max((v for v in a if v < CLAMP), default=0)
        return None, f"임계 {thr:g} 초과 샘플 없음(비클램프 최대 |x| {peak})"
    return onset, ""


def window(onset: int, n: int) -> tuple[int, bool]:
    """→ (start_ms, shifted). 시작 + 3초가 파일 끝을 넘으면 끝에 맞춰 당긴다."""
    start_ms = onset // MS
    if start_ms * MS + CLIP_SAMPLES > n:
        return (n - CLIP_SAMPLES) // MS, True
    return start_ms, False


def read_pcm(path: Path) -> bytes | None:
    """기존 조각의 PCM(1ch · 2byte · 16kHz 가 아니면 None)."""
    try:
        with wave.open(str(path), "rb") as wf:
            if (wf.getnchannels(), wf.getsampwidth(), wf.getframerate()) != (1, 2, SAMPLE_RATE):
                return None
            return wf.readframes(wf.getnframes())
    except (wave.Error, EOFError, OSError):
        return None


def write_clip(dst: Path, pcm: bytes) -> None:
    """임시 파일에 쓴 뒤 옮긴다(slice_negatives 와 같은 방식). wave 가 파일 = little-endian 을 맞춘다."""
    with tempfile.TemporaryDirectory(dir=dst.parent) as tmp:
        part = Path(tmp) / dst.name
        with wave.open(str(part), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(pcm)
        os.replace(part, dst)


def judge(src: Path, params: dict) -> tuple[dict, bytes | None]:
    """입력 1개 판정 → (manifest 행, 조각 PCM | None). 디스크 쓰기 없음."""
    row = {f: "" for f in MANIFEST_FIELDS} | {"source_path": str(src)}

    def reject(status: str, reason: str) -> tuple[dict, None]:
        return row | {"status": status, "reason": reason}, None

    m = NAME_RE.match(src.stem) if src.suffix == ".wav" else None
    if not m:
        return reject("rejected_name", "direct_{label}_{unit}_{take}.wav 형식이 아님")
    label, unit, take = m.groups()
    row.update(label=label, unit=unit, take=take)
    if label not in LABELS:
        return reject("rejected_label", f"label {label} ∉ {LABELS}")
    try:
        with wave.open(str(src), "rb") as wf:
            fmt = (wf.getnchannels(), wf.getsampwidth(), wf.getframerate())
            frames = wf.readframes(wf.getnframes())
    except (wave.Error, EOFError) as exc:
        return reject("rejected_decode", f"wave 로 읽지 못함: {exc}")
    if fmt != (1, 2, SAMPLE_RATE):
        return reject("rejected_format", f"(채널, 바이트, Hz) = {fmt} ≠ (1, 2, {SAMPLE_RATE})")
    samples = array("h", frames)   # wave.readframes = native 순서
    n = len(samples)
    a = [abs(v) for v in samples]  # 파이썬 int — −32768 도 32768 로 넘치지 않는다
    row.update(n_samples=n, clip_clamp_count=sum(v >= CLAMP for v in a))
    if n < CLIP_SAMPLES:
        return reject("rejected_too_short", f"{n}샘플 < {CLIP_SAMPLES}(pad 하지 않음)")
    onset, why = find_onset(a, params["baseline_ms"] * MS, params["onset_ratio"],
                            params["onset_floor"])
    if onset is None:
        return reject("rejected_no_onset", why)
    start_ms, shifted = window(onset, n)
    start = start_ms * MS
    pcm = frames[start * 2:(start + CLIP_SAMPLES) * 2]
    assert len(pcm) == CLIP_SAMPLES * 2, src
    name = f"{src.stem}_{start_ms:07d}.wav"
    assert source_key(Path(name).stem) == f"direct_{label}_{unit}", name   # D3 유닛 키
    row.update(onset_ms=onset // MS, start_ms=start_ms, shifted=int(shifted),
               out_rel_path=f"{label}/{name}")
    return row, pcm


def existing_stems(label_dir: Path) -> dict[str, list[Path]]:
    """{label}/ 의 기존 조각 → 입력 stem 소문자별 목록."""
    found: dict[str, list[Path]] = {}
    if label_dir.is_dir():
        for p in label_dir.iterdir():
            if m := OUT_RE.match(p.name):
                found.setdefault(m.group(1).lower(), []).append(p)
    return found


def slice_all(post: Path, out_dir: Path, params: dict, dry_run: bool) -> list[dict]:
    judged = [judge(p, params) for p in sorted(post.iterdir()) if p.is_file()]
    # 입력끼리 대소문자만 다른 stem — 처리 순서로 승자를 정하지 않게 전부 거부한다.
    stems = Counter(Path(r["source_path"]).stem.lower() for r, pcm in judged if pcm)
    by_label: dict[str, dict[str, list[Path]]] = {}
    rows: list[dict] = []
    for row, pcm in judged:
        if pcm is None:
            rows.append(row)
            continue
        stem = Path(row["source_path"]).stem
        dst = out_dir / row["out_rel_path"]
        if stems[stem.lower()] > 1:
            rows.append(row | {"status": "rejected_case_conflict",
                               "reason": "대소문자만 다른 입력 stem 이 함께 있음"})
            continue
        olds = by_label.setdefault(row["label"], existing_stems(dst.parent)).get(stem.lower(), [])
        if any(OUT_RE.match(p.name).group(1) != stem for p in olds):
            row |= {"status": "rejected_case_conflict",
                    "reason": f"대소문자만 다른 기존 조각: {', '.join(sorted(p.name for p in olds))}"}
        elif olds:
            same = [p.name for p in olds] == [dst.name] and read_pcm(olds[0]) == pcm
            row |= ({"status": "skipped_exists", "reason": "같은 테이크 · 같은 PCM 조각이 이미 있음"}
                    if same else
                    {"status": "rejected_conflict",
                     "reason": f"같은 테이크의 다른 조각이 있음(무접촉): "
                               f"{', '.join(sorted(p.name for p in olds))}"})
        elif dry_run:
            row["status"] = "planned"
        else:
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                write_clip(dst, pcm)
                row["status"] = "written"
            except OSError as exc:
                row |= {"status": "failed_write", "reason": str(exc)}
        rows.append(row)
    return rows


def receiver_check(rec: Path, n_post: int) -> str:
    """수신기 manifest.csv 의 post_saved 행 수 ↔ post/ wav 수(불일치는 기록만)."""
    path = rec / "manifest.csv"
    if not path.is_file():
        return f"수신기 manifest.csv 없음 — post/ wav {n_post}"
    with path.open(newline="", encoding="utf-8") as fh:
        saved = sum(r.get("status") == "post_saved" for r in csv.DictReader(fh))
    return f"수신기 manifest post_saved {saved} ↔ post/ wav {n_post} — " + (
        "일치" if saved == n_post else "불일치")


def summarize(rows: list[dict], check: str, params: dict, dry_run: bool) -> str:
    status = Counter(r["status"] for r in rows)
    out = ["# 직접녹음 조각내기 요약" + (" (dry-run — 쓰기 0)" if dry_run else ""), "",
           f"- 파라미터: baseline_ms {params['baseline_ms']} · onset_ratio {params['onset_ratio']}"
           f" · onset_floor {params['onset_floor']}",
           f"- {check}",
           f"- 입력 {len(rows)} · 창 당김(shifted) {sum(r['shifted'] == 1 for r in rows)}",
           "", "## 상태별", ""]
    out += [f"- {k}: {v}" for k, v in sorted(status.items())]
    bad = [r for r in rows if r["status"] not in ("planned", "written", "skipped_exists")]
    if bad:
        out += ["", "## 거부 · 실패 목록", ""]
        out += [f"- {Path(r['source_path']).name} {r['status']}: {r['reason']}" for r in bad]
    return "\n".join(out) + "\n"


def run(args: argparse.Namespace) -> int:
    rec = args.recording_dir.resolve()
    post = rec / "post"
    if not post.is_dir():
        raise SystemExit(f"--recording-dir 에 post/ 가 없다({rec}) — 수신기 --out-dir 루트를 준다"
                         "(post/ 자체를 가리키지 않는다).")
    out_dir = check_out_dir(args.out_dir)
    if out_dir == rec or out_dir.is_relative_to(rec):
        raise SystemExit(f"--out-dir 가 recording-dir 안이다({out_dir}) — 수신 원본 폴더 보존을 위해 거부.")
    if args.baseline_ms < 1 or args.onset_ratio <= 0 or args.onset_floor < 0:
        raise SystemExit("--baseline-ms ≥ 1 · --onset-ratio > 0 · --onset-floor ≥ 0 이어야 한다.")
    manifest = out_dir / MANIFEST
    if manifest.exists():
        with manifest.open(newline="", encoding="utf-8") as fh:
            header = tuple(next(csv.reader(fh), ()))
        if header != MANIFEST_FIELDS:
            raise SystemExit(f"기존 {manifest} 의 열이 다르다 — append 하지 않는다: {header}")
    params = {"baseline_ms": args.baseline_ms, "onset_ratio": args.onset_ratio,
              "onset_floor": args.onset_floor}
    rows = [r | params | {"recording_dir": str(rec)}
            for r in slice_all(post, out_dir, params, args.dry_run)]
    check = receiver_check(rec, sum(1 for p in post.glob("*.wav")))
    text = summarize(rows, check, params, args.dry_run)
    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)
        new = not manifest.exists()
        with manifest.open("a", newline="", encoding="utf-8") as fh:   # 세션 누적
            writer = csv.DictWriter(fh, fieldnames=MANIFEST_FIELDS)
            if new:
                writer.writeheader()
            writer.writerows(rows)
        (out_dir / SUMMARY).write_text(text, encoding="utf-8")
    print(text, end="")
    return 1 if any(r["status"] == "failed_write" for r in rows) else 0


def _path(value: str) -> Path:
    return Path(value).expanduser()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="직접녹음 post/ → 소리 시작점 기준 3초 · 16kHz · mono · PCM16 조각(직접녹음 모드)")
    parser.add_argument("--recording-dir", required=True, type=_path,
                        help="녹음 수신기 --out-dir 루트(post/ 만 읽는다)")
    parser.add_argument("--out-dir", required=True, type=_path,
                        help="산출 폴더 — repo · 데이터셋 폴더 · recording-dir 밖")
    parser.add_argument("--baseline-ms", required=True, type=int,
                        help="onset 기준 구간(파일 앞 ms) — 값 미정")
    parser.add_argument("--onset-ratio", required=True, type=float,
                        help="onset 임계 = 기준 median_high × 이 배수 — 값 미정")
    parser.add_argument("--onset-floor", required=True, type=float,
                        help="onset 최소 |x|(이 값 초과) — 값 미정")
    parser.add_argument("--dry-run", action="store_true",
                        help="wav · manifest · 폴더를 만들지 않고 판정만 출력")
    return run(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
