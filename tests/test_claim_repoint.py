"""Tests for Phase 1b Task 3: claims/bookmarks repointed to polymorphic entity ref.

Tests are written first (TDD). They verify:
  (a) ClaimVerification and ClaimRequest can be created with entity_type/entity_id
      and queried back via the updated helpers.
  (b) EntityBookmark add → exists → list works (exercises the API that the
      settings/main bookmark handlers use).
"""

from __future__ import annotations

import os

os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("_DATABASE_URL", "sqlite:///test_claim_repoint.sqlite")

import pytest  # noqa: E402


@pytest.fixture()
def db_session(app):
    """Push an app context, create all tables, yield db, then teardown."""
    from project.extensions import db

    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()


# ---------------------------------------------------------------------------
# (a) ClaimVerification with entity_type / entity_id
# ---------------------------------------------------------------------------


def test_claim_verification_entity_columns_exist(db_session):
    """ClaimVerification has entity_type and entity_id columns."""
    from project.models.claim import ClaimVerification

    cols = {c.name for c in ClaimVerification.__table__.columns}
    assert "entity_type" in cols, "entity_type column missing from ClaimVerification"
    assert "entity_id" in cols, "entity_id column missing from ClaimVerification"


def test_claim_verification_create_with_entity(db_session):
    """ClaimVerification can be created targeting a Person entity."""
    from project.models.claim import ClaimVerification
    from project.models.entity import Person
    from project.models.user import User
    from project.utils.enums import EntityType

    db = db_session
    user = User(email="cv-user@test.com")
    person = Person(first_name="Vera", slug="vera-cv")
    db.session.add_all([user, person])
    db.session.flush()

    cv = ClaimVerification(
        user_id=user.id,
        is_used=False,
        entity_type=EntityType.PERSON,
        entity_id=person.id,
    )
    db.session.add(cv)
    db.session.commit()

    fetched = db.session.get(ClaimVerification, cv.id)
    assert fetched is not None
    assert fetched.entity_type == EntityType.PERSON
    assert fetched.entity_id == person.id
    assert fetched.investor_id is None


def test_claim_verification_entity_type_org(db_session):
    """ClaimVerification can target an Organization entity."""
    from project.models.claim import ClaimVerification
    from project.models.entity import Organization
    from project.models.user import User
    from project.utils.enums import EntityType, OrgType

    db = db_session
    user = User(email="cv-org-user@test.com")
    org = Organization(name="TestOrg CV", slug="testorg-cv", org_type=OrgType.VC_FIRM)
    db.session.add_all([user, org])
    db.session.flush()

    cv = ClaimVerification(
        user_id=user.id,
        is_used=False,
        entity_type=EntityType.ORG,
        entity_id=org.id,
    )
    db.session.add(cv)
    db.session.commit()

    fetched = db.session.get(ClaimVerification, cv.id)
    assert fetched is not None
    assert fetched.entity_type == EntityType.ORG
    assert fetched.entity_id == org.id


def test_claim_verification_investor_id_nullable(db_session):
    """investor_id can be None (nullable) during migration window."""
    from project.models.claim import ClaimVerification
    from project.models.entity import Person
    from project.models.user import User
    from project.utils.enums import EntityType

    db = db_session
    user = User(email="cv-nullable@test.com")
    person = Person(first_name="Wren", slug="wren-nullable")
    db.session.add_all([user, person])
    db.session.flush()

    cv = ClaimVerification(
        user_id=user.id,
        is_used=False,
        entity_type=EntityType.PERSON,
        entity_id=person.id,
    )
    db.session.add(cv)
    db.session.commit()

    fetched = db.session.get(ClaimVerification, cv.id)
    assert fetched.investor_id is None  # nullable during migration window


def test_claim_verification_get_by_token(db_session):
    """get_by_token query helper still works with entity-targeted claim."""
    from project.models.claim import ClaimVerification
    from project.models.entity import Person
    from project.models.user import User
    from project.utils.enums import EntityType

    db = db_session
    user = User(email="cv-token@test.com")
    person = Person(first_name="Xena", slug="xena-token")
    db.session.add_all([user, person])
    db.session.flush()

    cv = ClaimVerification(
        user_id=user.id,
        is_used=False,
        entity_type=EntityType.PERSON,
        entity_id=person.id,
    )
    db.session.add(cv)
    db.session.commit()

    found = ClaimVerification.get_by_token(cv.token)
    assert found is not None
    assert found.id == cv.id


