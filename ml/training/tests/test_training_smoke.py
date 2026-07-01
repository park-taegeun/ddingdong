"""Step 6 — 합성 더미 관통 (실데이터 EPERM 무관, repo 안에서 실행).

더미 01_clips → 파이프라인(run_all, auto-clean 포함) → 05 → 학습(head fit 2ep, 더미 backbone)
→ 체크포인트 → test 평가까지 전관통. + SpecAugment train-only + clean 가드 stale 방지 검증.

  python -m ml.training.tests.test_training_smoke        # 단독 실행
  pytest ml/training/tests/test_training_smoke.py        # pytest

★ 실제 YAMNet(hub) 대신 결정적 더미 임베딩 주입 → 오프라인/네트워크 없이 관통.
  (실학습은 학부생 로컬에서 hub YAMNet 으로 — README 참조.)
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np

from ml.pipeline import config as pipe
from ml.pipeline import run_all
from ml.pipeline.audio_io import iter_audio_files
from ml.pipeline.make_dummy import make_dummy_dataset
from ml.training import config, data, evaluate, model, train
from ml.training.spec_augment import SpecAugment

PER_CLASS = 20  # split 비율(0.7/0.15/0.15) × 클래스 3 → 각 split·클래스 ≥1 보장


def dummy_embed_fn(waveform: np.ndarray) -> np.ndarray:
    """결정적 더미 backbone: waveform → [EMBED_DIM]. 클래스 분리 신호 포함(학습 가능).

    zero-crossing rate + rms 를 앞 2차원에 실어 클래스(주파수)별로 분리 가능하게 함.
    나머지는 waveform 해시로 만든 작은 결정적 노이즈(재현성).
    """
    wav = np.asarray(waveform, dtype=np.float32)
    zcr = float(np.mean(np.abs(np.diff(np.sign(wav))) > 0)) if wav.size > 1 else 0.0
    rms = float(np.sqrt(np.mean(wav**2))) if wav.size else 0.0
    seed = int(abs(hash((round(zcr, 4), round(rms, 4)))) % (2**32))
    rng = np.random.default_rng(seed)
    emb = 0.01 * rng.standard_normal(config.EMBED_DIM).astype(np.float32)
    emb[0] = zcr * 10.0   # 클래스 판별 신호(스케일 확대)
    emb[1] = rms * 10.0
    return emb


def _count_final(paths) -> dict:
    return {
        split: {c: len(list(iter_audio_files(paths.split_dir(split) / c))) for c in config.CLASSES}
        for split in config.SPLITS
    }


def test_smoke_end_to_end(tmp_root: Path | None = None):
    ctx = tempfile.TemporaryDirectory() if tmp_root is None else None
    root = Path(ctx.name) if ctx else tmp_root
    try:
        # 0) 더미 01_clips → 파이프라인(clean 포함) → 05_final_dataset
        make_dummy_dataset(root, per_class=PER_CLASS, seed=1)
        paths = pipe.resolve_paths(root)
        run_all.run(paths, clean=True)
        final_dir = paths.final

        # 1) clean 가드: 재실행해도 05 개수 불변(stale 중첩 없음)
        counts1 = _count_final(paths)
        run_all.run(paths, clean=True)
        counts2 = _count_final(paths)
        assert counts1 == counts2, f"clean 가드 실패(stale 중첩): {counts1} → {counts2}"
        print(f"[clean 가드] 재실행 후 개수 불변 OK: {counts2}")

        # 1b) clean_final 안전 가드: final 이름 아니면 거부
        import dataclasses
        from ml.pipeline import assemble
        bad = dataclasses.replace(paths, final=paths.root / "not_final")
        try:
            assemble.clean_final(bad)
            raise AssertionError("clean_final 이 잘못된 final 경로를 거부하지 않음")
        except ValueError:
            print("[clean 가드] 비-05 경로 삭제 거부 OK")

        # 2) class_weight 자동 산출(실측 배분 기반, sklearn balanced)
        train_ex = data.list_examples(final_dir, "train")
        cw = data.compute_class_weights([y for _, y in train_ex])
        assert set(cw) == set(range(config.NUM_CLASSES)) and all(v > 0 for v in cw.values())
        print(f"[class_weight] {{{', '.join(f'{config.CLASSES[k]}:{v:.3f}' for k, v in cw.items())}}}")

        # 3) 학습(head fit 2 epoch, 더미 backbone 주입) → 체크포인트/history
        out_dir = root / "_run"
        summary = train.train(
            final_dir, out_dir, embed_fn=dummy_embed_fn, epochs=2,
            batch_size=8, export_inference=False, verbose=0,
        )
        assert Path(summary["checkpoint"]).exists(), "체크포인트 미저장"
        assert Path(summary["history"]).exists(), "history 미저장"
        assert summary["params"]["head_trainable"] > 0, "trainable head 파라미터 0"
        print(f"[학습] epochs_run={summary['epochs_run']} "
              f"head_trainable={summary['params']['head_trainable']} 체크포인트 OK")

        # 4) SpecAugment: train=True 마스킹 / inference=False 항등
        _assert_spec_augment_train_only()

        # 5) test 평가: accuracy + per-class + confusion
        rep = evaluate.evaluate(final_dir, out_dir, embed_fn=dummy_embed_fn)
        assert 0.0 <= rep["accuracy"] <= 1.0
        assert set(rep["per_class"]) == set(config.CLASSES)
        cm = np.array(rep["confusion"])
        assert cm.shape == (config.NUM_CLASSES, config.NUM_CLASSES)
        assert (out_dir / config.EVAL_REPORT_NAME).exists()
        assert (out_dir / config.CONFUSION_NAME).exists()
        print(f"[평가] accuracy={rep['accuracy']:.3f} macro_f1={rep['macro_f1']:.3f} confusion={cm.shape} OK")
        print("\n=== 합성 더미 관통 전체 통과 ===")
    finally:
        if ctx:
            ctx.cleanup()


def _assert_spec_augment_train_only():
    import tensorflow as tf

    layer = SpecAugment()
    x = tf.ones([4, 40, 64], dtype=tf.float32)  # [batch, time, mel]
    # inference: 항등
    y_infer = layer(x, training=False)
    assert bool(tf.reduce_all(tf.equal(y_infer, x))), "SpecAugment 가 inference 에서 항등이 아님"
    # train: 마스킹 발생(폭 0 확률 있어 여러 번 시도, 최소 1회 마스킹 확인)
    tf.keras.utils.set_random_seed(config.SEED)
    masked = False
    for _ in range(30):
        y_train = layer(x, training=True)
        if float(tf.reduce_min(y_train)) == 0.0 and float(tf.reduce_sum(y_train)) < float(tf.reduce_sum(x)):
            masked = True
            break
    assert masked, "SpecAugment 가 train 에서 마스킹하지 않음"
    print("[SpecAugment] inference=항등 / train=마스킹 OK")


if __name__ == "__main__":
    test_smoke_end_to_end()
