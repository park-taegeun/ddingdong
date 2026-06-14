"""로컬 개발 서버 진입점.

실행:
    python run.py          # 직접 실행
    flask --app run run    # Flask CLI

배포(11주차)는 Gunicorn `run:app` 를 사용한다 (카테고리 6).
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    # 카테고리 8.1: Phase 2-1 은 로컬 M4, http://127.0.0.1:5000 단독 (TLS 는 11주차)
    app.run(host="127.0.0.1", port=5000, debug=True)
