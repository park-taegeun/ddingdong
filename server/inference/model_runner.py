"""SavedModel lazy-load 추론 러너.

★ TensorFlow import 는 **모듈 import 시점이 아니라 `ModelRunner` 인스턴스화 시점**에만
  일어난다(lazy). 라이브 서버가 이 모듈을 실수로 import 해도 TF(수백 MB)가 로드되지
  않도록 하기 위함(§2 데모 보호). model_path 주입식 — 더미/실모델 교체 가능.

시그니처(카테고리 33.2): 입력 waveform (1, None) float32 → 출력 (1, 3) float32.
라벨 순서 = CLASSES 상속(doorbell=0 / knock=1 / fire_alarm=2).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .constants import NUM_CLASSES


class ModelRunner:
    """SavedModel 을 lazy-load 하여 waveform → (1, 3) 확률을 반환하는 러너."""

    def __init__(self, model_path: str) -> None:
        # ── lazy import: 이 줄이 실행되는 시점(인스턴스화)에만 TF 로드 ──
        import tensorflow as tf  # noqa: PLC0415 (의도적 지연 import)

        self._tf = tf
        try:
            self._model: Any = tf.saved_model.load(model_path)
        except Exception as exc:  # noqa: BLE001 (경로/포맷 오류를 명확한 메시지로 승격)
            raise RuntimeError(f"SavedModel 로드 실패: {model_path!r} ({exc})") from exc

        if "serving_default" not in self._model.signatures:
            raise RuntimeError(
                f"serving_default 시그니처 없음: {model_path!r} "
                f"(존재 시그니처={list(self._model.signatures.keys())})"
            )
        self._infer: Any = self._model.signatures["serving_default"]
        # 입력 인자명은 export 방식마다 다름(waveform / keras_tensor 등) → introspect
        structured_inputs = self._infer.structured_input_signature[1]
        self._input_key: str = next(iter(structured_inputs.keys()))

    def predict(self, waveform: np.ndarray) -> np.ndarray:
        """waveform (1, N) float32 → (1, 3) float32 확률(softmax, sum≈1).

        Raises:
            ValueError: 출력 shape 가 계약 (1, 3) 이 아닐 때(시그니처 계약 위반).
        """
        tf = self._tf
        x = tf.convert_to_tensor(waveform, dtype=tf.float32)
        outputs = self._infer(**{self._input_key: x})
        # 시그니처 반환은 dict{name: tensor} — 단일 출력이므로 첫 값 추출
        scores_tensor = next(iter(outputs.values()))
        scores: np.ndarray = scores_tensor.numpy()
        if scores.shape != (1, NUM_CLASSES):
            raise ValueError(
                f"출력 shape 계약 위반: {scores.shape} != (1, {NUM_CLASSES}) "
                "(카테고리 33.2 서빙 시그니처)."
            )
        return scores
