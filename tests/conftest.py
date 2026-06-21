"""Shared pytest fixtures.

Sets dummy environment variables and neutralizes import-time network clients
BEFORE importing the application, so the app is importable without real
credentials (matching the dormant app's import-time client construction).
"""

import os
import sys
from unittest import mock

# --- env defaults (must run before `project` is imported) ---
os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("_DATABASE_URL", "sqlite:///test_db.sqlite")
# googlemaps.Client validates that the key starts with "AIza"; use a conforming dummy
os.environ.setdefault("_GOOGLE_MAPS_API_KEY", "AIzatest-maps-key")

# --- neutralize the Pub/Sub client that constructs at import with real creds ---
from google.cloud import pubsub_v1  # noqa: E402

pubsub_v1.PublisherClient.from_service_account_info = mock.MagicMock(return_value=mock.MagicMock())

import pytest  # noqa: E402


@pytest.fixture
def app():
    # import lazily so the env + patches above are in place first
    if "project" in sys.modules:
        del sys.modules["project"]
    from project import create_app

    application = create_app()
    application.config.update(TESTING=True)
    return application


@pytest.fixture
def client(app):
    return app.test_client()
