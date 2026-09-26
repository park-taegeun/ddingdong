"""평가 (Step 4) — test set 최종 성능: accuracy + 클래스별 P/R/F1 + confusion matrix.

  python -m ml.training.evaluate --classes doorbell,knock,fire_alarm --out-dir ~/runs/r3
  (--out-dir = 학습된 run 폴더. 미지정이면 env DDINGDONG_MODEL_DIR, 둘 다 없으면 실패)

기준선(사전테스트 pre-trained YAMNet Top-1): doorbell≈30% / knock≈40% / fire_alarm≈20%.
transfer learning head 학습 후 이 대비 개선 여부를 확인하는 것이 목적.

`--data-root` 또는 `DDINGDONG_DATA_ROOT` 는 **필수** — 둘 다 없으면 기본값 fallback 없이
`ValueError`로 즉시 실패한다(PR #60, `ml.pipeline.config.resolve_data_root`).
클래스·인덱스는 run 폴더 labels.json 이 출처 — `--classes` 가 그와 다르면 거부.
eval_report.json · confusion_matrix.csv 가 이미 있으면 거부(덮어쓰기 0).
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
    classes,
    allowed: tuple[str, ...] = config.CLASSES,
    embed_fn=None,
    yamnet_handle: str = config.YAMNET_HUB_HANDLE,
    checkpoint: Path | None = None,
) -> dict:
    """test set 평가 후 리포트 저장. 반환: {accuracy, per_class, confusion}.

    out_dir = 학습된 run 폴더(labels.json · 체크포인트 필수). 리포트도 여기에 쓴다.
    """
    import tensorflow as tf
    from sklearn.metrics import classification_report, confusion_matrix

    classes = config.read_labels(out_dir, classes, allowed)
    config.refuse_existing(out_dir, (config.EVAL_REPORT_NAME, config.CONFUSION_NAME))
    ckpt = checkpoint or (out_dir / config.CHECKPOINT_NAME)
    if not ckpt.exists():
        raise FileNotFoundError(
            f"체크포인트 없음: {ckpt}\n  → 먼저 `python -m ml.training.train` 실행 필요."
        )
    head = tf.keras.models.load_model(str(ckpt))
    config.check_head(head, classes, ckpt)

    if embed_fn is None:
        yamnet = model.load_yamnet(yamnet_handle)
        embed_fn = model.yamnet_embed_fn(yamnet)

    test_ex = data.list_examples(final_dir, "test", classes)
    y_true = np.array([y for _, y in test_ex])
    test_ds = data.make_embedding_dataset(test_ex, embed_fn, training=False)

    probs = head.predict(test_ds, verbose=0)
    y_pred = np.argmax(probs, axis=1)

    labels_idx = list(range(len(classes)))
    report = classification_report(
        y_true, y_pred, labels=labels_idx, target_names=list(classes),
        output_dict=True, zero_division=0,
    )
    cm = confusion_matrix(y_true, y_pred, labels=labels_idx)
    accuracy = float(report["accuracy"])
    macro_f1 = float(report["macro avg"]["f1-score"])

    # 리포트 저장 (json) — 기준선이 없는 클래스(예: other)는 null
    report_out = {
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "per_class": {
            c: {
                "precision": float(report[c]["precision"]),
                "recall": float(report[c]["recall"]),
                "f1": float(report[c]["f1-score"]),
                "support": int(report[c]["support"]),
                "pretrained_baseline_top1": PRETRAINED_BASELINE_TOP1.get(c),
            }
            for c in classes
        },
        "n_test": int(len(test_ex)),
    }
    (out_dir / config.EVAL_REPORT_NAME).write_text(
        json.dumps(report_out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # confusion matrix (csv: 행=true, 열=pred)
    with (out_dir / config.CONFUSION_NAME).open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["true\\pred", *classes])
        for i, cls in enumerate(classes):
            w.writerow([cls, *[int(x) for x in cm[i]]])

    _print_report(report_out, cm, classes)
    return {"accuracy": accuracy, "macro_f1": macro_f1,
            "per_class": report_out["per_class"], "confusion": cm.tolist()}


def _print_report(report_out: dict, cm: np.ndarray, classes: tuple[str, ...]) -> None:
    print(f"\n=== test 평가 (n={report_out['n_test']}) ===")
    print(f"accuracy={report_out['accuracy']:.4f}  macro_f1={report_out['macro_f1']:.4f}")
    print(f"\n{'class':<12}{'prec':>8}{'recall':>8}{'f1':>8}{'support':>9}{'base_top1':>11}")
    for c in classes:
        pc = report_out["per_class"][c]
        base = pc["pretrained_baseline_top1"]
        print(f"{c:<12}{pc['precision']:>8.3f}{pc['recall']:>8.3f}{pc['f1']:>8.3f}"
              f"{pc['support']:>9}{'-' if base is None else f'{base:.2f}':>11}")
    print("\nconfusion matrix (행=true, 열=pred):")
    print(f"{'':<12}" + "".join(f"{c:>12}" for c in classes))
    for i, c in enumerate(classes):
        print(f"{c:<12}" + "".join(f"{int(x):>12}" for x in cm[i]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="YAMNet 분류기 test 평가")
    parser.add_argument("--data-root", default=None)
    parser.add_argument("--classes", required=True,
                        help="평가할 클래스(쉼표 구분) — run 폴더 labels.json 과 같아야 함")
    parser.add_argument("--out-dir", default=None,
                        help="학습된 run 폴더(미지정=env DDINGDONG_MODEL_DIR, 둘 다 없으면 실패)")
    parser.add_argument("--checkpoint", default=None)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    final_dir = config.resolve_final_dir(args.data_root)
    out_dir = config.resolve_run_dir(args.out_dir)
    checkpoint = Path(args.checkpoint).expanduser() if args.checkpoint else None
    evaluate(final_dir, out_dir, classes=args.classes, checkpoint=checkpoint)
    return 0


if __name__ == "__main__":
    sys.exit(main())
