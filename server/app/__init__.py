"""app factory (create_app).

설정/확장/모델 생성을 한 함수에 모아, 테스트·배포에서 독립된 앱 인스턴스를
필요한 만큼 만들 수 있게 한다. 전역 app 객체에 의존하지 않는 표준 패턴.
"""

from flask import Flask, jsonify

from .config import Config
from .errors import register_error_handlers
from .extensions import db


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 한글 JSON 응답을 그대로 노출 (Flask 3.x: app.json.ensure_ascii)
    app.json.ensure_ascii = False

    # 확장 바인딩
    db.init_app(app)

    # 모델 import 후 Blueprint 등록 (import 시점에 db.Model 메타데이터 채워짐)
    from . import models  # noqa: F401  (create_all 이 인식하도록 import)
    from .captures import captures_bp
    from .registration_api import bp as registration_bp
    from .routes import bp as api_v1_bp

    app.register_blueprint(api_v1_bp)
    # 캡처 이미지 public 서빙(비인증, 앱 루트 /captures — 카테고리 7). url_prefix 없음.
    app.register_blueprint(captures_bp)
    # 초인종 등록 API(Dashboard Token, url_prefix /api/v1/registration).
    app.register_blueprint(registration_bp)
    register_error_handlers(app)

    # /detect 추론 입력 레벨(raw / peak) — 모델 계약(other 유무) + env override, 불일치면 기동 실패.
    # 모델 로드(수 초) 앞에서 검사해 설정 오류를 먼저 낸다.
    # WARNING 인 이유 = INFO 는 기본 로그 레벨에서 안 보인다(6.3(m)).
    from . import constants, serving_level

    app.config["SERVING_LEVEL_MODE"] = serving_level.resolve_mode(
        constants.PREDICTED_CLASSES, app.config.get("SERVING_LEVEL")
    )
    app.logger.warning(
        "serving_level: /detect 추론 입력 = %s (classes=%s, %s=%r)",
        app.config["SERVING_LEVEL_MODE"],
        constants.PREDICTED_CLASSES,
        serving_level.LEVEL_ENV,
        app.config.get("SERVING_LEVEL"),
    )

    # 실추론 모델 싱글턴 로드 + warmup (카테고리 6.2, env 게이트 DDINGDONG_MODEL_PATH)
    from .model_serving import init_app as init_model_serving

    init_model_serving(app)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    # Phase 2-1 로컬: 기동 시 테이블 생성 (마이그레이션 도구는 배포 단계에서 도입)
    with app.app_context():
        db.create_all()

    return app
