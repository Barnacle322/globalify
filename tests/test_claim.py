"""TDD tests for the claim email-verification flow (Phase 5 Task 1).

Written BEFORE implementation.  Run with::

    uv run pytest tests/test_claim.py -v

All tests are expected to FAIL until the production changes are in place.

Covers:
  1. POST /investor/<slug>/claim/email (person has email)  → ClaimVerification created + send_email called
  2. POST /investor/<slug>/claim/email (person has NO email) → no ClaimVerification, redirect to manual
  3. POST /investor/<slug>/claim/email/verify with correct token → user_id bound + is_used set
  4. Expired token → rejected
  5. Already-used token → rejected
  6. Already-claimed person (user_id already set) → rejected
  7. ClaimVerification.expire_all_by_user_id sets is_used (not the read-only property)
"""

from __future__ import annotations

import datetime

import pytest

# ---------------------------------------------------------------------------
# Shared helpers (mirrors test_authenticated_pages.py pattern)
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


def _make_person(db, *, first_name="Jane", last_name="Doe", slug="jane-doe", email=None, user_id=None):
    """Create a public, approved Person and return it."""
    from project.models.entity import Person

    person = Person(
        first_name=first_name,
        last_name=last_name,
        slug=slug,
        email=email,
        user_id=user_id,
        is_public=True,
        is_approved=True,
    )
    db.session.add(person)
    db.session.flush()
    return person


def _login(client, user_id: int):
    """Inject a Flask-Login session so current_user resolves to the given user."""
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True


# ---------------------------------------------------------------------------
# Test 1: email POST with a person who HAS an email → creates verification + sends email
# ---------------------------------------------------------------------------


class TestEmailPostWithPersonEmail:
    """POST /investor/<slug>/claim/email when the person has an email on file."""

    def test_creates_claim_verification_row(self, db_app, client, monkeypatch):
        """A ClaimVerification row must be inserted into the DB."""
        # Monkeypatch send_email so no network calls occur
        import project.routes.claim as claim_mod
        from project.extensions import db
        from project.models import ClaimVerification

        monkeypatch.setattr(claim_mod, "send_email", lambda *a, **kw: True)

        with db_app.app_context():
            user = _make_user(db, "claimant@example.com")
            person = _make_person(db, slug="alice-investor", email="alice@example.com")
            db.session.commit()
            user_id = user.id
            slug = person.slug

        _login(client, user_id)
        resp = client.post(
            f"/investor/{slug}/claim/email",
            json={},
            follow_redirects=False,
        )

        with db_app.app_context():
            count = db.session.scalar(db.select(db.func.count()).select_from(ClaimVerification))

        assert count == 1, f"Expected 1 ClaimVerification, got {count}"
        assert resp.status_code in (302, 200)

    def test_send_email_called_with_person_email(self, db_app, client, monkeypatch):
        """send_email must be called with the person's email address."""
        from project.extensions import db

        sent_to = []

        def fake_send_email(to, subject, html):
            sent_to.append(to)
            return True

        import project.routes.claim as claim_mod

        monkeypatch.setattr(claim_mod, "send_email", fake_send_email)

        with db_app.app_context():
            user = _make_user(db, "claimant2@example.com")
            person = _make_person(db, slug="bob-investor", email="bob@example.com")
            db.session.commit()
            user_id = user.id
            slug = person.slug

        _login(client, user_id)
        client.post(
            f"/investor/{slug}/claim/email",
            json={},
            follow_redirects=False,
        )

        assert sent_to == ["bob@example.com"], (
            f"send_email should have been called with 'bob@example.com', got {sent_to}"
        )


# ---------------------------------------------------------------------------
# Test 2: email POST when person has NO email → no verification, redirect to manual
# ---------------------------------------------------------------------------


class TestEmailPostNoPersonEmail:
    """POST /investor/<slug>/claim/email when the person has no email on file."""

    def test_no_claim_verification_created(self, db_app, client, monkeypatch):
        """No ClaimVerification row must be inserted when person has no email."""
        import project.routes.claim as claim_mod
        from project.extensions import db
        from project.models import ClaimVerification

        monkeypatch.setattr(claim_mod, "send_email", lambda *a, **kw: True)

        with db_app.app_context():
            user = _make_user(db, "claimant3@example.com")
            person = _make_person(db, slug="carol-investor", email=None)
            db.session.commit()
            user_id = user.id
            slug = person.slug

        _login(client, user_id)
        client.post(
            f"/investor/{slug}/claim/email",
            json={},
            follow_redirects=False,
        )

        with db_app.app_context():
            count = db.session.scalar(db.select(db.func.count()).select_from(ClaimVerification))

        assert count == 0, f"Expected 0 ClaimVerifications when person has no email, got {count}"

    def test_redirects_to_manual_path(self, db_app, client, monkeypatch):
        """Response must redirect to the manual claim path when person has no email."""
        import project.routes.claim as claim_mod
        from project.extensions import db

        monkeypatch.setattr(claim_mod, "send_email", lambda *a, **kw: True)

        with db_app.app_context():
            user = _make_user(db, "claimant4@example.com")
            person = _make_person(db, slug="dave-investor", email=None)
            db.session.commit()
            user_id = user.id
            slug = person.slug

        _login(client, user_id)
        resp = client.post(
            f"/investor/{slug}/claim/email",
            json={},
            follow_redirects=False,
        )

        # Must redirect, and the Location header must point at the manual path
        assert resp.status_code == 302, f"Expected 302 redirect, got {resp.status_code}"
        location = resp.headers.get("Location", "")
        assert "manual" in location, f"Redirect should go to the manual claim path, got Location: {location!r}"


