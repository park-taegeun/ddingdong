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
from datetime import timedelta, timezone

from flask import current_app

from .constants import (
    KAKAO_FEED_BUTTON_TITLE,
    KAKAO_HTTP_TIMEOUT_SECONDS,
    KAKAO_LINK_URL,
    KAKAO_MEMO_URL,
    KAKAO_REFRESH_TOKEN_TTL,
    KAKAO_SECONDARY_MAX_ATTEMPTS,
    KAKAO_TOKEN_URL,
    KST,
    PRIMARY_MESSAGES,
    SECONDARY_FEED_TITLES,
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
            # 토큰이 살아 있다고 판단했는데 카카오가 거부한 경우(콘솔 수동 재발급,
            # client_secret rotate, 서버 시계 어긋남 등). 원인 계층이 토큰이므로
            # token_expired 로 집계되도록 토큰 예외로 올린다.
            # 여기서 갱신 후 재발송하지 않는다 — "재시도 없음" 결정 그대로. 대신
            # 호출부가 DB 토큰을 만료 표시해 "다음 이벤트"에서 갱신이 태워진다
            # (_invalidate_access_token 주석의 자기 치유 규약).
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


def _invalidate_access_token():
    """DB 의 access 토큰을 "만료됨"으로 표시한다. 401 자기 치유의 유일한 진입점.

    경위(실측 2026-09-03): needs_refresh() 는 access_expires_at 만 본다. 그 값이 미래인데
    카카오가 토큰을 거부하는 상태(콘솔 수동 재발급 / client_secret rotate / 시계 어긋남)에
    들어가면, 갱신이 걸리지 않아 매 이벤트가 같은 죽은 토큰으로 401 을 반복하고
    access_expires_at 이 자연 만료될 때까지 1차 알림이 계속 실패했다. 401 을 받고도
    이 컬럼을 되돌리는 코드가 없었던 것이 원인이다(프로브로 3회 연속 401 재현).

    만료 시각을 "지금"으로 내린다. needs_refresh 는 (access_expires_at - now) <= 마진
    비교라 같은 값이어도 0 <= 마진 → True 이고, 다음 이벤트에서는 now 가 더 커져 음수가
    된다. _bootstrap 이 "발급 시각을 모르는 env 토큰"에 쓰는 표기와 같은 관용이다.

    ★ 같은 요청 안에서 재발송하지 않는다(위임 §5 Step 3 "재시도 없음"). 자기 치유는
      다음 이벤트에서 일어난다 — 이 함수는 상태만 바꾸고 네트워크를 건드리지 않는다.
    """
    # 이 함수도 commit 한다 → 가드는 커밋하는 쪽에 붙인다. 지금 호출 경로에서는
    # get_access_token() 이 이미 통과시킨 뒤라 사실상 재확인이지만, 나중에 호출 지점이
    # 옮겨져도 "남의 미커밋 변경이 딸려가는" 사고가 조용히 생기지 않게 남겨 둔다.
    _assert_commit_is_safe()

    row = db.session.get(KakaoToken, KakaoToken.SINGLETON_ID)
    if row is None:
        # 행이 없으면 다음 이벤트가 _bootstrap 으로 새로 만들고 그 경로가 이미 즉시
        # 갱신을 태운다 → 표시할 대상도, 표시할 이유도 없다.
        return

    now = utc_now()
    row.access_expires_at = now
    row.updated_at = now
    db.session.commit()
    # 토큰 값은 찍지 않는다. 무슨 일이 일어났는지만 남긴다.
    current_app.logger.warning(
        "kakao access token marked expired: memo 401 (다음 이벤트에서 갱신 시도)"
    )


def send_primary_text(predicted_class):
    """1차 텍스트 알림을 1회 발송한다. 성공이면 None, 실패면 skip_reason 문자열.

    반환값 계약: None(성공) / SKIP_REASON_TOKEN_EXPIRED / SKIP_REASON_KAKAO_API_ERROR.
    호출부는 이 값을 그대로 Notification.skip_reason 에 넣고 primary_sent=False 로
    기록한다. 발송 401 은 이번 요청에서 재발송하지 않고(재시도 금지) DB 토큰만 만료
    표시해 다음 이벤트가 갱신을 태우게 한다 — 자기 치유는 이벤트 경계를 넘어 일어난다.

    발송 실패로 /detect 를 5xx 로 떨어뜨리지 않는다 — ESP32 에게 "요청이 잘못됐다"고
    알리는 것이 아니고, 재시도해봐야 같은 카카오 장애를 다시 맞기 때문이다.

    ★ 호출 위치 제약: 이 함수는 두 지점에서 db.session.commit() 한다 —
      get_access_token() 의 갱신 성공, 그리고 발송 401 시 _invalidate_access_token().
      따라서 Notification 을 세션에 add 하기 전에 불러야 한다. 이 제약은 주석이 아니라
      _assert_commit_is_safe() 가 실행 시점에 강제한다(위반 시 RuntimeError → 5xx).
      그 RuntimeError 는 아래 except 절에 잡히지 않는다(KakaoTokenError/KakaoSendError
      만 잡는다) — 계약 위반이 "카카오 발송 실패"로 둔갑하면 버그가 숨기 때문이다.

    로그에 토큰을 남기지 않는다. 아래 예외 메시지는 상태 코드/예외 타입만 담는다.
    """
    # 본문을 먼저 만든다: 미등록 클래스(코딩 오류)라면 토큰 갱신 커밋도 네트워크 호출도
    # 일으키기 전에 터지는 편이 원인 추적에 낫다.
    message = _build_message(predicted_class)

    # try 를 둘로 나눈 이유: 같은 KakaoTokenError 라도 "토큰을 못 구했다"(갱신 실패)와
    # "구한 토큰을 카카오가 거부했다"(발송 401)는 후처리가 다르다. 후자만 DB 토큰을
    # 만료 표시해야 한다 — 전자에서 표시하면 이미 만료로 판정된 값을 다시 쓰는 무의미한
    # 쓰기이고, 갱신 실패 원인(env 미설정 등)은 표시로 풀리지 않는다.
    try:
        access_token = get_access_token()
    except KakaoTokenError as exc:
        current_app.logger.warning("kakao primary send skipped: %s", exc)
        return SKIP_REASON_TOKEN_EXPIRED

    try:
        _post_memo(access_token, message)
    except KakaoTokenError as exc:  # 401 — 토큰이 죽어 있다
        _invalidate_access_token()
        current_app.logger.warning("kakao primary send skipped: %s", exc)
        return SKIP_REASON_TOKEN_EXPIRED
    except KakaoSendError as exc:
        current_app.logger.warning("kakao primary send failed: %s", exc)
        return SKIP_REASON_KAKAO_API_ERROR

    current_app.logger.info("kakao primary sent: class=%s", predicted_class)
    return None


# ── 2차 알림 발송 (사진 feed → 자막 text, 카테고리 7 / 7.3) ──────────────
#
# ★ 이 절은 전부 신규 함수다. 위 1차 계층(토큰·_post_memo·_invalidate_access_token·
#   send_primary_text)은 2026-09-03 ④런타임 검증을 통과한 자산이라 시그니처·본문·상수를
#   건드리지 않았다 — 재사용은 **호출**로만 한다.
#
# ★ 왜 2건으로 나눠 보내는가 (근거유형 = 실측, 2026-09-04 프로브):
#   feed description 은 2줄에서 잘리고, 그 상한 기준이 글자 수가 아니라 줄 수라
#   절단 지점이 렌더 폭에 종속된다(52자·110자가 둘 다 2줄에서, 서로 다른 글자
#   위치에서 잘렸다). 즉 자막을 description 에 넣으면 서버가 안전한 길이를 정할 수
#   없다. 반면 text 템플릿은 266자 전문 렌더가 실측돼 있다(7.5(b)).
#   → 사진은 feed 로, 자막은 text 로 따로 보낸다. 순서는 **사진 먼저**(누가 왔는지가
#     뭐라고 말했는지보다 먼저 필요하다 — 근거유형 = 논증).
#   비용 = memo 왕복 p95 490ms(7.3) × 2 ≈ 1초 = 2차 15초 예산의 약 6.5%(논증, 산술).


def _feed_description(detected_at_utc):
    """feed 카드 본문. 감지 시각(KST) 한 줄 — 자막은 넣지 않는다(위 절 주석).

    자막을 배제한 자리에 무엇을 넣을지는 "2줄 안에 확실히 들어가고, 사진만으로는 알 수
    없는 정보"를 기준으로 골랐다. 감지 시각은 카드가 늦게 열렸을 때 "언제 온 방문인지"를
    복원해 주고, 길이가 고정(약 20자)이라 어떤 렌더 폭에서도 절단 위험이 없다
    — 실측 P1(15자)이 1줄로 전문 렌더된 구간이다.
    ★ 길이 상한 상수를 만들지 않는 이유 = 상한이 줄 수 기준이라 서버가 글자 수로 정할
      수 없기 때문이다(카테고리 20: 실측 없는 판정 금지). 대신 서버가 만드는 문자열
      자체를 짧게 고정한다.
    """
    if detected_at_utc is None:
        # 호출부가 시각을 못 주는 경우는 현재 없다. 그래도 카드 본문을 비워 두지 않는다
        # (description 은 feed 필수 필드이고, 빈 문자열이 렌더에서 어떻게 보이는지는
        #  실측된 적이 없다).
        return "방문자 사진이 도착했습니다."
    kst = detected_at_utc.replace(tzinfo=timezone.utc).astimezone(KST)
    return f"{kst.month}월 {kst.day}일 {kst.strftime('%H:%M')} 감지"


def _build_secondary_title(predicted_class):
    """클래스별 사진 카드 제목. _build_message 와 동형으로 폴백 없이 KeyError 를 낸다."""
    return SECONDARY_FEED_TITLES[predicted_class]


def _post_memo_feed(access_token, title, description, image_url):
    """memo default/send 를 feed 템플릿으로 1회 호출한다. 성공이면 반환, 실패면 예외.

    엔드포인트는 text 와 같은 memo default/send 다 — 템플릿 종류는 object_type 이
    가른다(7.3 실측도 이 경로로 이뤄졌다: "feed/default/send 왕복").

    ★ image_url 은 **사전 호스팅된 public URL 문자열만** 받는다. memo 에는 이미지 파일
      업로드 엔드포인트가 없어 바이트가 통과하지 못한다(카테고리 7 SSoT, 2026-07-31
      PoC-(30) 실사). 서버가 스스로 호스팅한 URL(image_store.public_url)을 싣는다.

    ★ POST 배관이 _post_memo 와 거의 같은데도 합치지 않은 이유: _post_memo 는
      ④런타임 검증분이라 본 PR 의 무변경 대상이다(시그니처·본문 불변). 공통 헬퍼로
      빼려면 그 함수를 고쳐야 하므로, 중복을 감수하고 신규 함수로 둔다.
      ★ 재조정 방법: 2차 경로가 ④런타임을 통과해 두 함수가 함께 "검증분"이 되면
        그때 공통 POST 헬퍼로 묶는다(그 리팩토링은 두 경로의 회귀가 함께 돌 때 안전하다).
    """
    template_object = json.dumps(
        {
            "object_type": "feed",
            "content": {
                "title": title,
                "description": description,
                "image_url": image_url,
                # link 는 feed content 필수 필드(text 템플릿과 동형, KAKAO_LINK_URL 주석).
                "link": {"web_url": KAKAO_LINK_URL, "mobile_web_url": KAKAO_LINK_URL},
            },
            "button_title": KAKAO_FEED_BUTTON_TITLE,
        },
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
            # 1차와 같은 계층 분리: 인증 거부는 토큰 예외로 올려 token_expired 로
            # 집계되게 한다(대시보드 skip_reason 키가 이미 두 갈래로 고정돼 있다).
            raise KakaoTokenError(f"feed 발송 인증 거부: HTTP {exc.code}") from exc
        # 에러 본문을 싣지 않는다 — 요청 파라미터 에코 가능성 배제(_post_memo 동형).
        raise KakaoSendError(f"feed 발송 실패: HTTP {exc.code}") from exc
    except Exception as exc:  # URLError/timeout/JSON 파싱 — 원인 타입만 남긴다
        raise KakaoSendError(f"feed 발송 실패: {type(exc).__name__}") from exc

    result_code = payload.get("result_code")
    if result_code != 0:
        detail = result_code if isinstance(result_code, int) else "missing"
        raise KakaoSendError(f"feed 발송 실패: result_code={detail}")


def _send_part(part, send_call):
    """2차 발송 1건을 최대 KAKAO_SECONDARY_MAX_ATTEMPTS 회 시도.

    반환 (sent, reason, token_dead):
      sent       발송 성공 여부
      reason     실패 시 skip_reason 계열 문자열, 성공이면 None
      token_dead 401 을 받아 토큰을 만료 표시했는가(호출부가 남은 건을 중단하는 신호)

    ★ 재시도 범위가 이 함수 안이라는 점이 설계의 핵심이다. 재시도는 **지금 실패한 그
      한 건**에만 걸리고, 이미 성공해 이 함수를 빠져나간 건은 어떤 경로로도 다시
      호출되지 않는다 → "2건 통째 재시도"로 성공한 사진이 중복 발송되는 경로가 코드에
      존재하지 않는다(카테고리 7 "1회 재시도"의 2건 분할 체제 해석, §2-D).

    ★ 재시도 대상을 HTTP 상태 코드가 아니라 **예외 클래스**로 가른 이유:
      - KakaoSendError = 네트워크 타임아웃 / 5xx / 그 밖의 HTTP 오류 / result_code≠0.
        일시적일 수 있으므로 재시도한다.
      - KakaoTokenError = 401(인증 거부) 또는 토큰 확보 실패. 재시도하지 않는다 —
        1차가 확립한 자기 치유 규약이 "같은 요청 안에서 재발송하지 않고 DB 토큰을 만료
        표시해 **다음 이벤트**에서 갱신을 태운다"이기 때문이다. 같은 죽은 토큰으로 즉시
        다시 쏘면 그 규약을 깨고 왕복만 낭비한다.
      기각한 대안 = 상태 코드별 분류(4xx 는 결정론적이니 재시도 제외). 그렇게 하려면
      _post_memo 가 상태 코드를 노출하도록 고쳐야 하는데 그 함수는 무변경 대상이고,
      결정론적 4xx 를 한 번 더 쏘는 비용(약 490ms)은 15초 예산에서 무해하다.
    """
    for attempt in range(1, KAKAO_SECONDARY_MAX_ATTEMPTS + 1):
        try:
            send_call()
        except KakaoTokenError as exc:
            _invalidate_access_token()
            current_app.logger.warning("kakao secondary %s failed: %s", part, exc)
            return False, SKIP_REASON_TOKEN_EXPIRED, True
        except KakaoSendError as exc:
            if attempt < KAKAO_SECONDARY_MAX_ATTEMPTS:
                current_app.logger.warning(
                    "kakao secondary %s retrying (%d/%d): %s",
                    part,
                    attempt,
                    KAKAO_SECONDARY_MAX_ATTEMPTS,
                    exc,
                )
                continue
            current_app.logger.warning("kakao secondary %s failed: %s", part, exc)
            return False, SKIP_REASON_KAKAO_API_ERROR, False
        return True, None, False


def send_secondary(predicted_class, image_url, caption, detected_at_utc):
    """2차 알림을 발송한다 — 사진(feed) 먼저, 자막(text) 나중.

    caption 이 None/빈 문자열이면 **text 발송을 아예 호출하지 않는다**(§2-C).
    현 시점 자막 소스는 mock 이다 — 실 STT(G23)는 미구현이고 본 PR 범위 밖이다.

    반환 dict:
      photo_sent      bool         사진 발송 성공 여부
      photo_reason    str | None   실패 사유(skip_reason 계열), 성공이면 None
      caption_sent    bool | None  자막 발송 성공 여부. **None = 자막이 없어 미발송**
      caption_reason  str | None   실패 사유, 성공·미발송이면 None

    ★ caption_sent 가 3상태(True/False/None)인 것이 §2-C 요구다 — "자막이 없어서 안
      보냄"(None)과 "보내려다 실패함"(False)이 호출부·로그·DB 어디서도 섞이지 않는다.

    ★ 호출 위치 제약 (1차와 동일): 이 함수는 get_access_token()/_invalidate_access_token()
      을 통해 db.session.commit() 할 수 있다. 따라서 **Notification 을 수정하기 전에**
      불러야 한다. 위반 시 _assert_commit_is_safe() 가 RuntimeError 를 올린다.

    ★ 토큰은 두 건이 **한 번 확보해 공유**한다. 확보 자체가 실패하면 네트워크 왕복을
      한 번도 태우지 않고 두 건 모두 token_expired 로 끝낸다 — 죽은 토큰으로 두 번
      쏘는 것은 이벤트당 왕복 상한만 늘리고 결과를 바꾸지 않는다.
    """
    result = {
        "photo_sent": False,
        "photo_reason": None,
        "caption_sent": None,
        "caption_reason": None,
    }
    has_caption = bool(caption)

    try:
        access_token = get_access_token()
    except KakaoTokenError as exc:
        current_app.logger.warning("kakao secondary skipped: %s", exc)
        result["photo_reason"] = SKIP_REASON_TOKEN_EXPIRED
        if has_caption:
            result["caption_sent"] = False
            result["caption_reason"] = SKIP_REASON_TOKEN_EXPIRED
        return result

    title = _build_secondary_title(predicted_class)
    description = _feed_description(detected_at_utc)

    # ① 사진(feed) — 먼저. "누가 왔는지"가 "뭐라고 말했는지"보다 먼저 필요하다.
    photo_sent, photo_reason, token_dead = _send_part(
        "photo",
        lambda: _post_memo_feed(access_token, title, description, image_url),
    )
    result["photo_sent"] = photo_sent
    result["photo_reason"] = photo_reason

    # ② 자막(text) — 나중. 사진이 실패해도 시도한다: 사용자에게 "뭐라고 말했는지"라도
    #    남기는 편이 아무것도 안 보내는 것보다 낫다(부분 성공은 상태에서 구분된다).
    if has_caption:
        if token_dead:
            # 방금 401 을 받아 토큰을 만료 표시했다 — 같은 죽은 토큰으로 두 번째 왕복을
            # 태우지 않는다(1차 자기 치유 규약: 치유는 다음 이벤트에서).
            result["caption_sent"] = False
            result["caption_reason"] = SKIP_REASON_TOKEN_EXPIRED
        else:
            # 자막은 1차와 같은 text 템플릿이라 검증분 _post_memo 를 그대로 재사용한다
            # (신규 함수 없이 호출만 — §2-A 무변경 유지).
            caption_sent, caption_reason, _ = _send_part(
                "caption", lambda: _post_memo(access_token, caption)
            )
            result["caption_sent"] = caption_sent
            result["caption_reason"] = caption_reason

    current_app.logger.info(
        "kakao secondary: class=%s photo=%s caption=%s photo_reason=%s caption_reason=%s",
        predicted_class,
        result["photo_sent"],
        result["caption_sent"],
        result["photo_reason"],
        result["caption_reason"],
    )
    return result
