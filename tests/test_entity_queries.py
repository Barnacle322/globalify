"""Tests for Phase 2b Task 1: get_by_slug + load_profile_bundle helpers.

TDD: these tests are written BEFORE the implementation.  Run them first to
confirm they fail with AttributeError/ImportError, then implement the helpers
in entity.py to make them green.
"""

from __future__ import annotations

import os

os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("_DATABASE_URL", "sqlite:///test_entity_queries.sqlite")

import pytest  # noqa: E402

# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_session(app):
    """Push an app context, create all tables, yield the db, then teardown."""
    from project.extensions import db

    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()


# ---------------------------------------------------------------------------
# Helpers importable
# ---------------------------------------------------------------------------


def test_get_by_slug_importable():
    """Person.get_by_slug and Organization.get_by_slug must be callable."""
    from project.models.entity import Organization, Person

    assert callable(Person.get_by_slug)
    assert callable(Organization.get_by_slug)


def test_load_profile_bundle_importable():
    """load_profile_bundle must be importable at module level."""
    from project.models.entity import load_profile_bundle

    assert callable(load_profile_bundle)


# ---------------------------------------------------------------------------
# Person.get_by_slug
# ---------------------------------------------------------------------------


def test_person_get_by_slug_returns_public_person(db_session):
    from project.models.entity import Person

    db = db_session
    person = Person(first_name="Alice", slug="alice-public", is_public=True)
    db.session.add(person)
    db.session.commit()

    result = Person.get_by_slug("alice-public")
    assert result is not None
    assert result.id == person.id
    assert result.first_name == "Alice"


def test_person_get_by_slug_ignores_nonpublic(db_session):
    from project.models.entity import Person

    db = db_session
    # default is_public=False
    person = Person(first_name="Bob", slug="bob-private")
    db.session.add(person)
    db.session.commit()

    result = Person.get_by_slug("bob-private")
    assert result is None


def test_person_get_by_slug_missing_returns_none(db_session):
    from project.models.entity import Person

    result = Person.get_by_slug("does-not-exist-xyz")
    assert result is None


def test_person_get_by_slug_public_only(db_session):
    """Slug exists but entity is not public → None."""
    from project.models.entity import Person

    db = db_session
    # Explicit is_public=False
    Person(first_name="Carol", slug="carol-notpublic", is_public=False)
    db.session.add(Person(first_name="Carol", slug="carol-notpublic", is_public=False))
    db.session.commit()

    assert Person.get_by_slug("carol-notpublic") is None


# ---------------------------------------------------------------------------
# Organization.get_by_slug
# ---------------------------------------------------------------------------


def test_org_get_by_slug_returns_public_org(db_session):
    from project.models.entity import Organization
    from project.utils.enums import OrgType

    db = db_session
    org = Organization(name="PublicVC", slug="public-vc", org_type=OrgType.VC_FIRM, is_public=True)
    db.session.add(org)
    db.session.commit()

    result = Organization.get_by_slug("public-vc")
    assert result is not None
    assert result.name == "PublicVC"


def test_org_get_by_slug_ignores_nonpublic(db_session):
    from project.models.entity import Organization
    from project.utils.enums import OrgType

    db = db_session
    org = Organization(name="PrivateVC", slug="private-vc", org_type=OrgType.VC_FIRM, is_public=False)
    db.session.add(org)
    db.session.commit()

    result = Organization.get_by_slug("private-vc")
    assert result is None


def test_org_get_by_slug_missing_returns_none(db_session):
    from project.models.entity import Organization

    result = Organization.get_by_slug("totally-missing-org")
    assert result is None


# ---------------------------------------------------------------------------
# load_profile_bundle — profile key
# ---------------------------------------------------------------------------


def test_load_profile_bundle_no_profile(db_session):
    """Bundle for an entity with no InvestorProfile should have profile=None."""
    from project.models.entity import Person, load_profile_bundle
    from project.utils.enums import EntityType

    db = db_session
    person = Person(first_name="Dave", slug="dave-noprofile", is_public=True)
    db.session.add(person)
    db.session.commit()

    bundle = load_profile_bundle(EntityType.PERSON, person.id)
    assert bundle["profile"] is None
    assert bundle["industries"] == []
    assert bundle["stages"] == []
    assert bundle["geographies"] == []
    assert bundle["notables"] == []
    assert bundle["affiliations"] == []


def test_load_profile_bundle_returns_profile(db_session):
    from project.models.entity import InvestorProfile, Person, load_profile_bundle
    from project.utils.enums import EntityType, InvestorType

    db = db_session
    person = Person(first_name="Eve", slug="eve-profile", is_public=True)
    db.session.add(person)
    db.session.flush()

    ip = InvestorProfile(
        entity_type=EntityType.PERSON,
        entity_id=person.id,
        investor_type=InvestorType.ANGEL,
        min_investment=10_000,
    )
    db.session.add(ip)
    db.session.commit()

    bundle = load_profile_bundle(EntityType.PERSON, person.id)
    assert bundle["profile"] is not None
    assert bundle["profile"].id == ip.id
    assert bundle["profile"].investor_type == InvestorType.ANGEL


