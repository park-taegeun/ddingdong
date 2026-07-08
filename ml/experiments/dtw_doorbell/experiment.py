"""분리 실험: intra(같은 초인종) vs inter(다른 초인종) 거리 분포 + 마진 + EER.

★ 실험 설계 (Step1 catch 결과):
  01_clips/doorbell 파일명 = `{원본ID}_{7자리 offset}.wav` → 같은 원본ID의 여러 조각
  = 한 소스 녹음의 인접 구간 = **같은 물리적 초인종**. 이 그룹으로
    intra쌍 = 같은 원본ID 다른 조각,  inter쌍 = 다른 원본ID
  를 구성한다(대체 self/other 설계 불필요 — 실그룹 확보됨).

★★ 캐비앗(리포트 대문짝): intra쌍은 "한 소스 녹음의 인접 조각"이라 **독립 재녹음(실제
   재-누름)보다 낙관적**이다 → 여기 마진은 상한 근사. 진짜 재-누름 변동은 학부생
   직접녹음(04_direct_recording, 카테고리 5)로 2층에서 재검증해야 확정.

이 파일의 거리 숫자는 학부생 로컬(2층) 실 클립 실행에서만 유효. MCP 세션은 synth_smoke.
"""

from __future__ import annotations

import argparse
import logging
import random
import re
import sys
from pathlib import Path

import numpy as np

from .constants import (
    GO_MARGIN_MIN,
    MAX_INTER_PAIRS,
    MAX_INTRA_PAIRS_PER_GROUP,
    PRETEST_MARGIN,
    RANDOM_SEED,
    TARGET_CLASS,
)
from .distance import dtw_cosine, has_fastdtw
from .features import wav_to_template

log = logging.getLogger("ml.experiments.dtw_doorbell")

_SRC_ID_RE = re.compile(r"^(.*)_(\d{7})\.wav$")


def source_id(filename: str) -> str:
    """`{원본ID}_{7자리offset}.wav` → 원본ID. 규칙 밖이면 확장자만 제거."""
    m = _SRC_ID_RE.match(filename)
    return m.group(1) if m else filename[:-4] if filename.endswith(".wav") else filename


def resolve_doorbell_dir(clips_dir: Path) -> Path:
    """--clips-dir 이 doorbell 폴더 자체거나 그 상위(01_clips)여도 동작."""
    if (clips_dir / TARGET_CLASS).is_dir():
        return clips_dir / TARGET_CLASS
    return clips_dir


def group_by_source(doorbell_dir: Path) -> dict[str, list[Path]]:
    """doorbell wav → 원본ID별 그룹."""
    groups: dict[str, list[Path]] = {}
    for p in sorted(doorbell_dir.glob("*.wav")):
        groups.setdefault(source_id(p.name), []).append(p)
    return groups


def build_pairs(
    groups: dict[str, list[Path]], *, seed: int = RANDOM_SEED
) -> tuple[list[tuple[Path, Path]], list[tuple[Path, Path]], dict[str, int]]:
    """intra쌍(같은 그룹)·inter쌍(다른 그룹) 샘플 구성. 상한 초과분은 stats로 반환."""
    rng = random.Random(seed)
    multi = {k: v for k, v in groups.items() if len(v) >= 2}

    intra: list[tuple[Path, Path]] = []
    intra_capped = 0
    for files in multi.values():
        combos = [(a, b) for i, a in enumerate(files) for b in files[i + 1 :]]
        rng.shuffle(combos)
        if len(combos) > MAX_INTRA_PAIRS_PER_GROUP:
            intra_capped += len(combos) - MAX_INTRA_PAIRS_PER_GROUP
        intra.extend(combos[:MAX_INTRA_PAIRS_PER_GROUP])

    # inter: 각 그룹 대표 1개끼리 랜덤 쌍(같은 그룹 회피)
    reps = [rng.choice(v) for v in groups.values()]
    rng.shuffle(reps)
    inter: list[tuple[Path, Path]] = []
    inter_possible = len(reps) * (len(reps) - 1) // 2
    for i in range(len(reps)):
        for j in range(i + 1, len(reps)):
            inter.append((reps[i], reps[j]))
    rng.shuffle(inter)
    inter_capped = max(0, len(inter) - MAX_INTER_PAIRS)
    inter = inter[:MAX_INTER_PAIRS]

    stats = {
        "groups_total": len(groups),
        "groups_multi": len(multi),
        "intra_pairs": len(intra),
        "intra_pairs_dropped_by_cap": intra_capped,
        "inter_pairs": len(inter),
        "inter_pairs_possible": inter_possible,
        "inter_pairs_dropped_by_cap": inter_capped,
    }
    return intra, inter, stats


