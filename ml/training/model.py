"""모델 — frozen YAMNet backbone + trainable 분류 head (카테고리 4).

학습 효율/배치 안정성을 위해 2단계로 분리:
  - backbone(YAMNet, frozen): waveform → per-patch embedding → mean-pool [1024].
    학습 대상 아님(변수 optimizer 미등록) = 사실상 frozen 특징추출기.
  - head(trainable): Dense(128)+Dropout → Dense(3, softmax). 이 head 만 fit.
배포용은 build_inference_model 로 backbone+head 를 waveform→확률 하나로 합성.
"""

from __future__ import annotations

import logging

import numpy as np
import tensorflow as tf

from . import config

log = logging.getLogger("ml.training.model")


# --------------------------------------------------------------------------
# backbone (YAMNet) — hub 로드는 지연(오프라인/테스트에서 import 만으로 네트워크 X).
# --------------------------------------------------------------------------
def load_yamnet(handle: str = config.YAMNET_HUB_HANDLE):
    """tensorflow_hub 로 YAMNet SavedModel 로드. (막힘 시 §9 — 대체 모델 금지.)"""
    import tensorflow_hub as hub

    log.info("YAMNet 로드: %s", handle)
    return hub.load(handle)


def yamnet_embed_fn(yamnet):
    """YAMNet SavedModel → embed_fn(waveform[np.float32]) -> mean-pool 임베딩[1024].

    YAMNet 반환 = (scores, embeddings[num_patches,1024], log_mel). 클립 단위 분류라
    patch 축 평균 풀링으로 [1024] 고정 벡터 산출.
    """
    def _embed(waveform: np.ndarray) -> np.ndarray:
        wav = tf.convert_to_tensor(np.asarray(waveform, dtype=np.float32))
        _scores, embeddings, _logmel = yamnet(wav)
        return tf.reduce_mean(embeddings, axis=0).numpy().astype(np.float32)

    return _embed


# --------------------------------------------------------------------------
# head (trainable)
# --------------------------------------------------------------------------
def build_head(
    input_dim: int = config.EMBED_DIM,
    hidden_units: int = config.HEAD_HIDDEN_UNITS,
    dropout: float = config.HEAD_DROPOUT,
    num_classes: int = config.NUM_CLASSES,
    seed: int = config.SEED,
) -> tf.keras.Model:
    """임베딩[input_dim] → 클래스 확률[num_classes]. 이 부분만 학습."""
    init = tf.keras.initializers.GlorotUniform(seed=seed)
    inputs = tf.keras.Input(shape=(input_dim,), name="embedding")
    x = inputs
    if hidden_units and hidden_units > 0:
        x = tf.keras.layers.Dense(
            hidden_units, activation="relu", kernel_initializer=init, name="head_hidden"
        )(x)
        x = tf.keras.layers.Dropout(dropout, seed=seed, name="head_dropout")(x)
    outputs = tf.keras.layers.Dense(
        num_classes, activation="softmax", kernel_initializer=init, name="head_logits"
    )(x)
    return tf.keras.Model(inputs, outputs, name="yamnet_head")


def build_inference_model(head: tf.keras.Model, yamnet) -> tf.keras.Model:
    """배포용: waveform[num_samples] → 클래스 확률[num_classes] (backbone+head 합성).

    backbone 은 trainable=False 로 감싸 명시적으로 frozen. 단일 클립 추론용.
    """
    waveform = tf.keras.Input(shape=(None,), batch_size=1, name="waveform", dtype=tf.float32)

    def _embed(wf):
        wf = tf.squeeze(wf, axis=0)                  # [1, N] → [N]
        _scores, embeddings, _logmel = yamnet(wf)
        pooled = tf.reduce_mean(embeddings, axis=0)  # [1024]
        return tf.expand_dims(pooled, axis=0)        # [1, 1024]

    embedding = tf.keras.layers.Lambda(_embed, name="yamnet_backbone")(waveform)
    probs = head(embedding)
    model = tf.keras.Model(waveform, probs, name="yamnet_classifier")
    model.get_layer("yamnet_backbone").trainable = False
    return model


def param_summary(head: tf.keras.Model) -> dict[str, int]:
    """head 파라미터 수 요약(backbone 은 frozen — 학습 파라미터 0)."""
    trainable = int(sum(np.prod(w.shape) for w in head.trainable_weights))
    non_trainable = int(sum(np.prod(w.shape) for w in head.non_trainable_weights))
    return {"head_trainable": trainable, "head_non_trainable": non_trainable}
