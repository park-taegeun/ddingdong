"""데모 시드 — 발표용 "완성 UX" 알림 5건을 서버 DB 에 결정론적으로 심는다.

배경 (카테고리 8 대시보드 / A1 조사):
  라이브 데이터 소스 = Flask 서버 DB 인데, /detect·/enrich 의 mock 추론은
  random 기반이라 3클래스·상태 조합을 재현할 수 없다. 발표에서 "초인종/노크/
  화재경보 + 사진 + 자막 + 2차 처리중 + 신뢰도 부족(미발송)" 이 한 화면에
  모두 뜨는 완성 UX 를 확정 렌더하기 위한 결정론적 시드.

특징:
  - detected_at = utc_now() - timedelta(...) 동적 → stats "오늘"(KST) 필터 통과.
  - delete → insert 라 재실행해도 중복이 쌓이지 않는다(idempotent).
  - idempotency_keys 테이블은 건드리지 않는다(멱등 캐시는 시드 대상 아님).
  - 사진은 dashboard/public/static/captures/*.svg (vite public 루트 서빙,
    프록시·서버 정적 라우트 0줄 변경). 직접 생성한 더미라 저작권·초상권 무관.
  - confidence 발송건은 전부 ≥ 0.7 (신뢰도 임계값 SSoT, 카테고리 6.1 계열),
    미발송건만 0.52. 필드를 명시 세팅하므로 /detect 임계값 로직(constants 0.6)은
    타지 않는다 → constants 정정 PR 과 독립적으로 동작.

실행:
    cd server && python seed.py
"""

from datetime import timedelta

from app import create_app
from app.extensions import db
from app.models import Notification
from app.utils import to_kst_iso, utc_now

# 이미지 경로(vite public 서빙): dashboard/public/static/captures/*.svg
_IMG_DOORBELL = "/static/captures/demo-doorbell.svg"
_IMG_KNOCK = "/static/captures/demo-knock.svg"

# 삽입 명세 5건 — 오래된 순(minutes_ago 큰 값)으로 나열해 뒤에 삽입될수록
# id(=cursor 정렬 키)가 커지고, 대시보드(id desc)에서 최신이 위로 온다.
_SEED_SPECS = [
    # 1) 초인종 · 2차 완료(사진 + 자막) → 배지 "전송 완료"
    {
        "minutes_ago": 200,
        "client_request_id": "seed_demo_0001",
        "request_id": "req_seed_doorbell_done",
        "predicted_class": "doorbell",
        "confidence": 0.87,
        "all_scores": {"doorbell": 0.87, "knock": 0.09, "fire_alarm": 0.04},
        "tof_applied": True,
        "tof_passed": True,
        "tof_reason": "zone_count=12 >= 8 + motion=true",
        "primary_sent": True,
        "enrich_status": "completed",
        "secondary_sent": True,
        "primary_delay_s": 2.4,  # 1차 지연(초): detected_at + 2.4s
        "secondary_delay_s": 8.5,  # 2차 지연(초): detected_at + 8.5s
        "skip_reason": None,
        "image_url": _IMG_DOORBELL,
        "stt_transcript": "택배 왔습니다. 문 앞에 두고 갈게요.",
        "stt_confidence": 0.94,
    },
    # 2) 노크 · 2차 완료(사진 + 자막) → 배지 "전송 완료"
    {
        "minutes_ago": 150,
        "client_request_id": "seed_demo_0002",
        "request_id": "req_seed_knock_done",
        "predicted_class": "knock",
        "confidence": 0.81,
        "all_scores": {"doorbell": 0.12, "knock": 0.81, "fire_alarm": 0.07},
        "tof_applied": True,
        "tof_passed": True,
        "tof_reason": "zone_count=10 >= 8 + motion=true",
        "primary_sent": True,
        "enrich_status": "completed",
        "secondary_sent": True,
        "primary_delay_s": 2.8,  # 1차 지연(초): detected_at + 2.8s
        "secondary_delay_s": 11.2,  # 2차 지연(초): detected_at + 11.2s
        "skip_reason": None,
        "image_url": _IMG_KNOCK,
        "stt_transcript": "계세요? 옆집인데요.",
        "stt_confidence": 0.90,
    },
    # 3) 화재경보 · ToF 우회, 1차만 발송(enrich skipped) → 배지 "1차 발송"
    #    4단계 대응 수칙은 UI 가 데이터 무관 정적 렌더(카테고리 7.1) → 미디어/STT 불필요
    {
        "minutes_ago": 95,
        "client_request_id": "seed_demo_0003",
        "request_id": "req_seed_fire_bypass",
        "predicted_class": "fire_alarm",
        "confidence": 0.93,
        "all_scores": {"doorbell": 0.03, "knock": 0.04, "fire_alarm": 0.93},
        "tof_applied": False,
        "tof_passed": None,
        "tof_reason": "fire_alarm_bypass",
        "primary_sent": True,
        "enrich_status": "skipped",
        "secondary_sent": False,
        "primary_delay_s": 2.1,  # 1차만 발송(2차 skipped) → 2차 지연 집계 제외
        "secondary_delay_s": None,
        "skip_reason": None,
        "image_url": None,
        "stt_transcript": None,
        "stt_confidence": None,
    },
    # 4) 초인종 · 신뢰도 부족 → 1차 미발송 → 배지 "발송 제외" + 사유 "신뢰도 부족"
    {
        "minutes_ago": 45,
        "client_request_id": "seed_demo_0004",
        "request_id": "req_seed_doorbell_lowconf",
        "predicted_class": "doorbell",
        "confidence": 0.52,
        "all_scores": {"doorbell": 0.52, "knock": 0.31, "fire_alarm": 0.17},
        "tof_applied": True,
        "tof_passed": True,
        "tof_reason": "zone_count=9 >= 8 + motion=true",
        "primary_sent": False,
        "enrich_status": "skipped",
        "secondary_sent": False,
        "primary_delay_s": None,  # 미발송(신뢰도 부족) → 1·2차 지연 집계 제외
        "secondary_delay_s": None,
        "skip_reason": "low_confidence",
        "image_url": None,
        "stt_transcript": None,
        "stt_confidence": None,
    },
    # 5) 노크 · 2차 처리중(사진/자막 대기) → 배지 "2차 처리 중" (최신 = 목록 최상단)
    {
        "minutes_ago": 12,
        "client_request_id": "seed_demo_0005",
        "request_id": "req_seed_knock_processing",
        "predicted_class": "knock",
        "confidence": 0.84,
        "all_scores": {"doorbell": 0.10, "knock": 0.84, "fire_alarm": 0.06},
        "tof_applied": True,
        "tof_passed": True,
        "tof_reason": "zone_count=11 >= 8 + motion=true",
        "primary_sent": True,
        "enrich_status": "processing",
        "secondary_sent": False,
        "primary_delay_s": 2.6,  # 1차 발송, 2차 처리중 → 2차 지연 집계 제외
        "secondary_delay_s": None,
        "skip_reason": None,
        "image_url": None,
        "stt_transcript": None,
        "stt_confidence": None,
    },
]


