# from ..project.models import User
import os

import pytest

from ..project import create_app, db


@pytest.fixture()
def app():
    os.environ["FLASK_ENV"] = "testing"
    app = create_app("sqlite:///test_db.sqlite")
    app.config["SERVER_NAME"] = "127.0.0.1"
    app.config["APPLICATION_ROOT"] = ""
    app.config["PREFERRED_URL_SCHEME"] = "http"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test_db.sqlite"
    app.config["DEBUG_TB_ENABLED"] = False
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["DEBUG"] = False

    with app.app_context():
        db.drop_all()
        db.create_all()

    yield app


@pytest.fixture()
def client(app):
    return app.test_client()
