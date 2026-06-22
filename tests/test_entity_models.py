"""Tests for the new entity model layer (Phase 1b Task 1).

Runs under the shared `app` fixture (SQLite in-memory via conftest.py).
Tests create the full entity graph, commit, read back, and verify
relationships + uniqueness constraints.
"""

from __future__ import annotations

import os

# Ensure env is set before any project import
os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("_DATABASE_URL", "sqlite:///test_entity_db.sqlite")

import pytest  # noqa: E402


@pytest.fixture()
def db_session(app):
    """Push an app context, create all tables, yield the db session, then teardown."""
    from project.extensions import db

    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()


# ---------------------------------------------------------------------------
# Enum import sanity
# ---------------------------------------------------------------------------


def test_entity_enums_importable():
    from project.utils.enums import (
        AffiliationRole,
        EntityType,
        InvestmentStage,
        InvestorType,
        LeadPreference,
        OrgType,
        PersonType,
    )

    assert EntityType.PERSON == "person"
    assert EntityType.ORG == "org"
    assert OrgType.VC_FIRM == "vc_firm"
    assert PersonType.ANGEL == "angel"
    assert AffiliationRole.FOUNDER == "founder"
    assert InvestorType.ANGEL == "angel"
    assert InvestmentStage.SEED == "seed"
    assert LeadPreference.LEAD == "lead"


# ---------------------------------------------------------------------------
# Model import sanity
# ---------------------------------------------------------------------------


def test_entity_models_importable():
    from project.models.entity import (
        Affiliation,
        EntityBookmark,
        EntityGeography,
        EntityIndustry,
        EntityNotable,
        EntityStage,
        Geography,
        InvestorProfile,
        Organization,
        Person,
    )

    assert Person is not None
    assert Organization is not None
    assert Affiliation is not None
    assert InvestorProfile is not None
    assert Geography is not None
    assert EntityIndustry is not None
    assert EntityStage is not None
    assert EntityGeography is not None
    assert EntityNotable is not None
    assert EntityBookmark is not None


# ---------------------------------------------------------------------------
# Person + Organization CRUD
# ---------------------------------------------------------------------------


def test_create_person(db_session):
    from project.models.entity import Person

    db = db_session
    person = Person(first_name="Alice", slug="alice-test")
    db.session.add(person)
    db.session.commit()

    fetched = db.session.get(Person, person.id)
    assert fetched is not None
    assert fetched.first_name == "Alice"
    assert fetched.slug == "alice-test"
    assert fetched.is_public is False
    assert fetched.is_approved is False
    assert fetched.last_name is None


def test_person_slug_unique(db_session):
    from sqlalchemy.exc import IntegrityError

    from project.models.entity import Person

    db = db_session
    db.session.add(Person(first_name="Bob", slug="dup-slug"))
    db.session.commit()

    db.session.add(Person(first_name="Carol", slug="dup-slug"))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_create_organization(db_session):
    from project.models.entity import Organization
    from project.utils.enums import OrgType

    db = db_session
    org = Organization(name="Acme Ventures", slug="acme-ventures", org_type=OrgType.VC_FIRM)
    db.session.add(org)
    db.session.commit()

    fetched = db.session.get(Organization, org.id)
    assert fetched is not None
    assert fetched.name == "Acme Ventures"
    assert fetched.org_type == OrgType.VC_FIRM
    assert fetched.is_public is True
    assert fetched.is_approved is False


# ---------------------------------------------------------------------------
# Affiliation
# ---------------------------------------------------------------------------


def test_create_affiliation(db_session):
    from project.models.entity import Affiliation, Organization, Person
    from project.utils.enums import AffiliationRole, OrgType

    db = db_session
    person = Person(first_name="Dave", slug="dave-aff")
    org = Organization(name="FundCo", slug="fundco", org_type=OrgType.MICRO_VC)
    db.session.add_all([person, org])
    db.session.flush()

    aff = Affiliation(person_id=person.id, organization_id=org.id, role=AffiliationRole.GP)
    db.session.add(aff)
    db.session.commit()

    fetched = db.session.get(Affiliation, aff.id)
    assert fetched is not None
    assert fetched.person_id == person.id
    assert fetched.organization_id == org.id
    assert fetched.role == AffiliationRole.GP
    assert fetched.is_current is True


