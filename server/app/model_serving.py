"""실추론 모델 싱글턴 로더 + warmup (카테고리 6.2 서빙 3결정 (a) 싱글턴 1회 로드,
2026-07-29 b-1 웹프로세스 상주 확정).

env 게이트: DDINGDONG_MODEL_PATH 미설정 → 로드 스킵(mock 폴백 신호, CI/문서환경 무영향).
설정됐는데 TensorFlow 가 없으면 조용히 mock 으로 내려가지 않고 fail-fast(명확한 에러로
앱 기동 중단) — 실추론을 명시적으로 요청한 설정 오류를 숨기지 않기 위함.

warmup: app factory 기동 시점에 모델을 로드하고 더미 입력으로 워밍 추론을 1회 수행해,
콜드스타트(그래프 트레이싱 등)를 요청 경로 밖으로 이동시킨다. "제거"가 아니라 "이동" —
서버 기동 후 첫 예열까지 수 초 소요되므로 시연 전 예열이 필요하다
(콜드 ≈103ms vs 웜 ≈6.74ms, 카테고리 6.2).

gunicorn preload + COW 공유(b-1 확정)는 11주차 배포 노트로 defer — 여기선 flask 단일
프로세스 dev 환경에서 검증 가능한 "요청경로 밖 이동" 원리만 구현한다.
"""

import time

from .constants import PREDICTED_CLASSES

_runner = None
_mode = "mock"
_load_ms = None
_warmup_ms = None


def init_app(app):
    """app factory 에서 1회 호출. MODEL_PATH 미설정이면 즉시 반환(mock 모드 유지)."""
    global _runner, _mode, _load_ms, _warmup_ms

    model_path = app.config.get("MODEL_PATH") or ""
    if not model_path:
        app.logger.info("model_serving: DDINGDONG_MODEL_PATH 미설정 → mock 모드(로드 스킵)")
        return

    import numpy as np
    from inference.constants import SAMPLE_RATE
    from inference.model_runner import ModelRunner

    load_started = time.monotonic()
    try:
        runner = ModelRunner(model_path)
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            f"model_serving: DDINGDONG_MODEL_PATH={model_path!r} 가 설정되었으나 "
            "TensorFlow 가 설치되어 있지 않습니다(fail-fast). 실추론 모드는 TF 설치가 "
            "필요합니다 — mock 모드로 되돌리려면 DDINGDONG_MODEL_PATH 를 미설정하세요."
        ) from exc
    load_ms = (time.monotonic() - load_started) * 1000

    # 더미 무음 입력(1초) 워밍 추론 1회 — 그래프 트레이싱 비용을 요청 경로 밖으로 이동
    dummy = np.zeros((1, SAMPLE_RATE), dtype=np.float32)
    warmup_started = time.monotonic()
    runner.predict(dummy)
    warmup_ms = (time.monotonic() - warmup_started) * 1000

    _runner, _load_ms, _warmup_ms, _mode = runner, load_ms, warmup_ms, "real"
    app.logger.info(
        "model_serving: 실추론 모드 진입 model_path=%s load_ms=%.1f warmup_ms=%.1f "
        "— 콜드스타트를 요청경로 밖으로 이동(제거 아님), 시연 전 예열 확인 필요",
        model_path,
        load_ms,
        warmup_ms,
    )


def is_real_mode():
    return _mode == "real" and _runner is not None


def predict(waveform):
    """(1, N) float32 waveform → (1, 3) float32 확률(softmax, sum≈1). real 모드에서만 호출."""
    return _runner.predict(waveform)


def scores_to_prediction(scores):
    """(1, 3) 확률 → (predicted_class, confidence, all_scores). mock_prediction 출력과 동형 키.

    라벨 순서 = PREDICTED_CLASSES(app.constants) — inference.constants.CLASSES 와 동일 순서
    상속(카테고리 33.2).
    """
    row = scores[0]
    idx = int(row.argmax())
    predicted_class = PREDICTED_CLASSES[idx]
    confidence = round(float(row[idx]), 2)
    all_scores = {c: round(float(row[i]), 2) for i, c in enumerate(PREDICTED_CLASSES)}
    return predicted_class, confidence, all_scores
