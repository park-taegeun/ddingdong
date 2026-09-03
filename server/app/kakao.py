"""카카오 나에게 보내기(memo) 연동 — 토큰 계층 (카테고리 7).

토큰 실값은 env 부트스트랩 → DB(kakao_tokens 단일 행) 경로로만 흐른다.
로그에는 토큰을 남기지 않는다(마스킹도 하지 않는다 — 아예 찍지 않는다).

HTTP 는 표준 라이브러리 urllib 로 한다. 근거 = repo 에 기존 HTTP 클라이언트
사용처가 0건(requests/httpx 미설치, grep 확인)이라 "기존 관례를 따른다"가
성립하지 않고, 새 외부 의존성 추가를 피하는 쪽이 requirements.txt 최소 유지
방침과 맞기 때문이다.
"""

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import timedelta

from flask import current_app

from .constants import (
    KAKAO_HTTP_TIMEOUT_SECONDS,
    KAKAO_REFRESH_TOKEN_TTL,
    KAKAO_TOKEN_URL,
)
from .extensions import db
from .models import KakaoToken
from .utils import utc_now


class KakaoTokenError(RuntimeError):
    """토큰 확보 실패. 조용한 폴백 없이 호출부로 올려 fail-fast 시킨다.

    호출부(/detect)는 이 예외를 잡아 1차 알림을 미발송으로 기록할 뿐,
    요청 전체를 5xx 로 떨어뜨리지 않는다.
    """


def _assert_commit_is_safe():
    """이 모듈이 commit 할 때 함께 딸려갈 남의 변경이 세션에 없는지 확인한다.

    docstring 규약("Notification 생성 이전에만 호출")을 실행 시점에 강제하는 가드다.
    규약 위반은 발송 실패가 아니라 코딩 계약 위반이므로 KakaoTokenError 가 아닌
    RuntimeError 로 올린다 — 호출부의 `except KakaoTokenError` 에 잡혀 "카카오 발송
    실패"로 조용히 둔갑하면 버그가 숨는다.

    session.deleted 는 검사하지 않는다: 이 경로에서 삭제 pending 이 될 수 있는 것은
    TTL 만료된 IdempotencyKey 뿐이고(routes.detect), 만료 키를 조금 일찍 지우는 것은
    의미상 무해하다.
    """
    foreign = [
        obj
        for obj in list(db.session.new) + list(db.session.dirty)
        if not isinstance(obj, KakaoToken)
    ]
    if foreign:
        raise RuntimeError(
            "kakao.get_access_token() 은 세션에 미커밋 변경이 있는 지점에서 호출할 수 "
            f"없다(토큰 갱신 커밋에 딸려간다). 계류 중: {[type(o).__name__ for o in foreign]}"
        )


def _bootstrap(now_utc):
    """DB 에 행이 없을 때 env 값으로 단일 행을 만든다 (최초 1회, 커밋은 하지 않음)."""
    access_token = current_app.config.get("KAKAO_ACCESS_TOKEN", "")
    refresh_token = current_app.config.get("KAKAO_REFRESH_TOKEN", "")
    if not refresh_token:
        raise KakaoTokenError("KAKAO_REFRESH_TOKEN 미설정 — 토큰 부트스트랩 불가")

    row = KakaoToken(
        id=KakaoToken.SINGLETON_ID,
        access_token=access_token,
        refresh_token=refresh_token,
        # env 의 access 토큰이 언제 발급됐는지 서버는 알 수 없다. 남은 수명을 낙관하면
        # 이미 만료된 토큰으로 발송해 401 을 맞는다 → "만료"로 간주해 첫 사용에서
        # 반드시 갱신을 태운다. 갱신 응답의 expires_in 이 들어오는 순간부터 만료
        # 시각은 추정이 아니라 실값이 된다.
        access_expires_at=now_utc,
        # refresh 만료는 잔여 1개월 미만일 때만 갱신 응답이 알려주므로 지금은 알 수
        # 없다. 60일 상한으로 두되 이 값으로 발송을 막지는 않는다.
        # (판정 방법: 실제 만료는 갱신 호출 실패로 드러나고 fail-fast 로 처리된다.
        #  이 컬럼을 게이트로 쓰면 추정값 때문에 멀쩡한 토큰을 막을 수 있다.)
        refresh_expires_at=now_utc + KAKAO_REFRESH_TOKEN_TTL,
        updated_at=now_utc,
    )
    db.session.add(row)
    return row