# ---------------------------------------------------------------------------
# Test 3: verification POST with correct token → user_id bound + is_used set
# ---------------------------------------------------------------------------


class TestVerificationPostSuccess:
    """POST /investor/<slug>/claim/email/verify with a valid, fresh token."""

    def test_person_user_id_bound_on_success(self, db_app, client, monkeypatch):
        """person.user_id must equal current_user.id after successful verification."""
        import project.routes.claim as claim_mod
        from project.extensions import db
        from project.models import ClaimVerification
        from project.models.entity import Person
        from project.utils.enums import EntityType

        monkeypatch.setattr(claim_mod, "send_email", lambda *a, **kw: True)

        with db_app.app_context():
            user = _make_user(db, "verifier@example.com")
            person = _make_person(db, slug="eve-investor", email="eve@example.com")
            db.session.flush()

            verification = ClaimVerification(
                user_id=user.id,
                entity_type=EntityType.PERSON,
                entity_id=person.id,
            )
            db.session.add(verification)
            db.session.commit()
            user_id = user.id
            slug = person.slug
            token = verification.token

        _login(client, user_id)
        client.post(
            f"/investor/{slug}/claim/email/verify",
            json={"code": token},
            follow_redirects=False,
        )

        # Re-fetch from DB to confirm the bind persisted
        with db_app.app_context():
            fetched_person = Person.get_by_slug(slug)
            assert fetched_person is not None
            assert fetched_person.user_id == user_id, f"Expected person.user_id={user_id}, got {fetched_person.user_id}"

    def test_is_used_set_on_success(self, db_app, client, monkeypatch):
        """verification.is_used must be True after successful verification."""
        import project.routes.claim as claim_mod
        from project.extensions import db
        from project.models import ClaimVerification
        from project.utils.enums import EntityType

        monkeypatch.setattr(claim_mod, "send_email", lambda *a, **kw: True)

        with db_app.app_context():
            user = _make_user(db, "verifier2@example.com")
            person = _make_person(db, slug="frank-investor", email="frank@example.com")
            db.session.flush()

            verification = ClaimVerification(
                user_id=user.id,
                entity_type=EntityType.PERSON,
                entity_id=person.id,
            )
            db.session.add(verification)
            db.session.commit()
            user_id = user.id
            slug = person.slug
            token = verification.token
            verification_id = verification.id

        _login(client, user_id)
        client.post(
            f"/investor/{slug}/claim/email/verify",
            json={"code": token},
            follow_redirects=False,
        )

        with db_app.app_context():
            fetched_ver = db.session.get(ClaimVerification, verification_id)
            assert fetched_ver is not None
            assert fetched_ver.is_used is True, f"Expected verification.is_used=True, got {fetched_ver.is_used}"


# ---------------------------------------------------------------------------
# Test 4: expired token → rejected
# ---------------------------------------------------------------------------


class TestVerificationExpiredToken:
    """POST verify with a token whose created_at is far in the past."""

    def test_expired_token_rejected(self, db_app, client, monkeypatch):
        """An expired token must be rejected; user_id must remain unset."""
        import project.routes.claim as claim_mod
        from project.extensions import db
        from project.models import ClaimVerification
        from project.models.entity import Person
        from project.utils.enums import EntityType

        monkeypatch.setattr(claim_mod, "send_email", lambda *a, **kw: True)

        with db_app.app_context():
            user = _make_user(db, "verifier3@example.com")
            person = _make_person(db, slug="grace-investor", email="grace@example.com")
            db.session.flush()

            verification = ClaimVerification(
                user_id=user.id,
                entity_type=EntityType.PERSON,
                entity_id=person.id,
            )
            db.session.add(verification)
            db.session.flush()

            # Force expiry by back-dating created_at by 10 minutes
            expired_time = datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=10)
            verification.created_at = expired_time
            db.session.commit()

            user_id = user.id
            slug = person.slug
            token = verification.token

        _login(client, user_id)
        resp = client.post(
            f"/investor/{slug}/claim/email/verify",
            json={"code": token},
            follow_redirects=False,
        )

        with db_app.app_context():
            fetched_person = Person.get_by_slug(slug)
            assert fetched_person.user_id is None, (
                f"Expected person.user_id=None after expired token, got {fetched_person.user_id}"
            )
        assert resp.status_code == 302, f"Expected redirect, got {resp.status_code}"


