"""앱 설정. .env 를 읽어 토큰/DB 경로를 주입한다 (카테고리 6.1)."""

import os

from dotenv import load_dotenv

# server/app/config.py → dirname 두 번 = server/ 디렉토리
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

# server/.env 로드 (없어도 에러 없이 통과 → 환경변수 직접 주입도 허용)
load_dotenv(os.path.join(BASE_DIR, ".env"))


class Config:
    # 카테고리 6.1: Device / Dashboard Bearer Token 분리. 기본값 빈 문자열 →
    # auth.py 에서 빈 토큰은 항상 인증 실패 처리 (토큰 미설정 우회 방지).
    DEVICE_TOKEN = os.environ.get("DEVICE_TOKEN", "")
    DASHBOARD_TOKEN = os.environ.get("DASHBOARD_TOKEN", "")

    # 카테고리 6: SQLite + Flask-SQLAlchemy. 미설정 시 server/ddingdong.db (*.db = gitignore)
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'ddingdong.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
