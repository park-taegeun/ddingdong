"""SpecAugment — 로그멜 스펙트로그램 시간·주파수 마스킹 (카테고리 5).

★ 학습 시점(on-the-fly) 적용, **train 배치에만**. Keras 의 `training` 플래그를 그대로
  존중하므로 val/test(=inference) 에서는 자동으로 항등(identity) — 마스킹 0.
  (decisions.md 카테고리 5: freq_mask=10 / time_mask=5. val/test 절대 미적용.)

입력 텐서 규격: [batch, time, mel] 로그멜. 마스크 폭은 [0, param] 균등 랜덤.
마스크 값은 0(로그멜에서 무음 근사) — Park et al. 2019 의 기본과 동일.
"""

from __future__ import annotations

import tensorflow as tf

from . import config


class SpecAugment(tf.keras.layers.Layer):
    """train 배치에만 시간/주파수 마스킹을 거는 SpecAugment 레이어.

    val/test 에서는 Keras `training=False` 경로로 입력을 그대로 통과(항등).
    """

    def __init__(
        self,
        freq_mask_param: int = config.SPECAUG_FREQ_MASK_PARAM,
        time_mask_param: int = config.SPECAUG_TIME_MASK_PARAM,
        n_freq_masks: int = config.SPECAUG_N_FREQ_MASKS,
        n_time_masks: int = config.SPECAUG_N_TIME_MASKS,
        mask_value: float = 0.0,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.freq_mask_param = int(freq_mask_param)
        self.time_mask_param = int(time_mask_param)
        self.n_freq_masks = int(n_freq_masks)
        self.n_time_masks = int(n_time_masks)
        self.mask_value = float(mask_value)

    def _axis_mask(self, x: tf.Tensor, axis: int, param: int) -> tf.Tensor:
        """axis(1=time, 2=freq) 방향으로 폭 [0,param] 랜덤 구간 하나를 마스킹."""
        length = tf.shape(x)[axis]
        # 마스크 폭 f ∈ [0, min(param, length)] — 축이 param 보다 짧아도 안전.
        cap = tf.minimum(param, length)
        f = tf.random.uniform([], maxval=cap + 1, dtype=tf.int32)
        # 시작 위치 f0 ∈ [0, length - f]
        f0 = tf.random.uniform([], maxval=tf.maximum(length - f, 1), dtype=tf.int32)
        idx = tf.range(length)
        keep = tf.logical_or(idx < f0, idx >= f0 + f)  # True = 보존
        keep = tf.cast(keep, x.dtype)
        # 브로드캐스트용 shape: 해당 축만 length, 나머지는 1
        shape = [1, 1, 1]
        shape[axis] = -1
        keep = tf.reshape(keep, shape)
        masked_value = tf.cast(self.mask_value, x.dtype)
        return x * keep + masked_value * (1.0 - keep)

    def call(self, inputs: tf.Tensor, training: bool | None = None) -> tf.Tensor:
        # training 이 None 이면 Keras 가 학습/추론 컨텍스트로 채워줌. 추론이면 항등.
        if not training:
            return inputs
        x = inputs
        for _ in range(self.n_time_masks):
            x = self._axis_mask(x, axis=1, param=self.time_mask_param)
        for _ in range(self.n_freq_masks):
            x = self._axis_mask(x, axis=2, param=self.freq_mask_param)
        return x

    def get_config(self) -> dict:
        cfg = super().get_config()
        cfg.update(
            freq_mask_param=self.freq_mask_param,
            time_mask_param=self.time_mask_param,
            n_freq_masks=self.n_freq_masks,
            n_time_masks=self.n_time_masks,
            mask_value=self.mask_value,
        )
        return cfg
