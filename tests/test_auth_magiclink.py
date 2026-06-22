"""Tests for magic-link passwordless auth.

TDD: written before the implementation; run `uv run pytest tests/test_auth_magiclink.py`
to see them fail, then pass once the implementation is in place.
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_app(app):
    """App with a fully-created, in-memory SQLite schema."""
    from project.extensions import db as _db

    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


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
# LoginToken model tests
# ---------------------------------------------------------------------------


class TestLoginTokenIssueAndVerify:
    """Happy-path: issue a token and verify+consume it returns the user."""

    def test_issue_returns_raw_string(self, db_app):
        from project.extensions import db
        from project.models import LoginToken

        with db_app.app_context():
            user = _make_user(db, "happy@example.com")
            db.session.commit()

            raw = LoginToken.issue(user, "login")
            assert isinstance(raw, str)
            assert len(raw) > 20  # raw token is urlsafe(32) → 43 chars

    def test_verify_and_consume_returns_user(self, db_app):
        from project.extensions import db
        from project.models import LoginToken

        with db_app.app_context():
            user = _make_user(db, "consume@example.com")
            db.session.commit()
            user_id = user.id

            raw = LoginToken.issue(user, "login")
            result = LoginToken.verify_and_consume(raw, "login")

            assert result is not None
            assert result.id == user_id

    def test_token_is_marked_consumed(self, db_app):
        from project.extensions import db
        from project.models import LoginToken

        with db_app.app_context():
            user = _make_user(db, "mark@example.com")
            db.session.commit()

            raw = LoginToken.issue(user, "login")
            LoginToken.verify_and_consume(raw, "login")

            # Second call with same token must return None
            result2 = LoginToken.verify_and_consume(raw, "login")
            assert result2 is None


class TestLoginTokenExpiry:
    """Expired token must be rejected."""

    def test_expired_token_returns_none(self, db_app):
        from project.extensions import db
        from project.models import LoginToken

        with db_app.app_context():
            user = _make_user(db, "expired@example.com")
            db.session.commit()

            # Issue with a TTL of 0 minutes → already expired
            raw = LoginToken.issue(user, "login", ttl_minutes=0)
            result = LoginToken.verify_and_consume(raw, "login")
            assert result is None


class TestLoginTokenAlreadyConsumed:
    """Already-consumed token must be rejected."""

    def test_double_consume_returns_none(self, db_app):
        from project.extensions import db
        from project.models import LoginToken

        with db_app.app_context():
            user = _make_user(db, "double@example.com")
            db.session.commit()

            raw = LoginToken.issue(user, "login")
            first = LoginToken.verify_and_consume(raw, "login")
            assert first is not None

            second = LoginToken.verify_and_consume(raw, "login")
            assert second is None


class TestLoginTokenWrongPurpose:
    """Token issued for one purpose must not be accepted for another."""

    def test_wrong_purpose_rejected(self, db_app):
        from project.extensions import db
        from project.models import LoginToken

        with db_app.app_context():
            user = _make_user(db, "purpose@example.com")
            db.session.commit()

            raw = LoginToken.issue(user, "login")
            result = LoginToken.verify_and_consume(raw, "reset")
            assert result is None


class TestLoginTokenTampered:
    """A token that doesn't match any hash in the DB must return None."""

    def test_tampered_token_rejected(self, db_app):
        from project.extensions import db
        from project.models import LoginToken

        with db_app.app_context():
            user = _make_user(db, "tamper@example.com")
            db.session.commit()

            raw = LoginToken.issue(user, "login")
            tampered = raw[:-3] + "AAA"
            result = LoginToken.verify_and_consume(tampered, "login")
            assert result is None


# ---------------------------------------------------------------------------
# Route: POST /login
# ---------------------------------------------------------------------------


class TestPostLogin:
    """POST /login must create a token and call send_magic_link."""

    def test_creates_token_and_calls_send_stub(self, db_app, client, caplog):
        """POST /login creates a LoginToken row and logs the magic link."""
        import logging

        from project.extensions import db
        from project.models import LoginToken

        with db_app.app_context():
            _make_user(db, "postlogin@example.com")
            db.session.commit()

        with caplog.at_level(logging.INFO, logger="project"):
            response = client.post(
                "/login",
                data={"email": "postlogin@example.com"},
                follow_redirects=False,
            )

        # Must redirect (to check-your-email state)
        assert response.status_code in (302, 303)

        with db_app.app_context():
            from project.models import LoginToken

            tokens = db.session.scalars(db.select(LoginToken)).all()
            assert len(tokens) >= 1

        # Stub logger must have logged the link
        assert any("postlogin@example.com" in r.message for r in caplog.records)

    def test_creates_user_if_not_exists(self, db_app, client, caplog):
        """POST /login with unknown email must create the User (find-or-create)."""
        import logging

        from project.models import User

        with caplog.at_level(logging.INFO, logger="project"):
            client.post(
                "/login",
                data={"email": "brandnew@example.com"},
                follow_redirects=False,
            )

        with db_app.app_context():
            user = User.get_by_email("brandnew@example.com")
            assert user is not None


# ---------------------------------------------------------------------------
# Route: GET /auth/verify?token=<valid>
# ---------------------------------------------------------------------------


class TestGetVerifyMagicLink:
    """GET /auth/verify?token=<valid> must log the user in."""

    def test_valid_token_logs_in(self, db_app, client):
        """After visiting the verify URL the session should contain _user_id."""
        from project.extensions import db
        from project.models import LoginToken

        with db_app.app_context():
            user = _make_user(db, "verifylogin@example.com")
            db.session.commit()
            user_id = user.id
            raw = LoginToken.issue(user, "login")

        response = client.get(f"/auth/verify?token={raw}", follow_redirects=False)
        assert response.status_code in (302, 303)

        # After the redirect the session should carry _user_id
        with client.session_transaction() as sess:
            assert sess.get("_user_id") == str(user_id)

    def test_invalid_token_redirects_to_login(self, db_app, client):
        """Invalid token must redirect to /login, not 500."""
        response = client.get("/auth/verify?token=not-a-real-token", follow_redirects=False)
        assert response.status_code in (302, 303)
        location = response.headers.get("Location", "")
        assert "login" in location

    def test_missing_token_redirects_to_login(self, db_app, client):
        """Missing token param must redirect to /login."""
        response = client.get("/auth/verify", follow_redirects=False)
        assert response.status_code in (302, 303)
        location = response.headers.get("Location", "")
        assert "login" in location
