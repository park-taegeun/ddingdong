"""초인종 등록 API — 상태 조회 · 수집 시작 · 해제 (Dashboard Token 전용).

저장 층은 registration.py. commit 은 여기 각 엔드포인트가 한 번만 한다.
"""

from flask import Blueprint, jsonify, request

from . import registration
from .auth import dashboard_auth
from .constants import (
    REGISTRATION_EXPIRES_MAX_SECONDS,
    REGISTRATION_GUARD_MIN,
    REGISTRATION_TARGET_COUNT_MAX,
)
from .errors import ApiError
from .extensions import db
from .utils import utc_now

bp = Blueprint("registration", __name__, url_prefix="/api/v1/registration")

# start 본문 키 → 상한. 두 키 모두 필수, 기본값 없음.
_START_LIMITS = {
    "target_count": REGISTRATION_TARGET_COUNT_MAX,
    "expires_in_seconds": REGISTRATION_EXPIRES_MAX_SECONDS,
}


@bp.get("")
@dashboard_auth
def get_status():
    return jsonify(registration.status(utc_now())), 200


@bp.post("/start")
@dashboard_auth
def start():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ApiError(400, "bad_request", "본문은 JSON 객체여야 합니다.")
    missing = sorted(_START_LIMITS.keys() - body.keys())
    unknown = sorted(body.keys() - _START_LIMITS.keys())
    if missing or unknown:
        raise ApiError(
            400, "bad_request", f"본문 키 불일치 (누락: {missing}, 모르는 키: {unknown})."
        )
    for key, upper in _START_LIMITS.items():
        value = body[key]
        # type() 비교 = bool(int 의 하위형) · float 거부
        if type(value) is not int or not REGISTRATION_GUARD_MIN <= value <= upper:
            raise ApiError(
                400,
                "bad_request",
                f"{key} 는 {REGISTRATION_GUARD_MIN}~{upper} 정수여야 합니다.",
            )

    now = utc_now()
    try:
        registration.start(body["target_count"], body["expires_in_seconds"], now)
    except registration.RegistrationConflict as exc:
        raise ApiError(
            409,
            "conflict",
            f"이미 등록이 진행 중이거나 완료된 상태입니다 (state={exc.state}). 먼저 해제하세요.",
        ) from exc
    db.session.commit()
    return jsonify(registration.status(now)), 201


@bp.delete("")
@dashboard_auth
def clear():
    registration.clear()
    db.session.commit()
    return jsonify(registration.status(utc_now())), 200