# ---------------------------------------------------------------------------
# load_profile_bundle — industries
# ---------------------------------------------------------------------------


def test_load_profile_bundle_industries(db_session):
    from project.extensions import db as ext_db
    from project.models.entity import EntityIndustry, Person, load_profile_bundle
    from project.models.helpers import Industry
    from project.utils.enums import EntityType

    db = db_session
    person = Person(first_name="Frank", slug="frank-ind", is_public=True)
    db.session.add(person)
    db.session.flush()

    industry = ext_db.session.scalar(ext_db.select(Industry).limit(1))
    if industry is None:
        industry = Industry(name="FinTech", category="Finance")
        db.session.add(industry)
        db.session.flush()

    db.session.add(EntityIndustry(entity_type=EntityType.PERSON, entity_id=person.id, industry_id=industry.id))
    db.session.commit()

    bundle = load_profile_bundle(EntityType.PERSON, person.id)
    assert len(bundle["industries"]) == 1
    assert bundle["industries"][0].id == industry.id


# ---------------------------------------------------------------------------
# load_profile_bundle — stages
# ---------------------------------------------------------------------------


def test_load_profile_bundle_stages(db_session):
    from project.models.entity import EntityStage, Person, load_profile_bundle
    from project.utils.enums import EntityType, InvestmentStage

    db = db_session
    person = Person(first_name="Grace", slug="grace-stage", is_public=True)
    db.session.add(person)
    db.session.flush()

    db.session.add(EntityStage(entity_type=EntityType.PERSON, entity_id=person.id, stage=InvestmentStage.SEED))
    db.session.add(EntityStage(entity_type=EntityType.PERSON, entity_id=person.id, stage=InvestmentStage.SERIES_A))
    db.session.commit()

    bundle = load_profile_bundle(EntityType.PERSON, person.id)
    assert len(bundle["stages"]) == 2
    stage_values = {s for s in bundle["stages"]}
    assert InvestmentStage.SEED in stage_values
    assert InvestmentStage.SERIES_A in stage_values


# ---------------------------------------------------------------------------
# load_profile_bundle — geographies
# ---------------------------------------------------------------------------


def test_load_profile_bundle_geographies(db_session):
    from project.models.entity import EntityGeography, Geography, Person, load_profile_bundle
    from project.utils.enums import EntityType

    db = db_session
    person = Person(first_name="Hank", slug="hank-geo", is_public=True)
    geo = Geography(slug="fr", name="France", type="country", country_code="FR")
    db.session.add_all([person, geo])
    db.session.flush()

    db.session.add(EntityGeography(entity_type=EntityType.PERSON, entity_id=person.id, geography_id=geo.id))
    db.session.commit()

    bundle = load_profile_bundle(EntityType.PERSON, person.id)
    assert len(bundle["geographies"]) == 1
    assert bundle["geographies"][0].slug == "fr"


# ---------------------------------------------------------------------------
# load_profile_bundle — notables
# ---------------------------------------------------------------------------


def test_load_profile_bundle_notables(db_session):
    from project.models.entity import EntityNotable, NotableInvestment, Person, load_profile_bundle
    from project.utils.enums import EntityType

    db = db_session
    person = Person(first_name="Iris", slug="iris-notable", is_public=True)
    notable = NotableInvestment(name="TechCo")
    db.session.add_all([person, notable])
    db.session.flush()

    db.session.add(EntityNotable(entity_type=EntityType.PERSON, entity_id=person.id, notable_investment_id=notable.id))
    db.session.commit()

    bundle = load_profile_bundle(EntityType.PERSON, person.id)
    assert len(bundle["notables"]) == 1
    assert bundle["notables"][0].name == "TechCo"


# ---------------------------------------------------------------------------
# load_profile_bundle — affiliations (Person → orgs)
# ---------------------------------------------------------------------------


def test_load_profile_bundle_person_affiliations(db_session):
    """For a Person entity, affiliations should be the Affiliation rows where person_id matches."""
    from project.models.entity import Affiliation, Organization, Person, load_profile_bundle
    from project.utils.enums import AffiliationRole, EntityType, OrgType

    db = db_session
    person = Person(first_name="Jack", slug="jack-aff", is_public=True)
    org = Organization(name="JackFund", slug="jackfund", org_type=OrgType.VC_FIRM)
    db.session.add_all([person, org])
    db.session.flush()

    aff = Affiliation(person_id=person.id, organization_id=org.id, role=AffiliationRole.PARTNER)
    db.session.add(aff)
    db.session.commit()

    bundle = load_profile_bundle(EntityType.PERSON, person.id)
    assert len(bundle["affiliations"]) == 1
    assert bundle["affiliations"][0].person_id == person.id
    assert bundle["affiliations"][0].organization_id == org.id


