"""보드 배경음(INMP441 잡음 바닥) 전용 테이크 post/ WAV → `other` 3초 조각 — 보드 배경 모드.

  python -m ml.curation.slice_boardbg \
      --recording-dir "~/ddingdong-측정결과/<날짜>/boardbg_rec" \
      --out-dir       "~/ddingdong-측정결과/<날짜>/boardbg_clips" \
      --unit <유닛> --baseline-ms <ms> --onset-ratio <배수> --onset-floor <|x|> [--dry-run]

근거 = 사용자 결정 D-a(2026-09-26, PoC-(59)): 현 모델에 보드 배경(pre)을 넣으면 knock 로 오탐한다.
소재 = 「소리 없이 `s` 만 누른 전용 배경 테이크」의 post(5.12초). pre(2.048초)는 읽지 않는다.

규칙
  - 입력 = `--recording-dir/post/direct_{label}_{unit}_{take}.wav`(녹음 수신기 규칙) 만.
  - 유닛 가드: post/ 의 파일 중 하나라도 이름이 규칙 밖이거나 유닛이 --unit 과 다르면 실행 전체 거부(쓰기 0).
  - 테이크별 판정(첫 매치에서 멈춘다): 규격(16kHz · mono · 16bit) → 3초 미만(pad 하지 않음) →
    클램프(|x| ≥ 32767) ≥ 1 → 소리 시작점 검출(slice_direct.find_onset, 파일 전체) → 통과.
  - 통과 = 비중첩 3초 분할, 잔여 버림(33.7(i) 네거티브 모드). 5.12초 → 1조각 @0. 리샘플 · 정규화 0.
  - 출력 `{out-dir}/other/boardbg_{unit}_{take}_{start_ms:07d}.wav` — source_key = `boardbg_{unit}`.
  - 멱등 = 테이크 단위(slice_direct 와 같다): 같은 이름 · 같은 PCM 이면 skip, 다르면 conflict(무접촉),
    대소문자만 다른 이름도 conflict.
  - manifest = out-dir 의 boardbg_slice_manifest.csv 에 append(판정 · 사유 · 피크 · 클램프 수 · 검출 시각 ·
    산출 파일 · 파라미터).

한계: 소리 검사는 조용한 이벤트(임계 미만)를 놓친다 — README 「보드 배경」 절의 실측 수치 참고.
값 3개와 경로 · 유닛은 필수 인자다(기본값 없음). 산출은 repo · 데이터셋 폴더 · recording-dir 밖에만 쓴다.
"""

from __future__ import annotations

import argparse
import csv
import re
import wave
from array import array
from collections import Counter
from pathlib import Path

from ..pipeline.config import SAMPLE_RATE, source_key
from .slice_direct import (CLAMP, MS, NAME_RE, OUT_RE, existing_stems, find_onset, read_pcm,
                           write_clip)
from .slice_negatives import CLASS_DIR, CLIP_SAMPLES, check_out_dir

UNIT_RE = re.compile(r"^[A-Za-z0-9]+$")   # 녹음 수신기 UNIT_RE 와 같다(밑줄 금지)
PREFIX = "boardbg_"
MANIFEST = "boardbg_slice_manifest.csv"
MANIFEST_FIELDS = ("recording_dir", "source_path", "unit", "take", "n_samples", "peak",
                   "clamp_count", "onset_ms", "out_rel_paths", "status", "reason",
                   "baseline_ms", "onset_ratio", "onset_floor")


def unit_violations(post: Path, unit: str) -> list[str]:
    """post/ 에서 이름 규칙 밖이거나 유닛이 다른 파일 목록(비면 통과)."""
    bad = []
    for p in sorted(post.iterdir()):
        if not p.is_file():
            continue
        m = NAME_RE.match(p.stem) if p.suffix == ".wav" else None
        if not m:
            bad.append(f"{p.name}(이름 규칙 밖)")
        elif m.group(2) != unit:
            bad.append(f"{p.name}(유닛 {m.group(2)})")
    return bad


