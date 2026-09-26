"""/detect 등록 계측 훅 — 수집 중이면 템플릿 저장, 등록 뒤면 거리 기록 (관측 전용).

발송 · 응답 · Notification · enrich_status 에 영향 0. 판정(알림 차단 · 수집 중 억제)은
후속 판정 PR 소관이고, 여기서는 거리를 재서 남기기만 한다.

★ 호출 위치 계약: routes.detect() 에서 카카오 1차 발송 **뒤**, 단일 db.session.commit()
  **앞**. 카카오 계층은 토큰 갱신 때 commit 하며 kakao._assert_commit_is_safe() 가
  세션의 미커밋 객체(flush 뒤 계류분 포함)를 보면 RuntimeError 를 낸다 — 이 훅이 발송
  앞에서 템플릿을 add 하면 발송 경로가 5xx 가 된다.
★ 이 모듈은 commit · 명시적 flush 를 하지 않는다(저장 층과 같은 규칙).
★ 훅 안 예외는 전부 잡아 ERROR 로그로 남기고 쓰기 없이 돌아간다 — 계측이 알림을 막으면
  안 된다. 그래서 실패할 수 있는 계산(디코드 · 특징 · DTW)을 전부 끝낸 뒤에만 add 한다.
"""

import time

from flask import current_app

from inference.audio_decode import decode_pcm16

from . import registration
from .constants import REGISTRATION_STATE_COLLECTING, REGISTRATION_STATE_REGISTERED
from .extensions import db
from .models import RegistrationMatch
from .sound_match import dtw_cosine_distance, waveform_to_template


def observe(pcm, waveform, client_request_id, predicted_class, now):
    """pcm = 원본 int16 PCM bytes, waveform = decode_pcm16(pcm) 결과 (1, N). 반환값 없음."""
    try:
        _observe(pcm, waveform, client_request_id, predicted_class, now)
    except Exception:
        current_app.logger.exception(
            "registration observe failed (detect continues): client_request_id=%s",
            client_request_id,
        )


def _observe(pcm, waveform, client_request_id, predicted_class, now):
    state, row = registration.current(now)

    if state == REGISTRATION_STATE_COLLECTING:
        # 수락 조건 없음(클래스 · 신뢰도 · ToF 무관) — 조건은 재학습 뒤 결정한다.
        result = registration.add_template(pcm, client_request_id, now)
        current_app.logger.info(
            "registration template: result=%s client_request_id=%s", result, client_request_id
        )
        return
    if state != REGISTRATION_STATE_REGISTERED:
        return

    stored = registration.load_registered_templates()
    started = time.monotonic()
    query = waveform_to_template(waveform[0])
    distances = [
        dtw_cosine_distance(waveform_to_template(decode_pcm16(p)[0]), query) for p in stored
    ]
    compare_ms = (time.monotonic() - started) * 1000

    # 계산이 전부 끝난 뒤에만 쓴다(위에서 예외가 나면 여기 오지 않는다).
    db.session.add(
        RegistrationMatch(
            client_request_id=client_request_id,
            registration_id=row.registration_id,
            predicted_class=predicted_class,
            template_count=len(distances),
            distances=distances,
            min_distance=min(distances),
            mean_distance=sum(distances) / len(distances),
            compare_ms=compare_ms,
            created_at=now,
        )
    )
    current_app.logger.info(
        "registration match: client_request_id=%s predicted_class=%s min=%.4f compare_ms=%.1f",
        client_request_id,
        predicted_class,
        min(distances),
        compare_ms,
    )