def test_load_profile_bundle_org_affiliations(db_session):
    """For an Organization entity, affiliations should be Affiliation rows where organization_id matches."""
    from project.models.entity import Affiliation, Organization, Person, load_profile_bundle
    from project.utils.enums import AffiliationRole, EntityType, OrgType

    db = db_session
    person = Person(first_name="Kate", slug="kate-orgaff", is_public=True)
    org = Organization(name="KateFund", slug="katefund", org_type=OrgType.ACCELERATOR)
    db.session.add_all([person, org])
    db.session.flush()

    aff = Affiliation(person_id=person.id, organization_id=org.id, role=AffiliationRole.GP)
    db.session.add(aff)
    db.session.commit()

    bundle = load_profile_bundle(EntityType.ORG, org.id)
    assert len(bundle["affiliations"]) == 1
    assert bundle["affiliations"][0].organization_id == org.id
    assert bundle["affiliations"][0].person_id == person.id


# ---------------------------------------------------------------------------
# Full integration: bundle with all facets at once
# ---------------------------------------------------------------------------


def test_load_profile_bundle_full_integration(db_session):
    """Create a full graph and assert all bundle keys are populated correctly."""
    from project.extensions import db as ext_db
    from project.models.entity import (
        Affiliation,
        EntityGeography,
        EntityIndustry,
        EntityNotable,
        EntityStage,
        Geography,
        InvestorProfile,
        NotableInvestment,
        Organization,
        Person,
        load_profile_bundle,
    )
    from project.models.helpers import Industry
    from project.utils.enums import (
        AffiliationRole,
        EntityType,
        InvestmentStage,
        InvestorType,
        OrgType,
    )

    db = db_session

    person = Person(first_name="Liam", slug="liam-bundle", is_public=True)
    org = Organization(name="LiamCapital", slug="liam-capital", org_type=OrgType.MICRO_VC)
    db.session.add_all([person, org])
    db.session.flush()

    # InvestorProfile
    ip = InvestorProfile(
        entity_type=EntityType.PERSON,
        entity_id=person.id,
        investor_type=InvestorType.ANGEL,
        n_investments=5,
    )
    db.session.add(ip)

    # Affiliation
    aff = Affiliation(person_id=person.id, organization_id=org.id, role=AffiliationRole.ADVISOR)
    db.session.add(aff)

    # Geography
    geo = Geography(slug="jp", name="Japan", type="country", country_code="JP")
    db.session.add(geo)
    db.session.flush()

    # Industry
    industry = ext_db.session.scalar(ext_db.select(Industry).limit(1))
    if industry is None:
        industry = Industry(name="HealthTech", category="Health")
        db.session.add(industry)
        db.session.flush()

    # NotableInvestment
    notable = NotableInvestment(name="MegaStartup")
    db.session.add(notable)
    db.session.flush()

    # Facets
    db.session.add(EntityIndustry(entity_type=EntityType.PERSON, entity_id=person.id, industry_id=industry.id))
    db.session.add(EntityStage(entity_type=EntityType.PERSON, entity_id=person.id, stage=InvestmentStage.PRE_SEED))
    db.session.add(EntityGeography(entity_type=EntityType.PERSON, entity_id=person.id, geography_id=geo.id))
    db.session.add(EntityNotable(entity_type=EntityType.PERSON, entity_id=person.id, notable_investment_id=notable.id))
    db.session.commit()

    bundle = load_profile_bundle(EntityType.PERSON, person.id)

    assert bundle["profile"] is not None
    assert bundle["profile"].investor_type == InvestorType.ANGEL
    assert bundle["profile"].n_investments == 5

    assert len(bundle["industries"]) == 1
    assert bundle["industries"][0].id == industry.id

    assert len(bundle["stages"]) == 1
    assert bundle["stages"][0] == InvestmentStage.PRE_SEED

    assert len(bundle["geographies"]) == 1
    assert bundle["geographies"][0].slug == "jp"

    assert len(bundle["notables"]) == 1
    assert bundle["notables"][0].name == "MegaStartup"

    assert len(bundle["affiliations"]) == 1
    assert bundle["affiliations"][0].organization_id == org.id

    # Nothing leaks to the wrong entity type
    org_bundle = load_profile_bundle(EntityType.ORG, org.id)
    assert org_bundle["profile"] is None
    assert org_bundle["industries"] == []
    assert org_bundle["stages"] == []
    assert org_bundle["geographies"] == []
    assert org_bundle["notables"] == []
    # But org bundle should see the affiliation from org side
    assert len(org_bundle["affiliations"]) == 1
    assert org_bundle["affiliations"][0].person_id == person.id
