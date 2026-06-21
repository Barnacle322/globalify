import pytest
from pydantic import ValidationError

from project.config import Environment, Settings


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "abc123")
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setenv("_DATABASE_URL", "sqlite:///x.db")
    monkeypatch.setenv("SQLALCHEMY_POOL_SIZE", "7")

    settings = Settings(_env_file=None)

    assert settings.secret_key == "abc123"
    assert settings.env is Environment.TESTING
    assert settings.is_testing is True
    assert settings.database_url == "sqlite:///x.db"
    assert settings.sqlalchemy_pool_size == 7


def test_secret_key_is_required(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_database_url_has_safe_default(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "abc123")
    monkeypatch.delenv("_DATABASE_URL", raising=False)
    settings = Settings(_env_file=None)
    assert settings.database_url == "sqlite:///db.sqlite"
