import pytest
from pydantic import ValidationError


def test_app_boots(app):
    assert app is not None
    assert app.testing is True


def test_expected_blueprints_registered(app):
    for name in ("auth", "main", "search", "settings", "profile", "admin"):
        assert name in app.blueprints


def test_app_handles_a_request(client):
    # an unknown path should still route through the app (proves it serves)
    response = client.get("/this-path-does-not-exist")
    assert response.status_code in (404, 308)


def test_create_app_requires_secret_key(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    import sys

    sys.modules.pop("project", None)

    with pytest.raises(ValidationError):
        from project import create_app  # noqa: F401
