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
    KAKAO_LINK_URL,
    KAKAO_MEMO_URL,
    KAKAO_REFRESH_TOKEN_TTL,
    KAKAO_TOKEN_URL,
    PRIMARY_MESSAGES,
)
from .extensions import db
from .models import KakaoToken
from .utils import utc_now


class KakaoTokenError(RuntimeError):
    """토큰 확보 실패. 조용한 폴백 없이 호출부로 올려 fail-fast 시킨다.

    호출부(/detect)는 이 예외를 잡아 1차 알림을 미발송으로 기록할 뿐,
    요청 전체를 5xx 로 떨어뜨리지 않는다.
    """


class KakaoSendError(RuntimeError):
    """memo 발송 실패(네트워크/HTTP/응답 계약 위반).

    토큰 계층 실패(KakaoTokenError)와 굳이 나누는 이유 = 대시보드 집계 키가
    token_expired / kakao_api_error 두 갈래로 이미 고정돼 있어서다
    (dashboard/src/types/stats.ts SkipReasonCounts). 원인 계층이 다르면 다른 키로
    집계돼야 "토큰이 죽은 것"과 "카카오가 안 받은 것"을 화면에서 구분할 수 있다.
    """


# skip_reason 값 (dashboard/src/types/stats.ts SkipReasonCounts 4종 중 카카오 소관 2종).
# routes.py 가 Notification.skip_reason 에 그대로 넣는다.
SKIP_REASON_TOKEN_EXPIRED = "token_expired"
SKIP_REASON_KAKAO_API_ERROR = "kakao_api_error"


