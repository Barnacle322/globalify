"""Tests for Cap captcha integration — NO network calls.

TDD: written before the implementation.

Groups:
  (a) verify_captcha unconfigured → always True (skip-mode for dev/test/CI).
  (b) verify_captcha configured + mocked HTTP: success→True, failure→False,
      exception→False, None-token→False (no network call).
  (c) POST /login with Cap configured + failing verify → rejected.
  (d) POST /login unconfigured → token issued as before.
  (e) Settings: cap_is_configured property.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings(**overrides):
    """Build a Settings object with test defaults, bypassing .env."""
    envs = {
        "SECRET_KEY": "test-secret",
        "FLASK_ENV": "testing",
        "_DATABASE_URL": "sqlite:///test.sqlite",
    }
    envs.update(overrides)
    with patch.dict(os.environ, envs, clear=False):
        from project.config import Settings

        return Settings(_env_file=None)


def _make_user(db, email: str, *, is_verified: bool = True):
    from project.models import User, UserInfo, UserPayment

    user = User(email=email, is_verified=is_verified)
    db.session.add(user)
    db.session.flush()

    user_info = UserInfo(
        first_name="Test",
        last_name="User",
        username=f"testuser_{user.id}",
        is_complete=True,
        user=user,
    )
    db.session.add(user_info)

    payment = UserPayment(user=user)
    db.session.add(payment)
    db.session.flush()
    return user


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


import pytest  # noqa: E402


@pytest.fixture()
def db_app(app):
    """App with a fully-created, in-memory SQLite schema."""
    from project.extensions import db as _db

    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


# ---------------------------------------------------------------------------
# (a) verify_captcha unconfigured → always True
# ---------------------------------------------------------------------------


class TestVerifyCaptchaUnconfigured:
    """When Cap env vars are absent, verify_captcha must skip and return True."""

    def test_none_token_returns_true_when_unconfigured(self, monkeypatch):
        """verify_captcha(None) → True when Cap is not configured."""
        for var in ("_CAP_API_ENDPOINT", "_CAP_SITE_KEY", "_CAP_SECRET"):
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("SECRET_KEY", "test-secret")
        monkeypatch.setenv("FLASK_ENV", "testing")
        monkeypatch.setenv("_DATABASE_URL", "sqlite:///test.sqlite")

        from project.config import Settings
        from project.utils import cap as cap_module

        settings = Settings(_env_file=None)
        monkeypatch.setattr(cap_module, "_settings", settings)

        assert cap_module.verify_captcha(None) is True

    def test_empty_token_returns_true_when_unconfigured(self, monkeypatch):
        """verify_captcha('') → True when Cap is not configured."""
        for var in ("_CAP_API_ENDPOINT", "_CAP_SITE_KEY", "_CAP_SECRET"):
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("SECRET_KEY", "test-secret")
        monkeypatch.setenv("FLASK_ENV", "testing")
        monkeypatch.setenv("_DATABASE_URL", "sqlite:///test.sqlite")

        from project.config import Settings
        from project.utils import cap as cap_module

        settings = Settings(_env_file=None)
        monkeypatch.setattr(cap_module, "_settings", settings)

        assert cap_module.verify_captcha("") is True

    def test_any_token_returns_true_when_unconfigured(self, monkeypatch):
        """verify_captcha('some-token') → True when Cap is not configured."""
        for var in ("_CAP_API_ENDPOINT", "_CAP_SITE_KEY", "_CAP_SECRET"):
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("SECRET_KEY", "test-secret")
        monkeypatch.setenv("FLASK_ENV", "testing")
        monkeypatch.setenv("_DATABASE_URL", "sqlite:///test.sqlite")

        from project.config import Settings
        from project.utils import cap as cap_module

        settings = Settings(_env_file=None)
        monkeypatch.setattr(cap_module, "_settings", settings)

        assert cap_module.verify_captcha("some-token") is True

    def test_no_network_call_when_unconfigured(self, monkeypatch):
        """requests.post must never be called when Cap is not configured."""
        for var in ("_CAP_API_ENDPOINT", "_CAP_SITE_KEY", "_CAP_SECRET"):
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("SECRET_KEY", "test-secret")
        monkeypatch.setenv("FLASK_ENV", "testing")
        monkeypatch.setenv("_DATABASE_URL", "sqlite:///test.sqlite")

        from project.config import Settings
        from project.utils import cap as cap_module

        settings = Settings(_env_file=None)
        monkeypatch.setattr(cap_module, "_settings", settings)

        mock_post = MagicMock(side_effect=AssertionError("requests.post must NOT be called when unconfigured"))
        monkeypatch.setattr(cap_module.requests, "post", mock_post)

        cap_module.verify_captcha("token")

        mock_post.assert_not_called()


# ---------------------------------------------------------------------------
# (b) verify_captcha configured + mocked HTTP
# ---------------------------------------------------------------------------


class TestVerifyCaptchaConfigured:
    """When Cap is configured, verify_captcha calls siteverify and parses the result."""

    def _configure(self, monkeypatch):
        monkeypatch.setenv("_CAP_API_ENDPOINT", "https://cap.example.com")
        monkeypatch.setenv("_CAP_SITE_KEY", "test-site-key")
        monkeypatch.setenv("_CAP_SECRET", "test-secret-key")
        monkeypatch.setenv("SECRET_KEY", "test-secret")
        monkeypatch.setenv("FLASK_ENV", "testing")
        monkeypatch.setenv("_DATABASE_URL", "sqlite:///test.sqlite")

    def _set_settings(self, monkeypatch):
        from project.config import Settings
        from project.utils import cap as cap_module

        settings = Settings(_env_file=None)
        monkeypatch.setattr(cap_module, "_settings", settings)
        return cap_module

    def test_success_true_returns_true(self, monkeypatch):
        """When siteverify returns {'success': True}, verify_captcha returns True."""
        self._configure(monkeypatch)
        cap_module = self._set_settings(monkeypatch)

        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True}
        mock_post = MagicMock(return_value=mock_response)
        monkeypatch.setattr(cap_module.requests, "post", mock_post)

        result = cap_module.verify_captcha("valid-token")

        assert result is True
        mock_post.assert_called_once()

    def test_success_false_returns_false(self, monkeypatch):
        """When siteverify returns {'success': False}, verify_captcha returns False."""
        self._configure(monkeypatch)
        cap_module = self._set_settings(monkeypatch)

        mock_response = MagicMock()
        mock_response.json.return_value = {"success": False}
        mock_post = MagicMock(return_value=mock_response)
        monkeypatch.setattr(cap_module.requests, "post", mock_post)

        result = cap_module.verify_captcha("invalid-token")

        assert result is False

    def test_network_exception_returns_false(self, monkeypatch):
        """When requests.post raises (timeout/network), verify_captcha returns False (fail-closed)."""
        self._configure(monkeypatch)
        cap_module = self._set_settings(monkeypatch)

        import requests as req_lib

        mock_post = MagicMock(side_effect=req_lib.exceptions.Timeout("timed out"))
        monkeypatch.setattr(cap_module.requests, "post", mock_post)

        result = cap_module.verify_captcha("some-token")

        assert result is False

    def test_none_token_returns_false_without_network_call(self, monkeypatch):
        """When configured and token is None, verify_captcha returns False without network call."""
        self._configure(monkeypatch)
        cap_module = self._set_settings(monkeypatch)

        mock_post = MagicMock(side_effect=AssertionError("requests.post must NOT be called for None token"))
        monkeypatch.setattr(cap_module.requests, "post", mock_post)

        result = cap_module.verify_captcha(None)

        assert result is False
        mock_post.assert_not_called()

    def test_empty_token_returns_false_without_network_call(self, monkeypatch):
        """When configured and token is empty string, verify_captcha returns False without network call."""
        self._configure(monkeypatch)
        cap_module = self._set_settings(monkeypatch)

        mock_post = MagicMock(side_effect=AssertionError("requests.post must NOT be called for empty token"))
        monkeypatch.setattr(cap_module.requests, "post", mock_post)

        result = cap_module.verify_captcha("")

        assert result is False
        mock_post.assert_not_called()

    def test_siteverify_url_is_correct(self, monkeypatch):
        """verify_captcha POSTs to {cap_api_endpoint}/{cap_site_key}/siteverify."""
        self._configure(monkeypatch)
        cap_module = self._set_settings(monkeypatch)

        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True}
        mock_post = MagicMock(return_value=mock_response)
        monkeypatch.setattr(cap_module.requests, "post", mock_post)

        cap_module.verify_captcha("my-token")

        call_args = mock_post.call_args
        url = call_args[0][0] if call_args[0] else call_args[1].get("url", call_args[0][0])
        assert url == "https://cap.example.com/test-site-key/siteverify"

    def test_siteverify_posts_secret_and_response(self, monkeypatch):
        """verify_captcha sends {secret, response} in the request body."""
        self._configure(monkeypatch)
        cap_module = self._set_settings(monkeypatch)

        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True}
        mock_post = MagicMock(return_value=mock_response)
        monkeypatch.setattr(cap_module.requests, "post", mock_post)

        cap_module.verify_captcha("my-token")

        call_kwargs = mock_post.call_args[1]
        # Could be json= or data= — check both
        payload = call_kwargs.get("json") or call_kwargs.get("data") or {}
        assert payload.get("secret") == "test-secret-key"
        assert payload.get("response") == "my-token"

    def test_trailing_slash_stripped_from_endpoint(self, monkeypatch):
        """Trailing slash on cap_api_endpoint must not double up in the URL."""
        monkeypatch.setenv("_CAP_API_ENDPOINT", "https://cap.example.com/")
        # site key carried in the path: {endpoint}/{site_key}/siteverify
        monkeypatch.setenv("_CAP_SITE_KEY", "test-site-key")
        monkeypatch.setenv("_CAP_SECRET", "test-secret-key")
        monkeypatch.setenv("SECRET_KEY", "test-secret")
        monkeypatch.setenv("FLASK_ENV", "testing")
        monkeypatch.setenv("_DATABASE_URL", "sqlite:///test.sqlite")

        from project.config import Settings
        from project.utils import cap as cap_module

        settings = Settings(_env_file=None)
        monkeypatch.setattr(cap_module, "_settings", settings)

        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True}
        mock_post = MagicMock(return_value=mock_response)
        monkeypatch.setattr(cap_module.requests, "post", mock_post)

        cap_module.verify_captcha("token")

        call_url = mock_post.call_args[0][0]
        assert call_url == "https://cap.example.com/test-site-key/siteverify"
        assert "//" not in call_url.replace("://", "")


# ---------------------------------------------------------------------------
# (c) POST /login with Cap configured + failing verify → rejected
# ---------------------------------------------------------------------------


class TestLoginCapConfigured:
    """POST /login with Cap configured: failing captcha must be rejected."""

    def test_failing_captcha_rejects_login_no_token_created(self, db_app, client, monkeypatch):
        """When Cap configured + verify returns False: redirect back, no LoginToken created."""
        from project.extensions import db
        from project.models import LoginToken

        with db_app.app_context():
            _make_user(db, "cap_reject@example.com")
            db.session.commit()

        # Patch verify_captcha where it is used (imported into auth route module)
        import project.routes.auth as auth_module

        monkeypatch.setattr(auth_module, "verify_captcha", lambda token: False)

        response = client.post(
            "/login",
            data={"email": "cap_reject@example.com"},
            follow_redirects=False,
        )

        # Must redirect (to login with error)
        assert response.status_code in (302, 303)
        location = response.headers.get("Location", "")
        assert "login" in location

        # No LoginToken must be created
        with db_app.app_context():
            tokens = db.session.scalars(db.select(LoginToken)).all()
            assert len(tokens) == 0, f"LoginToken was created despite captcha failure: {tokens}"

    def test_passing_captcha_allows_login(self, db_app, client, monkeypatch, caplog):
        """When Cap configured + verify returns True: token issued normally."""
        import logging

        from project.extensions import db
        from project.models import LoginToken

        with db_app.app_context():
            _make_user(db, "cap_pass@example.com")
            db.session.commit()

        # Patch verify_captcha where it is used (imported into auth route module)
        import project.routes.auth as auth_module

        monkeypatch.setattr(auth_module, "verify_captcha", lambda token: True)

        with caplog.at_level(logging.INFO, logger="project"):
            response = client.post(
                "/login",
                data={"email": "cap_pass@example.com", "cap-token": "valid-cap-token"},
                follow_redirects=False,
            )

        assert response.status_code in (302, 303)

        with db_app.app_context():
            tokens = db.session.scalars(db.select(LoginToken)).all()
            assert len(tokens) >= 1


# ---------------------------------------------------------------------------
# (d) POST /login unconfigured → token issued as before
# ---------------------------------------------------------------------------


class TestLoginCapUnconfigured:
    """POST /login without Cap config must work exactly as before."""

    def test_login_still_works_without_cap_config(self, db_app, client, caplog, monkeypatch):
        """POST /login without Cap env vars issues a token (no captcha check)."""
        import logging

        from project.extensions import db
        from project.models import LoginToken

        # Ensure Cap vars are absent
        for var in ("_CAP_API_ENDPOINT", "_CAP_SITE_KEY", "_CAP_SECRET"):
            monkeypatch.delenv(var, raising=False)

        with db_app.app_context():
            _make_user(db, "unconfigured@example.com")
            db.session.commit()

        with caplog.at_level(logging.INFO, logger="project"):
            response = client.post(
                "/login",
                data={"email": "unconfigured@example.com"},
                follow_redirects=False,
            )

        assert response.status_code in (302, 303)

        with db_app.app_context():
            tokens = db.session.scalars(db.select(LoginToken)).all()
            assert len(tokens) >= 1


# ---------------------------------------------------------------------------
# (e) Settings: cap_is_configured property
# ---------------------------------------------------------------------------


class TestCapIsConfigured:
    """Settings.cap_is_configured returns True only when endpoint + site key + secret are all set.

    Current Cap carries the site key in the URL path, so it is required.
    """

    def test_false_when_no_cap_vars(self, monkeypatch):
        for var in ("_CAP_API_ENDPOINT", "_CAP_SITE_KEY", "_CAP_SECRET"):
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("SECRET_KEY", "test-secret")
        monkeypatch.setenv("FLASK_ENV", "testing")

        from project.config import Settings

        settings = Settings(_env_file=None)
        assert settings.cap_is_configured is False

    def test_false_when_only_endpoint_set(self, monkeypatch):
        monkeypatch.setenv("_CAP_API_ENDPOINT", "https://cap.example.com")
        monkeypatch.delenv("_CAP_SECRET", raising=False)
        monkeypatch.delenv("_CAP_SITE_KEY", raising=False)
        monkeypatch.setenv("SECRET_KEY", "test-secret")
        monkeypatch.setenv("FLASK_ENV", "testing")

        from project.config import Settings

        settings = Settings(_env_file=None)
        assert settings.cap_is_configured is False

    def test_false_when_only_secret_set(self, monkeypatch):
        monkeypatch.delenv("_CAP_API_ENDPOINT", raising=False)
        monkeypatch.setenv("_CAP_SECRET", "secret123")
        monkeypatch.delenv("_CAP_SITE_KEY", raising=False)
        monkeypatch.setenv("SECRET_KEY", "test-secret")
        monkeypatch.setenv("FLASK_ENV", "testing")

        from project.config import Settings

        settings = Settings(_env_file=None)
        assert settings.cap_is_configured is False

    def test_false_when_site_key_missing(self, monkeypatch):
        """Endpoint + secret without a site key is NOT configured (site key is in the URL path)."""
        monkeypatch.setenv("_CAP_API_ENDPOINT", "https://cap.example.com")
        monkeypatch.setenv("_CAP_SECRET", "secret123")
        monkeypatch.delenv("_CAP_SITE_KEY", raising=False)
        monkeypatch.setenv("SECRET_KEY", "test-secret")
        monkeypatch.setenv("FLASK_ENV", "testing")

        from project.config import Settings

        settings = Settings(_env_file=None)
        assert settings.cap_is_configured is False

    def test_true_when_all_cap_vars_set(self, monkeypatch):
        monkeypatch.setenv("_CAP_API_ENDPOINT", "https://cap.example.com")
        monkeypatch.setenv("_CAP_SITE_KEY", "site-key")
        monkeypatch.setenv("_CAP_SECRET", "secret123")
        monkeypatch.setenv("SECRET_KEY", "test-secret")
        monkeypatch.setenv("FLASK_ENV", "testing")

        from project.config import Settings

        settings = Settings(_env_file=None)
        assert settings.cap_is_configured is True
