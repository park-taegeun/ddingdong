"""Bearer Token 인증 미들웨어 (카테고리 6.1: Device / Dashboard 분리).

상수시간 비교(hmac.compare_digest)로 타이밍 공격을 막고,
토큰 미설정(빈 문자열)은 항상 실패시켜 설정 누락이 인증 우회로 이어지지 않게 한다.
"""

import hmac
from functools import wraps

from flask import current_app, request

from .errors import ApiError


def _extract_bearer():
    header = request.headers.get("Authorization", "")
    prefix = "Bearer "
    if not header.startswith(prefix):
        return None
    return header[len(prefix):].strip()


def _require_token(config_key):
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            token = _extract_bearer()
            expected = current_app.config.get(config_key) or ""
            # expected 가 빈 문자열이면(토큰 미설정) compare_digest 결과와 무관하게 차단
            if not expected or not token or not hmac.compare_digest(token, expected):
                raise ApiError(401, "unauthorized", "유효하지 않은 인증 토큰입니다.")
            return view(*args, **kwargs)

        return wrapper

    return decorator


# ESP32 전용 / 대시보드 전용 데코레이터
device_auth = _require_token("DEVICE_TOKEN")
dashboard_auth = _require_token("DASHBOARD_TOKEN")
