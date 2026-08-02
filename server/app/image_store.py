"""로컬 이미지 스토어 (스켈레톤 = 로컬 파일시스템, concrete 단일 구현).

캡처 이미지를 로컬 파일시스템에 opaque(추측 불가) 키로 저장하고, 그 키를 담은
public URL 을 발급한다. 카카오 memo(나에게 보내기)엔 이미지 파일 업로드 API 가 없어
image_url(사전 호스팅된 public URL 문자열)만 수신하므로(카테고리 7 정정), 서버가
캡처 이미지를 스스로 public 호스팅한 뒤 그 URL 을 실어 발송해야 한다.

★ 로컬 파일시스템 = 스켈레톤. 11주차 EC2 배포 시 **이 모듈만** 실 public 호스팅
(EC2 static route / 오브젝트 스토리지)으로 교체하며, /enrich 배선(store_image →
public_url 호출부)은 불변이다. 소비처가 현재 1개뿐이라 다중 백엔드 추상 인터페이스는
두지 않는다(카테고리 6.2 학습 16 over-abstraction 회피). 저장 경로·URL base 는 config
(CAPTURE_STORE_DIR / CAPTURE_URL_BASE)로 빼 교체가 config 변경으로 끝나게 한다.

보안(카테고리 7): URL 경로 키 = secrets.token_urlsafe 로 생성한 추측 불가 문자열.
notification_id·순차값·해시-유추 가능값에서 유래하지 않는다(옆 번호를 찔러 남의
방문자 사진을 여는 프라이버시 유출 차단). 비인증 서빙 라우트(captures.py)의 유일한
접근 게이트가 이 opaque 키이므로, 키 화이트리스트 검증으로 path traversal 도 차단한다.
"""

import os
import re
import secrets
import time

from flask import current_app

from .constants import CAPTURE_OPAQUE_BYTES, CAPTURE_TTL

# token_urlsafe 출력 문자셋(URL-safe base64: A-Z a-z 0-9 _ -) 화이트리스트.
# resolve_path 에서 이 패턴을 벗어난 키는 즉시 거부 → path traversal(../, 슬래시,
# 확장자 주입 등)을 파일시스템 접근 전에 원천 차단.
_OPAQUE_KEY_RE = re.compile(r"^[A-Za-z0-9_-]+$")

# 저장 파일 확장자 — 캡처는 JPEG(카테고리 6.2 SOI 0xFFD8 검증). opaque 키(URL)엔 확장자를
# 노출하지 않고 디스크 파일명에만 붙여 content-type 판별을 단순화한다.
_IMAGE_EXT = ".jpg"


def _store_dir():
    """캡처 저장 디렉토리(config). 없으면 생성. 기본 = server/instance/captures(비버전)."""
    path = current_app.config["CAPTURE_STORE_DIR"]
    os.makedirs(path, exist_ok=True)
    return path


def store_image(image_bytes):
    """이미지 바이트를 opaque 키로 저장하고 그 키(opaque_id)를 반환.

    키 = secrets.token_urlsafe(CAPTURE_OPAQUE_BYTES) — 암호학적 난수라 추측 불가.
    파일명 = 키 + 확장자. 저장 시각(mtime)이 TTL 만료 판정 기준이 된다.
    """
    opaque_id = secrets.token_urlsafe(CAPTURE_OPAQUE_BYTES)
    path = os.path.join(_store_dir(), opaque_id + _IMAGE_EXT)
    with open(path, "wb") as f:
        f.write(image_bytes)
    return opaque_id


def resolve_path(opaque_id):
    """opaque 키 → 저장 파일 절대경로. 키 형식 위반/부재/만료면 None.

    - 키 화이트리스트(_OPAQUE_KEY_RE) 미통과 = traversal 시도(../, 슬래시 등) → None
      (파일시스템 접근 전에 차단하므로 store_dir 밖 경로 조합 자체가 불가)
    - 파일 부재 → None
    - mtime 기준 TTL(CAPTURE_TTL) 초과 → None (실삭제는 cleanup_expired 가 담당)
    존재/부재를 같은 None 으로 통일해 서빙 라우트가 404 만 노출(정보 누수 최소화).
    """
    if not opaque_id or not _OPAQUE_KEY_RE.match(opaque_id):
        return None
    path = os.path.join(_store_dir(), opaque_id + _IMAGE_EXT)
    if not os.path.isfile(path):
        return None
    if time.time() - os.path.getmtime(path) > CAPTURE_TTL.total_seconds():
        return None
    return path


def public_url(opaque_id):
    """opaque 키 → public 이미지 URL. base(config CAPTURE_URL_BASE) + 키 조합.

    로컬 = "/captures/<id>"(본 앱 비인증 서빙 라우트). 11주차 = 실 host(EC2 static /
    오브젝트 스토리지)로 CAPTURE_URL_BASE 만 바꾸면 배선 불변으로 교체된다.
    """
    base = current_app.config["CAPTURE_URL_BASE"].rstrip("/")
    return f"{base}/{opaque_id}"


def cleanup_expired():
    """TTL(CAPTURE_TTL) 초과 캡처 파일 삭제 후 삭제 개수 반환.

    호출 가능한 헬퍼(수동) — 주기 스케줄링은 11주차 defer(스케줄러/cron 신설 안 함).
    """
    store_dir = current_app.config["CAPTURE_STORE_DIR"]
    if not os.path.isdir(store_dir):
        return 0
    cutoff = time.time() - CAPTURE_TTL.total_seconds()
    removed = 0
    for name in os.listdir(store_dir):
        path = os.path.join(store_dir, name)
        if os.path.isfile(path) and os.path.getmtime(path) < cutoff:
            os.remove(path)
            removed += 1
    return removed
