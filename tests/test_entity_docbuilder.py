"""Tests for the shared _build_entity_doc helper (Phase 2d Task 1).

Verifies that _build_entity_doc returns correctly shaped dicts for both
Person and Organization entities WITHOUT requiring Typesense — pure SQLite.
"""

from __future__ import annotations

import os

os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("_DATABASE_URL", "sqlite:///test_docbuilder_db.sqlite")

import pytest  # noqa: E402


@pytest.fixture()
def db_session(app):
    """Push an app context, create all tables, yield the db extension, then teardown."""
    from project.extensions import db

    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()


# ---------------------------------------------------------------------------
# Person doc tests
# ---------------------------------------------------------------------------


def test_build_entity_doc_person_basic_fields(db_session):
    """_build_entity_doc returns required id/entity_type/db_id/name for a Person."""
    from project.models.entity import Person
    from project.models.entity_search import _build_entity_doc
    from project.utils.enums import EntityType

    db = db_session
    person = Person(
        first_name="Alice",
        last_name="Investor",
        slug="alice-investor",
        headline="Early-stage VC",
        about="Focus on climate tech",
        website="https://alice.vc",
        linkedin="alice-investor",
        twitter="alicevc",
    )
    db.session.add(person)
    db.session.commit()

    doc = _build_entity_doc(EntityType.PERSON, person, db.session)

    assert doc["id"] == f"person_{person.id}"
    assert doc["entity_type"] == "person"
    assert doc["db_id"] == person.id
    assert doc["name"] == "Alice Investor"
    assert doc["slug"] == "alice-investor"
    assert doc["about"] == "Focus on climate tech"
    assert doc["headline"] == "Early-stage VC"
    assert doc["website"] == "https://alice.vc"
    assert doc["linkedin"] == "alice-investor"
    assert doc["twitter"] == "alicevc"
    # No industries/stages/geographies → keys absent
    assert "industries" not in doc
    assert "stages" not in doc
    assert "geographies" not in doc
    assert "country_code" not in doc
    assert "org_type" not in doc  # only orgs have this


def test_build_entity_doc_person_with_affiliation_industry_stage_geo(db_session):
    """Person doc picks up org_name, industries (as slugs), stages and geographies."""
    from project.models.entity import (
        Affiliation,
        EntityGeography,
        EntityIndustry,
        EntityNotable,
        EntityStage,
        Geography,
        NotableInvestment,
        Organization,
        Person,
    )
    from project.models.entity_search import _build_entity_doc
    from project.models.helpers import Industry
    from project.utils.enums import (
        AffiliationRole,
        EntityType,
        InvestmentStage,
        OrgType,
    )

    db = db_session

    # Org
    org = Organization(name="Acme Capital", slug="acme-capital", org_type=OrgType.VC_FIRM)
    db.session.add(org)
    db.session.flush()

    # Person
    person = Person(first_name="Bob", last_name="Builder", slug="bob-builder")
    db.session.add(person)
    db.session.flush()

    # Affiliation (current)
    aff = Affiliation(
        person_id=person.id,
        organization_id=org.id,
        role=AffiliationRole.PARTNER,
        is_current=True,
    )
    db.session.add(aff)

    # Industry — reuse the pre-seeded "SaaS" row (after_create populates it)
    industry = db.session.scalar(db.select(Industry).where(Industry.slug == "saas"))
    if industry is None:
        industry = Industry(name="SaaS", category="Technology")
        db.session.add(industry)
        db.session.flush()

    ei = EntityIndustry(
        entity_type=EntityType.PERSON,
        entity_id=person.id,
        industry_id=industry.id,
    )
    db.session.add(ei)

    # Stage
    es = EntityStage(
        entity_type=EntityType.PERSON,
        entity_id=person.id,
        stage=InvestmentStage.SEED,
    )
    db.session.add(es)

    # Geography
    geo = Geography(slug="us", name="United States", type="country", country_code="US")
    db.session.add(geo)
    db.session.flush()

    eg = EntityGeography(
        entity_type=EntityType.PERSON,
        entity_id=person.id,
        geography_id=geo.id,
    )
    db.session.add(eg)

    # NotableInvestment
    notable = NotableInvestment(name="TechStartup")
    db.session.add(notable)
    db.session.flush()

    en = EntityNotable(
        entity_type=EntityType.PERSON,
        entity_id=person.id,
        notable_investment_id=notable.id,
    )
    db.session.add(en)

    db.session.commit()

    doc = _build_entity_doc(EntityType.PERSON, person, db.session)

    assert doc["id"] == f"person_{person.id}"
    assert doc["entity_type"] == "person"
    assert doc["db_id"] == person.id
    assert doc["name"] == "Bob Builder"
    assert doc["org_name"] == "Acme Capital"
    assert doc["industries"] == ["saas"]
    assert doc["stages"] == [InvestmentStage.SEED.value]
    assert doc["geographies"] == ["us"]
    assert doc["country_code"] == "US"
    assert doc["notable_investments"] == ["TechStartup"]


def test_build_entity_doc_person_industry_fallback_to_name(db_session):
    """When an Industry has no slug, its name is used as the index value."""
    from project.models.entity import EntityIndustry, Person
    from project.models.entity_search import _build_entity_doc
    from project.models.helpers import Industry
    from project.utils.enums import EntityType

    db = db_session

    person = Person(first_name="Carl", slug="carl-noslug")
    db.session.add(person)
    db.session.flush()

    industry = Industry(name="ClimateOps", category="Green", slug=None)
    db.session.add(industry)
    db.session.flush()

    ei = EntityIndustry(entity_type=EntityType.PERSON, entity_id=person.id, industry_id=industry.id)
    db.session.add(ei)
    db.session.commit()

    doc = _build_entity_doc(EntityType.PERSON, person, db.session)
    assert doc["industries"] == ["ClimateOps"]


