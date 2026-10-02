"""/detect 등록 판정 + 계측 — 수집 중 억제 · 소리 불일치 차단 · 템플릿 저장 · 거리 기록.

두 단계로 나뉜다(같은 스냅샷 · 같은 거리 리스트를 공유):
  before_send() — 정책 뒤 · **카카오 앞**. 상태 조회 1회 + (판정 경로면) 거리 계산 + 판정.
                  읽기만 한다(SELECT) — 세션에 add 0.
  record()      — **카카오 뒤** · 단일 commit 앞. 템플릿 · 측정 행 · 실패 행 add 전부.

★ 위치 계약: 카카오 계층은 토큰 갱신 때 commit 하며 kakao._assert_commit_is_safe() 가
  세션의 미커밋 객체(flush 뒤 계류분 포함)를 보면 RuntimeError 를 낸다 — add 를 카카오
  앞으로 옮기면 발송 경로가 5xx 가 된다. 읽기만 한 객체는 가드에 걸리지 않는다.
★ 이 모듈은 commit · 명시적 flush 를 하지 않는다(저장 층과 같은 규칙).
★ 판정 대상 = 예측 doorbell + 정책 결과 「발송」. 그 밖의 클래스 · 미발송 건은 현행 그대로.
★ 계산 실패(예외 · 저장 템플릿 0개)는 막지 않는다(fail-open, 명시 정책 — constants.py
  REGISTRATION_MATCH_MAX_DISTANCE 위 주석): 발송 + ERROR 로그 + registration_failures 행.
"""

import time
from dataclasses import dataclass

from flask import current_app

from inference.audio_decode import decode_pcm16

from . import registration
from .constants import (
    CONFIDENCE_THRESHOLD,
    REGISTRATION_MATCH_MAX_DISTANCE,
    REGISTRATION_STATE_COLLECTING,
    REGISTRATION_STATE_REGISTERED,
    SKIP_REASON_REGISTRATION_COLLECTING,
    SKIP_REASON_REGISTRATION_MISMATCH,
)
from .extensions import db
from .models import RegistrationFailure, RegistrationMatch
from .sound_match import dtw_cosine_distance, waveform_to_template

_ERROR_TEXT_MAX = 120  # 예외 타입 + 메시지 앞부분만 남긴다


@dataclass
class Snapshot:
    """요청 1건의 등록 상태 스냅샷. before_send 가 만들고 record 가 그대로 쓴다."""

    judged: bool  # 판정 경로(doorbell + 정책 발송)인가
    state: str | None = None  # None = 상태 조회 실패
    registration_id: str | None = None
    distances: list | None = None  # 계산은 요청당 최대 1회 — 판정과 측정 행이 같은 리스트
    compare_ms: float | None = None
    error: str | None = None
    skip_reason: str | None = None


def judge(state, predicted_class, policy_sends, min_distance):
    """순수 함수 → 등록 skip_reason 또는 None(정책 결과 그대로).

    min_distance None = 계산 실패 → None(막지 않음, fail-open 명시 정책).
    """
    if not policy_sends or predicted_class != "doorbell":
        return None
    if state == REGISTRATION_STATE_COLLECTING:
        return SKIP_REASON_REGISTRATION_COLLECTING
    if (
        state == REGISTRATION_STATE_REGISTERED
        and min_distance is not None
        and min_distance > REGISTRATION_MATCH_MAX_DISTANCE
    ):
        return SKIP_REASON_REGISTRATION_MISMATCH
    return None


def accepts_template(predicted_class, confidence):
    """순수 함수 — 수집 중 템플릿 수락 조건: doorbell + 알림 신뢰도 게이트 통과(ToF 무관).

    비교는 _apply_prediction_policy 와 같은 값 · 같은 식(confidence 는 이미 반올림 2자리).
    """
    return predicted_class == "doorbell" and not confidence < CONFIDENCE_THRESHOLD


def before_send(waveform, client_request_id, pred, now):
    """카카오 앞. 예외를 밖으로 내지 않는다 — 실패는 snap.error 에 담고 판정은 None."""
    snap = Snapshot(judged=pred["primary_sent"] and pred["predicted_class"] == "doorbell")
    try:
        snap.state, row = registration.current(now)
        snap.registration_id = row.registration_id if row is not None else None
    except Exception as exc:
        _fail(snap, exc, client_request_id)
        return snap
    if snap.judged and snap.state == REGISTRATION_STATE_REGISTERED:
        _measure(snap, waveform, client_request_id)
    snap.skip_reason = judge(
        snap.state,
        pred["predicted_class"],
        pred["primary_sent"],
        min(snap.distances) if snap.distances else None,
    )
    return snap


def record(pcm, waveform, snap, client_request_id, pred, now):
    """카카오 뒤 · commit 앞. pcm = 원본 int16 PCM bytes, waveform = decode_pcm16(pcm)."""
    try:
        _record(pcm, waveform, snap, client_request_id, pred, now)
    except Exception:
        current_app.logger.exception(
            "registration record failed (detect continues): client_request_id=%s",
            client_request_id,
        )


def _record(pcm, waveform, snap, client_request_id, pred, now):
    if snap.state == REGISTRATION_STATE_COLLECTING:
        if accepts_template(pred["predicted_class"], pred["confidence"]):
            result = registration.add_template(pcm, client_request_id, now)
            current_app.logger.info(
                "registration template: result=%s client_request_id=%s", result, client_request_id
            )
    elif snap.state == REGISTRATION_STATE_REGISTERED and snap.distances is None and snap.error is None:
        # 판정 경로가 아니었던 건 — 측정 행용 거리를 여기서 1회 잰다(1차 발송 지연 0).
        _measure(snap, waveform, client_request_id)

    # 계산이 전부 끝난 뒤에만 쓴다.
    if snap.distances:
        db.session.add(
            RegistrationMatch(
                client_request_id=client_request_id,
                registration_id=snap.registration_id,
                predicted_class=pred["predicted_class"],
                template_count=len(snap.distances),
                distances=snap.distances,
                min_distance=min(snap.distances),
                mean_distance=sum(snap.distances) / len(snap.distances),
                compare_ms=snap.compare_ms,
                created_at=now,
            )
        )
        current_app.logger.info(
            "registration match: client_request_id=%s predicted_class=%s min=%.4f compare_ms=%.1f",
            client_request_id,
            pred["predicted_class"],
            min(snap.distances),
            snap.compare_ms,
        )
    if snap.error is not None:
        db.session.add(
            RegistrationFailure(
                client_request_id=client_request_id,
                registration_id=snap.registration_id,
                predicted_class=pred["predicted_class"],
                judged=snap.judged,
                error=snap.error,
                created_at=now,
            )
        )


def _measure(snap, waveform, client_request_id):
    """저장 템플릿마다 거리 → snap.distances. 실패 · 템플릿 0개면 snap.error."""
    try:
        stored = registration.load_registered_templates()
        if not stored:
            raise LookupError("no_templates")
        started = time.monotonic()
        query = waveform_to_template(waveform[0])
        distances = [
            dtw_cosine_distance(waveform_to_template(decode_pcm16(p)[0]), query) for p in stored
        ]
        snap.compare_ms = (time.monotonic() - started) * 1000
        snap.distances = distances
    except Exception as exc:
        _fail(snap, exc, client_request_id)


def _fail(snap, exc, client_request_id):
    snap.error = f"{type(exc).__name__}: {exc}"[:_ERROR_TEXT_MAX]
    current_app.logger.exception(
        "registration judgment input failed — %s: client_request_id=%s",
        "fail-open, sending as policy decided" if snap.judged else "measurement only",
        client_request_id,
    )