def test_affiliation_unique_constraint(db_session):
    """Same (person, org, role) triple must be rejected."""
    from sqlalchemy.exc import IntegrityError

    from project.models.entity import Affiliation, Organization, Person
    from project.utils.enums import AffiliationRole, OrgType

    db = db_session
    person = Person(first_name="Eve", slug="eve-aff")
    org = Organization(name="DupFund", slug="dupfund", org_type=OrgType.ACCELERATOR)
    db.session.add_all([person, org])
    db.session.flush()

    db.session.add(Affiliation(person_id=person.id, organization_id=org.id, role=AffiliationRole.PARTNER))
    db.session.commit()

    db.session.add(Affiliation(person_id=person.id, organization_id=org.id, role=AffiliationRole.PARTNER))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


# ---------------------------------------------------------------------------
# InvestorProfile
# ---------------------------------------------------------------------------


def test_create_investor_profile_person(db_session):
    from project.models.entity import InvestorProfile, Person
    from project.utils.enums import EntityType, InvestorType, LeadPreference

    db = db_session
    person = Person(first_name="Fran", slug="fran-ip")
    db.session.add(person)
    db.session.flush()

    ip = InvestorProfile(
        entity_type=EntityType.PERSON,
        entity_id=person.id,
        investor_type=InvestorType.ANGEL,
        min_investment=25000,
        max_investment=250000,
        lead_pref=LeadPreference.LEAD,
    )
    db.session.add(ip)
    db.session.commit()

    fetched = db.session.get(InvestorProfile, ip.id)
    assert fetched is not None
    assert fetched.entity_type == EntityType.PERSON
    assert fetched.entity_id == person.id
    assert fetched.investor_type == InvestorType.ANGEL
    assert fetched.min_investment == 25000
    assert fetched.accepts_cold_inbound is False
    assert fetched.is_active is True


def test_investor_profile_unique_constraint(db_session):
    """(entity_type, entity_id) must be unique per InvestorProfile."""
    from sqlalchemy.exc import IntegrityError

    from project.models.entity import InvestorProfile, Organization
    from project.utils.enums import EntityType, OrgType

    db = db_session
    org = Organization(name="UniqueOrg", slug="unique-org", org_type=OrgType.VC_FIRM)
    db.session.add(org)
    db.session.flush()

    db.session.add(InvestorProfile(entity_type=EntityType.ORG, entity_id=org.id))
    db.session.commit()

    db.session.add(InvestorProfile(entity_type=EntityType.ORG, entity_id=org.id))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


# ---------------------------------------------------------------------------
# Geography
# ---------------------------------------------------------------------------


def test_create_geography(db_session):
    from project.models.entity import Geography

    db = db_session
    geo = Geography(slug="us", name="United States", type="country", country_code="US")
    db.session.add(geo)
    db.session.commit()

    fetched = db.session.get(Geography, geo.id)
    assert fetched is not None
    assert fetched.slug == "us"
    assert fetched.country_code == "US"
    assert fetched.latitude is None


def test_geography_slug_unique(db_session):
    from sqlalchemy.exc import IntegrityError

    from project.models.entity import Geography

    db = db_session
    db.session.add(Geography(slug="dup-geo", name="Place A", type="city"))
    db.session.commit()

    db.session.add(Geography(slug="dup-geo", name="Place B", type="city"))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


# ---------------------------------------------------------------------------
# EntityIndustry
# ---------------------------------------------------------------------------


def test_create_entity_industry(db_session):
    from project.models.entity import EntityIndustry, Person
    from project.models.helpers import Industry
    from project.utils.enums import EntityType

    db = db_session
    person = Person(first_name="Gus", slug="gus-ind")
    db.session.add(person)
    db.session.flush()

    industry = db.session.scalar(db.select(Industry).limit(1))
    if industry is None:
        industry = Industry(name="Test Industry", category="Test")
        db.session.add(industry)
        db.session.flush()

    ei = EntityIndustry(entity_type=EntityType.PERSON, entity_id=person.id, industry_id=industry.id)
    db.session.add(ei)
    db.session.commit()

    fetched = db.session.get(EntityIndustry, ei.id)
    assert fetched is not None
    assert fetched.entity_type == EntityType.PERSON
    assert fetched.industry_id == industry.id


