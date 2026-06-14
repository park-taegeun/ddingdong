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
    from .routes import bp as api_v1_bp

    app.register_blueprint(api_v1_bp)
    register_error_handlers(app)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    # Phase 2-1 로컬: 기동 시 테이블 생성 (마이그레이션 도구는 배포 단계에서 도입)
    with app.app_context():
        db.create_all()

    return app