def test_claim_verification_get_last_unused(db_session):
    """get_last_unused_by_user_id works with entity-targeted claim."""
    from project.models.claim import ClaimVerification
    from project.models.entity import Person
    from project.models.user import User
    from project.utils.enums import EntityType

    db = db_session
    user = User(email="cv-last@test.com")
    person = Person(first_name="Yara", slug="yara-last")
    db.session.add_all([user, person])
    db.session.flush()

    cv = ClaimVerification(
        user_id=user.id,
        is_used=False,
        entity_type=EntityType.PERSON,
        entity_id=person.id,
    )
    db.session.add(cv)
    db.session.commit()

    found = ClaimVerification.get_last_unused_by_user_id(user.id)
    assert found is not None
    assert found.entity_id == person.id


# ---------------------------------------------------------------------------
# (a) ClaimRequest with entity_type / entity_id
# ---------------------------------------------------------------------------


def test_claim_request_entity_columns_exist(db_session):
    """ClaimRequest has entity_type and entity_id columns."""
    from project.models.claim import ClaimRequest

    cols = {c.name for c in ClaimRequest.__table__.columns}
    assert "entity_type" in cols, "entity_type column missing from ClaimRequest"
    assert "entity_id" in cols, "entity_id column missing from ClaimRequest"


def test_claim_request_create_with_entity(db_session):
    """ClaimRequest can be created with entity_type/entity_id."""
    from project.models.claim import ClaimRequest
    from project.models.entity import Person
    from project.models.user import User
    from project.utils.enums import EntityType

    db = db_session
    user = User(email="cr-user@test.com")
    person = Person(first_name="Zara", slug="zara-cr")
    db.session.add_all([user, person])
    db.session.flush()

    cr = ClaimRequest(
        user_id=user.id,
        entity_type=EntityType.PERSON,
        entity_id=person.id,
    )
    db.session.add(cr)
    db.session.commit()

    fetched = db.session.get(ClaimRequest, cr.id)
    assert fetched is not None
    assert fetched.entity_type == EntityType.PERSON
    assert fetched.entity_id == person.id
    assert fetched.investor_id is None


def test_claim_request_get_by_id(db_session):
    """get_by_id query helper works with entity-targeted claim."""
    from project.models.claim import ClaimRequest
    from project.models.entity import Person
    from project.models.user import User
    from project.utils.enums import EntityType

    db = db_session
    user = User(email="cr-byid@test.com")
    person = Person(first_name="Abel", slug="abel-cr")
    db.session.add_all([user, person])
    db.session.flush()

    cr = ClaimRequest(user_id=user.id, entity_type=EntityType.PERSON, entity_id=person.id)
    db.session.add(cr)
    db.session.commit()

    found = ClaimRequest.get_by_id(cr.id)
    assert found is not None
    assert found.entity_id == person.id


def test_claim_request_get_by_user_id(db_session):
    """get_by_user_id helper works with entity-targeted claim."""
    from project.models.claim import ClaimRequest
    from project.models.entity import Person
    from project.models.user import User
    from project.utils.enums import EntityType

    db = db_session
    user = User(email="cr-byuid@test.com")
    person = Person(first_name="Beth", slug="beth-cr")
    db.session.add_all([user, person])
    db.session.flush()

    cr = ClaimRequest(user_id=user.id, entity_type=EntityType.PERSON, entity_id=person.id)
    db.session.add(cr)
    db.session.commit()

    found = ClaimRequest.get_by_user_id(user.id)
    assert found is not None
    assert found.entity_id == person.id


def test_claim_request_get_all_orm(db_session):
    """get_all() uses pure ORM (no table() literals) and returns created records."""
    from project.models.claim import ClaimRequest
    from project.models.entity import Person
    from project.models.user import User
    from project.utils.enums import EntityType

    db = db_session
    user = User(email="cr-all@test.com")
    person = Person(first_name="Carl", slug="carl-cr")
    db.session.add_all([user, person])
    db.session.flush()

    cr = ClaimRequest(user_id=user.id, entity_type=EntityType.PERSON, entity_id=person.id)
    db.session.add(cr)
    db.session.commit()

    results = ClaimRequest.get_all()
    ids = [r.id for r in results]
    assert cr.id in ids


def test_claim_request_get_pending_by_user_id(db_session):
    """get_pending_by_user_id() returns pending entity-targeted requests without table() literals."""
    from project.models.claim import ClaimRequest
    from project.models.entity import Person
    from project.models.user import User
    from project.utils.enums import EntityType, RequestStatus

    db = db_session
    user = User(email="cr-pending@test.com")
    person = Person(first_name="Dana", slug="dana-cr")
    db.session.add_all([user, person])
    db.session.flush()

    cr = ClaimRequest(user_id=user.id, entity_type=EntityType.PERSON, entity_id=person.id)
    db.session.add(cr)
    db.session.commit()

    assert cr.status == RequestStatus.PENDING

    results = ClaimRequest.get_pending_by_user_id(user.id)
    ids = [r.id for r in results]
    assert cr.id in ids


