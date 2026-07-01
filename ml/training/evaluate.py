"""평가 (Step 4) — test set 최종 성능: accuracy + 클래스별 P/R/F1 + confusion matrix.

  python -m ml.training.evaluate                    # DDINGDONG_DATA_ROOT env 사용
  python -m ml.training.evaluate --data-root "..."

기준선(사전테스트 pre-trained YAMNet Top-1): doorbell≈30% / knock≈40% / fire_alarm≈20%.
transfer learning head 학습 후 이 대비 개선 여부를 확인하는 것이 목적.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from pathlib import Path

import numpy as np

from . import config, data, model

log = logging.getLogger("ml.training.evaluate")

# 사전테스트 pre-trained 기준선(개선 확인용, 하드코딩 = 발표 참고값).
PRETRAINED_BASELINE_TOP1: dict[str, float] = {
    "doorbell": 0.30, "knock": 0.40, "fire_alarm": 0.20,
}


def evaluate(
    final_dir: Path,
    out_dir: Path,
    *,
    embed_fn=None,
    yamnet_handle: str = config.YAMNET_HUB_HANDLE,
    checkpoint: Path | None = None,
) -> dict:
    """test set 평가 후 리포트 저장. 반환: {accuracy, per_class, confusion}."""
    import tensorflow as tf
    from sklearn.metrics import classification_report, confusion_matrix

    ckpt = checkpoint or (out_dir / config.CHECKPOINT_NAME)
    if not ckpt.exists():
        raise FileNotFoundError(
            f"체크포인트 없음: {ckpt}\n  → 먼저 `python -m ml.training.train` 실행 필요."
        )
    head = tf.keras.models.load_model(str(ckpt))

    if embed_fn is None:
        yamnet = model.load_yamnet(yamnet_handle)
        embed_fn = model.yamnet_embed_fn(yamnet)

    test_ex = data.list_examples(final_dir, "test")
    y_true = np.array([y for _, y in test_ex])
    test_ds = data.make_embedding_dataset(test_ex, embed_fn, training=False)

    probs = head.predict(test_ds, verbose=0)
    y_pred = np.argmax(probs, axis=1)

    labels_idx = list(range(config.NUM_CLASSES))
    report = classification_report(
        y_true, y_pred, labels=labels_idx, target_names=list(config.CLASSES),
        output_dict=True, zero_division=0,
    )
    cm = confusion_matrix(y_true, y_pred, labels=labels_idx)
    accuracy = float(report["accuracy"])
    macro_f1 = float(report["macro avg"]["f1-score"])

    # 리포트 저장 (json)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_out = {
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "per_class": {
            c: {
                "precision": float(report[c]["precision"]),
                "recall": float(report[c]["recall"]),
                "f1": float(report[c]["f1-score"]),
                "support": int(report[c]["support"]),
                "pretrained_baseline_top1": PRETRAINED_BASELINE_TOP1[c],
            }
            for c in config.CLASSES
        },
        "n_test": int(len(test_ex)),
    }
    (out_dir / config.EVAL_REPORT_NAME).write_text(
        json.dumps(report_out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # confusion matrix (csv: 행=true, 열=pred)
    with (out_dir / config.CONFUSION_NAME).open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["true\\pred", *config.CLASSES])
        for i, cls in enumerate(config.CLASSES):
            w.writerow([cls, *[int(x) for x in cm[i]]])

    _print_report(report_out, cm)
    return {"accuracy": accuracy, "macro_f1": macro_f1,
            "per_class": report_out["per_class"], "confusion": cm.tolist()}


def _print_report(report_out: dict, cm: np.ndarray) -> None:
    print(f"\n=== test 평가 (n={report_out['n_test']}) ===")
    print(f"accuracy={report_out['accuracy']:.4f}  macro_f1={report_out['macro_f1']:.4f}")
    print(f"\n{'class':<12}{'prec':>8}{'recall':>8}{'f1':>8}{'support':>9}{'base_top1':>11}")
    for c in config.CLASSES:
        pc = report_out["per_class"][c]
        print(f"{c:<12}{pc['precision']:>8.3f}{pc['recall']:>8.3f}{pc['f1']:>8.3f}"
              f"{pc['support']:>9}{pc['pretrained_baseline_top1']:>11.2f}")
    print("\nconfusion matrix (행=true, 열=pred):")
    print(f"{'':<12}" + "".join(f"{c:>12}" for c in config.CLASSES))
    for i, c in enumerate(config.CLASSES):
        print(f"{c:<12}" + "".join(f"{int(x):>12}" for x in cm[i]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="YAMNet 분류기 test 평가")
    parser.add_argument("--data-root", default=None)
    parser.add_argument("--out-dir", default=None)
    parser.add_argument("--checkpoint", default=None)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    final_dir = config.resolve_final_dir(args.data_root)
    out_dir = Path(args.out_dir).expanduser() if args.out_dir else config.model_dir()
    checkpoint = Path(args.checkpoint).expanduser() if args.checkpoint else None
    evaluate(final_dir, out_dir, checkpoint=checkpoint)
    return 0


if __name__ == "__main__":
    sys.exit(main())