def test_entity_industry_unique_constraint(db_session):
    """(entity_type, entity_id, industry_id) must be unique."""
    from sqlalchemy.exc import IntegrityError

    from project.models.entity import EntityIndustry, Person
    from project.models.helpers import Industry
    from project.utils.enums import EntityType

    db = db_session
    person = Person(first_name="Hank", slug="hank-ind")
    db.session.add(person)
    db.session.flush()

    industry = db.session.scalar(db.select(Industry).limit(1))
    if industry is None:
        industry = Industry(name="Test Industry 2", category="Test")
        db.session.add(industry)
        db.session.flush()

    db.session.add(EntityIndustry(entity_type=EntityType.PERSON, entity_id=person.id, industry_id=industry.id))
    db.session.commit()

    db.session.add(EntityIndustry(entity_type=EntityType.PERSON, entity_id=person.id, industry_id=industry.id))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


# ---------------------------------------------------------------------------
# EntityStage
# ---------------------------------------------------------------------------


def test_create_entity_stage(db_session):
    from project.models.entity import EntityStage, Organization
    from project.utils.enums import EntityType, InvestmentStage, OrgType

    db = db_session
    org = Organization(name="StageOrg", slug="stage-org", org_type=OrgType.VC_FIRM)
    db.session.add(org)
    db.session.flush()

    es = EntityStage(entity_type=EntityType.ORG, entity_id=org.id, stage=InvestmentStage.SEED)
    db.session.add(es)
    db.session.commit()

    fetched = db.session.get(EntityStage, es.id)
    assert fetched is not None
    assert fetched.stage == InvestmentStage.SEED


def test_entity_stage_unique_constraint(db_session):
    from sqlalchemy.exc import IntegrityError

    from project.models.entity import EntityStage, Person
    from project.utils.enums import EntityType, InvestmentStage

    db = db_session
    person = Person(first_name="Ivy", slug="ivy-stage")
    db.session.add(person)
    db.session.flush()

    db.session.add(EntityStage(entity_type=EntityType.PERSON, entity_id=person.id, stage=InvestmentStage.PRE_SEED))
    db.session.commit()

    db.session.add(EntityStage(entity_type=EntityType.PERSON, entity_id=person.id, stage=InvestmentStage.PRE_SEED))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


# ---------------------------------------------------------------------------
# EntityGeography
# ---------------------------------------------------------------------------


def test_create_entity_geography(db_session):
    from project.models.entity import EntityGeography, Geography, Person
    from project.utils.enums import EntityType

    db = db_session
    person = Person(first_name="Jake", slug="jake-geo")
    geo = Geography(slug="uk", name="United Kingdom", type="country", country_code="GB")
    db.session.add_all([person, geo])
    db.session.flush()

    eg = EntityGeography(entity_type=EntityType.PERSON, entity_id=person.id, geography_id=geo.id)
    db.session.add(eg)
    db.session.commit()

    fetched = db.session.get(EntityGeography, eg.id)
    assert fetched is not None
    assert fetched.geography_id == geo.id


def test_entity_geography_unique_constraint(db_session):
    from sqlalchemy.exc import IntegrityError

    from project.models.entity import EntityGeography, Geography, Person
    from project.utils.enums import EntityType

    db = db_session
    person = Person(first_name="Kim", slug="kim-geo")
    geo = Geography(slug="de", name="Germany", type="country", country_code="DE")
    db.session.add_all([person, geo])
    db.session.flush()

    db.session.add(EntityGeography(entity_type=EntityType.PERSON, entity_id=person.id, geography_id=geo.id))
    db.session.commit()

    db.session.add(EntityGeography(entity_type=EntityType.PERSON, entity_id=person.id, geography_id=geo.id))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


# ---------------------------------------------------------------------------
# EntityNotable
# ---------------------------------------------------------------------------


def test_create_entity_notable(db_session):
    from project.models.entity import EntityNotable, NotableInvestment, Person
    from project.utils.enums import EntityType

    db = db_session
    person = Person(first_name="Lena", slug="lena-notable")
    notable = NotableInvestment(name="Acme Corp")
    db.session.add_all([person, notable])
    db.session.flush()

    en = EntityNotable(entity_type=EntityType.PERSON, entity_id=person.id, notable_investment_id=notable.id)
    db.session.add(en)
    db.session.commit()

    fetched = db.session.get(EntityNotable, en.id)
    assert fetched is not None
    assert fetched.notable_investment_id == notable.id


