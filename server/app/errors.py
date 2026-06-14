"""통일된 JSON 에러 응답 (HTTP Status 8종 처리, 카테고리 6.1).

API 가 내보내는 상태 코드:
  200 OK              조회 성공 / idempotency 재요청 replay
  201 Created         detect / enrich 신규 처리 성공
  400 Bad Request     필수 필드 누락 / 잘못된 파라미터
  401 Unauthorized    Device / Dashboard 토큰 검증 실패
  404 Not Found       존재하지 않는 request_id / 라우트
  409 Conflict        이미 처리된 알림에 대한 enrich 재요청
  429 Too Many Requests  device 5초당 1회 초과 (Retry-After 헤더)
  500 Internal Server Error  예기치 못한 서버 오류
"""

from flask import jsonify
from werkzeug.exceptions import HTTPException


class ApiError(Exception):
    """라우트에서 raise 하는 의도된 에러. 통일된 JSON 으로 변환된다."""

    def __init__(self, status_code, code, message, headers=None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.headers = headers or {}


def _body(code, message):
    return {"error": {"code": code, "message": message}}


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def _handle_api_error(err):
        resp = jsonify(_body(err.code, err.message))
        resp.status_code = err.status_code
        for key, value in err.headers.items():  # 예: 429 의 Retry-After
            resp.headers[key] = value
        return resp

    @app.errorhandler(HTTPException)
    def _handle_http_exception(err):
        # 라우트 미존재(404)/메서드 불일치(405) 등도 JSON 으로 통일
        code = (err.name or "error").lower().replace(" ", "_")
        resp = jsonify(_body(code, err.description or err.name))
        resp.status_code = err.code or 500
        return resp

    @app.errorhandler(Exception)
    def _handle_unexpected(err):
        app.logger.exception("처리되지 않은 서버 오류")
        resp = jsonify(_body("internal_server_error", "서버 내부 오류가 발생했습니다."))
        resp.status_code = 500
        return resp
