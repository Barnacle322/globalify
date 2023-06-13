import os
from datetime import timedelta

from flask import Flask

from .extensions import db, login_manager
from .routes.main import main, page_not_found, unauthorized


def create_app(DATABASE_URL=os.getenv("_DATABASE_URL", "sqlite:///db.sqlite")):
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["REMEMBER_COOKIE_DURATION"] = timedelta(days=30)
    app.secret_key = os.getenv("SECRET_KEY", os.urandom(32))

    app.register_blueprint(main)

    app.register_error_handler(404, page_not_found)
    app.register_error_handler(401, unauthorized)

    db.init_app(app)
    login_manager.init_app(app)

    return app


application = create_app()