def _distances(
    pairs: list[tuple[Path, Path]], backend: str, cache: dict[Path, np.ndarray]
) -> list[float]:
    out: list[float] = []
    for a, b in pairs:
        ta = cache.get(a)
        if ta is None:
            ta = cache[a] = wav_to_template(a)
        tb = cache.get(b)
        if tb is None:
            tb = cache[b] = wav_to_template(b)
        out.append(dtw_cosine(ta, tb, backend=backend))
    return out


def separation_margin(intra: list[float], inter: list[float]) -> dict[str, float]:
    """분리 마진 = (inter평균 − intra평균) / pooled_std (Cohen's d류). 양수·클수록 좋음."""
    ia = np.asarray(intra, dtype=np.float64)
    ib = np.asarray(inter, dtype=np.float64)
    mean_intra = float(ia.mean()) if ia.size else 0.0
    mean_inter = float(ib.mean()) if ib.size else 0.0
    var_intra = float(ia.var(ddof=1)) if ia.size > 1 else 0.0
    var_inter = float(ib.var(ddof=1)) if ib.size > 1 else 0.0
    pooled = float(np.sqrt((var_intra + var_inter) / 2.0))
    margin = (mean_inter - mean_intra) / pooled if pooled > 1e-12 else 0.0
    return {
        "mean_intra": mean_intra,
        "mean_inter": mean_inter,
        "std_intra": float(np.sqrt(var_intra)),
        "std_inter": float(np.sqrt(var_inter)),
        "pooled_std": pooled,
        "margin": margin,
    }


def threshold_sweep(
    intra: list[float], inter: list[float], *, steps: int = 200
) -> dict[str, float]:
    """임계값 스윕 → 최고정확도 임계 + EER. intra=등록(같음), 거리≤임계 → 매칭 판정."""
    ia = np.asarray(intra, dtype=np.float64)
    ib = np.asarray(inter, dtype=np.float64)
    if ia.size == 0 or ib.size == 0:
        return {"best_threshold": 0.0, "best_accuracy": 0.0, "eer": 1.0, "eer_threshold": 0.0}
    lo = float(min(ia.min(), ib.min()))
    hi = float(max(ia.max(), ib.max()))
    span = hi - lo or 1.0
    best_acc, best_thr, best_eer, eer_thr, best_gap = 0.0, lo, 1.0, lo, float("inf")
    for k in range(steps + 1):
        thr = lo + span * k / steps
        frr = float((ia > thr).mean())  # 등록인데 거절
        far = float((ib <= thr).mean())  # 미등록인데 수락
        acc = float(((ia <= thr).sum() + (ib > thr).sum()) / (ia.size + ib.size))
        if acc > best_acc:
            best_acc, best_thr = acc, thr
        if abs(far - frr) < best_gap:
            best_gap, best_eer, eer_thr = abs(far - frr), (far + frr) / 2.0, thr
    return {
        "best_threshold": best_thr,
        "best_accuracy": best_acc,
        "eer": best_eer,
        "eer_threshold": eer_thr,
    }


