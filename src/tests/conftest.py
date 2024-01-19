# from ..project.models import User
import pytest

from ..project import create_app, db


@pytest.fixture()
def app():
    app = create_app("sqlite:///test_db.sqlite")
    app.config.update({"WTF_CSRF_ENABLED": False})

    with app.app_context():
        db.drop_all()
        db.create_all()

    yield app


@pytest.fixture()
def client(app):
    return app.test_client()
