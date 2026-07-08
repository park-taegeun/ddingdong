"""합성 더미 SavedModel 생성기 (실데이터·실 best.keras·실 YAMNet 불필요).

카테고리 33.2 서빙 시그니처와 **shape/dtype 만 일치**하는 random-init 스텁:
  입력 waveform (1, None) float32 → 출력 (1, 3) float32 softmax(sum≈1).
분류 성능은 무의미(random projection). 목적 = MCP 자기검증·CI 에서 서빙/벤치/계약
테스트의 **코드 경로**를 실 모델 없이 태우기 위함(§2 스코프 1층).

가변 길이(1, None) 안전: waveform 을 고정 5개 통계(mean/std/max/min/rms)로 pool 한 뒤
random dense(5→3) + softmax. 어떤 길이 입력도 (1, 3) 로 매핑.

실행(server/ 에서):  python3 -m inference.make_dummy_savedmodel --out-dir <경로>
"""

from __future__ import annotations

import argparse
import sys

import numpy as np

from .constants import NUM_CLASSES

_FEATURE_DIM = 5  # pool 통계 개수(mean/std/max/min/rms)


def build_dummy_savedmodel(out_dir: str, seed: int = 0) -> str:
    """random-init 더미 SavedModel 을 out_dir 에 저장하고 경로를 반환."""
    import tensorflow as tf  # lazy: 생성 시점에만 TF 로드

    rng = np.random.default_rng(seed)  # 결정적 가중치(재현 가능)
    w_np = rng.standard_normal((_FEATURE_DIM, NUM_CLASSES)).astype(np.float32)
    b_np = rng.standard_normal((NUM_CLASSES,)).astype(np.float32)

    class _DummyServing(tf.Module):
        def __init__(self) -> None:
            super().__init__()
            # tf.Variable 로 보유 → 객체 그래프에 tracked(untracked resource 회피)
            self.w = tf.Variable(w_np, trainable=False, name="proj_w")
            self.b = tf.Variable(b_np, trainable=False, name="proj_b")

        @tf.function(
            input_signature=[tf.TensorSpec([1, None], tf.float32, name="waveform")]
        )
        def serve(self, waveform: "tf.Tensor") -> dict[str, "tf.Tensor"]:
            # (1, None) → 고정 5통계 (1, 5). axis=1 reduction 이라 길이 무관.
            mean = tf.reduce_mean(waveform, axis=1)
            std = tf.math.reduce_std(waveform, axis=1)
            mx = tf.reduce_max(waveform, axis=1)
            mn = tf.reduce_min(waveform, axis=1)
            rms = tf.sqrt(tf.reduce_mean(tf.square(waveform), axis=1) + 1e-12)
            feat = tf.stack([mean, std, mx, mn, rms], axis=1)  # (1, 5)
            logits = tf.matmul(feat, self.w) + self.b          # (1, 3)
            probs = tf.nn.softmax(logits, axis=1)              # (1, 3), sum≈1
            return {"scores": probs}

    module = _DummyServing()
    tf.saved_model.save(
        module, out_dir, signatures={"serving_default": module.serve}
    )
    return out_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="합성 더미 SavedModel 생성기")
    parser.add_argument(
        "--out-dir", required=True, help="더미 SavedModel 저장 경로(디렉터리)"
    )
    parser.add_argument("--seed", type=int, default=0, help="가중치 시드(결정적)")
    args = parser.parse_args(argv)

    path = build_dummy_savedmodel(args.out_dir, seed=args.seed)
    print(f"더미 SavedModel 저장 → {path}")
    print("★ random-init 스텁 — 분류 성능 무의미(코드 경로 검증 전용).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
