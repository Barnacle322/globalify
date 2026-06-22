"""Tests for backfill_entities() — Phase 1b Task 2.

TDD: this file is written BEFORE the backfill module.  Running it before
``src/project/models/backfill.py`` exists produces import failures.  Once the
module is implemented all assertions should pass.

Fixture layout
--------------
* 2 Investors
    - investor_a: firm_name = "Acme Capital" (EXACT match against the seeded
      InvestmentFirm → should create an Affiliation pointing at that Org).
    - investor_b: firm_name = "Unknown Ventures" (NO match → stub Org created).
* 1 InvestmentFirm: name = "Acme Capital"
* 1 Industry + 1 Round linked to investor_a via M2M
* 1 NotableInvestment linked to investor_a via M2M
* 1 InvestorBookmark  (user → investor_a)
* 1 InvestmentFirmBookmark  (user → the InvestmentFirm)
"""

from __future__ import annotations

import os

os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("_DATABASE_URL", "sqlite:///test_backfill_db.sqlite")

import pytest  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_session(app):
    """Push an app context, create ALL tables, yield the db object, then teardown."""
    from project.extensions import db

    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def seeded(db_session):  # noqa: C901  (acceptable complexity for a fixture)
    """Seed a minimal fixture and return a namespace with all seeded objects."""
    from project.models.backfill import InvestmentFirm, InvestmentFirmBookmark, Investor, InvestorBookmark
    from project.models.entity import NotableInvestment
    from project.models.helpers import Industry, Round
    from project.models.user import User

    db = db_session

    # User (needed for bookmarks)
    user = User(email="backfill-user@test.com")
    db.session.add(user)
    db.session.flush()

    # InvestmentFirm (will be exact-matched by investor_a.firm_name)
    firm = InvestmentFirm(name="Acme Capital", slug="acme-capital")
    db.session.add(firm)
    db.session.flush()

    # Industry + Round (auto-populated from after_create events, but we create
    # explicit ones to guarantee they exist and have known ids)
    industry = db.session.scalar(db.select(Industry).limit(1))
    if industry is None:
        industry = Industry(name="FinTech", category="Finance")
        db.session.add(industry)
        db.session.flush()

    round_ = db.session.scalar(db.select(Round).where(Round.name == "Seed"))
    if round_ is None:
        round_ = Round(name="Seed")
        db.session.add(round_)
        db.session.flush()

    # NotableInvestment
    notable = NotableInvestment(name="TestPortfolioCo")
    db.session.add(notable)
    db.session.flush()

    # Investor A — firm_name exactly matches the InvestmentFirm above
    investor_a = Investor(
        first_name="Alice",
        last_name="Smith",
        slug="alice-smith-bf",
        firm_name="Acme Capital",
        about="Angel investor",
        position="Partner",
        is_public=True,
        is_approved=True,
        location="New York",
        min_investment=50000,
        max_investment=500000,
        n_investments=10,
        n_exits=2,
    )
    # Investor B — firm_name does NOT match any existing firm
    investor_b = Investor(
        first_name="Bob",
        last_name="Jones",
        slug="bob-jones-bf",
        firm_name="Unknown Ventures",
        about=None,
        position=None,
        is_public=False,
        is_approved=False,
    )
    db.session.add_all([investor_a, investor_b])
    db.session.flush()

    # M2M: industry + round + notable → investor_a only
    investor_a.industries.append(industry)
    investor_a.rounds.append(round_)
    investor_a.notable_investments.append(notable)
    db.session.flush()

    # Bookmarks
    inv_bm = InvestorBookmark(user_id=user.id, investor_id=investor_a.id)
    firm_bm = InvestmentFirmBookmark(user_id=user.id, investment_firm_id=firm.id)
    db.session.add_all([inv_bm, firm_bm])
    db.session.commit()

    class Namespace:
        pass

    ns = Namespace()
    ns.db = db
    ns.user = user
    ns.firm = firm
    ns.industry = industry
    ns.round_ = round_
    ns.notable = notable
    ns.investor_a = investor_a
    ns.investor_b = investor_b
    ns.inv_bm = inv_bm
    ns.firm_bm = firm_bm
    return ns


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_backfill_module_importable():
    """The backfill module must be importable."""
    from project.models.backfill import backfill_entities  # noqa: F401

    assert callable(backfill_entities)


def test_backfill_returns_counts(seeded):
    """backfill_entities() must return a counts dict with expected keys."""
    from project.models.backfill import backfill_entities

    counts = backfill_entities(seeded.db.session)

    expected_keys = {
        "persons",
        "organizations",
        "stub_orgs",
        "affiliations",
        "investor_profiles",
        "entity_industries",
        "entity_stages",
        "entity_notables",
        "entity_geographies",
        "entity_bookmarks",
    }
    assert expected_keys == set(counts.keys()), f"Missing keys: {expected_keys - set(counts.keys())}"