def _uncommitted_classes():
    """이 세션에 걸린 미커밋 변경의 클래스 목록(= 지금 commit 하면 함께 저장될 것들).

    session.new/dirty 만으로는 부족하다: flush 를 거친 객체는 두 컬렉션에서 빠지지만
    커밋은 안 된 상태로 트랜잭션에 남아, 토큰 갱신 커밋에 그대로 딸려간다.
    (발견 경위 = 2026-09-03 Step 3 negative control — 발송 호출을 db.session.flush()
     뒤로 옮겨봤더니 flush 이전만 보던 초판 가드가 이를 잡지 못했다.)

    인스턴스가 아니라 클래스(InstanceState.class_)를 본다 — 뒤에서 말하는 약참조
    문제로 인스턴스 자체는 None 이 될 수 있기 때문이다.

    ★ 알려진 한계(실측 2026-09-03): flush 이후 SQLAlchemy 의 identity map 은 약참조라,
      호출부가 객체 참조를 전혀 들고 있지 않으면 InstanceState 까지 수거돼 이 검사가
      비어 버린다. 즉 "flush 했고 그 객체를 아무도 안 들고 있는" 경우는 못 잡는다.
      실제 위험 지점인 routes.detect() 는 notif 지역변수로 참조를 끝까지 들고 있어
      이 한계에 걸리지 않는다(negative control 로 검출 확인). 완전한 검출은 DBAPI
      커넥션의 쓰기 트랜잭션 여부를 봐야 하는데 SQLite 전용 결합이라 채택하지 않았다.

    ※ SessionTransaction 의 _new/_dirty 는 공개 API 가 아니다. SQLAlchemy 상향으로
      사라지면 getattr 이 조용히 건너뛰어 flush 이전 검사만 남는다 — 가드가 약해질
      뿐 앱이 죽지는 않게 한다(퇴화 감지는 회귀 테스트 소관).
    """
    classes = [type(obj) for obj in list(db.session.new) + list(db.session.dirty)]

    # db.session 은 scoped_session 프록시라 get_transaction 을 노출하지 않는다 →
    # 호출해서 실제 Session 을 꺼낸다.
    tx = getattr(db.session(), "get_transaction", lambda: None)()
    for attr in ("_new", "_dirty"):
        for state in getattr(tx, attr, None) or ():
            classes.append(state.class_)

    seen, unique = set(), []
    for cls in classes:
        if cls not in seen:
            seen.add(cls)
            unique.append(cls)
    return unique


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
        cls for cls in _uncommitted_classes() if not issubclass(cls, KakaoToken)
    ]
    if foreign:
        raise RuntimeError(
            "kakao.get_access_token() 은 세션에 미커밋 변경이 있는 지점에서 호출할 수 "
            f"없다(토큰 갱신 커밋에 딸려간다). 계류 중: {[c.__name__ for c in foreign]}"
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


# ── 1차 텍스트 알림 발송 (카테고리 7) ────────────────────────────────────
def _build_message(predicted_class):
    """클래스별 1차 알림 본문. 분할·축약 없이 상수 원문 그대로 돌려준다.

    PREDICTED_CLASSES 는 닫힌 3종 enum(카테고리 4)이라 키 부재는 발송 실패가 아니라
    코딩 오류다 → get 폴백으로 임의 문구를 지어내지 않고 KeyError 로 시끄럽게 터뜨린다.
    잘못된 본문을 화재 상황에 보내는 것보다 낫다.
    """
    return PRIMARY_MESSAGES[predicted_class]


def _post_memo(access_token, message):
    """memo default/send 를 1회 호출한다. 성공이면 반환, 실패면 예외.

    재시도·백오프 없음(위임 §5 Step 3). 5초 예산 안에 두 번째 왕복을 태울 여유가 없고,
    실패는 요청 실패가 아니라 "1차 알림 미발송"으로 기록되면 되기 때문이다.
    """
    template_object = json.dumps(
        {
            "object_type": "text",
            "text": message,
            # link 는 text 템플릿 필수 필드다(web_url/mobile_web_url 중 최소 1개).
            # 이동 대상이 아직 없어 고정값을 쓴다 — 근거는 constants.KAKAO_LINK_URL 주석.
            "link": {"web_url": KAKAO_LINK_URL, "mobile_web_url": KAKAO_LINK_URL},
        },
        # 한글·기호를 \uXXXX 로 부풀리지 않는다. 본문은 urlencode 가 다시 퍼센트 인코딩한다.
        ensure_ascii=False,
    )
    data = urllib.parse.urlencode({"template_object": template_object}).encode("utf-8")
    req = urllib.request.Request(
        KAKAO_MEMO_URL,
        data=data,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=KAKAO_HTTP_TIMEOUT_SECONDS) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            # 토큰이 살아 있다고 판단했는데 카카오가 거부한 경우(폐기·권한 변경 등).
            # 원인 계층이 토큰이므로 token_expired 로 집계되도록 토큰 예외로 올린다.
            # 여기서 갱신 후 재발송하지 않는다 — "재시도 없음" 결정 그대로.
            raise KakaoTokenError(f"memo 발송 인증 거부: HTTP {exc.code}") from exc
        # 에러 본문을 싣지 않는다 — 요청 파라미터 에코 가능성 배제(_refresh 와 동형).
        raise KakaoSendError(f"memo 발송 실패: HTTP {exc.code}") from exc
    except Exception as exc:  # URLError/timeout/JSON 파싱 — 원인 타입만 남긴다
        raise KakaoSendError(f"memo 발송 실패: {type(exc).__name__}") from exc

    # 카카오는 HTTP 200 이어도 result_code 로 실패를 알린다(성공 = 0).
    result_code = payload.get("result_code")
    if result_code != 0:
        detail = result_code if isinstance(result_code, int) else "missing"
        raise KakaoSendError(f"memo 발송 실패: result_code={detail}")


def send_primary_text(predicted_class):
    """1차 텍스트 알림을 1회 발송한다. 성공이면 None, 실패면 skip_reason 문자열.

    반환값 계약: None(성공) / SKIP_REASON_TOKEN_EXPIRED / SKIP_REASON_KAKAO_API_ERROR.
    호출부는 이 값을 그대로 Notification.skip_reason 에 넣고 primary_sent=False 로
    기록한다. 발송 실패로 /detect 를 5xx 로 떨어뜨리지 않는다 — ESP32 에게 "요청이
    잘못됐다"고 알리는 것이 아니고, 재시도해봐야 같은 카카오 장애를 다시 맞기 때문이다.

    ★ 호출 위치 제약: get_access_token() 이 갱신 성공 시 db.session.commit() 한다.
      따라서 Notification 을 세션에 add 하기 전에 불러야 한다. 이 제약은 주석이 아니라
      _assert_commit_is_safe() 가 실행 시점에 강제한다(위반 시 RuntimeError → 5xx).
      그 RuntimeError 는 아래 except 절에 잡히지 않는다(KakaoTokenError/KakaoSendError
      만 잡는다) — 계약 위반이 "카카오 발송 실패"로 둔갑하면 버그가 숨기 때문이다.

    로그에 토큰을 남기지 않는다. 아래 예외 메시지는 상태 코드/예외 타입만 담는다.
    """
    # 본문을 먼저 만든다: 미등록 클래스(코딩 오류)라면 토큰 갱신 커밋도 네트워크 호출도
    # 일으키기 전에 터지는 편이 원인 추적에 낫다.
    message = _build_message(predicted_class)

    try:
        access_token = get_access_token()
        _post_memo(access_token, message)
    except KakaoTokenError as exc:
        current_app.logger.warning("kakao primary send skipped: %s", exc)
        return SKIP_REASON_TOKEN_EXPIRED
    except KakaoSendError as exc:
        current_app.logger.warning("kakao primary send failed: %s", exc)
        return SKIP_REASON_KAKAO_API_ERROR

    current_app.logger.info("kakao primary sent: class=%s", predicted_class)
    return None
