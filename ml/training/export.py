"""추론 SavedModel export (Step 5) — best.keras(head) + YAMNet → 서빙 SavedModel.

  python -m ml.training.export                       # 기본 경로(config.model_dir)
  python -m ml.training.export --checkpoint "…/best.keras" --out-dir "…"

학습된 head(best.keras)만 있으면 재학습 없이 배포 아티팩트를 만든다. frozen YAMNet
backbone + head 를 model.build_inference_model 로 합성(waveform→클래스 확률)한 뒤
Keras 3 model.export() 로 서빙 SavedModel 을 내보낸다.

★ 왜 model.export() 인가: tf.saved_model.save(model) 은 Lambda 클로저가 캡처한 frozen
  YAMNet 리소스가 객체 그래프에 미추적(untracked)이라 'Tried to export … untracked
  resource' AssertionError 로 실패한다. model.export() 는 ExportArchive 가 서빙
  tf.function 을 트레이스하며 캡처 리소스를 함께 추적·직렬화하므로 해소된다
  (decisions.md 33.3-③). 라벨 인덱스는 config.CLASSES(SSoT)를 그대로 상속한다.

실 YAMNet(hub) 로드는 학부생 로컬 런타임에서 수행(오프라인/테스트는 yamnet 주입).
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import config, model

log = logging.getLogger("ml.training.export")

SAVEDMODEL_NAME: str = "inference_savedmodel"       # 배포 아티팩트 디렉토리명


def export_savedmodel(
    out_dir: Path,
    *,
    checkpoint: Path | None = None,
    yamnet=None,
    yamnet_handle: str = config.YAMNET_HUB_HANDLE,
    export_dir: Path | None = None,
) -> dict:
    """best.keras(head) + YAMNet → 서빙 SavedModel 저장. 반환: 산출 요약 dict.

    yamnet 미지정 → hub 에서 로드(실행). 테스트는 결정적 더미 backbone 을 주입.
    """
    ckpt = checkpoint or (out_dir / config.CHECKPOINT_NAME)
    if not ckpt.exists():
        raise FileNotFoundError(
            f"체크포인트 없음: {ckpt}\n  → 먼저 `python -m ml.training.train` 실행 필요."
        )
    import tensorflow as tf

    head = tf.keras.models.load_model(str(ckpt))
    if yamnet is None:
        yamnet = model.load_yamnet(yamnet_handle)

    infer = model.build_inference_model(head, yamnet)
    target = Path(export_dir) if export_dir else (out_dir / SAVEDMODEL_NAME)
    target.parent.mkdir(parents=True, exist_ok=True)
    infer.export(str(target))                        # ★ Keras 3 표준(미추적 리소스 해소)
    log.info("추론 SavedModel(export) 저장 → %s", target)
    return {
        "savedmodel": str(target),
        "checkpoint": str(ckpt),
        "classes": list(config.CLASSES),             # 배포 라벨 순서(index=0..N-1)
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="best.keras → 서빙 SavedModel export")
    parser.add_argument("--out-dir", default=None, help="산출물 경로(미지정=config.model_dir)")
    parser.add_argument("--checkpoint", default=None, help="head 체크포인트(미지정=out-dir/best.keras)")
    parser.add_argument("--export-dir", default=None, help="SavedModel 출력 경로(미지정=out-dir/inference_savedmodel)")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    out_dir = Path(args.out_dir).expanduser() if args.out_dir else config.model_dir()
    checkpoint = Path(args.checkpoint).expanduser() if args.checkpoint else None
    export_dir = Path(args.export_dir).expanduser() if args.export_dir else None
    summary = export_savedmodel(out_dir, checkpoint=checkpoint, export_dir=export_dir)
    print("\n=== export 완료 ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
