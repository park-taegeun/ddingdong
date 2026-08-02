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

    # 카테고리 6.2: 실추론 env 게이트. 미설정 = mock 유지, 설정 = ModelRunner 싱글턴 로드.
    MODEL_PATH = os.environ.get("DDINGDONG_MODEL_PATH", "")

    # 카테고리 6: SQLite + Flask-SQLAlchemy. 미설정 시 server/ddingdong.db (*.db = gitignore)
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'ddingdong.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 카테고리 7: 캡처 이미지 public 호스팅 (스켈레톤 = 로컬 파일시스템, image_store.py).
    # 저장 디렉토리 = 기본 server/instance/captures (인스턴스/비버전 경로, .gitignore 대상 —
    # 방문자 사진은 개인정보라 절대 커밋 금지). URL base = 기본 로컬 서빙 라우트("/captures").
    # ★ 11주차 교체 지점: 실 public 호스팅(EC2 static route / 오브젝트 스토리지)으로 이관 시
    # 이 두 값만 실 host 경로/URL 로 바꾸면 image_store 배선 불변으로 교체된다.
    CAPTURE_STORE_DIR = os.environ.get(
        "DDINGDONG_CAPTURE_DIR", os.path.join(BASE_DIR, "instance", "captures")
    )
    CAPTURE_URL_BASE = os.environ.get("DDINGDONG_CAPTURE_URL_BASE", "/captures")