# ---------------------------------------------------------------------------
# Organization doc tests
# ---------------------------------------------------------------------------


def test_build_entity_doc_org_basic_fields(db_session):
    """_build_entity_doc returns required id/entity_type/db_id/name/org_type for an Org."""
    from project.models.entity import Organization
    from project.models.entity_search import _build_entity_doc
    from project.utils.enums import EntityType, OrgType

    db = db_session
    org = Organization(
        name="Seed Partners",
        slug="seed-partners",
        org_type=OrgType.VC_FIRM,
        about="Early stage fund",
        website="https://seed.vc",
    )
    db.session.add(org)
    db.session.commit()

    doc = _build_entity_doc(EntityType.ORG, org, db.session)

    assert doc["id"] == f"org_{org.id}"
    assert doc["entity_type"] == "org"
    assert doc["db_id"] == org.id
    assert doc["name"] == "Seed Partners"
    assert doc["slug"] == "seed-partners"
    assert doc["about"] == "Early stage fund"
    assert doc["org_type"] == OrgType.VC_FIRM.value
    assert doc["website"] == "https://seed.vc"
    assert "person_names" not in doc
    assert "industries" not in doc
    assert "check_size_min" not in doc
    assert "check_size_max" not in doc


def test_build_entity_doc_org_with_profile_and_geo(db_session):
    """Org doc picks up investor profile fields (check_size, stages) and geography."""
    from project.models.entity import (
        EntityGeography,
        EntityStage,
        Geography,
        InvestorProfile,
        Organization,
    )
    from project.models.entity_search import _build_entity_doc
    from project.utils.enums import EntityType, InvestmentStage, InvestorType, OrgType

    db = db_session

    org = Organization(name="Series A Fund", slug="series-a-fund", org_type=OrgType.VC_FIRM)
    db.session.add(org)
    db.session.flush()

    profile = InvestorProfile(
        entity_type=EntityType.ORG,
        entity_id=org.id,
        investor_type=InvestorType.VC_FIRM,
        min_investment=500_000,
        max_investment=5_000_000,
        n_investments=12,
        n_exits=3,
        accepts_cold_inbound=True,
        is_active=True,
    )
    db.session.add(profile)

    stage = EntityStage(
        entity_type=EntityType.ORG,
        entity_id=org.id,
        stage=InvestmentStage.SERIES_A,
    )
    db.session.add(stage)

    geo = Geography(slug="gb", name="United Kingdom", type="country", country_code="GB")
    db.session.add(geo)
    db.session.flush()

    eg = EntityGeography(entity_type=EntityType.ORG, entity_id=org.id, geography_id=geo.id)
    db.session.add(eg)
    db.session.commit()

    doc = _build_entity_doc(EntityType.ORG, org, db.session)

    assert doc["org_type"] == OrgType.VC_FIRM.value
    assert doc["investor_type"] == InvestorType.VC_FIRM.value
    assert doc["check_size_min"] == 500_000
    assert doc["check_size_max"] == 5_000_000
    assert doc["n_investments"] == 12
    assert doc["n_exits"] == 3
    assert doc["accepts_cold_inbound"] is True
    assert doc["is_active"] is True
    assert doc["stages"] == [InvestmentStage.SERIES_A.value]
    assert doc["geographies"] == ["gb"]
    assert doc["country_code"] == "GB"


def test_build_entity_doc_org_person_names(db_session):
    """Org doc aggregates affiliated person names into person_names list."""
    from project.models.entity import Affiliation, Organization, Person
    from project.models.entity_search import _build_entity_doc
    from project.utils.enums import AffiliationRole, EntityType, OrgType

    db = db_session

    org = Organization(name="Duo Fund", slug="duo-fund", org_type=OrgType.VC_FIRM)
    db.session.add(org)
    db.session.flush()

    p1 = Person(first_name="Alice", last_name="One", slug="alice-one")
    p2 = Person(first_name="Bob", last_name="Two", slug="bob-two")
    db.session.add_all([p1, p2])
    db.session.flush()

    db.session.add(Affiliation(person_id=p1.id, organization_id=org.id, role=AffiliationRole.PARTNER))
    db.session.add(Affiliation(person_id=p2.id, organization_id=org.id, role=AffiliationRole.PARTNER))
    db.session.commit()

    doc = _build_entity_doc(EntityType.ORG, org, db.session)

    assert set(doc["person_names"]) == {"Alice One", "Bob Two"}


# ---------------------------------------------------------------------------
# NotableInvestment relocation sanity
# ---------------------------------------------------------------------------


def test_notable_investment_importable_from_entity(db_session):
    """NotableInvestment is importable from project.models.entity after relocation."""
    from project.models.entity import NotableInvestment

    db = db_session
    ni = NotableInvestment(name="MegaCorp")
    db.session.add(ni)
    db.session.commit()

    fetched = db.session.get(NotableInvestment, ni.id)
    assert fetched is not None
    assert fetched.name == "MegaCorp"
    assert fetched.to_dict() == {"id": ni.id, "name": "MegaCorp"}


def test_notable_investment_still_re_exported_from_investor(db_session):
    """NotableInvestment remains importable from project.models.investor for BC."""
    from project.models.investor import NotableInvestment  # noqa: F401 — just ensure importable

    assert NotableInvestment.__tablename__ == "notable_investment"
