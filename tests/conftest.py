"""Shared pytest fixtures.

Sets dummy environment variables BEFORE importing the application,
so the app is importable without real credentials.
"""

import os
import sys

# --- env defaults (must run before `project` is imported) ---
os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("_DATABASE_URL", "sqlite:///test_db.sqlite")

import pytest  # noqa: E402


@pytest.fixture
def app():
    # import lazily so the env above is in place first
    if "project" in sys.modules:
        del sys.modules["project"]
    from project import create_app

    application = create_app()
    application.config.update(TESTING=True)
    return application


@pytest.fixture
def client(app):
    return app.test_client()
