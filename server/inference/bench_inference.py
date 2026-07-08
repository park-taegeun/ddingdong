"""추론 서빙 벤치 하네스 (standalone). RSS 분해 측정 + 지연 p50/p95 + verdict.

★★ 스코프 1층 경고 ★★ 기본값(--model-path 미지정)은 **합성 더미** SavedModel →
   산출 숫자(RSS·지연)는 **더미 기준·무의미**. 실 판정은 학부생 로컬(2층, 실
   `--model-path`) / 11주차 EC2(3층). 이 하네스가 죽이려는 리스크 = TF+YAMNet 이
   t3.small 2GB 에 fit 되는지 + 추론이 5초 예산 안인지 — **실 SavedModel 로 재실행 필수**.

RSS 체크포인트 4개(baseline → import tf → model load → inference)로 분해 측정 →
어디서 메모리를 잡아먹는지(대개 TF import) 드러나야 TFLite 전환 판단이 가능.

실행(server/ 에서):
  python3 -m inference.bench_inference                          # 더미 자동 생성·측정
  python3 -m inference.bench_inference --model-path <실 SavedModel>   # 학부생 로컬(2층)
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Callable

import numpy as np

from .constants import (
    DEFAULT_CLIP_SECONDS,
    DEFAULT_ITERATIONS,
    DEFAULT_WARMUP,
    LATENCY_BUDGET_MS,
    MEM_BUDGET_MB,
    SAMPLE_RATE,
    TFLITE_ADVISE_RATIO,
)


def _rss_mb() -> float:
    """현재 프로세스 RSS(MB). psutil 있으면 순간값, 없으면 resource peak(high-watermark).

    ★ resource.ru_maxrss 는 peak(감소 안 함) — baseline→import→load→infer 는 단조
      증가 단계라 각 체크포인트에서 peak≈현재. 플랫폼 단위 차: macOS=bytes, Linux=KB.
    """
    try:
        import psutil  # type: ignore

        return psutil.Process().memory_info().rss / (1024 * 1024)
    except Exception:  # noqa: BLE001 (psutil 부재 → stdlib fallback)
        import resource

        maxrss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # darwin: bytes / linux: kilobytes
        divisor = 1024 * 1024 if sys.platform == "darwin" else 1024
        return maxrss / divisor


def _synth_pcm16(duration_sec: float, sample_rate: int) -> bytes:
    """결정적 합성 오디오(440Hz sine) → PCM int16 LE 바이트. random 미사용(재현 가능)."""
    n = int(duration_sec * sample_rate)
    t = np.arange(n, dtype=np.float64) / sample_rate
    wave = 0.2 * np.sin(2.0 * np.pi * 440.0 * t)
    pcm = (wave * 32767.0).astype("<i2")
    return pcm.tobytes()


def _percentile(values: list[float], q: float) -> float:
    return float(np.percentile(np.asarray(values), q)) if values else 0.0


def run_bench(
    model_path: str | None,
    *,
    iterations: int = DEFAULT_ITERATIONS,
    warmup: int = DEFAULT_WARMUP,
    clip_seconds: float = DEFAULT_CLIP_SECONDS,
    log: Callable[[str], None] = print,
) -> dict[str, object]:
    """벤치 실행 → RSS 체크포인트 + 지연 통계 + verdict dict 반환.

    model_path=None → 임시 디렉터리에 더미 SavedModel 자동 생성.
    """
    # 지연 import 로 baseline 을 TF 로드 전에 측정 (핵심: import 비용 분리)
    from .audio_decode import decode_pcm16

    rss_baseline = _rss_mb()

    # ── 1) 더미 자동 생성(옵션) ──
    is_dummy = model_path is None
    tmp_dir: str | None = None
    if is_dummy:
        import tempfile

        from .make_dummy_savedmodel import build_dummy_savedmodel

        tmp_dir = tempfile.mkdtemp(prefix="dummy_savedmodel_")
        model_path = build_dummy_savedmodel(tmp_dir)
        log(f"[더미] 합성 SavedModel 생성 → {model_path} (★숫자 무의미)")

    # ── 2) TF import RSS(대개 여기서 대부분 점유) ──
    import tensorflow as tf  # noqa: F401 (RSS 체크포인트 목적 import)

    rss_after_import = _rss_mb()

    # ── 3) 모델 로드 RSS ──
    from .model_runner import ModelRunner

    runner = ModelRunner(model_path)  # type: ignore[arg-type]
    rss_after_load = _rss_mb()

    # ── 4) 추론 워밍업(graph trace 제외) + 측정 ──
    pcm = _synth_pcm16(clip_seconds, SAMPLE_RATE)
    waveform = decode_pcm16(pcm, SAMPLE_RATE)

    for _ in range(max(0, warmup)):
        runner.predict(waveform)

    latencies_ms: list[float] = []
    for _ in range(max(1, iterations)):
        t0 = time.perf_counter()
        runner.predict(waveform)
        latencies_ms.append((time.perf_counter() - t0) * 1000.0)
    rss_infer = _rss_mb()

    if tmp_dir is not None:
        import shutil

        shutil.rmtree(tmp_dir, ignore_errors=True)

    peak_rss = max(rss_baseline, rss_after_import, rss_after_load, rss_infer)
    p50 = _percentile(latencies_ms, 50)
    p95 = _percentile(latencies_ms, 95)

    return {
        "is_dummy": is_dummy,
        "sample_rate": SAMPLE_RATE,
        "clip_seconds": clip_seconds,
        "iterations": len(latencies_ms),
        "warmup": max(0, warmup),
        "rss_mb": {
            "baseline": round(rss_baseline, 1),
            "after_import_tf": round(rss_after_import, 1),
            "after_model_load": round(rss_after_load, 1),
            "during_inference": round(rss_infer, 1),
            "peak": round(peak_rss, 1),
        },
        "rss_delta_mb": {
            "import_tf": round(rss_after_import - rss_baseline, 1),
            "model_load": round(rss_after_load - rss_after_import, 1),
        },
        "latency_ms": {"p50": round(p50, 2), "p95": round(p95, 2)},
        "verdict": _verdict(peak_rss, p95),
    }


def _verdict(peak_rss: float, p95: float) -> dict[str, object]:
    advise_threshold = MEM_BUDGET_MB * TFLITE_ADVISE_RATIO
    return {
        "peak_rss_mb": round(peak_rss, 1),
        "mem_budget_mb": MEM_BUDGET_MB,
        "mem_within_budget": peak_rss <= MEM_BUDGET_MB,
        "p95_ms": round(p95, 2),
        "latency_budget_ms": LATENCY_BUDGET_MS,
        "latency_within_budget": p95 <= LATENCY_BUDGET_MS,
        "tflite_advise_threshold_mb": round(advise_threshold, 1),
        "tflite_recommended": peak_rss > advise_threshold,
    }


def _print_report(result: dict[str, object]) -> None:
    rss = result["rss_mb"]  # type: ignore[index]
    delta = result["rss_delta_mb"]  # type: ignore[index]
    lat = result["latency_ms"]  # type: ignore[index]
    v = result["verdict"]  # type: ignore[index]

    print("\n===== 추론 서빙 벤치 결과 =====")
    if result["is_dummy"]:
        print("★★ 더미 기준·무의미 — 학부생 로컬에서 실 SavedModel(--model-path)로 재실행 필요 ★★")
    print(
        f"입력: {result['clip_seconds']}s @ {result['sample_rate']}Hz | "
        f"iterations={result['iterations']} (warmup={result['warmup']} 제외)"
    )
    print("\n[RSS 체크포인트 MB] (peak/high-watermark)")
    print(f"  baseline            : {rss['baseline']}")
    print(f"  +import tensorflow   : {rss['after_import_tf']}   (Δ {delta['import_tf']})")
    print(f"  +model load          : {rss['after_model_load']}   (Δ {delta['model_load']})")
    print(f"  during inference     : {rss['during_inference']}")
    print(f"  peak                 : {rss['peak']}")
    print("\n[지연 ms]")
    print(f"  p50={lat['p50']}  p95={lat['p95']}")

    print("\n[verdict]")
    mem_ok = "OK" if v["mem_within_budget"] else "초과"
    lat_ok = "OK" if v["latency_within_budget"] else "초과"
    print(f"  메모리 : peak {v['peak_rss_mb']}MB / {v['mem_budget_mb']}MB 예산 → {mem_ok}")
    print(f"  지연   : p95 {v['p95_ms']}ms / {v['latency_budget_ms']}ms 예산 → {lat_ok}")
    print(
        f"  TFLite : peak > {v['tflite_advise_threshold_mb']}MB "
        f"(예산의 {int(TFLITE_ADVISE_RATIO*100)}%) 초과 시 변환 권고 → "
        f"{'권고' if v['tflite_recommended'] else '불필요'}"
    )
    print(
        "\n[gunicorn preload COW 주석] 워커 2개(preload_app=True)는 fork 후 모델 페이지를\n"
        "  copy-on-write 로 공유 → 실메모리 ≈ 1×(모델) + 2×(워커 오버헤드), 2×모델 아님.\n"
        "  단 추론 중 쓰기 페이지는 COW 분리되므로 위 peak 는 워커 1개 기준 하한값."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="추론 서빙 벤치 하네스(RSS+지연+verdict)")
    parser.add_argument(
        "--model-path", default=None,
        help="SavedModel 경로. 미지정 시 합성 더미 자동 생성(숫자 무의미).",
    )
    parser.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS)
    parser.add_argument("--warmup", type=int, default=DEFAULT_WARMUP)
    parser.add_argument("--clip-seconds", type=float, default=DEFAULT_CLIP_SECONDS)
    args = parser.parse_args(argv)

    result = run_bench(
        args.model_path,
        iterations=args.iterations,
        warmup=args.warmup,
        clip_seconds=args.clip_seconds,
    )
    _print_report(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