def run_experiment(
    clips_dir: Path, *, backend: str = "auto", max_groups: int | None = None, seed: int = RANDOM_SEED
) -> dict[str, object]:
    """실 클립(2층) 분리 실험 실행 → 리포트 dict."""
    doorbell_dir = resolve_doorbell_dir(clips_dir)
    if not doorbell_dir.is_dir():
        raise FileNotFoundError(f"doorbell 클립 폴더 없음: {doorbell_dir}")
    groups = group_by_source(doorbell_dir)
    if max_groups is not None:
        groups = dict(list(groups.items())[:max_groups])
    intra_pairs, inter_pairs, pair_stats = build_pairs(groups, seed=seed)
    if not intra_pairs or not inter_pairs:
        raise ValueError(
            f"쌍 부족 (intra={len(intra_pairs)}, inter={len(inter_pairs)}) — "
            "그룹당 조각 2개 이상 원본이 필요"
        )
    cache: dict[Path, np.ndarray] = {}
    intra_d = _distances(intra_pairs, backend, cache)
    inter_d = _distances(inter_pairs, backend, cache)
    return _assemble_report(intra_d, inter_d, pair_stats, backend, is_synthetic=False)


def _assemble_report(
    intra_d: list[float],
    inter_d: list[float],
    pair_stats: dict[str, int],
    backend: str,
    *,
    is_synthetic: bool,
) -> dict[str, object]:
    margin = separation_margin(intra_d, inter_d)
    sweep = threshold_sweep(intra_d, inter_d)
    go = margin["margin"] >= GO_MARGIN_MIN
    return {
        "is_synthetic": is_synthetic,
        "backend": "fastdtw" if (backend in ("auto", "fastdtw") and has_fastdtw()) else "exact",
        "pairs": pair_stats,
        "separation": margin,
        "threshold": sweep,
        "pretest_margin": PRETEST_MARGIN,
        "go_margin_min": GO_MARGIN_MIN,
        "recommendation": "GO" if go else "NO-GO/재검토",
    }


def print_report(report: dict[str, object]) -> None:
    sep = report["separation"]  # type: ignore[index]
    thr = report["threshold"]  # type: ignore[index]
    pairs = report["pairs"]  # type: ignore[index]
    print("\n===== DTW 초인종 분리 실험 =====")
    if report["is_synthetic"]:
        print("★★ 합성·무의미 — 학부생 로컬(2층) 실 클립으로 재실행해야 유효 ★★")
    print(f"백엔드: {report['backend']}  |  쌍: intra={pairs['intra_pairs']} inter={pairs['inter_pairs']}")
    dropped = pairs["intra_pairs_dropped_by_cap"] + pairs["inter_pairs_dropped_by_cap"]
    if dropped:
        print(f"  (상한으로 제외된 쌍 {dropped}개 — silent 아님, 재현 위해 명시)")
    print("\n[거리 분포]")
    print(f"  intra(같은 초인종) : 평균 {sep['mean_intra']:.4f} ± {sep['std_intra']:.4f}")
    print(f"  inter(다른 초인종) : 평균 {sep['mean_inter']:.4f} ± {sep['std_inter']:.4f}")
    print("\n[분리 지표]")
    print(f"  마진(Cohen's d류)  : {sep['margin']:.3f}   (pretest 기준 {report['pretest_margin']})")
    print(f"  임계 스윕 최고정확도 : {thr['best_accuracy']*100:.1f}%  @ 거리 {thr['best_threshold']:.4f}")
    print(f"  EER               : {thr['eer']*100:.1f}%  @ 거리 {thr['eer_threshold']:.4f}")
    print("\n[판정]")
    print(
        f"  margin {sep['margin']:.3f} vs 권고선 {report['go_margin_min']} → "
        f"{report['recommendation']}"
    )
    if not report["is_synthetic"]:
        print(
            "  ★ 캐비앗: intra=한 소스 녹음의 인접 조각 → 실 재-누름보다 낙관적. "
            "직접녹음(04)으로 재확인 필요."
        )


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="DTW 초인종 분리 실험 (2층: 실 클립)")
    parser.add_argument(
        "--clips-dir",
        required=True,
        type=Path,
        help="01_clips 또는 01_clips/doorbell 경로 (실데이터, repo 밖 홈)",
    )
    parser.add_argument("--backend", default="auto", choices=("auto", "exact", "fastdtw"))
    parser.add_argument("--max-groups", type=int, default=None, help="빠른 확인용 그룹 제한")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    args = parser.parse_args(argv)

    report = run_experiment(
        args.clips_dir, backend=args.backend, max_groups=args.max_groups, seed=args.seed
    )
    print_report(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