def _refresh(row, now_utc):
    """refresh_token 으로 access 토큰을 재발급받아 행을 갱신하고 즉시 커밋한다.

    행 필드는 응답 파싱·검증을 모두 통과한 뒤에만 건드린다 → 실패 경로에서 이 행은
    dirty 상태가 되지 않고, 세션에 부분 변경이 남지 않는다.
    """
    rest_api_key = current_app.config.get("KAKAO_REST_API_KEY", "")
    client_secret = current_app.config.get("KAKAO_CLIENT_SECRET", "")
    if not rest_api_key:
        raise KakaoTokenError("KAKAO_REST_API_KEY 미설정 — 토큰 갱신 불가")
    if not client_secret:
        # 카카오는 REST API 키 발급 시 client secret 을 기본 활성화한다.
        # 빠뜨리면 갱신이 통째로 실패하므로 조용히 넘기지 않는다.
        raise KakaoTokenError("KAKAO_CLIENT_SECRET 미설정 — 토큰 갱신 불가")

    data = urllib.parse.urlencode(
        {
            "grant_type": "refresh_token",
            "client_id": rest_api_key,
            "refresh_token": row.refresh_token,
            "client_secret": client_secret,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        KAKAO_TOKEN_URL,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=KAKAO_HTTP_TIMEOUT_SECONDS) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # 에러 본문(error/error_description)을 그대로 로그에 싣지 않는다 — 요청 파라미터
        # 에코 가능성을 배제하기 위해 상태 코드만 올린다.
        raise KakaoTokenError(f"토큰 갱신 실패: HTTP {exc.code}") from exc
    except Exception as exc:  # URLError/timeout/JSON 파싱 — 원인 타입만 남긴다
        raise KakaoTokenError(f"토큰 갱신 실패: {type(exc).__name__}") from exc

    access_token = payload.get("access_token")
    expires_in = payload.get("expires_in")
    if not access_token or not isinstance(expires_in, int):
        raise KakaoTokenError("토큰 갱신 응답에 access_token/expires_in 이 없다")

    row.access_token = access_token
    row.access_expires_at = now_utc + timedelta(seconds=expires_in)

    # refresh_token 은 "잔여 수명 1개월 미만"일 때만 응답에 포함된다. 없을 때 기존
    # 값을 None/빈값으로 덮으면 갱신 경로가 통째로 죽으므로, 있을 때만 교체한다.
    new_refresh = payload.get("refresh_token")
    if new_refresh:
        row.refresh_token = new_refresh
        refresh_expires_in = payload.get("refresh_token_expires_in")
        if isinstance(refresh_expires_in, int):
            row.refresh_expires_at = now_utc + timedelta(seconds=refresh_expires_in)

    row.updated_at = now_utc
    db.session.commit()
    # 토큰 값은 찍지 않는다. 남은 수명(초)만 운영 확인용으로 남긴다.
    current_app.logger.info("kakao token refreshed: access_expires_in=%ds", expires_in)


def get_access_token():
    """유효한 access 토큰 문자열을 돌려준다. 만료 임박이면 갱신 후 돌려준다.

    실패 시 KakaoTokenError. 조용한 폴백(만료 토큰 그대로 반환) 없음.

    ★ 호출 위치 제약: 갱신 성공 시 이 함수가 db.session.commit() 한다. 아직 커밋되면
    안 되는 변경이 세션에 걸린 지점에서 부르면 그 변경까지 함께 커밋된다.
    /detect 에서는 Notification 생성 이전 지점에서만 호출한다.
    이 제약은 주석 규약이 아니라 _assert_commit_is_safe() 로 실행 시점에 강제된다.
    """
    _assert_commit_is_safe()

    now = utc_now()
    row = db.session.get(KakaoToken, KakaoToken.SINGLETON_ID)
    bootstrapped = row is None
    if bootstrapped:
        row = _bootstrap(now)

    if row.needs_refresh(now):
        try:
            _refresh(row, now)
        except KakaoTokenError:
            if bootstrapped:
                # 갱신이 실패하면 방금 만든 부트스트랩 행도 남기지 않는다 —
                # 미완성 상태가 세션에 남아 이후 commit 에 딸려가는 것을 차단.
                db.session.expunge(row)
            raise

    return row.access_token
