from ..project import create_app, db
from ..project.models import User
import pytest


@pytest.fixture(scope="module")
def app():
    app = create_app("sqlite:///test_db.sqlite")
    with app.app_context():
        db.drop_all()
        db.create_all()

    yield app


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()