def test_entity_notable_unique_constraint(db_session):
    from sqlalchemy.exc import IntegrityError

    from project.models.entity import EntityNotable, NotableInvestment, Person
    from project.utils.enums import EntityType

    db = db_session
    person = Person(first_name="Max", slug="max-notable")
    notable = NotableInvestment(name="Beta Corp")
    db.session.add_all([person, notable])
    db.session.flush()

    db.session.add(EntityNotable(entity_type=EntityType.PERSON, entity_id=person.id, notable_investment_id=notable.id))
    db.session.commit()

    db.session.add(EntityNotable(entity_type=EntityType.PERSON, entity_id=person.id, notable_investment_id=notable.id))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


# ---------------------------------------------------------------------------
# EntityBookmark
# ---------------------------------------------------------------------------


def test_create_entity_bookmark(db_session):
    from project.models.entity import EntityBookmark, Person
    from project.models.user import User
    from project.utils.enums import EntityType

    db = db_session
    user = User(email="bookmarker@test.com")
    person = Person(first_name="Nina", slug="nina-bm")
    db.session.add_all([user, person])
    db.session.flush()

    bm = EntityBookmark(user_id=user.id, entity_type=EntityType.PERSON, entity_id=person.id)
    db.session.add(bm)
    db.session.commit()

    fetched = db.session.get(EntityBookmark, bm.id)
    assert fetched is not None
    assert fetched.user_id == user.id
    assert fetched.entity_type == EntityType.PERSON
    assert fetched.created_at is not None


def test_entity_bookmark_unique_constraint(db_session):
    """(user_id, entity_type, entity_id) must be unique."""
    from sqlalchemy.exc import IntegrityError

    from project.models.entity import EntityBookmark, Person
    from project.models.user import User
    from project.utils.enums import EntityType

    db = db_session
    user = User(email="dup-bookmarker@test.com")
    person = Person(first_name="Oscar", slug="oscar-bm")
    db.session.add_all([user, person])
    db.session.flush()

    db.session.add(EntityBookmark(user_id=user.id, entity_type=EntityType.PERSON, entity_id=person.id))
    db.session.commit()

    db.session.add(EntityBookmark(user_id=user.id, entity_type=EntityType.PERSON, entity_id=person.id))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_entity_bookmark_get_by_user_id(db_session):
    from project.models.entity import EntityBookmark, Organization, Person
    from project.models.user import User
    from project.utils.enums import EntityType, OrgType

    db = db_session
    user = User(email="listing@test.com")
    person = Person(first_name="Paula", slug="paula-list")
    org = Organization(name="ListOrg", slug="list-org", org_type=OrgType.VC_FIRM)
    db.session.add_all([user, person, org])
    db.session.flush()

    db.session.add(EntityBookmark(user_id=user.id, entity_type=EntityType.PERSON, entity_id=person.id))
    db.session.add(EntityBookmark(user_id=user.id, entity_type=EntityType.ORG, entity_id=org.id))
    db.session.commit()

    results = EntityBookmark.get_by_user_id(user.id)
    assert len(results) == 2


def test_entity_bookmark_exists(db_session):
    from project.models.entity import EntityBookmark, Person
    from project.models.user import User
    from project.utils.enums import EntityType

    db = db_session
    user = User(email="exists@test.com")
    person = Person(first_name="Quinn", slug="quinn-exists")
    db.session.add_all([user, person])
    db.session.flush()

    assert EntityBookmark.exists(user.id, EntityType.PERSON, person.id) is False

    db.session.add(EntityBookmark(user_id=user.id, entity_type=EntityType.PERSON, entity_id=person.id))
    db.session.commit()

    assert EntityBookmark.exists(user.id, EntityType.PERSON, person.id) is True


# ---------------------------------------------------------------------------
# Full graph integration test
# ---------------------------------------------------------------------------