# ---------------------------------------------------------------------------
# Test 5: already-used token → rejected
# ---------------------------------------------------------------------------


class TestVerificationUsedToken:
    """POST verify with a token that has is_used=True."""

    def test_used_token_rejected(self, db_app, client, monkeypatch):
        """An already-used token must be rejected; user_id must remain unset."""
        import project.routes.claim as claim_mod
        from project.extensions import db
        from project.models import ClaimVerification
        from project.models.entity import Person
        from project.utils.enums import EntityType

        monkeypatch.setattr(claim_mod, "send_email", lambda *a, **kw: True)

        with db_app.app_context():
            user = _make_user(db, "verifier4@example.com")
            person = _make_person(db, slug="henry-investor", email="henry@example.com")
            db.session.flush()

            verification = ClaimVerification(
                user_id=user.id,
                entity_type=EntityType.PERSON,
                entity_id=person.id,
                is_used=True,  # pre-mark as used
            )
            db.session.add(verification)
            db.session.commit()

            user_id = user.id
            slug = person.slug
            token = verification.token

        _login(client, user_id)
        resp = client.post(
            f"/investor/{slug}/claim/email/verify",
            json={"code": token},
            follow_redirects=False,
        )

        with db_app.app_context():
            fetched_person = Person.get_by_slug(slug)
            assert fetched_person.user_id is None, (
                f"Expected person.user_id=None after used token, got {fetched_person.user_id}"
            )
        assert resp.status_code == 302, f"Expected redirect, got {resp.status_code}"


# ---------------------------------------------------------------------------
# Test 6: already-claimed person → rejected
# ---------------------------------------------------------------------------


class TestVerificationAlreadyClaimedPerson:
    """POST verify when person.user_id is already set to another user."""

    def test_already_claimed_person_rejected(self, db_app, client, monkeypatch):
        """Verification must be rejected if person.user_id is already set."""
        import project.routes.claim as claim_mod
        from project.extensions import db
        from project.models import ClaimVerification
        from project.models.entity import Person
        from project.utils.enums import EntityType

        monkeypatch.setattr(claim_mod, "send_email", lambda *a, **kw: True)

        with db_app.app_context():
            existing_owner = _make_user(db, "owner@example.com")
            claimant = _make_user(db, "claimant5@example.com")
            db.session.flush()

            # Person is already claimed by existing_owner
            person = _make_person(
                db,
                slug="iris-investor",
                email="iris@example.com",
                user_id=existing_owner.id,
            )
            db.session.flush()

            verification = ClaimVerification(
                user_id=claimant.id,
                entity_type=EntityType.PERSON,
                entity_id=person.id,
            )
            db.session.add(verification)
            db.session.commit()

            claimant_id = claimant.id
            existing_owner_id = existing_owner.id
            slug = person.slug
            token = verification.token

        _login(client, claimant_id)
        resp = client.post(
            f"/investor/{slug}/claim/email/verify",
            json={"code": token},
            follow_redirects=False,
        )

        with db_app.app_context():
            fetched_person = db.session.scalar(db.select(Person).where(Person.slug == slug))
            assert fetched_person.user_id == existing_owner_id, (
                f"person.user_id should still be {existing_owner_id}, got {fetched_person.user_id}"
            )
        assert resp.status_code == 302, f"Expected redirect, got {resp.status_code}"


# ---------------------------------------------------------------------------
# Test 7: expire_all_by_user_id sets is_used (NOT the read-only is_expired property)
# ---------------------------------------------------------------------------


class TestExpireAllByUserId:
    """ClaimVerification.expire_all_by_user_id must set is_used=True, not is_expired."""

    def test_expire_all_sets_is_used(self, db_app):
        """After expire_all_by_user_id, all verifications for that user have is_used=True."""
        from project.extensions import db
        from project.models import ClaimVerification
        from project.utils.enums import EntityType

        with db_app.app_context():
            user = _make_user(db, "expire-user@example.com")
            db.session.flush()

            v1 = ClaimVerification(
                user_id=user.id,
                entity_type=EntityType.PERSON,
                entity_id=1,
            )
            v2 = ClaimVerification(
                user_id=user.id,
                entity_type=EntityType.PERSON,
                entity_id=2,
            )
            db.session.add_all([v1, v2])
            db.session.commit()
            user_id = user.id
            v1_id = v1.id
            v2_id = v2.id

        with db_app.app_context():
            ClaimVerification.expire_all_by_user_id(user_id)

        with db_app.app_context():
            fv1 = db.session.get(ClaimVerification, v1_id)
            fv2 = db.session.get(ClaimVerification, v2_id)
            assert fv1.is_used is True, f"Expected fv1.is_used=True, got {fv1.is_used}"
            assert fv2.is_used is True, f"Expected fv2.is_used=True, got {fv2.is_used}"
