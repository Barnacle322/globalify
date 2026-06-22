"""Render smoke tests for pages that were broken by the Person/Organization model
pivot.  Each test GETs an authenticated page and asserts the response is NOT a
500 (it may be a 200 or a redirect, but must never be an Internal Server Error).

These tests were written *before* the template fixes so they would have failed
with HTTP 500 when the templates still accessed removed legacy attributes
(`investor.rounds`, `investor.industries`, `claim_request.investor.slug`, …).
After the fixes they all pass.
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
    """Inject a Flask-Login session so *current_user* resolves to the given user."""
    with client.session_transaction() as sess:
        # Flask-Login stores the user PK as a string under "_user_id"
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSettingsGeneralPage:
    """GET /settings/general as an authenticated regular user."""

    def test_settings_general_no_investor(self, db_app, client):
        """Regular user with no linked Person — page must not 500."""
        from project.extensions import db

        with db_app.app_context():
            user = _make_user(db, "regular@example.com")
            db.session.commit()
            user_id = user.id

        _login(client, db_app, user_id)
        resp = client.get("/settings/general", follow_redirects=False)
        assert resp.status_code != 500, f"Got 500: {resp.data[:300]}"

    def test_settings_general_with_investor(self, db_app, client):
        """Regular user linked to a Person — page must not 500."""
        from project.extensions import db
        from project.models import Person

        with db_app.app_context():
            user = _make_user(db, "investor@example.com")
            db.session.flush()
            person = Person(
                first_name="Alice",
                last_name="Smith",
                slug="alice-smith",
                user_id=user.id,
                is_public=True,
                is_approved=True,
            )
            db.session.add(person)
            db.session.commit()
            user_id = user.id

        _login(client, db_app, user_id)
        resp = client.get("/settings/general", follow_redirects=False)
        assert resp.status_code != 500, f"Got 500: {resp.data[:300]}"


class TestAdminClaimRequestsPage:
    """GET /admin/claim-requests as an admin user."""

    def test_claim_requests_empty(self, db_app, client):
        """No claim requests — page must not 500."""
        from project.extensions import db

        with db_app.app_context():
            admin = _make_user(db, "admin@example.com", is_admin=True)
            db.session.commit()
            admin_id = admin.id

        _login(client, db_app, admin_id)
        resp = client.get("/admin/claim-requests", follow_redirects=False)
        assert resp.status_code != 500, f"Got 500: {resp.data[:300]}"

    def test_claim_requests_with_person_entity(self, db_app, client):
        """Claim request referencing a Person — must not 500 (was broken by
        the removal of the `.investor` relationship on ClaimRequest)."""
        from project.extensions import db
        from project.models import ClaimRequest, Person
        from project.utils.enums import EntityType

        with db_app.app_context():
            admin = _make_user(db, "admin2@example.com", is_admin=True)
            regular = _make_user(db, "claimant@example.com")
            db.session.flush()

            person = Person(
                first_name="Bob",
                last_name="Jones",
                slug="bob-jones",
                is_public=False,
                is_approved=False,
            )
            db.session.add(person)
            db.session.flush()

            cr = ClaimRequest(
                user_id=regular.id,
                entity_type=EntityType.PERSON,
                entity_id=person.id,
                email="claimant@example.com",
            )
            db.session.add(cr)
            db.session.commit()
            admin_id = admin.id

        _login(client, db_app, admin_id)
        resp = client.get("/admin/claim-requests", follow_redirects=False)
        assert resp.status_code != 500, f"Got 500: {resp.data[:300]}"


class TestAdminUpdateInvestorPage:
    """GET /admin/investors/<id> as an admin — was broken by .rounds/.industries."""

    def test_update_investor_no_500(self, db_app, client):
        from project.extensions import db
        from project.models import Person

        with db_app.app_context():
            admin = _make_user(db, "admin3@example.com", is_admin=True)
            person = Person(
                first_name="Carol",
                last_name="White",
                slug="carol-white",
                is_public=True,
                is_approved=True,
            )
            db.session.add(person)
            db.session.commit()
            admin_id = admin.id
            person_id = person.id

        _login(client, db_app, admin_id)
        resp = client.get(f"/admin/investors/{person_id}", follow_redirects=False)
        assert resp.status_code != 500, f"Got 500: {resp.data[:300]}"


class TestAdminUpdateInvestmentFirmPage:
    """GET /admin/investment-firms/<id> as an admin — was broken by .rounds/.industries."""

    def test_update_investment_firm_no_500(self, db_app, client):
        from project.extensions import db
        from project.models import Organization
        from project.utils.enums import OrgType

        with db_app.app_context():
            admin = _make_user(db, "admin4@example.com", is_admin=True)
            org = Organization(
                name="Acme Capital",
                slug="acme-capital",
                org_type=OrgType.VC_FIRM,
                is_public=True,
                is_approved=False,
            )
            db.session.add(org)
            db.session.commit()
            admin_id = admin.id
            org_id = org.id

        _login(client, db_app, admin_id)
        resp = client.get(f"/admin/investment-firms/{org_id}", follow_redirects=False)
        assert resp.status_code != 500, f"Got 500: {resp.data[:300]}"
