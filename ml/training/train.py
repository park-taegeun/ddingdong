"""학습 루프 (Step 3) — head fine-tuning + class_weight 자동 + early stopping + 체크포인트.

  python -m ml.training.train                       # DDINGDONG_DATA_ROOT env 사용
  python -m ml.training.train --data-root "..."     # 05_final_dataset 상위 경로

frozen YAMNet 임베딩 위에서 head 만 학습. class_weight 는 실측 train 배분에서 자동 산출.
best val_loss 체크포인트 + fit history(json) 저장. 실데이터는 학부생 로컬(EPERM).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np

from . import config, data, model

log = logging.getLogger("ml.training.train")


def _macro_f1_callback(val_ds, y_val):
    """val set 매 epoch macro-F1 을 sklearn 으로 계산해 history 에 기록하는 콜백."""
    import tensorflow as tf
    from sklearn.metrics import f1_score

    class _MacroF1(tf.keras.callbacks.Callback):
        def on_epoch_end(self, epoch, logs=None):
            logs = logs if logs is not None else {}
            probs = self.model.predict(val_ds, verbose=0)
            y_pred = np.argmax(probs, axis=1)
            logs["val_macro_f1"] = float(
                f1_score(y_val, y_pred, average="macro", zero_division=0)
            )

    return _MacroF1()


def train(
    final_dir: Path,
    out_dir: Path,
    *,
    embed_fn=None,
    yamnet_handle: str = config.YAMNET_HUB_HANDLE,
    epochs: int = config.EPOCHS,
    batch_size: int = config.BATCH_SIZE,
    export_inference: bool = True,
    verbose: int = 1,
) -> dict:
    """head 학습 후 산출물(체크포인트/history/labels) 저장. 반환: 요약 dict.

    embed_fn 미지정 → hub YAMNet 로드해 임베딩 함수 구성(실학습). 테스트는 더미 주입.
    """
    import tensorflow as tf

    tf.keras.utils.set_random_seed(config.SEED)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) 인덱싱 + class_weight(실측 자동 산출)
    train_ex = data.list_examples(final_dir, "train")
    val_ex = data.list_examples(final_dir, "val")
    y_train = [y for _, y in train_ex]
    y_val = [y for _, y in val_ex]
    class_weights = data.compute_class_weights(y_train)
    log.info("train=%d val=%d | class_weight=%s", len(train_ex), len(val_ex),
             {config.CLASSES[k]: round(v, 3) for k, v in class_weights.items()})

    # 2) backbone(embed_fn)
    yamnet = None
    if embed_fn is None:
        yamnet = model.load_yamnet(yamnet_handle)
        embed_fn = model.yamnet_embed_fn(yamnet)

    # 3) 데이터셋 (train 만 shuffle, val 은 증강·셔플 없음)
    train_ds = data.make_embedding_dataset(train_ex, embed_fn, training=True, batch_size=batch_size)
    val_ds = data.make_embedding_dataset(val_ex, embed_fn, training=False, batch_size=batch_size)

    # 4) head + compile (sparse CE + accuracy; macro-F1 은 콜백으로 history 기록)
    head = model.build_head()
    head.compile(
        optimizer=tf.keras.optimizers.Adam(config.LEARNING_RATE),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(),
        metrics=[tf.keras.metrics.SparseCategoricalAccuracy(name="accuracy")],
    )
    params = model.param_summary(head)
    log.info("head params: trainable=%(head_trainable)d non_trainable=%(head_non_trainable)d", params)

    ckpt_path = out_dir / config.CHECKPOINT_NAME
    callbacks = [
        tf.keras.callbacks.ModelCheckpoint(
            str(ckpt_path), monitor="val_loss", save_best_only=True, verbose=verbose
        ),
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss", patience=config.EARLY_STOP_PATIENCE,
            restore_best_weights=True, verbose=verbose,
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss", factor=config.REDUCE_LR_FACTOR,
            patience=config.REDUCE_LR_PATIENCE, verbose=verbose,
        ),
        tf.keras.callbacks.TerminateOnNaN(),  # NaN loss 시 임의 진행 말고 즉시 중단(§9)
        _macro_f1_callback(val_ds, y_val),
    ]

    # 5) fit
    history = head.fit(
        train_ds, validation_data=val_ds, epochs=epochs,
        class_weight=class_weights, callbacks=callbacks, verbose=verbose,
    )

    # 6) 산출물 저장 (history / labels / 추론 모델)
    hist_path = out_dir / config.HISTORY_NAME
    hist_path.write_text(
        json.dumps({k: [float(x) for x in v] for k, v in history.history.items()},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    labels_path = out_dir / config.LABELS_NAME
    labels_path.write_text(
        json.dumps({"classes": list(config.CLASSES),
                    "index": {c: i for i, c in enumerate(config.CLASSES)}},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if export_inference and yamnet is not None:
        # backbone(hub SavedModel)+head 합성 그래프는 SavedModel 로 내보내는 게 견고
        # (.keras 의 Lambda 직렬화 제약 회피). 이 경로는 실 YAMNet 로 학부생 런타임에서 검증.
        infer = model.build_inference_model(head, yamnet)
        export_dir = out_dir / "inference_savedmodel"
        tf.saved_model.save(infer, str(export_dir))
        log.info("추론 SavedModel 저장 → %s", export_dir)

    log.info("체크포인트 → %s | history → %s", ckpt_path, hist_path)
    return {
        "checkpoint": str(ckpt_path),
        "history": str(hist_path),
        "labels": str(labels_path),
        "class_weights": class_weights,
        "params": params,
        "epochs_run": len(history.history.get("loss", [])),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="YAMNet head fine-tuning")
    parser.add_argument("--data-root", default=None, help="05_final_dataset 상위(미지정=env)")
    parser.add_argument("--out-dir", default=None, help="산출물 경로(미지정=config.model_dir)")
    parser.add_argument("--epochs", type=int, default=config.EPOCHS)
    parser.add_argument("--batch-size", type=int, default=config.BATCH_SIZE)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    final_dir = config.resolve_final_dir(args.data_root)
    out_dir = Path(args.out_dir).expanduser() if args.out_dir else config.model_dir()
    summary = train(final_dir, out_dir, epochs=args.epochs, batch_size=args.batch_size)
    print("\n=== 학습 완료 ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