def test_full_entity_graph(db_session):
    """Create a Person+Org with Affiliation, InvestorProfile, and all entity_* facets."""
    from project.models.entity import (
        Affiliation,
        EntityBookmark,
        EntityGeography,
        EntityIndustry,
        EntityNotable,
        EntityStage,
        Geography,
        InvestorProfile,
        NotableInvestment,
        Organization,
        Person,
    )
    from project.models.helpers import Industry
    from project.models.user import User
    from project.utils.enums import (
        AffiliationRole,
        EntityType,
        InvestmentStage,
        InvestorType,
        LeadPreference,
        OrgType,
    )

    db = db_session

    # Entities
    person = Person(first_name="Rosa", last_name="Parks", slug="rosa-parks-test", headline="Angel Investor")
    org = Organization(name="Parks Capital", slug="parks-capital", org_type=OrgType.VC_FIRM)
    user = User(email="graph-user@test.com")
    db.session.add_all([person, org, user])
    db.session.flush()

    # Affiliation
    aff = Affiliation(person_id=person.id, organization_id=org.id, role=AffiliationRole.GP)
    db.session.add(aff)

    # InvestorProfiles
    ip_person = InvestorProfile(
        entity_type=EntityType.PERSON,
        entity_id=person.id,
        investor_type=InvestorType.ANGEL,
        min_investment=10000,
        max_investment=100000,
        lead_pref=LeadPreference.BOTH,
        accepts_cold_inbound=True,
    )
    ip_org = InvestorProfile(
        entity_type=EntityType.ORG,
        entity_id=org.id,
        investor_type=InvestorType.VC_FIRM,
        n_investments=50,
        lead_pref=LeadPreference.LEAD,
        thesis="Early-stage B2B SaaS",
    )
    db.session.add_all([ip_person, ip_org])

    # Geography
    geo = Geography(slug="us-ny", name="New York", type="city", country_code="US", latitude=40.7128, longitude=-74.0060)
    db.session.add(geo)
    db.session.flush()

    # Industry
    industry = db.session.scalar(db.select(Industry).limit(1))
    if industry is None:
        industry = Industry(name="SaaS", category="Technology")
        db.session.add(industry)
        db.session.flush()

    # Notable investment
    notable = NotableInvestment(name="StartupX")
    db.session.add(notable)
    db.session.flush()

    # Facets for person
    db.session.add(EntityIndustry(entity_type=EntityType.PERSON, entity_id=person.id, industry_id=industry.id))
    db.session.add(EntityStage(entity_type=EntityType.PERSON, entity_id=person.id, stage=InvestmentStage.SEED))
    db.session.add(EntityGeography(entity_type=EntityType.PERSON, entity_id=person.id, geography_id=geo.id))
    db.session.add(EntityNotable(entity_type=EntityType.PERSON, entity_id=person.id, notable_investment_id=notable.id))

    # Facets for org
    db.session.add(EntityIndustry(entity_type=EntityType.ORG, entity_id=org.id, industry_id=industry.id))
    db.session.add(EntityStage(entity_type=EntityType.ORG, entity_id=org.id, stage=InvestmentStage.SERIES_A))
    db.session.add(EntityGeography(entity_type=EntityType.ORG, entity_id=org.id, geography_id=geo.id))
    db.session.add(EntityNotable(entity_type=EntityType.ORG, entity_id=org.id, notable_investment_id=notable.id))

    # Bookmark
    bm = EntityBookmark(user_id=user.id, entity_type=EntityType.PERSON, entity_id=person.id)
    db.session.add(bm)

    db.session.commit()

    # --- Read back and assert ---
    p = db.session.get(Person, person.id)
    assert p is not None
    assert p.first_name == "Rosa"
    assert p.headline == "Angel Investor"

    o = db.session.get(Organization, org.id)
    assert o is not None
    assert o.name == "Parks Capital"

    fetched_aff = db.session.get(Affiliation, aff.id)
    assert fetched_aff.person_id == person.id

    fetched_ip = db.session.get(InvestorProfile, ip_person.id)
    assert fetched_ip.entity_type == EntityType.PERSON
    assert fetched_ip.accepts_cold_inbound is True

    assert EntityBookmark.exists(user.id, EntityType.PERSON, person.id) is True
    assert EntityBookmark.exists(user.id, EntityType.ORG, org.id) is False
