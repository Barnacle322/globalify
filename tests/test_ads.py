"""Tests for free-tier ad slots (Phase 4, Task 3).

Covers:
- ads_enabled config flag (default False)
- show_ads context processor logic
- Ad slot markup appears for anonymous viewers when ads_enabled=True
- Ad slot markup does NOT appear for Pro users even when ads_enabled=True
- Ad slot markup does NOT appear for anyone when ads_enabled=False (default)
- Ad slot appears on browse page (/investors) and profile page (/investors/<slug>)
"""

from __future__ import annotations

import sys

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


@pytest.fixture()
def ads_app(monkeypatch):
    """App fixture with _ADS_ENABLED=true in the environment."""
    monkeypatch.setenv("_ADS_ENABLED", "true")
    # Force re-import so the new env var is picked up
    for mod in list(sys.modules.keys()):
        if mod == "project" or mod.startswith("project."):
            del sys.modules[mod]
    from project import create_app

    application = create_app()
    application.config.update(TESTING=True)
    return application


@pytest.fixture()
def ads_db_app(ads_app):
    """ads_app with fully-created schema."""
    from project.extensions import db as _db

    with ads_app.app_context():
        _db.create_all()
        yield ads_app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def ads_client(ads_app):
    return ads_app.test_client()


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
    """Create a public Person."""
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


# A distinctive string that must appear in _ad_slot.html
AD_MARKER = b"data-ad-slot"


# ---------------------------------------------------------------------------
# Unit tests — config flag
# ---------------------------------------------------------------------------


class TestAdsEnabledConfig:
    """ads_enabled defaults to False; can be set via _ADS_ENABLED env var."""

    def test_ads_enabled_defaults_false(self, app):
        """ads_enabled is False when _ADS_ENABLED is not set."""
        from project.config import get_settings

        with app.app_context():
            cfg = get_settings()
            assert cfg.ads_enabled is False

    def test_ads_enabled_true_via_env(self, ads_app):
        """ads_enabled is True when _ADS_ENABLED=true is in the environment."""
        from project.config import get_settings

        with ads_app.app_context():
            cfg = get_settings()
            assert cfg.ads_enabled is True


# ---------------------------------------------------------------------------
# Unit tests — show_ads context processor
# ---------------------------------------------------------------------------


class TestShowAdsContextProcessor:
    """show_ads = ads_enabled AND NOT (authenticated AND Pro)."""

    def test_show_ads_false_when_ads_disabled(self, db_app, client):
        """With ads_enabled=False (default), show_ads is False for anonymous user."""
        with db_app.app_context():
            pass  # ensure schema

        resp = client.get("/investors")
        assert resp.status_code == 200
        assert AD_MARKER not in resp.data, "Ad slot must not appear when ads_enabled=False"

    def test_show_ads_true_for_anonymous_when_ads_enabled(self, ads_db_app, ads_client):
        """Anonymous viewer sees ad slot when ads_enabled=True."""
        with ads_db_app.app_context():
            pass  # ensure schema

        resp = ads_client.get("/investors")
        assert resp.status_code == 200
        assert AD_MARKER in resp.data, "Ad slot must appear for anonymous viewer when ads_enabled=True"

    def test_show_ads_true_for_free_user_when_ads_enabled(self, ads_db_app, ads_client):
        """Authenticated free (non-Pro) user sees ad slot when ads_enabled=True."""
        from project.extensions import db

        with ads_db_app.app_context():
            user = _make_user(db, "free_ads@example.com")
            db.session.commit()
            user_id = user.id

        _login(ads_client, ads_db_app, user_id)
        resp = ads_client.get("/investors")
        assert resp.status_code == 200
        assert AD_MARKER in resp.data, "Free user should see ad slot when ads_enabled=True"

    def test_show_ads_false_for_pro_user_when_ads_enabled(self, ads_db_app, ads_client):
        """Pro user NEVER sees ad slot, even when ads_enabled=True."""
        from project.extensions import db

        with ads_db_app.app_context():
            user = _make_user(db, "pro_ads@example.com")
            db.session.commit()
            user.user_payment.grant_pro("lifetime")
            user_id = user.id

        _login(ads_client, ads_db_app, user_id)
        resp = ads_client.get("/investors")
        assert resp.status_code == 200
        assert AD_MARKER not in resp.data, "Pro user must NOT see ad slot even when ads_enabled=True"


# ---------------------------------------------------------------------------
# Placement tests — browse page and profile page
# ---------------------------------------------------------------------------


class TestAdSlotPlacement:
    """Ad slot appears in the right places on the page."""

    def test_ad_slot_on_browse_page(self, ads_db_app, ads_client):
        """Browse /investors page shows ad slot for anonymous viewer."""
        with ads_db_app.app_context():
            pass

        resp = ads_client.get("/investors")
        assert resp.status_code == 200
        assert AD_MARKER in resp.data

    def test_ad_slot_on_person_profile(self, ads_db_app, ads_client):
        """Person profile page shows ad slot in sidebar for anonymous viewer."""
        from project.extensions import db

        with ads_db_app.app_context():
            person = _make_person(db, slug="jane-ads-person", email="jane.ads@example.com")
            db.session.commit()
            slug = person.slug

        resp = ads_client.get(f"/investors/{slug}")
        assert resp.status_code == 200
        assert AD_MARKER in resp.data, "Ad slot must appear on person profile for anonymous viewer"

    def test_no_ad_slot_on_person_profile_for_pro(self, ads_db_app, ads_client):
        """Person profile page does NOT show ad slot for Pro viewer."""
        from project.extensions import db

        with ads_db_app.app_context():
            user = _make_user(db, "pro_profile@example.com")
            db.session.commit()
            user.user_payment.grant_pro("lifetime")
            user_id = user.id
            person = _make_person(db, slug="jane-ads-pro", email="jane.adsno@example.com")
            db.session.commit()
            slug = person.slug

        _login(ads_client, ads_db_app, user_id)
        resp = ads_client.get(f"/investors/{slug}")
        assert resp.status_code == 200
        assert AD_MARKER not in resp.data, "Pro viewer must NOT see ad slot on person profile"
