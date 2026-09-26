"""초인종 등록 저장 층 — 상태 판정 · 조회 · 시작 · 해제 · 템플릿 추가/로드.

★ 이 모듈의 함수는 전부 commit 하지 않는다. commit 은 호출부가 한 번만 한다
  (registration_api 의 각 엔드포인트, 후속 /detect 계측 훅).

호출처: registration_api(status · start · clear). add_template ·
load_registered_templates 는 후속 /detect 계측 훅용이며 지금은 호출처가 없다.
"""

import uuid
from datetime import timedelta

from sqlalchemy import delete, func, select

from .constants import (
    AUDIO_MAX_BYTES,
    REGISTRATION_STATE_COLLECTING,
    REGISTRATION_STATE_EXPIRED,
    REGISTRATION_STATE_NONE,
    REGISTRATION_STATE_REGISTERED,
)
from .extensions import db
from .models import RegistrationState, RegistrationTemplate
from .utils import to_kst_iso, utc_now


class RegistrationConflict(Exception):
    """collecting · registered 상태에서 start 를 부른 경우. API 가 409 로 바꾼다."""

    def __init__(self, state):
        super().__init__(state)
        self.state = state


def state_of(row, now):
    """등록 행 + 현재 시각(naive UTC) → 상태 문자열. 읽기 전용 순수 함수.

    판정 순서 = 행 없음 → completed_at → 만료 비교. now == expires_at 이면 expired.
    """
    if row is None:
        return REGISTRATION_STATE_NONE
    if row.completed_at is not None:
        return REGISTRATION_STATE_REGISTERED
    if now < row.expires_at:
        return REGISTRATION_STATE_COLLECTING
    return REGISTRATION_STATE_EXPIRED


def _row():
    return db.session.get(RegistrationState, RegistrationState.SINGLETON_ID)


def _count(registration_id):
    # COUNT 쿼리 — 상태 조회가 PCM BLOB 을 읽지 않게 한다. 다른 registration_id(고아)는 제외.
    return db.session.scalar(
        select(func.count())
        .select_from(RegistrationTemplate)
        .where(RegistrationTemplate.registration_id == registration_id)
    )


def status(now):
    """상태 본문 6키. registration_id · PCM 은 넣지 않는다. 값이 없으면 None."""
    row = _row()
    if row is None:
        return {
            "state": REGISTRATION_STATE_NONE,
            "collected": 0,
            "target": None,
            "started_at": None,
            "expires_at": None,
            "registered_at": None,
        }
    return {
        "state": state_of(row, now),
        "collected": _count(row.registration_id),
        "target": row.target_count,
        "started_at": to_kst_iso(row.started_at),
        "expires_at": to_kst_iso(row.expires_at),
        "registered_at": to_kst_iso(row.completed_at),
    }


def start(target_count, expires_in_seconds, now):
    """새 수집을 시작한다. collecting · registered 면 RegistrationConflict.

    none · expired 면 템플릿을 전부(고아 포함) 지우고 상태 행을 새 registration_id 로
    만들거나 덮어쓴다. 입력 범위 검증은 API 층 소관.
    """
    row = _row()
    state = state_of(row, now)
    if state in (REGISTRATION_STATE_COLLECTING, REGISTRATION_STATE_REGISTERED):
        raise RegistrationConflict(state)

    db.session.execute(delete(RegistrationTemplate))
    if row is None:
        row = RegistrationState(id=RegistrationState.SINGLETON_ID)
        db.session.add(row)
    row.registration_id = uuid.uuid4().hex
    row.target_count = target_count
    row.started_at = now
    row.expires_at = now + timedelta(seconds=expires_in_seconds)
    row.completed_at = None


def clear():
    """템플릿 전부(고아 포함) + 상태 행 삭제. 어느 상태에서나 동작, none 이면 no-op."""
    db.session.execute(delete(RegistrationTemplate))
    db.session.execute(delete(RegistrationState))


def add_template(pcm, client_request_id, now):
    """collecting 이고 collected < target 일 때만 PCM 을 템플릿으로 추가한다.

    반환: "added" | "completed"(이번 추가로 목표 개수 도달 → completed_at = now)
          | "not_collecting"(그 밖의 모든 경우 — 아무것도 바꾸지 않음).
    pcm 검증 위반(bytes 아님 · 빈 값 · 홀수 길이 · AUDIO_MAX_BYTES 초과)은 ValueError.

    ★ commit 순서 계약: 이 함수는 세션에 계류 변경을 남긴다(COUNT 쿼리의 autoflush 로
      flush 된 상태일 수도 있다). kakao._assert_commit_is_safe 는 세션의 미커밋 변경을
      flush 뒤 계류분까지 보고 RuntimeError 를 내므로, /detect 훅은 카카오 호출 **뒤**에만
      이 함수를 부르고 Notification 과 함께 한 번에 commit 해야 한다.
    """
    if not isinstance(pcm, bytes):
        raise ValueError(f"pcm 은 bytes 여야 함: {type(pcm).__name__}")
    if not pcm or len(pcm) % 2 or len(pcm) > AUDIO_MAX_BYTES:
        raise ValueError(f"pcm 길이 부적합: {len(pcm)} bytes (1~{AUDIO_MAX_BYTES}, 짝수)")

    row = _row()
    if state_of(row, now) != REGISTRATION_STATE_COLLECTING:
        return "not_collecting"
    collected = _count(row.registration_id)
    if collected >= row.target_count:
        return "not_collecting"

    db.session.add(
        RegistrationTemplate(
            registration_id=row.registration_id,
            client_request_id=client_request_id,
            pcm=pcm,
            created_at=now,
        )
    )
    if collected + 1 == row.target_count:
        row.completed_at = now
        return "completed"
    return "added"


def load_registered_templates():
    """registered 면 현재 registration_id 의 PCM bytes 목록(생성 순), 아니면 []."""
    row = _row()
    # registered 판정은 만료와 무관하므로 now 값이 결과를 바꾸지 않는다.
    if state_of(row, utc_now()) != REGISTRATION_STATE_REGISTERED:
        return []
    return list(
        db.session.scalars(
            select(RegistrationTemplate.pcm)
            .where(RegistrationTemplate.registration_id == row.registration_id)
            .order_by(RegistrationTemplate.id)
        )
    )