def judge(src: Path, unit: str, params: dict) -> tuple[dict, list[tuple[str, bytes]]]:
    """테이크 1개 판정 → (manifest 행, [(산출 이름, PCM)]). 디스크 쓰기 없음."""
    take = NAME_RE.match(src.stem).group(3)
    row = {f: "" for f in MANIFEST_FIELDS} | {"source_path": str(src), "unit": unit, "take": take}

    def reject(status: str, reason: str) -> tuple[dict, list]:
        return row | {"status": status, "reason": reason}, []

    try:
        with wave.open(str(src), "rb") as wf:
            fmt = (wf.getnchannels(), wf.getsampwidth(), wf.getframerate())
            frames = wf.readframes(wf.getnframes())
    except (wave.Error, EOFError) as exc:
        return reject("rejected_format", f"wave 로 읽지 못함: {exc}")
    if fmt != (1, 2, SAMPLE_RATE):
        return reject("rejected_format", f"(채널, 바이트, Hz) = {fmt} ≠ (1, 2, {SAMPLE_RATE})")
    a = [abs(v) for v in array("h", frames)]   # 파이썬 int — −32768 도 넘치지 않는다
    n = len(a)
    clamp = sum(v >= CLAMP for v in a)
    row.update(n_samples=n, peak=max(a, default=0), clamp_count=clamp)
    if n < CLIP_SAMPLES:
        return reject("rejected_short", f"{n}샘플 < {CLIP_SAMPLES}(pad 하지 않음)")
    if clamp:
        return reject("rejected_clamp", f"|x| ≥ {CLAMP} 샘플 {clamp}개")
    onset, _ = find_onset(a, params["baseline_ms"] * MS, params["onset_ratio"],
                          params["onset_floor"])
    if onset is not None:
        row["onset_ms"] = onset // MS
        return reject("rejected_sound", f"소리 시작점 검출 @{onset // MS}ms")
    clips = []
    for i in range(n // CLIP_SAMPLES):   # 비중첩 분할, 잔여 버림
        start = i * CLIP_SAMPLES
        name = f"{PREFIX}{unit}_{take}_{start // MS:07d}.wav"
        assert source_key(Path(name).stem) == f"{PREFIX}{unit}", name   # 유닛 그룹 키
        clips.append((name, frames[start * 2:(start + CLIP_SAMPLES) * 2]))
    row["out_rel_paths"] = ";".join(f"{CLASS_DIR}/{name}" for name, _ in clips)
    return row, clips


def slice_all(post: Path, out_dir: Path, unit: str, params: dict, dry_run: bool) -> list[dict]:
    judged = [judge(p, unit, params) for p in sorted(post.iterdir()) if p.is_file()]
    # 산출 테이크 stem 이 대소문자 무시로 겹치는 입력(label 만 다른 같은 테이크 번호 포함)은 전부 거부.
    dup = Counter(f"{PREFIX}{unit}_{r['take']}".lower() for r, clips in judged if clips)
    class_dir = out_dir / CLASS_DIR
    olds_by = existing_stems(class_dir)
    rows = []
    for row, clips in judged:
        if not clips:
            rows.append(row)
            continue
        stem = f"{PREFIX}{unit}_{row['take']}"
        olds = olds_by.get(stem.lower(), [])
        names = sorted(name for name, _ in clips)
        if dup[stem.lower()] > 1:
            row |= {"status": "rejected_name_conflict",
                    "reason": f"같은 산출 이름 {stem} 을 만드는 입력이 여럿(label · 대소문자만 다름)"}
        elif any(OUT_RE.match(p.name).group(1) != stem for p in olds):
            row |= {"status": "rejected_case_conflict",
                    "reason": f"대소문자만 다른 기존 조각: {', '.join(sorted(p.name for p in olds))}"}
        elif olds:
            same = (sorted(p.name for p in olds) == names
                    and all(read_pcm(class_dir / name) == pcm for name, pcm in clips))
            row |= ({"status": "skipped_exists", "reason": "같은 테이크 · 같은 PCM 조각이 이미 있음"}
                    if same else
                    {"status": "rejected_conflict",
                     "reason": f"같은 테이크의 다른 조각이 있음(무접촉): "
                               f"{', '.join(sorted(p.name for p in olds))}"})
        elif dry_run:
            row["status"] = "planned"
        else:
            try:
                class_dir.mkdir(parents=True, exist_ok=True)
                for name, pcm in clips:
                    write_clip(class_dir / name, pcm)
                row["status"] = "written"
            except OSError as exc:
                row |= {"status": "failed_write", "reason": str(exc)}
        rows.append(row)
    return rows


def summarize(rows: list[dict], params: dict, dry_run: bool) -> str:
    out = ["# 보드 배경 조각내기" + (" (dry-run — 쓰기 0)" if dry_run else ""), "",
           f"- 파라미터: baseline_ms {params['baseline_ms']} · onset_ratio {params['onset_ratio']}"
           f" · onset_floor {params['onset_floor']}", ""]
    out += [f"- {k}: {v}" for k, v in sorted(Counter(r["status"] for r in rows).items())]
    out += ["", "| 테이크 | 판정 | 피크 | 클램프 | 검출 ms | 산출 · 사유 |",
            "|---|---|---|---|---|---|"]
    out += [f"| {Path(r['source_path']).name} | {r['status']} | {r['peak']} | {r['clamp_count']} "
            f"| {r['onset_ms']} | {r['out_rel_paths'] or r['reason']} |" for r in rows]
    return "\n".join(out) + "\n"


def run(args: argparse.Namespace) -> int:
    rec = args.recording_dir.resolve()
    post = rec / "post"
    if not post.is_dir():
        raise SystemExit(f"--recording-dir 에 post/ 가 없다({rec}) — 수신기 --out-dir 루트를 준다.")
    out_dir = check_out_dir(args.out_dir)
    if out_dir == rec or out_dir.is_relative_to(rec):
        raise SystemExit(f"--out-dir 가 recording-dir 안이다({out_dir}) — 수신 원본 폴더 보존을 위해 거부.")
    if not UNIT_RE.match(args.unit):
        raise SystemExit(f"--unit 은 영문 · 숫자만(밑줄 금지, 수신기 규칙): {args.unit!r}")
    if args.baseline_ms < 1 or args.onset_ratio <= 0 or args.onset_floor < 0:
        raise SystemExit("--baseline-ms ≥ 1 · --onset-ratio > 0 · --onset-floor ≥ 0 이어야 한다.")
    bad = unit_violations(post, args.unit)
    if bad:
        raise SystemExit(f"post/ 에 --unit {args.unit} 밖의 파일 {len(bad)}개 — 실행 전체 거부(쓰기 0): "
                         + ", ".join(bad))
    manifest = out_dir / MANIFEST
    if manifest.exists():
        with manifest.open(newline="", encoding="utf-8") as fh:
            header = tuple(next(csv.reader(fh), ()))
        if header != MANIFEST_FIELDS:
            raise SystemExit(f"기존 {manifest} 의 열이 다르다 — append 하지 않는다: {header}")
    params = {"baseline_ms": args.baseline_ms, "onset_ratio": args.onset_ratio,
              "onset_floor": args.onset_floor}
    rows = [r | params | {"recording_dir": str(rec)}
            for r in slice_all(post, out_dir, args.unit, params, args.dry_run)]
    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)
        new = not manifest.exists()
        with manifest.open("a", newline="", encoding="utf-8") as fh:   # 세션 누적
            writer = csv.DictWriter(fh, fieldnames=MANIFEST_FIELDS)
            if new:
                writer.writeheader()
            writer.writerows(rows)
    print(summarize(rows, params, args.dry_run), end="")
    return 1 if any(r["status"] == "failed_write" for r in rows) else 0


def _path(value: str) -> Path:
    return Path(value).expanduser()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="보드 배경 전용 테이크 post/ → other 3초 · 16kHz · mono · PCM16 조각(보드 배경 모드)")
    parser.add_argument("--recording-dir", required=True, type=_path,
                        help="녹음 수신기 --out-dir 루트(post/ 만 읽는다)")
    parser.add_argument("--out-dir", required=True, type=_path,
                        help="산출 폴더 — repo · 데이터셋 폴더 · recording-dir 밖")
    parser.add_argument("--unit", required=True,
                        help="이 폴더의 유일한 유닛 — 다른 유닛 파일이 하나라도 있으면 거부")
    parser.add_argument("--baseline-ms", required=True, type=int,
                        help="소리 검사 기준 구간(파일 앞 ms) — 값 미정")
    parser.add_argument("--onset-ratio", required=True, type=float,
                        help="소리 임계 = 기준 median_high × 이 배수 — 값 미정")
    parser.add_argument("--onset-floor", required=True, type=float,
                        help="소리 최소 |x|(이 값 초과) — 값 미정")
    parser.add_argument("--dry-run", action="store_true",
                        help="wav · manifest · 폴더를 만들지 않고 판정 표만 출력")
    return run(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
