"""부스 자막 정리 — 지정한 시간대(KST)의 알림 행(notifications)만 지운다.

배경 (감사 AU-02, 2026-10-13):
  부스에서 관람객이 벨을 누르면 그 사람이 한 말(자막 = notifications.stt)과 사진 참조
  (notifications.image_url)가 노트북 DB 에 기한 없이 남는다. 부스가 끝난 뒤 그 시간대 행만
  지우는 도구다. DB 파일을 통째로 바꾸거나 지우지 않는다 — 같은 파일에 카카오 토큰
  (kakao_tokens)이 있다.

실행 (server/ 에서, 서버를 끈 뒤 — SQLite 동시 쓰기 회피):
    cd server && venv/bin/python3 -B purge_notifications.py --from "2026-10-20 10:00" --to "2026-10-20 17:00"
  → 대상 DB 파일 이름 · 구간 · 지울 행 수 · 가장 이른/늦은 시각 · 클래스별 개수만 보여 주고 끝난다
    (쓰기 0 · 종료 코드 2). 확인한 뒤 같은 명령에 --confirm-delete 를 붙여 다시 실행한다.
  구간 = 반열린 [from, to) — from 정각 행은 지우고 to 정각 행은 남긴다. 둘 다 KST, 기본값 없음.
  from ≥ to · 형식 오류면 DB 를 열기 전에 종료한다(종료 코드 2, argparse).

지우지 않는 것:
  - 사진 파일: 이 도구는 행만 지운다(image_url 이 가리키는 파일은 그대로). 부스 사진 폴더를
    따로 지정해(DDINGDONG_CAPTURE_DIR) 부스가 끝나면 폴더째 지운다.
  - 등록 템플릿(registration_templates.pcm): 등록 해제(registration.clear())로 지운다.
  - 다른 테이블: 자막 · 사진 참조 필드가 없고 notifications 를 외래 키로 참조하는 곳도 없다.
    idempotency_keys.response_json 은 /detect 응답 스냅샷이라 stt · image_url 이 늘 None 이다
    (2차 /enrich 는 이 캐시를 고치지 않는다). registration_matches · registration_failures 는
    숫자 · 오류 요약뿐, kakao_tokens · registration_state · device_heartbeats 는 무관.
  - 카카오톡 대화방의 카드: 카톡에서 손으로 지운다.

출력에는 개수 · 시각 · 클래스만 찍는다(자막 내용 · 사진 id · client_request_id 는 찍지 않는다).
"""

import argparse
import os
import sys
from datetime import datetime, timezone

from sqlalchemy import func

from app import create_app
from app.constants import KST
from app.extensions import db
from app.models import Notification
from app.utils import to_kst_iso

_INPUT_FORMAT = "%Y-%m-%d %H:%M"


def kst_to_naive_utc(text):
    """「YYYY-MM-DD HH:MM」(KST) → naive UTC (DB detected_at 과 같은 표현)."""
    kst = datetime.strptime(text, _INPUT_FORMAT).replace(tzinfo=KST)
    return kst.astimezone(timezone.utc).replace(tzinfo=None)


def purge(app, start, end, confirm):
    """start · end = naive UTC, 구간 [start, end). confirm=False 면 세기만 하고 2, True 면 삭제 후 0."""
    in_range = (Notification.detected_at >= start) & (Notification.detected_at < end)
    span = f"{to_kst_iso(start)} ~ {to_kst_iso(end)} (끝 시각 제외)"
    with app.app_context():
        db_name = os.path.basename(db.engine.url.database or "")
        query = db.session.query(Notification)
        outside_before = query.filter(~in_range).count()
        print(f"[purge] 대상 DB = {db_name} · 구간 {span}")

        if not confirm:
            by_class = (
                db.session.query(
                    Notification.predicted_class,
                    func.count(),
                    func.min(Notification.detected_at),
                    func.max(Notification.detected_at),
                )
                .filter(in_range)
                .group_by(Notification.predicted_class)
                .order_by(Notification.predicted_class)
                .all()
            )
            total = sum(r[1] for r in by_class)
            print(f"        지울 알림 {total}건 · 구간 밖 {outside_before}건 — 아무것도 바꾸지 않았다.")
            if by_class:
                first = min(r[2] for r in by_class)
                last = max(r[3] for r in by_class)
                print(f"        가장 이른 {to_kst_iso(first)} · 가장 늦은 {to_kst_iso(last)}")
                print("        클래스별 " + " · ".join(f"{c} {n}건" for c, n, _, _ in by_class))
            print("        지우려면 같은 명령에 --confirm-delete 를 붙여 다시 실행.")
            return 2

        deleted = query.filter(in_range).delete(synchronize_session=False)
        db.session.commit()
        outside_after = query.filter(~in_range).count()
        print(f"        알림 {deleted}건 삭제 · 구간 밖 {outside_before}건 → {outside_after}건.")
        return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="지정한 시간대(KST)의 알림 행만 삭제(부스 자막 정리)")
    for flag, dest, label in (("--from", "start", "시작(포함)"), ("--to", "end", "끝(제외)")):
        parser.add_argument(
            flag,
            dest=dest,
            required=True,
            type=kst_to_naive_utc,
            metavar='"YYYY-MM-DD HH:MM"',
            help=f"구간 {label}, KST",
        )
    parser.add_argument(
        "--confirm-delete",
        action="store_true",
        help="구간 안 알림 행을 실제로 지운다. 없으면 개수만 보여 주고 끝난다.",
    )
    args = parser.parse_args(argv)
    if args.start >= args.end:
        parser.error("--from 은 --to 보다 앞이어야 한다")
    return purge(create_app(), args.start, args.end, args.confirm_delete)


if __name__ == "__main__":
    sys.exit(main())