def test_backfill_person_count(seeded):
    """One Person per Investor."""
    from project.models.backfill import backfill_entities
    from project.models.entity import Person

    db = seeded.db
    counts = backfill_entities(db.session)

    assert counts["persons"] == 2  # investor_a + investor_b
    assert db.session.query(Person).count() == 2


def test_backfill_organization_count(seeded):
    """One Org per InvestmentFirm + one stub Org for unmatched firm_name."""
    from project.models.backfill import backfill_entities
    from project.models.entity import Organization

    db = seeded.db
    counts = backfill_entities(db.session)

    # 1 real firm + 1 stub = 2 total
    assert counts["organizations"] == 2
    assert counts["stub_orgs"] == 1
    assert db.session.query(Organization).count() == 2


def test_backfill_matched_affiliation_links_correct_org(seeded):
    """investor_a's firm_name 'Acme Capital' must link to the existing Organization."""
    from project.models.backfill import backfill_entities
    from project.models.entity import Affiliation, Organization, Person
    from project.utils.enums import AffiliationRole, OrgType

    db = seeded.db
    backfill_entities(db.session)

    # Find the person that was created from investor_a
    person_a = db.session.scalar(db.select(Person).where(Person.slug == "alice-smith-bf"))
    assert person_a is not None, "Person for investor_a not found"

    # Find the org created from the InvestmentFirm (not a stub)
    real_org = db.session.scalar(db.select(Organization).where(Organization.org_type == OrgType.VC_FIRM))
    assert real_org is not None, "Real VC_FIRM org not found"
    assert real_org.name == "Acme Capital"

    # Affiliation must link person_a → real_org
    aff = db.session.scalar(
        db.select(Affiliation).where(
            Affiliation.person_id == person_a.id,
            Affiliation.organization_id == real_org.id,
        )
    )
    assert aff is not None, "Affiliation from investor_a to real org not found"
    assert aff.role == AffiliationRole.PARTNER


def test_backfill_unmatched_creates_stub_org(seeded):
    """investor_b's unmatched firm_name must produce a stub Org + Affiliation."""
    from project.models.backfill import backfill_entities
    from project.models.entity import Affiliation, Organization, Person
    from project.utils.enums import OrgType

    db = seeded.db
    backfill_entities(db.session)

    # Person for investor_b
    person_b = db.session.scalar(db.select(Person).where(Person.slug == "bob-jones-bf"))
    assert person_b is not None, "Person for investor_b not found"

    # Stub org should exist with OTHER type
    stub_org = db.session.scalar(
        db.select(Organization).where(
            Organization.name == "Unknown Ventures",
            Organization.org_type == OrgType.OTHER,
        )
    )
    assert stub_org is not None, "Stub org for 'Unknown Ventures' not found"
    assert stub_org.is_public is False

    # Affiliation must exist
    aff = db.session.scalar(
        db.select(Affiliation).where(
            Affiliation.person_id == person_b.id,
            Affiliation.organization_id == stub_org.id,
        )
    )
    assert aff is not None, "Affiliation for investor_b stub not found"


def test_backfill_investor_profiles(seeded):
    """One InvestorProfile per person AND per real org (stub org also gets one)."""
    from project.models.backfill import backfill_entities
    from project.models.entity import InvestorProfile

    db = seeded.db
    counts = backfill_entities(db.session)

    # 2 persons + 2 orgs (1 real + 1 stub) = 4 profiles
    assert counts["investor_profiles"] == 4
    assert db.session.query(InvestorProfile).count() == 4


def test_backfill_entity_industries(seeded):
    """EntityIndustry rows mirror the seeded M2M (investor_a has 1 industry)."""
    from project.models.backfill import backfill_entities
    from project.models.entity import EntityIndustry

    db = seeded.db
    counts = backfill_entities(db.session)

    # investor_a → 1 industry; investor_b → 0; firm → 0
    assert counts["entity_industries"] == 1
    assert db.session.query(EntityIndustry).count() == 1


def test_backfill_entity_stages(seeded):
    """EntityStage rows mirror the seeded rounds (investor_a has 'Seed' → SEED)."""
    from project.models.backfill import backfill_entities
    from project.models.entity import EntityStage
    from project.utils.enums import InvestmentStage

    db = seeded.db
    counts = backfill_entities(db.session)

    # investor_a → Round("Seed") → InvestmentStage.SEED (exactly 1 stage row)
    assert counts["entity_stages"] == 1
    assert db.session.query(EntityStage).count() == 1

    stages = db.session.scalars(db.select(EntityStage)).all()
    stage_values = {s.stage for s in stages}
    assert InvestmentStage.SEED in stage_values


