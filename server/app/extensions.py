"""Flask 확장 인스턴스. app factory 와 분리해 순환 import 를 막는다."""

from flask_sqlalchemy import SQLAlchemy

# create_app 안에서 db.init_app(app) 으로 앱에 바인딩한다.
db = SQLAlchemy()