# ---------------------------------------------------------------------------
# (b) EntityBookmark add → exists → list (settings/main handler API)
# ---------------------------------------------------------------------------


def test_entity_bookmark_add_exists_list(db_session):
    """Full lifecycle: add bookmark → exists returns True → list returns it."""
    from project.models.entity import EntityBookmark, Person
    from project.models.user import User
    from project.utils.enums import EntityType

    db = db_session
    user = User(email="bm-lifecycle@test.com")
    person = Person(first_name="Eli", slug="eli-bm")
    db.session.add_all([user, person])
    db.session.flush()

    # Before adding: not in list, not exists
    assert EntityBookmark.exists(user.id, EntityType.PERSON, person.id) is False
    assert len(EntityBookmark.get_by_user_id(user.id)) == 0

    # Add
    bm = EntityBookmark(user_id=user.id, entity_type=EntityType.PERSON, entity_id=person.id)
    db.session.add(bm)
    db.session.commit()

    # After adding: exists, in list
    assert EntityBookmark.exists(user.id, EntityType.PERSON, person.id) is True
    listing = EntityBookmark.get_by_user_id(user.id)
    assert len(listing) == 1
    assert listing[0].entity_type == EntityType.PERSON
    assert listing[0].entity_id == person.id


def test_entity_bookmark_toggle_remove(db_session):
    """Simulate handler toggle: add then delete, exists → False."""
    from project.models.entity import EntityBookmark, Organization
    from project.models.user import User
    from project.utils.enums import EntityType, OrgType

    db = db_session
    user = User(email="bm-toggle@test.com")
    org = Organization(name="ToggleOrg", slug="toggle-org", org_type=OrgType.MICRO_VC)
    db.session.add_all([user, org])
    db.session.flush()

    # Add
    bm = EntityBookmark(user_id=user.id, entity_type=EntityType.ORG, entity_id=org.id)
    db.session.add(bm)
    db.session.commit()
    assert EntityBookmark.exists(user.id, EntityType.ORG, org.id) is True

    # Remove (like handler does)
    existing = db.session.scalar(
        db.select(EntityBookmark).where(
            EntityBookmark.user_id == user.id,
            EntityBookmark.entity_type == EntityType.ORG,
            EntityBookmark.entity_id == org.id,
        )
    )
    assert existing is not None
    db.session.delete(existing)
    db.session.commit()

    assert EntityBookmark.exists(user.id, EntityType.ORG, org.id) is False
    assert len(EntityBookmark.get_by_user_id(user.id)) == 0


def test_entity_bookmark_multi_entity_types(db_session):
    """A user can bookmark both a Person and an Org; get_by_user_id returns both."""
    from project.models.entity import EntityBookmark, Organization, Person
    from project.models.user import User
    from project.utils.enums import EntityType, OrgType

    db = db_session
    user = User(email="bm-multi@test.com")
    person = Person(first_name="Finn", slug="finn-multi")
    org = Organization(name="MultiOrg", slug="multi-org", org_type=OrgType.ACCELERATOR)
    db.session.add_all([user, person, org])
    db.session.flush()

    db.session.add(EntityBookmark(user_id=user.id, entity_type=EntityType.PERSON, entity_id=person.id))
    db.session.add(EntityBookmark(user_id=user.id, entity_type=EntityType.ORG, entity_id=org.id))
    db.session.commit()

    results = EntityBookmark.get_by_user_id(user.id)
    assert len(results) == 2
    types = {r.entity_type for r in results}
    assert EntityType.PERSON in types
    assert EntityType.ORG in types


# ---------------------------------------------------------------------------
# SearchHistoryType enum back-compat
# ---------------------------------------------------------------------------


def test_search_history_type_has_person_and_org():
    """SearchHistoryType has PERSON and ORG members (Phase 1b additions)."""
    from project.utils.enums import SearchHistoryType

    assert hasattr(SearchHistoryType, "PERSON"), "SearchHistoryType.PERSON missing"
    assert hasattr(SearchHistoryType, "ORG"), "SearchHistoryType.ORG missing"
    assert SearchHistoryType.PERSON.value == "person"
    assert SearchHistoryType.ORG.value == "org"


def test_search_history_type_old_members_preserved():
    """Old INVESTOR / INVESTMENT_FIRM / COMPANY members are still present for back-compat."""
    from project.utils.enums import SearchHistoryType

    assert hasattr(SearchHistoryType, "INVESTOR")
    assert hasattr(SearchHistoryType, "INVESTMENT_FIRM")
    assert hasattr(SearchHistoryType, "COMPANY")
