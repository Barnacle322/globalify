# from ..project.models import User
import pytest

from ..project import create_app, db


@pytest.fixture()
def app():
    app = create_app("sqlite:///test_db.sqlite")
    app.config.update({"WTF_CSRF_ENABLED": False, "DEBUG_TB_ENABLED": False})
    app.config["SERVER_NAME"] = "localhost"
    app.config["APPLICATION_ROOT"] = ""
    app.config["PREFERRED_URL_SCHEME"] = "http"

    with app.app_context():
        db.drop_all()
        db.create_all()

    yield app


@pytest.fixture()
def client(app):
    return app.test_client()
