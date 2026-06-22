"""backfill_entities — Phase 1b Task 2.

Pure function that reads the OLD catalog (Investor / InvestmentFirm + their
firm_name strings + M2M facets + bookmarks) and writes into the NEW entity
model (Person / Organization / Affiliation / InvestorProfile / Geography and
the polymorphic entity_* join tables introduced in Task 1).

All existing rows in the old tables are left completely untouched.

Round name → InvestmentStage mapping
--------------------------------------
"Pre-Seed"  → PRE_SEED
"Seed"      → SEED
"Series A"  → SERIES_A
"Series B"  → SERIES_B
"Series C"  → SERIES_C
Names that imply "B+" (contain "B+" or both B and C) expand to SERIES_B +
SERIES_C.  Unrecognised names are silently skipped.
"""

from __future__ import annotations

import uuid

from slugify import slugify
from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String, func, text
from sqlalchemy.orm import Mapped, joinedload, mapped_column, relationship
from thefuzz import fuzz

from ..extensions import db
from ..utils.enums import (
    AffiliationRole,
    EntityType,
    InvestmentStage,
    OrgType,
)
from .entity import (
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
from .helpers import Industry, Round

# ---------------------------------------------------------------------------
# Legacy ORM classes — defined here so that db.create_all() creates the old
# tables in test environments and backfill_entities() can query them.
# These classes are NOT registered in models/__init__.py and should NOT be
# used outside this module.  The real tables still exist in production until
# Phase 2d Task 5's migration drops them.
# ---------------------------------------------------------------------------

_investor_round = db.Table(
    "investor_round",
    Column("investor_id", Integer, ForeignKey("investor.id"), primary_key=True),
    Column("round_id", Integer, ForeignKey("round.id"), primary_key=True),
)

_investor_industry = db.Table(
    "investor_industry",
    Column("investor_id", Integer, ForeignKey("investor.id"), primary_key=True),
    Column("industry_id", Integer, ForeignKey("industry.id"), primary_key=True),
)

_investor_notable_investment = db.Table(
    "investor_notable_investment",
    Column("investor_id", Integer, ForeignKey("investor.id"), primary_key=True),
    Column("notable_investment_id", Integer, ForeignKey("notable_investment.id"), primary_key=True),
)

_investment_firm_notable_investment = db.Table(
    "investment_firm_notable_investment",
    Column("investment_firm_id", Integer, ForeignKey("investment_firm.id"), primary_key=True),
    Column("notable_investment_id", Integer, ForeignKey("notable_investment.id"), primary_key=True),
)

_investment_firm_round = db.Table(
    "investment_firm_round",
    Column("investment_firm_id", Integer, ForeignKey("investment_firm.id"), primary_key=True),
    Column("round_id", Integer, ForeignKey("round.id"), primary_key=True),
)

_investment_firm_industry = db.Table(
    "investment_firm_industry",
    Column("investment_firm_id", Integer, ForeignKey("investment_firm.id"), primary_key=True),
    Column("industry_id", Integer, ForeignKey("industry.id"), primary_key=True),
)


class Investor(db.Model):
    """Legacy ORM class — reads the 'investor' table for backfill purposes only."""

    __tablename__ = "investor"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[str | None] = mapped_column(String, nullable=True)
    slug: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    firm_name: Mapped[str | None] = mapped_column(String, nullable=True)
    about: Mapped[str | None] = mapped_column(String, nullable=True)
    position: Mapped[str | None] = mapped_column(String, nullable=True)
    website: Mapped[str | None] = mapped_column(String, nullable=True)
    linkedin: Mapped[str | None] = mapped_column(String, nullable=True)
    twitter: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String, nullable=True)
    n_investments: Mapped[int | None] = mapped_column(Integer, nullable=True)
    n_exits: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_investment: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    max_investment: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    _coordinates: Mapped[str | None] = mapped_column(String, nullable=True)
    _country: Mapped[str | None] = mapped_column(String, nullable=True)
    bias: Mapped[int | None] = mapped_column(Integer, nullable=True)
    search_index: Mapped[str | None] = mapped_column(String, nullable=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("user.id"), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    is_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    notable_investments: Mapped[list[NotableInvestment]] = relationship(secondary=_investor_notable_investment)
    rounds: Mapped[list[Round]] = relationship(secondary=_investor_round)
    industries: Mapped[list[Industry]] = relationship(secondary=_investor_industry)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<Investor {self.first_name} {self.last_name}>"


class InvestmentFirm(db.Model):
    """Legacy ORM class — reads the 'investment_firm' table for backfill purposes only."""

    __tablename__ = "investment_firm"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    slug: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    about: Mapped[str | None] = mapped_column(String, nullable=True)
    website: Mapped[str | None] = mapped_column(String, nullable=True)
    linkedin: Mapped[str | None] = mapped_column(String, nullable=True)
    twitter: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    phone_number: Mapped[str | None] = mapped_column(String, nullable=True)
    n_investments: Mapped[int | None] = mapped_column(Integer, nullable=True)
    n_exits: Mapped[int | None] = mapped_column(Integer, nullable=True)
    n_employees: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_investment: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_investment: Mapped[int | None] = mapped_column(Integer, nullable=True)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    _coordinates: Mapped[str | None] = mapped_column(String, nullable=True)
    _country: Mapped[str | None] = mapped_column(String, nullable=True)
    bias: Mapped[int | None] = mapped_column(Integer, nullable=True)
    search_index: Mapped[str | None] = mapped_column(String, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    notable_investments: Mapped[list[NotableInvestment]] = relationship(secondary=_investment_firm_notable_investment)
    rounds: Mapped[list[Round]] = relationship(secondary=_investment_firm_round)
    industries: Mapped[list[Industry]] = relationship(secondary=_investment_firm_industry)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<InvestmentFirm {self.name}>"


class InvestorBookmark(db.Model):
    """Legacy ORM class — reads 'investor_bookmark' for backfill purposes only."""

    __tablename__ = "investor_bookmark"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    investor_id: Mapped[int] = mapped_column(Integer, ForeignKey("investor.id"), nullable=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class InvestmentFirmBookmark(db.Model):
    """Legacy ORM class — reads 'investment_firm_bookmark' for backfill purposes only."""

    __tablename__ = "investment_firm_bookmark"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    investment_firm_id: Mapped[int] = mapped_column(Integer, ForeignKey("investment_firm.id"), nullable=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_ROUND_MAP: dict[str, list[InvestmentStage]] = {
    "Pre-Seed": [InvestmentStage.PRE_SEED],
    "Seed": [InvestmentStage.SEED],
    "Series A": [InvestmentStage.SERIES_A],
    "Series B": [InvestmentStage.SERIES_B],
    "Series C": [InvestmentStage.SERIES_C],
    # Expansion variants recorded in production data
    "Series B+": [InvestmentStage.SERIES_B, InvestmentStage.SERIES_C],
    "Series C+": [InvestmentStage.SERIES_C],
}

_FUZZY_THRESHOLD = 90


def _round_to_stages(round_name: str) -> list[InvestmentStage]:
    """Map a Round.name to one or more InvestmentStage values.

    Falls back to a fuzzy scan of *_ROUND_MAP* if the name isn't an exact key,
    then returns an empty list if nothing matches.
    """
    if round_name in _ROUND_MAP:
        return _ROUND_MAP[round_name]

    # Treat names that contain "B+" literally
    if "B+" in round_name or ("Series B" in round_name and "Series C" in round_name):
        return [InvestmentStage.SERIES_B, InvestmentStage.SERIES_C]

    # Try case-insensitive exact match
    lower = round_name.strip().lower()
    for key, stages in _ROUND_MAP.items():
        if key.lower() == lower:
            return stages

    return []


def _unique_slug(base: str, used: set[str]) -> str:
    """Return *base* slug (or *base*-<4hex>) that is not in *used*; register it."""
    slug = base
    if slug in used:
        slug = f"{base}-{uuid.uuid4().hex[:4]}"
    used.add(slug)
    return slug


def _get_or_create_geography(session, location: str, geo_cache: dict[str, Geography]) -> Geography:
    """Get or create a Geography row for a free-text location string."""
    key = location.strip().lower()
    if key in geo_cache:
        return geo_cache[key]

    slug = slugify(location.strip())
    # Try to load an existing row first (idempotency within a run)
    existing = session.scalar(db.select(Geography).where(Geography.slug == slug))
    if existing is not None:
        geo_cache[key] = existing
        return existing

    geo = Geography(slug=slug, name=location.strip(), type="city")
    session.add(geo)
    session.flush()
    geo_cache[key] = geo
    return geo


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def backfill_entities(session) -> dict[str, int]:  # noqa: C901 (acceptable length for a migration fn)
    """Map old Investor/InvestmentFirm catalog into the new entity model.

    Parameters
    ----------
    session:
        An active SQLAlchemy ``Session`` (typically ``db.session``).

    Returns
    -------
    dict
        Counts report with keys:
        persons, organizations, stub_orgs, affiliations, investor_profiles,
        entity_industries, entity_stages, entity_notables, entity_geographies,
        entity_bookmarks.
    """
    counts: dict[str, int] = {
        "persons": 0,
        "organizations": 0,
        "stub_orgs": 0,
        "affiliations": 0,
        "investor_profiles": 0,
        "entity_industries": 0,
        "entity_stages": 0,
        "entity_notables": 0,
        "entity_geographies": 0,
        "entity_bookmarks": 0,
    }

    # Track slugs we hand out so we never duplicate within a single run
    used_person_slugs: set[str] = set()
    used_org_slugs: set[str] = set()

    # Geography cache: normalised location string → Geography row
    geo_cache: dict[str, Geography] = {}

    # ------------------------------------------------------------------
    # Step 1: Investors → Person
    # ------------------------------------------------------------------
    investors = session.scalars(db.select(Investor)).all()

    # investor.id → Person (needed later for facets / bookmarks)
    investor_person: dict[int, Person] = {}

    for inv in investors:
        slug = _unique_slug(inv.slug or slugify(f"{inv.first_name} {inv.last_name or ''}"), used_person_slugs)
        person = Person(
            first_name=inv.first_name,
            last_name=inv.last_name,
            slug=slug,
            about=inv.about,
            # Investor.position → Person.headline
            headline=inv.position,
            website=inv.website,
            linkedin=inv.linkedin,
            twitter=inv.twitter,
            email=inv.email,
            phone_number=inv.phone_number,
            is_public=bool(inv.is_public),
            is_approved=bool(inv.is_approved),
            user_id=inv.user_id,
        )
        session.add(person)
        investor_person[inv.id] = person

    session.flush()
    counts["persons"] = len(investor_person)

    # ------------------------------------------------------------------
    # Step 2: InvestmentFirms → Organization
    # ------------------------------------------------------------------
    firms = session.scalars(db.select(InvestmentFirm)).all()

    # firm.id → Organization
    firm_org: dict[int, Organization] = {}
    # normalised name → Organization (for fuzzy matching firm_name strings)
    name_org: dict[str, Organization] = {}

    for firm in firms:
        slug = _unique_slug(
            firm.slug or slugify(firm.name or f"firm-{firm.id}"),
            used_org_slugs,
        )
        org = Organization(
            name=firm.name or "",
            slug=slug,
            org_type=OrgType.VC_FIRM,
            about=firm.about,
            website=firm.website,
            linkedin=firm.linkedin,
            twitter=firm.twitter,
            email=firm.email,
            phone_number=firm.phone_number,
            n_employees=firm.n_employees,
            is_public=True,
        )
        session.add(org)
        firm_org[firm.id] = org
        if firm.name:
            name_org[firm.name.strip().lower()] = org

    session.flush()
    counts["organizations"] = len(firm_org)

    # ------------------------------------------------------------------
    # Step 3: Affiliations (Investor.firm_name → Affiliation)
    # ------------------------------------------------------------------
    # Reload investors with their relationship data
    investors = (
        session.scalars(
            db.select(Investor).options(
                *[],  # already loaded above; re-query ensures fresh state
            )
        )
        .unique()
        .all()
    )

    for inv in investors:
        raw_name = inv.firm_name
        if not raw_name or not raw_name.strip():
            continue

        person = investor_person[inv.id]
        normalized = raw_name.strip().lower()

        # 1. Exact match (case-insensitive)
        matched_org: Organization | None = name_org.get(normalized)

        # 2. Fuzzy match if no exact hit
        if matched_org is None:
            best_ratio = 0
            for cand_name, cand_org in name_org.items():
                ratio = fuzz.ratio(normalized, cand_name)
                if ratio >= _FUZZY_THRESHOLD and ratio > best_ratio:
                    best_ratio = ratio
                    matched_org = cand_org

        if matched_org is not None:
            # Link to existing org
            aff = Affiliation(
                person_id=person.id,
                organization_id=matched_org.id,
                role=AffiliationRole.PARTNER,
            )
            session.add(aff)
            counts["affiliations"] += 1
        else:
            # Create stub org
            stub_slug = _unique_slug(slugify(raw_name.strip()), used_org_slugs)
            stub_org = Organization(
                name=raw_name.strip(),
                slug=stub_slug,
                org_type=OrgType.OTHER,
                is_public=False,
            )
            session.add(stub_org)
            session.flush()

            counts["stub_orgs"] += 1
            counts["organizations"] += 1

            # Register stub in name_org so duplicate firm_names share the same stub
            name_org[normalized] = stub_org

            aff = Affiliation(
                person_id=person.id,
                organization_id=stub_org.id,
                role=AffiliationRole.PARTNER,
            )
            session.add(aff)
            counts["affiliations"] += 1

    session.flush()

    # ------------------------------------------------------------------
    # Step 4: InvestorProfile per Person + per Organization
    # ------------------------------------------------------------------
    for inv in investors:
        person = investor_person[inv.id]
        ip = InvestorProfile(
            entity_type=EntityType.PERSON,
            entity_id=person.id,
            min_investment=inv.min_investment,
            max_investment=inv.max_investment,
            n_investments=inv.n_investments,
            n_exits=inv.n_exits,
            accepts_cold_inbound=False,
            is_active=True,
        )
        session.add(ip)
        counts["investor_profiles"] += 1

    for firm in firms:
        org = firm_org[firm.id]
        ip = InvestorProfile(
            entity_type=EntityType.ORG,
            entity_id=org.id,
            min_investment=firm.min_investment,
            max_investment=firm.max_investment,
            n_investments=firm.n_investments,
            n_exits=firm.n_exits,
            thesis=firm.about,
            accepts_cold_inbound=False,
            is_active=True,
        )
        session.add(ip)
        counts["investor_profiles"] += 1

    # Also create InvestorProfile for stub orgs (they have no InvestmentFirm source)
    # Identify stub org objects by tracking them above — we'll do it via a second pass
    # on the affiliations we just created, finding orgs with org_type=OTHER.
    stub_orgs = session.scalars(db.select(Organization).where(Organization.org_type == OrgType.OTHER)).all()
    for stub in stub_orgs:
        ip = InvestorProfile(
            entity_type=EntityType.ORG,
            entity_id=stub.id,
            accepts_cold_inbound=False,
            is_active=True,
        )
        session.add(ip)
        counts["investor_profiles"] += 1

    session.flush()

    # ------------------------------------------------------------------
    # Step 5: EntityIndustry / EntityStage / EntityNotable (Investor M2M)
    # ------------------------------------------------------------------
    # Reload investors with relationships eagerly loaded
    investors_with_facets = (
        session.scalars(
            db.select(Investor).options(
                joinedload(Investor.industries),
                joinedload(Investor.rounds),
                joinedload(Investor.notable_investments),
            )
        )
        .unique()
        .all()
    )

    for inv in investors_with_facets:
        person = investor_person[inv.id]
        etype = EntityType.PERSON
        eid = person.id

        for industry in inv.industries:
            ei = EntityIndustry(entity_type=etype, entity_id=eid, industry_id=industry.id)
            session.add(ei)
            counts["entity_industries"] += 1

        for round_ in inv.rounds:
            for stage in _round_to_stages(round_.name):
                es = EntityStage(entity_type=etype, entity_id=eid, stage=stage)
                session.add(es)
                counts["entity_stages"] += 1

        for notable in inv.notable_investments:
            en = EntityNotable(entity_type=etype, entity_id=eid, notable_investment_id=notable.id)
            session.add(en)
            counts["entity_notables"] += 1

    # InvestmentFirm M2M
    firms_with_facets = (
        session.scalars(
            db.select(InvestmentFirm).options(
                joinedload(InvestmentFirm.industries),
                joinedload(InvestmentFirm.rounds),
                joinedload(InvestmentFirm.notable_investments),
            )
        )
        .unique()
        .all()
    )

    for firm in firms_with_facets:
        org = firm_org[firm.id]
        etype = EntityType.ORG
        eid = org.id

        for industry in firm.industries:
            ei = EntityIndustry(entity_type=etype, entity_id=eid, industry_id=industry.id)
            session.add(ei)
            counts["entity_industries"] += 1

        for round_ in firm.rounds:
            for stage in _round_to_stages(round_.name):
                es = EntityStage(entity_type=etype, entity_id=eid, stage=stage)
                session.add(es)
                counts["entity_stages"] += 1

        for notable in firm.notable_investments:
            en = EntityNotable(entity_type=etype, entity_id=eid, notable_investment_id=notable.id)
            session.add(en)
            counts["entity_notables"] += 1

    session.flush()

    # ------------------------------------------------------------------
    # Step 6: EntityGeography (Investor.location + InvestmentFirm.location)
    # ------------------------------------------------------------------
    for inv in investors:
        if not inv.location or not inv.location.strip():
            continue
        person = investor_person[inv.id]
        geo = _get_or_create_geography(session, inv.location, geo_cache)
        eg = EntityGeography(
            entity_type=EntityType.PERSON,
            entity_id=person.id,
            geography_id=geo.id,
        )
        session.add(eg)
        counts["entity_geographies"] += 1

    for firm in firms:
        if not firm.location or not firm.location.strip():
            continue
        org = firm_org[firm.id]
        geo = _get_or_create_geography(session, firm.location, geo_cache)
        eg = EntityGeography(
            entity_type=EntityType.ORG,
            entity_id=org.id,
            geography_id=geo.id,
        )
        session.add(eg)
        counts["entity_geographies"] += 1

    session.flush()

    # ------------------------------------------------------------------
    # Step 7: EntityBookmark
    # ------------------------------------------------------------------
    inv_bookmarks = session.scalars(db.select(InvestorBookmark)).all()
    for bm in inv_bookmarks:
        person = investor_person.get(bm.investor_id)
        if person is None:
            continue
        eb = EntityBookmark(
            user_id=bm.user_id,
            entity_type=EntityType.PERSON,
            entity_id=person.id,
        )
        session.add(eb)
        counts["entity_bookmarks"] += 1

    firm_bookmarks = session.scalars(db.select(InvestmentFirmBookmark)).all()
    for bm in firm_bookmarks:
        org = firm_org.get(bm.investment_firm_id)
        if org is None:
            continue
        eb = EntityBookmark(
            user_id=bm.user_id,
            entity_type=EntityType.ORG,
            entity_id=org.id,
        )
        session.add(eb)
        counts["entity_bookmarks"] += 1

    session.commit()

    return counts