def test_backfill_entity_notables(seeded):
    """EntityNotable rows mirror the seeded notable investments (investor_a has 1)."""
    from project.models.backfill import backfill_entities
    from project.models.entity import EntityNotable

    db = seeded.db
    counts = backfill_entities(db.session)

    assert counts["entity_notables"] == 1
    assert db.session.query(EntityNotable).count() == 1


def test_backfill_entity_geographies(seeded):
    """investor_a.location = 'New York' → Geography created + EntityGeography linked."""
    from project.models.backfill import backfill_entities
    from project.models.entity import EntityGeography, Geography

    db = seeded.db
    counts = backfill_entities(db.session)

    # 1 geography for investor_a's "New York" location (investor_b has no location)
    assert counts["entity_geographies"] == 1
    geos = db.session.scalars(db.select(Geography)).all()
    geo_names = {g.name for g in geos}
    assert "New York" in geo_names

    entity_geos = db.session.scalars(db.select(EntityGeography)).all()
    assert len(entity_geos) == 1


def test_backfill_entity_bookmarks(seeded):
    """InvestorBookmark + InvestmentFirmBookmark → 2 EntityBookmark rows."""
    from project.models.backfill import backfill_entities
    from project.models.entity import EntityBookmark
    from project.utils.enums import EntityType

    db = seeded.db
    counts = backfill_entities(db.session)

    assert counts["entity_bookmarks"] == 2
    assert db.session.query(EntityBookmark).count() == 2

    bms = db.session.scalars(db.select(EntityBookmark)).all()
    entity_types = {bm.entity_type for bm in bms}
    assert EntityType.PERSON in entity_types
    assert EntityType.ORG in entity_types


def test_backfill_person_fields_mapped(seeded):
    """Check that key Person fields are correctly copied from Investor."""
    from project.models.backfill import backfill_entities
    from project.models.entity import Person

    db = seeded.db
    backfill_entities(db.session)

    person_a = db.session.scalar(db.select(Person).where(Person.slug == "alice-smith-bf"))
    assert person_a is not None
    assert person_a.first_name == "Alice"
    assert person_a.last_name == "Smith"
    assert person_a.about == "Angel investor"
    assert person_a.headline == "Partner"  # Investor.position → Person.headline
    assert person_a.is_public is True
    assert person_a.is_approved is True


def test_backfill_organization_fields_mapped(seeded):
    """Check that key Organization fields are correctly copied from InvestmentFirm."""
    from project.models.backfill import backfill_entities
    from project.models.entity import Organization
    from project.utils.enums import OrgType

    db = seeded.db
    backfill_entities(db.session)

    org = db.session.scalar(db.select(Organization).where(Organization.name == "Acme Capital"))
    assert org is not None
    assert org.slug == "acme-capital"
    assert org.org_type == OrgType.VC_FIRM
    assert org.is_public is True


def test_backfill_investor_profile_fields(seeded):
    """InvestorProfile for investor_a should carry investment range."""
    from project.models.backfill import backfill_entities
    from project.models.entity import InvestorProfile, Person
    from project.utils.enums import EntityType

    db = seeded.db
    backfill_entities(db.session)

    person_a = db.session.scalar(db.select(Person).where(Person.slug == "alice-smith-bf"))
    profile = db.session.scalar(
        db.select(InvestorProfile).where(
            InvestorProfile.entity_type == EntityType.PERSON,
            InvestorProfile.entity_id == person_a.id,
        )
    )
    assert profile is not None
    assert profile.min_investment == 50000
    assert profile.max_investment == 500000
    assert profile.n_investments == 10
    assert profile.n_exits == 2
    assert profile.accepts_cold_inbound is False
    assert profile.is_active is True


def test_backfill_series_b_plus_expansion(db_session):
    """Round name 'Series B+' must produce BOTH SERIES_B and SERIES_C EntityStage rows."""
    from project.models.backfill import Investor, backfill_entities
    from project.models.entity import EntityStage, Person
    from project.models.helpers import Round
    from project.utils.enums import InvestmentStage

    db = db_session

    round_b_plus = Round(name="Series B+")
    db.session.add(round_b_plus)
    db.session.flush()

    investor = Investor(
        first_name="Carol",
        last_name="Chen",
        slug="carol-chen-bplus",
        is_public=False,
        is_approved=False,
    )
    db.session.add(investor)
    db.session.flush()

    investor.rounds.append(round_b_plus)
    db.session.commit()

    backfill_entities(db.session)

    person = db.session.scalar(db.select(Person).where(Person.slug == "carol-chen-bplus"))
    assert person is not None, "Person for Series B+ investor not found"

    stages = db.session.scalars(db.select(EntityStage).where(EntityStage.entity_id == person.id)).all()
    stage_values = {s.stage for s in stages}

    assert InvestmentStage.SERIES_B in stage_values, f"SERIES_B missing from expanded B+ stages; got {stage_values}"
    assert InvestmentStage.SERIES_C in stage_values, f"SERIES_C missing from expanded B+ stages; got {stage_values}"


