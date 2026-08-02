"""public 캡처 이미지 서빙 라우트 (비인증, 앱 루트 — /api/v1 아래 X = public 에셋).

프로덕션에서 카카오가 image_url 을 **비인증으로 lazy fetch** 하므로(카테고리 7), 이
라우트에 Device/Dashboard 토큰 인증을 붙이지 않는다 — 인증을 붙이면 카카오 fetch 가
401 로 실패한다. 유일한 접근 게이트는 추측 불가한 opaque 키(image_store)다.

★ 11주차 교체 지점: 실 public 호스팅(EC2 static / 오브젝트 스토리지)으로 이관되면 이
라우트는 image_store 모듈과 함께 대체된다(/enrich 배선은 불변).
"""

from flask import Blueprint, send_file

from . import image_store
from .errors import ApiError

captures_bp = Blueprint("captures", __name__)


@captures_bp.get("/captures/<opaque_id>")
def serve_capture(opaque_id):
    # 인증 데코레이터 없음(의도적, 카테고리 7). 키 형식 위반(traversal 시도)·부재·만료는
    # resolve_path 가 모두 None 으로 반환 → 동일 404(존재/부재 정보 노출 최소화).
    path = image_store.resolve_path(opaque_id)
    if path is None:
        raise ApiError(404, "not_found", "이미지를 찾을 수 없습니다.")
    return send_file(path, mimetype="image/jpeg")