def _build_notification(spec, now):
    """명세 dict → Notification. 시각/미디어/STT 파생 필드를 detected_at 기준으로 계산."""
    detected_at = now - timedelta(minutes=spec["minutes_ago"])
    # 발송 시각 = detected_at + 명세 지연(초). 목표 1차 5초 / 2차 15초 이내를 만족하는
    # 현실적 값을 spec 에 명시(결정론적). 미발송·2차 미완료건은 delay None → sent_at None.
    primary_sent_at = (
        detected_at + timedelta(seconds=spec["primary_delay_s"])
        if spec["primary_sent"]
        else None
    )
    secondary_sent_at = (
        detected_at + timedelta(seconds=spec["secondary_delay_s"])
        if spec["secondary_sent"]
        else None
    )

    stt = None
    if spec["stt_transcript"] is not None:
        stt = {
            "transcript": spec["stt_transcript"],
            "confidence": spec["stt_confidence"],
            "language": "ko-KR",
            "processed_at": to_kst_iso(secondary_sent_at),
        }

    return Notification(
        client_request_id=spec["client_request_id"],
        request_id=spec["request_id"],
        device_id="ddingdong-demo-01",
        detected_at=detected_at,
        predicted_class=spec["predicted_class"],
        confidence=spec["confidence"],
        all_scores=spec["all_scores"],
        tof_applied=spec["tof_applied"],
        tof_passed=spec["tof_passed"],
        tof_reason=spec["tof_reason"],
        primary_sent=spec["primary_sent"],
        primary_sent_at=primary_sent_at,
        enrich_status=spec["enrich_status"],
        secondary_sent=spec["secondary_sent"],
        secondary_sent_at=secondary_sent_at,
        skip_reason=spec["skip_reason"],
        image_url=spec["image_url"],
        image_thumbnail_url=spec["image_url"],  # 데모: 썸네일 = 원본 동일 경로
        audio_url=None,
        stt=stt,
    )


def seed():
    app = create_app()
    with app.app_context():
        # 데모 재현성: 기존 알림 전량 삭제 후 재삽입(재실행해도 중복 없음).
        # idempotency_keys 는 의도적으로 보존(멱등 캐시는 시드 대상 아님).
        deleted = db.session.query(Notification).delete()

        now = utc_now()
        rows = [_build_notification(spec, now) for spec in _SEED_SPECS]
        db.session.add_all(rows)
        db.session.commit()

        print(f"[seed] 기존 알림 {deleted}건 삭제 → 데모 알림 {len(rows)}건 삽입 완료.")
        for n in rows:
            print(f"       - {n.predicted_class:<11} conf={n.confidence} "
                  f"enrich={n.enrich_status} primary_sent={n.primary_sent}")


if __name__ == "__main__":
    seed()