def test_backfill_fuzzy_match_near_name(db_session):
    """A firm_name that fuzzy-scores >= 90 against an existing firm must link to that org."""
    from project.models.backfill import InvestmentFirm, Investor, backfill_entities
    from project.models.entity import Affiliation, Organization, Person

    db = db_session

    firm = InvestmentFirm(name="Acme Capital", slug="acme-capital-fuzz")
    db.session.add(firm)
    db.session.flush()

    # "acme capital" (lowercase) scores 100 via fuzz.ratio against "acme capital"
    investor = Investor(
        first_name="Dave",
        last_name="Diaz",
        slug="dave-diaz-fuzz",
        firm_name="acme capital",  # lowercase near-variant; ratio == 100
        is_public=False,
        is_approved=False,
    )
    db.session.add(investor)
    db.session.commit()

    org_count_before = db.session.query(Organization).count()
    backfill_entities(db.session)

    # Organization count should not have grown beyond the 1 real firm
    org_count_after = db.session.query(Organization).count()
    # Only 1 org from the firm — no new stub should have been created
    assert org_count_after == org_count_before + 1, (
        f"Expected exactly 1 new org (the real firm), got {org_count_after - org_count_before}"
    )

    person = db.session.scalar(db.select(Person).where(Person.slug == "dave-diaz-fuzz"))
    assert person is not None

    real_org = db.session.scalar(db.select(Organization).where(Organization.name == "Acme Capital"))
    assert real_org is not None

    aff = db.session.scalar(
        db.select(Affiliation).where(
            Affiliation.person_id == person.id,
            Affiliation.organization_id == real_org.id,
        )
    )
    assert aff is not None, "Affiliation to existing 'Acme Capital' org not found after fuzzy match"


def test_backfill_duplicate_firm_name_shares_stub(db_session):
    """Two investors with the SAME unmatched firm_name share exactly ONE stub Organization."""
    from project.models.backfill import Investor, backfill_entities
    from project.models.entity import Affiliation, Organization, Person

    db = db_session

    inv1 = Investor(
        first_name="Eve",
        last_name="Evans",
        slug="eve-evans-ghost",
        firm_name="Ghost Ventures",
        is_public=False,
        is_approved=False,
    )
    inv2 = Investor(
        first_name="Frank",
        last_name="Fong",
        slug="frank-fong-ghost",
        firm_name="Ghost Ventures",
        is_public=False,
        is_approved=False,
    )
    db.session.add_all([inv1, inv2])
    db.session.commit()

    backfill_entities(db.session)

    ghost_orgs = db.session.scalars(db.select(Organization).where(Organization.name == "Ghost Ventures")).all()
    assert len(ghost_orgs) == 1, f"Expected exactly 1 stub org for 'Ghost Ventures', found {len(ghost_orgs)}"
    stub_org = ghost_orgs[0]

    person1 = db.session.scalar(db.select(Person).where(Person.slug == "eve-evans-ghost"))
    person2 = db.session.scalar(db.select(Person).where(Person.slug == "frank-fong-ghost"))
    assert person1 is not None
    assert person2 is not None

    aff1 = db.session.scalar(
        db.select(Affiliation).where(
            Affiliation.person_id == person1.id,
            Affiliation.organization_id == stub_org.id,
        )
    )
    aff2 = db.session.scalar(
        db.select(Affiliation).where(
            Affiliation.person_id == person2.id,
            Affiliation.organization_id == stub_org.id,
        )
    )
    assert aff1 is not None, "Affiliation for eve-evans-ghost to Ghost Ventures stub not found"
    assert aff2 is not None, "Affiliation for frank-fong-ghost to Ghost Ventures stub not found"


def test_backfill_entity_industry_discriminator(seeded):
    """EntityIndustry for an investor has entity_type == PERSON and correct entity_id."""
    from project.models.backfill import backfill_entities
    from project.models.entity import EntityIndustry, Person
    from project.utils.enums import EntityType

    db = seeded.db
    backfill_entities(db.session)

    person_a = db.session.scalar(db.select(Person).where(Person.slug == "alice-smith-bf"))
    assert person_a is not None

    ei = db.session.scalar(
        db.select(EntityIndustry).where(
            EntityIndustry.entity_id == person_a.id,
            EntityIndustry.entity_type == EntityType.PERSON,
        )
    )
    assert ei is not None, "EntityIndustry row for investor_a not found"
    assert ei.entity_type == EntityType.PERSON, f"Expected entity_type PERSON, got {ei.entity_type}"
    assert ei.entity_id == person_a.id, f"Expected entity_id {person_a.id}, got {ei.entity_id}"
