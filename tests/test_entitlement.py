"""Tests for Pro entitlement logic and Pro-gated UI.

Covers:
- User.is_pro property (default, granted, expiry logic)
- UserPayment.grant_pro / revoke_pro helpers
- GET /pricing returns 200 (paddle NOT configured in test env)
- Pro user sees contact info on person profile
- Non-Pro authenticated user sees "Unlock with Pro" on person profile
- Anonymous user does NOT see contact email on person profile
"""

from __future__ import annotations

import datetime

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


def _make_user(db, email: str, *, is_admin: bool = False, is_verified: bool = True):
    """Create a User + UserInfo + UserPayment and return the flushed User."""
    from project.models import User, UserInfo, UserPayment

    user = User(email=email, is_verified=is_verified, is_admin=is_admin)
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


def _login(client, app, user_id: int):
    """Inject a Flask-Login session so current_user resolves to the given user."""
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True


def _make_person(db, *, slug: str, email: str = "investor@example.com"):
    """Create a public Person with an email address."""
    from project.models import Person

    person = Person(
        first_name="Jane",
        last_name="Doe",
        slug=slug,
        is_public=True,
        is_approved=True,
        email=email,
    )
    db.session.add(person)
    db.session.flush()
    return person


# ---------------------------------------------------------------------------
# Unit tests — User.is_pro property
# ---------------------------------------------------------------------------


class TestUserIsProProperty:
    """User.is_pro reflects UserPayment.is_pro flag and expiry."""

    def test_is_pro_false_by_default(self, db_app):
        """Newly created user with UserPayment has is_pro=False."""
        from project.extensions import db

        with db_app.app_context():
            user = _make_user(db, "default@example.com")
            db.session.commit()
            assert user.is_pro is False

    def test_grant_pro_lifetime(self, db_app):
        """grant_pro('lifetime') without expiry sets is_pro=True indefinitely."""
        from project.extensions import db

        with db_app.app_context():
            user = _make_user(db, "lifetime@example.com")
            db.session.commit()
            user.user_payment.grant_pro("lifetime")
            assert user.is_pro is True

    def test_grant_pro_with_future_expiry(self, db_app):
        """grant_pro with a future expiry still returns True."""
        from project.extensions import db

        with db_app.app_context():
            user = _make_user(db, "future@example.com")
            db.session.commit()
            future = datetime.datetime.now(datetime.UTC).replace(tzinfo=None) + datetime.timedelta(days=30)
            user.user_payment.grant_pro("subscription", future)
            assert user.is_pro is True

    def test_pro_expired_returns_false(self, db_app):
        """is_pro returns False when pro_expires_at is in the past."""
        from project.extensions import db

        with db_app.app_context():
            user = _make_user(db, "expired@example.com")
            db.session.commit()
            past = datetime.datetime.now(datetime.UTC).replace(tzinfo=None) - datetime.timedelta(days=1)
            user.user_payment.is_pro = True
            user.user_payment.pro_source = "subscription"
            user.user_payment.pro_expires_at = past
            db.session.commit()
            assert user.is_pro is False

    def test_revoke_pro(self, db_app):
        """revoke_pro() sets is_pro back to False."""
        from project.extensions import db

        with db_app.app_context():
            user = _make_user(db, "revoke@example.com")
            db.session.commit()
            user.user_payment.grant_pro("lifetime")
            assert user.is_pro is True
            user.user_payment.revoke_pro()
            assert user.is_pro is False


# ---------------------------------------------------------------------------
# Route test — /pricing
# ---------------------------------------------------------------------------


class TestPricingRoute:
    def test_pricing_returns_200(self, db_app, client):
        """/pricing must return 200 even with Paddle NOT configured (test env)."""
        with db_app.app_context():
            pass  # just ensure schema is set up

        resp = client.get("/pricing")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.data[:300]}"

    def test_pricing_shows_coming_soon_without_paddle(self, db_app, client):
        """When paddle_is_configured is False, page shows 'Coming soon' copy."""
        resp = client.get("/pricing")
        assert b"Coming soon" in resp.data


# ---------------------------------------------------------------------------
# Profile DOM tests — Pro gating on person profile
# ---------------------------------------------------------------------------


class TestPersonProfileProGating:
    """Person profile contact section branches on viewer_is_pro."""

    def test_pro_user_sees_contact_email(self, db_app, client):
        """Authenticated Pro user sees the investor's email in the DOM."""
        from project.extensions import db

        with db_app.app_context():
            user = _make_user(db, "pro_viewer@example.com")
            db.session.commit()
            user.user_payment.grant_pro("lifetime")
            user_id = user.id
            person = _make_person(db, slug="jane-doe-pro", email="jane.contact@example.com")
            db.session.commit()
            slug = person.slug

        _login(client, db_app, user_id)
        resp = client.get(f"/investors/{slug}", follow_redirects=False)
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.data[:300]}"
        assert b"jane.contact@example.com" in resp.data, "Pro viewer should see the contact email"

    def test_non_pro_user_sees_unlock_cta(self, db_app, client):
        """Authenticated non-Pro user does NOT see the contact email, sees CTA instead."""
        from project.extensions import db

        with db_app.app_context():
            user = _make_user(db, "free_viewer@example.com")
            db.session.commit()
            user_id = user.id
            person = _make_person(db, slug="jane-doe-free", email="jane.contact2@example.com")
            db.session.commit()
            slug = person.slug

        _login(client, db_app, user_id)
        resp = client.get(f"/investors/{slug}", follow_redirects=False)
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.data[:300]}"
        assert b"jane.contact2@example.com" not in resp.data, "Non-Pro viewer should NOT see the contact email"
        assert b"Unlock with Pro" in resp.data, "Non-Pro viewer should see the Pro upsell CTA"

    def test_anonymous_user_does_not_see_contact_email(self, db_app, client):
        """Anonymous (unauthenticated) user does NOT see the contact email."""
        from project.extensions import db

        with db_app.app_context():
            person = _make_person(db, slug="jane-doe-anon", email="jane.contact3@example.com")
            db.session.commit()
            slug = person.slug

        resp = client.get(f"/investors/{slug}", follow_redirects=False)
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.data[:300]}"
        assert b"jane.contact3@example.com" not in resp.data, "Anonymous user should NOT see the contact email"
