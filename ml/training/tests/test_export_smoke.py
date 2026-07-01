"""Step 5 회귀 가드 — best.keras + (더미)YAMNet → 서빙 SavedModel export 관통.

frozen backbone(YAMNet)이 Lambda 클로저로 캡처되면 tf.saved_model.save 는 'untracked
resource' 로 실패한다. 이 테스트는 (1) 그 실패를 재현하고 (2) export_savedmodel() 의
model.export() 경로가 성공 + 재로드 + 서빙 시그니처 추론까지 되는지 고정한다.

실 YAMNet/실데이터 없이(EPERM·네트워크 무관) 결정적 더미 backbone 을 주입해 관통한다.

  python -m ml.training.tests.test_export_smoke
  pytest ml/training/tests/test_export_smoke.py
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import tensorflow as tf

from ml.training import config, export, model


class _DummyYamnet(tf.Module):
    """hub YAMNet 대역: waveform → (scores, embeddings[T,EMBED_DIM], logmel), 변수 보유."""

    def __init__(self, dim: int = config.EMBED_DIM):
        super().__init__()
        self.proj = tf.Variable(
            tf.random.normal([1, dim], seed=config.SEED), trainable=False, name="proj"
        )

    @tf.function(input_signature=[tf.TensorSpec([None], tf.float32)])
    def __call__(self, waveform):
        n = tf.shape(waveform)[0]
        num_patches = tf.maximum(n // 100, 1)
        embeddings = tf.ones([num_patches, 1]) * self.proj        # [T, EMBED_DIM]
        scores = tf.zeros([num_patches, 521])
        logmel = tf.zeros([num_patches, config.MEL_BANDS])
        return scores, embeddings, logmel


def _load_dummy_yamnet(work: Path):
    """save→load 왕복으로 hub.load() 처럼 '원시 trackable SavedModel' 을 만든다."""
    p = work / "dummy_yamnet"
    tf.saved_model.save(_DummyYamnet(), str(p))
    return tf.saved_model.load(str(p))


def _make_best_keras(work: Path) -> Path:
    """학습 산출물(best.keras=head)만 있는 상태를 모사."""
    head = model.build_head()
    ckpt = work / config.CHECKPOINT_NAME
    head.save(str(ckpt))
    return ckpt


def test_untracked_resource_reproduces_then_export_fixes():
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        yamnet = _load_dummy_yamnet(work)
        ckpt = _make_best_keras(work)

        # (1) 버그 재현: 원시 tf.saved_model.save 는 미추적 리소스로 실패해야 한다.
        head = tf.keras.models.load_model(str(ckpt))
        infer = model.build_inference_model(head, yamnet)
        raised = False
        try:
            tf.saved_model.save(infer, str(work / "raw_fail"))
        except (AssertionError, ValueError) as e:
            raised = "untracked" in str(e).lower() or "resource" in str(e).lower()
        assert raised, "전제 미재현: tf.saved_model.save 가 미추적 리소스로 실패하지 않음"

        # (2) 수정 경로: export_savedmodel(model.export) 은 성공해야 한다.
        summary = export.export_savedmodel(work, checkpoint=ckpt, yamnet=yamnet)
        out = Path(summary["savedmodel"])
        assert out.exists() and (out / "saved_model.pb").exists(), "SavedModel 미생성"
        assert summary["classes"] == list(config.CLASSES), "라벨 순서(SSoT) 불일치"

        # (3) 재로드 + 서빙 시그니처 추론: [1, NUM_CLASSES] softmax.
        loaded = tf.saved_model.load(str(out))
        sig = loaded.signatures["serving_default"]
        wav = tf.constant(np.random.randn(1, config.SAMPLE_RATE).astype(np.float32))
        res = sig(wav)
        probs = list(res.values())[0].numpy()
        assert probs.shape == (1, config.NUM_CLASSES), f"출력 shape {probs.shape}"
        assert abs(float(probs.sum()) - 1.0) < 1e-4, f"softmax 합 {probs.sum()}"
        print(
            f"[export] 재현+수정 OK | classes={summary['classes']} "
            f"| serving out={probs.shape} sum≈{float(probs.sum()):.4f}"
        )


if __name__ == "__main__":
    test_untracked_resource_reproduces_then_export_fixes()
    print("=== export 관통 전체 통과 ===")
