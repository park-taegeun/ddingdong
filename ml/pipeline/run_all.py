"""전체 파이프라인 오케스트레이터.

  python -m ml.pipeline.run_all                 # DDINGDONG_DATA_ROOT(env) 또는 기본 경로
  DDINGDONG_DATA_ROOT="..." python -m ml.pipeline.run_all
  python -m ml.pipeline.run_all --data-root "..."

Step1 전처리 → Step2 분할 → Step3 증강(train) → Step4 조립 → Step5 누수 가드.
"""

from __future__ import annotations

import argparse
import logging
import sys

from . import assemble, augment, config, preprocess, split
from .config import Paths
from .guards import assert_no_leakage


def _print_summary(final_counts: dict[str, dict[str, int]], guard: dict[str, int]) -> None:
    print("\n=== 05_final_dataset 개수 (split × class) ===")
    header = f"{'split':<7}" + "".join(f"{c:>12}" for c in config.CLASSES) + f"{'total':>9}"
    print(header)
    for split_name in ("train", "val", "test"):
        row = final_counts[split_name]
        total = sum(row.values())
        print(f"{split_name:<7}" + "".join(f"{row[c]:>12}" for c in config.CLASSES) + f"{total:>9}")
    print(f"\n누수 가드 통과 — 고유 stem: "
          f"train={guard['train']} val={guard['val']} test={guard['test']} (겹침 0)")


def run(paths: Paths, clean: bool = True) -> dict[str, dict[str, int]]:
    log = logging.getLogger("ml.pipeline")
    log.info("DATA_ROOT = %s", paths.root)

    if not paths.clips.is_dir():
        raise FileNotFoundError(
            f"입력 폴더 없음: {paths.clips}\n"
            f"  → DDINGDONG_DATA_ROOT 를 '01_clips' 상위 폴더로 지정했는지 확인."
        )

    # clean=True(기본): 각 스테이지가 write 전 자기 산출 폴더(02/03/05)를 비워 stale
    # 잔재를 제거. 특히 02 stale(가드 도입 전 빈 클립)이 05 로 부활하던 회귀 차단.
    preprocess.preprocess(paths, clean=clean)
    split.split_dataset(paths)
    augment.augment(paths, clean=clean)
    if clean:
        # 05 재생성 전 기존 train/val/test 를 비워 stale 중첩 방지(--no-clean 로 opt-out).
        assemble.clean_final(paths)
    final_counts = assemble.assemble(paths)
    guard = assert_no_leakage(assemble.load_final_manifest(paths))
    _print_summary(final_counts, guard)
    return final_counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ddingdong ML 데이터 파이프라인")
    parser.add_argument(
        "--data-root", default=None,
        help="데이터 루트(01_clips 상위). 미지정 시 DDINGDONG_DATA_ROOT env 또는 기본 경로.",
    )
    parser.add_argument("--quiet", action="store_true", help="INFO 로그 억제")
    parser.add_argument(
        "--no-clean", action="store_true",
        help="스테이지(02/03/05) 재생성 전 auto-clean 비활성(기본은 stale 방지 위해 clean).",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    run(config.resolve_paths(args.data_root), clean=not args.no_clean)
    return 0


if __name__ == "__main__":
    sys.exit(main())
