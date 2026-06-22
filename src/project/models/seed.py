"""seed_demo_entities — Phase 2d Task 3.

Creates ~25 diverse demo entities directly in the new entity model layer
(Person + Organization + Affiliation + InvestorProfile + EntityStage +
EntityIndustry + EntityGeography).  No dependency on the legacy Investor /
InvestmentFirm models.

Call this once after db.create_all() to populate a fresh development DB with
enough variety that all facet pages (/investors/seed, /investors/fintech,
/firms/vc-firm, /investors/london …) return results.
"""

from __future__ import annotations

from ..utils.enums import (
    AffiliationRole,
    EntityType,
    InvestmentStage,
    InvestorType,
    LeadPreference,
    OrgType,
)
from .entity import (
    Affiliation,
    EntityGeography,
    EntityIndustry,
    EntityStage,
    Geography,
    InvestorProfile,
    Organization,
    Person,
)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_industry_by_slug(slug: str):
    """Return an Industry row by slug (auto-populated by after_create event).

    Industry.populate() fires on after_create and fills the table from
    ``utils.info_lists.aggregate``, so all standard slugs are guaranteed to
    exist after ``db.create_all()``.  We look up by slug — which is the
    stable canonical handle — rather than by the exact display name.

    Falls back to creating a new row if somehow absent (e.g., custom test DB).
    """
    from .helpers import Industry

    ind = Industry.get_by_slug(slug)
    if ind is None:
        # Shouldn't happen after db.create_all, but be defensive.

        ind = Industry(name=slug.replace("-", " ").title(), category="Other", slug=slug)
        from ..extensions import db

        db.session.add(ind)
        db.session.flush()
    return ind


def _get_or_create_geography(
    session, slug: str, name: str, geo_type: str, country_code: str | None = None
) -> Geography:
    """Return a Geography row, creating it if absent."""
    from ..extensions import db

    geo = session.scalar(db.select(Geography).where(Geography.slug == slug))
    if geo is None:
        geo = Geography(slug=slug, name=name, type=geo_type, country_code=country_code)
        session.add(geo)
        session.flush()
    return geo


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def seed_demo_entities(session) -> dict[str, int]:
    """Seed ~25 demo entities into the new entity model.

    Parameters
    ----------
    session:
        An active SQLAlchemy session (typically ``db.session``).

    Returns
    -------
    dict
        Counts of created rows per model type.
    """

    counts: dict[str, int] = {
        "persons": 0,
        "organizations": 0,
        "affiliations": 0,
        "investor_profiles": 0,
        "entity_stages": 0,
        "entity_industries": 0,
        "entity_geographies": 0,
    }

    # ------------------------------------------------------------------
    # Industries — look up by slug from the auto-populated Industry table
    # (Industry.populate() fires via SQLAlchemy after_create event)
    # ------------------------------------------------------------------
    fintech = _get_industry_by_slug("fintech")  # "FinTech"
    ai = _get_industry_by_slug("ai")  # "AI"
    climate = _get_industry_by_slug("climate")  # "Climate"
    healthcare = _get_industry_by_slug("healthcare-medtech")  # "Healthcare/MedTech"
    saas = _get_industry_by_slug("saas")  # "SaaS"
    consumer = _get_industry_by_slug("consumer")  # "Consumer"
    deeptech = _get_industry_by_slug("deeptech")  # "DeepTech"
    crypto = _get_industry_by_slug("cryptocurrency-blockchain")  # "Cryptocurrency/Blockchain"

    session.flush()

    # ------------------------------------------------------------------
    # Geographies
    # ------------------------------------------------------------------
    sf = _get_or_create_geography(session, "san-francisco-california", "San Francisco, CA", "city", "US")
    ny = _get_or_create_geography(session, "new-york-new-york", "New York, NY", "city", "US")
    london = _get_or_create_geography(session, "london", "London", "city", "GB")
    berlin = _get_or_create_geography(session, "berlin", "Berlin", "city", "DE")
    boston = _get_or_create_geography(session, "boston-massachusetts", "Boston, MA", "city", "US")
    singapore = _get_or_create_geography(session, "singapore", "Singapore", "city", "SG")
    austin = _get_or_create_geography(session, "austin-texas", "Austin, TX", "city", "US")

    session.flush()

    # ------------------------------------------------------------------
    # Organizations
    # ------------------------------------------------------------------

    def _add_org(
        name,
        slug,
        org_type,
        about=None,
        website=None,
        linkedin=None,
        twitter=None,
        n_employees=None,
    ):
        org = Organization(
            name=name,
            slug=slug,
            org_type=org_type,
            about=about,
            website=website,
            linkedin=linkedin,
            twitter=twitter,
            n_employees=n_employees,
            is_public=True,
            is_approved=True,
        )
        session.add(org)
        return org

    sequoia = _add_org(
        "Sequoia Capital",
        "sequoia-capital",
        OrgType.VC_FIRM,
        about="Iconic multi-stage VC backing legendary founders.",
        website="https://sequoiacap.com",
        linkedin="sequoia-capital",
        twitter="sequoia",
        n_employees=120,
    )

    a16z = _add_org(
        "Andreessen Horowitz",
        "andreessen-horowitz",
        OrgType.VC_FIRM,
        about="Top-tier VC firm investing in software and the next frontier.",
        website="https://a16z.com",
        linkedin="andreessen-horowitz",
        twitter="a16z",
        n_employees=200,
    )

    yc = _add_org(
        "Y Combinator",
        "y-combinator",
        OrgType.ACCELERATOR,
        about="The world's most successful startup accelerator.",
        website="https://ycombinator.com",
        linkedin="y-combinator",
        twitter="ycombinator",
        n_employees=50,
    )

    first_round = _add_org(
        "First Round Capital",
        "first-round-capital",
        OrgType.VC_FIRM,
        about="Seed-stage VC focused on exceptional founders.",
        website="https://firstround.com",
        linkedin="first-round-capital",
        twitter="firstround",
        n_employees=30,
    )

    techstars = _add_org(
        "Techstars",
        "techstars",
        OrgType.ACCELERATOR,
        about="A global accelerator and startup community.",
        website="https://techstars.com",
        linkedin="techstars",
        twitter="techstars",
        n_employees=300,
    )

    tiger_global = _add_org(
        "Tiger Global Management",
        "tiger-global-management",
        OrgType.PE_FIRM,
        about="Crossover fund investing in public and private technology companies.",
        website="https://tigerglobal.com",
        linkedin="tiger-global-management",
        n_employees=80,
    )

    general_catalyst = _add_org(
        "General Catalyst",
        "general-catalyst",
        OrgType.VC_FIRM,
        about="Multi-stage investor partnering with founders from day one.",
        website="https://generalcatalyst.com",
        linkedin="general-catalyst",
        twitter="gcvp",
        n_employees=60,
    )

    mv_seed = _add_org(
        "Hustle Fund",
        "hustle-fund",
        OrgType.MICRO_VC,
        about="Pre-seed micro-VC backing hustlers solving big problems.",
        website="https://hustlefund.vc",
        linkedin="hustle-fund",
        twitter="HustleFundVC",
        n_employees=10,
    )

    gv = _add_org(
        "Google Ventures",
        "google-ventures",
        OrgType.CORPORATE_VC,
        about="Google's independent VC arm. Early-stage across all industries.",
        website="https://gv.com",
        linkedin="google-ventures",
        twitter="gv",
        n_employees=70,
    )

    family_capital = _add_org(
        "Pritzker Group Venture Capital",
        "pritzker-group-vc",
        OrgType.FAMILY_OFFICE,
        about="Family office backed VC investing in early growth companies.",
        website="https://pritzkergroup.com",
        linkedin="pritzker-group",
        n_employees=20,
    )

    atomic = _add_org(
        "Atomic",
        "atomic-vc",
        OrgType.VENTURE_STUDIO,
        about="Venture studio that co-founds companies with world-class founders.",
        website="https://atomic.vc",
        linkedin="atomic-vc",
        twitter="atomicvc",
        n_employees=50,
    )

    session.flush()
    counts["organizations"] = 11

    # ------------------------------------------------------------------
    # InvestorProfiles for Organizations
    # ------------------------------------------------------------------

    def _add_org_profile(
        org, investor_type, min_inv, max_inv, lead_pref, cold_inbound, n_inv, n_exits, thesis, stages, industries, geos
    ):
        ip = InvestorProfile(
            entity_type=EntityType.ORG,
            entity_id=org.id,
            investor_type=investor_type,
            min_investment=min_inv,
            max_investment=max_inv,
            lead_pref=lead_pref,
            accepts_cold_inbound=cold_inbound,
            n_investments=n_inv,
            n_exits=n_exits,
            thesis=thesis,
            is_active=True,
        )
        session.add(ip)
        counts["investor_profiles"] += 1
        for stage in stages:
            session.add(EntityStage(entity_type=EntityType.ORG, entity_id=org.id, stage=stage))
            counts["entity_stages"] += 1
        for ind in industries:
            session.add(EntityIndustry(entity_type=EntityType.ORG, entity_id=org.id, industry_id=ind.id))
            counts["entity_industries"] += 1
        for geo in geos:
            session.add(EntityGeography(entity_type=EntityType.ORG, entity_id=org.id, geography_id=geo.id))
            counts["entity_geographies"] += 1

    _add_org_profile(
        sequoia,
        InvestorType.VC_FIRM,
        1_000_000,
        50_000_000,
        LeadPreference.LEAD,
        False,
        2500,
        400,
        "We partner with legendary founders from the beginning.",
        [InvestmentStage.SEED, InvestmentStage.SERIES_A, InvestmentStage.SERIES_B, InvestmentStage.GROWTH],
        [saas, ai, fintech],
        [sf, ny],
    )
    _add_org_profile(
        a16z,
        InvestorType.VC_FIRM,
        500_000,
        100_000_000,
        LeadPreference.LEAD,
        False,
        1200,
        180,
        "Software is eating the world. We back the builders.",
        [InvestmentStage.SEED, InvestmentStage.SERIES_A, InvestmentStage.SERIES_B, InvestmentStage.SERIES_C],
        [saas, ai, crypto, fintech],
        [sf, ny],
    )
    _add_org_profile(
        yc,
        InvestorType.ACCELERATOR,
        125_000,
        500_000,
        LeadPreference.LEAD,
        True,
        4000,
        800,
        "Make something people want.",
        [InvestmentStage.PRE_SEED, InvestmentStage.SEED],
        [saas, fintech, ai, consumer, healthcare],
        [sf],
    )
    _add_org_profile(
        first_round,
        InvestorType.VC_FIRM,
        500_000,
        5_000_000,
        LeadPreference.LEAD,
        True,
        350,
        60,
        "Seed-stage conviction bets on exceptional teams.",
        [InvestmentStage.PRE_SEED, InvestmentStage.SEED],
        [saas, fintech, healthcare],
        [sf, ny],
    )
    _add_org_profile(
        techstars,
        InvestorType.ACCELERATOR,
        100_000,
        300_000,
        LeadPreference.LEAD,
        True,
        3500,
        400,
        "The worldwide network for entrepreneurs.",
        [InvestmentStage.PRE_SEED, InvestmentStage.SEED],
        [saas, consumer, fintech, climate],
        [ny, london, berlin],
    )
    _add_org_profile(
        tiger_global,
        InvestorType.PRIVATE_EQUITY,
        50_000_000,
        500_000_000,
        LeadPreference.BOTH,
        False,
        400,
        80,
        "Growth and late-stage technology investments globally.",
        [InvestmentStage.SERIES_C, InvestmentStage.GROWTH, InvestmentStage.LATE_STAGE],
        [saas, fintech, consumer],
        [ny, singapore],
    )
    _add_org_profile(
        general_catalyst,
        InvestorType.VC_FIRM,
        1_000_000,
        30_000_000,
        LeadPreference.LEAD,
        False,
        600,
        100,
        "Partnering from the earliest stage through IPO.",
        [InvestmentStage.SEED, InvestmentStage.SERIES_A, InvestmentStage.SERIES_B],
        [healthcare, ai, saas, climate],
        [boston, ny, sf],
    )
    _add_org_profile(
        mv_seed,
        InvestorType.MICRO_VC,
        25_000,
        150_000,
        LeadPreference.LEAD,
        True,
        700,
        50,
        "Invest in founders who hustle hard and move fast.",
        [InvestmentStage.PRE_SEED, InvestmentStage.SEED],
        [saas, fintech, consumer],
        [sf, austin],
    )
    _add_org_profile(
        gv,
        InvestorType.CORPORATE_VC,
        500_000,
        20_000_000,
        LeadPreference.BOTH,
        True,
        800,
        120,
        "Invest across life sciences, healthcare, AI/ML and enterprise.",
        [InvestmentStage.SEED, InvestmentStage.SERIES_A, InvestmentStage.SERIES_B],
        [ai, healthcare, deeptech, saas],
        [sf, ny, london],
    )
    _add_org_profile(
        family_capital,
        InvestorType.FAMILY_OFFICE,
        1_000_000,
        10_000_000,
        LeadPreference.FOLLOW,
        False,
        150,
        25,
        "Patient capital for entrepreneurs building durable businesses.",
        [InvestmentStage.SERIES_A, InvestmentStage.SERIES_B],
        [consumer, fintech, healthcare],
        [ny, boston],
    )
    _add_org_profile(
        atomic,
        InvestorType.VENTURE_STUDIO,
        500_000,
        5_000_000,
        LeadPreference.LEAD,
        True,
        50,
        10,
        "We co-found companies: idea through product-market fit.",
        [InvestmentStage.IDEA, InvestmentStage.PRE_SEED, InvestmentStage.SEED],
        [saas, ai, fintech, consumer],
        [sf],
    )

    session.flush()

    # ------------------------------------------------------------------
    # Persons (angels + partners)
    # ------------------------------------------------------------------

    def _add_person(first_name, last_name, slug, headline, about=None, website=None, linkedin=None, twitter=None):
        p = Person(
            first_name=first_name,
            last_name=last_name,
            slug=slug,
            headline=headline,
            about=about,
            website=website,
            linkedin=linkedin,
            twitter=twitter,
            is_public=True,
            is_approved=True,
        )
        session.add(p)
        return p

    sarah = _add_person(
        "Sarah",
        "Chen",
        "sarah-chen",
        "Partner at Sequoia Capital",
        about="15 years investing in enterprise SaaS and fintech from seed to IPO.",
        linkedin="sarah-chen-vc",
        twitter="sarahchen_vc",
    )

    marcus = _add_person(
        "Marcus",
        "Johnson",
        "marcus-johnson",
        "Angel Investor & Serial Founder",
        about="Former CTO of 3 unicorns. Now backing the next generation of deep tech founders.",
        website="https://marcusjohnson.io",
        linkedin="marcus-johnson-angel",
        twitter="marcusjohnson",
    )

    priya = _add_person(
        "Priya",
        "Patel",
        "priya-patel",
        "Principal at Andreessen Horowitz",
        about="Investing in AI infrastructure and developer tools. Ex-Google Brain.",
        linkedin="priya-patel-a16z",
        twitter="priya_a16z",
    )

    oliver = _add_person(
        "Oliver",
        "Müller",
        "oliver-muller",
        "Managing Partner at Earlybird VC",
        about="Berlin-based investor in European B2B SaaS and climate tech.",
        website="https://earlybird.com",
        linkedin="oliver-muller-earlybird",
        twitter="olivermuller_vc",
    )

    jessica = _add_person(
        "Jessica",
        "Park",
        "jessica-park",
        "Partner at GV (Google Ventures)",
        about="Life sciences and healthcare AI. MD/MBA, formerly at Mayo Clinic.",
        linkedin="jessica-park-gv",
        twitter="jessicapark_gv",
    )

    david = _add_person(
        "David",
        "Osei",
        "david-osei",
        "Angel Investor | Climate Tech Scout",
        about="Backing early-stage climate startups across Africa and Europe.",
        linkedin="david-osei-climate",
        twitter="davidosei_climate",
    )

    rachel = _add_person(
        "Rachel",
        "Novak",
        "rachel-novak",
        "General Partner at Hustle Fund",
        about="Pre-seed bets on fast-moving founders in fintech and consumer.",
        linkedin="rachel-novak-hustlefund",
        twitter="rachelnovak_vc",
    )

    tom = _add_person(
        "Tom",
        "Hayashi",
        "tom-hayashi",
        "Founding Partner, Atomic",
        about="Studio founder and operator. Built companies in payments, health, and logistics.",
        linkedin="tom-hayashi-atomic",
        twitter="tomhayashi",
    )

    aisha = _add_person(
        "Aisha",
        "Rahman",
        "aisha-rahman",
        "Angel Investor & LP",
        about="Southeast Asia-focused angel in B2B SaaS and healthcare. Based in Singapore.",
        linkedin="aisha-rahman-angel",
        twitter="aisharahman_sg",
    )

    carlos = _add_person(
        "Carlos",
        "Vega",
        "carlos-vega",
        "Partner at General Catalyst",
        about="Investing in AI-first companies from pre-seed to growth.",
        linkedin="carlos-vega-gc",
        twitter="carlosvega_gc",
    )

    nina = _add_person(
        "Nina",
        "Holst",
        "nina-holst",
        "Scout at Y Combinator",
        about="YC scout focused on European founders. Ex-founder of two YC companies.",
        linkedin="nina-holst-yc",
        twitter="ninaholst_yc",
    )

    james = _add_person(
        "James",
        "Okafor",
        "james-okafor",
        "Partner at First Round Capital",
        about="Consumer and marketplace specialist. Led investments in 4 unicorns.",
        linkedin="james-okafor-frc",
        twitter="jamesokafor_frc",
    )

    session.flush()
    counts["persons"] = 12

    # ------------------------------------------------------------------
    # InvestorProfiles for Persons
    # ------------------------------------------------------------------

    def _add_person_profile(
        person,
        investor_type,
        min_inv,
        max_inv,
        lead_pref,
        cold_inbound,
        n_inv,
        n_exits,
        thesis,
        stages,
        industries,
        geos,
    ):
        ip = InvestorProfile(
            entity_type=EntityType.PERSON,
            entity_id=person.id,
            investor_type=investor_type,
            min_investment=min_inv,
            max_investment=max_inv,
            lead_pref=lead_pref,
            accepts_cold_inbound=cold_inbound,
            n_investments=n_inv,
            n_exits=n_exits,
            thesis=thesis,
            is_active=True,
        )
        session.add(ip)
        counts["investor_profiles"] += 1
        for stage in stages:
            session.add(EntityStage(entity_type=EntityType.PERSON, entity_id=person.id, stage=stage))
            counts["entity_stages"] += 1
        for ind in industries:
            session.add(EntityIndustry(entity_type=EntityType.PERSON, entity_id=person.id, industry_id=ind.id))
            counts["entity_industries"] += 1
        for geo in geos:
            session.add(EntityGeography(entity_type=EntityType.PERSON, entity_id=person.id, geography_id=geo.id))
            counts["entity_geographies"] += 1

    _add_person_profile(
        sarah,
        InvestorType.VC_FIRM,
        500_000,
        10_000_000,
        LeadPreference.LEAD,
        False,
        80,
        15,
        "Conviction bets on enterprise SaaS & fintech founders.",
        [InvestmentStage.SEED, InvestmentStage.SERIES_A, InvestmentStage.SERIES_B],
        [saas, fintech],
        [sf, ny],
    )
    _add_person_profile(
        marcus,
        InvestorType.ANGEL,
        25_000,
        250_000,
        LeadPreference.BOTH,
        True,
        45,
        8,
        "Deep tech and developer infrastructure. Write first checks.",
        [InvestmentStage.PRE_SEED, InvestmentStage.SEED],
        [deeptech, ai, saas],
        [sf],
    )
    _add_person_profile(
        priya,
        InvestorType.VC_FIRM,
        250_000,
        5_000_000,
        LeadPreference.FOLLOW,
        False,
        30,
        4,
        "AI infrastructure, MLOps, and the developer ecosystem.",
        [InvestmentStage.SEED, InvestmentStage.SERIES_A],
        [ai, saas, deeptech],
        [sf, ny],
    )
    _add_person_profile(
        oliver,
        InvestorType.VC_FIRM,
        500_000,
        8_000_000,
        LeadPreference.LEAD,
        True,
        60,
        12,
        "European-first B2B SaaS and climate tech from seed to Series B.",
        [InvestmentStage.SEED, InvestmentStage.SERIES_A, InvestmentStage.SERIES_B],
        [saas, climate, deeptech],
        [berlin, london],
    )
    _add_person_profile(
        jessica,
        InvestorType.CORPORATE_VC,
        500_000,
        15_000_000,
        LeadPreference.BOTH,
        True,
        55,
        10,
        "Healthcare AI and digital health — from bench to bedside.",
        [InvestmentStage.SEED, InvestmentStage.SERIES_A, InvestmentStage.SERIES_B],
        [healthcare, ai, deeptech],
        [sf, boston],
    )
    _add_person_profile(
        david,
        InvestorType.ANGEL,
        10_000,
        100_000,
        LeadPreference.FOLLOW,
        True,
        20,
        2,
        "Climate solutions with emerging market applications.",
        [InvestmentStage.PRE_SEED, InvestmentStage.SEED],
        [climate, deeptech],
        [london, berlin],
    )
    _add_person_profile(
        rachel,
        InvestorType.MICRO_VC,
        25_000,
        150_000,
        LeadPreference.LEAD,
        True,
        120,
        18,
        "First checks for scrappy founders with outsized hustle.",
        [InvestmentStage.PRE_SEED, InvestmentStage.SEED],
        [fintech, consumer, saas],
        [sf, ny, austin],
    )
    _add_person_profile(
        tom,
        InvestorType.VENTURE_STUDIO,
        100_000,
        2_000_000,
        LeadPreference.LEAD,
        True,
        18,
        4,
        "Co-build companies from day zero in fintech, health, and logistics.",
        [InvestmentStage.IDEA, InvestmentStage.PRE_SEED, InvestmentStage.SEED],
        [fintech, healthcare, saas],
        [sf],
    )
    _add_person_profile(
        aisha,
        InvestorType.ANGEL,
        5_000,
        50_000,
        LeadPreference.FOLLOW,
        True,
        25,
        3,
        "Southeast Asia B2B SaaS and healthcare angels.",
        [InvestmentStage.PRE_SEED, InvestmentStage.SEED],
        [saas, healthcare, fintech],
        [singapore],
    )
    _add_person_profile(
        carlos,
        InvestorType.VC_FIRM,
        1_000_000,
        20_000_000,
        LeadPreference.LEAD,
        False,
        40,
        6,
        "AI-first companies redefining legacy industries.",
        [InvestmentStage.SEED, InvestmentStage.SERIES_A, InvestmentStage.SERIES_B],
        [ai, saas, healthcare],
        [boston, ny, sf],
    )
    _add_person_profile(
        nina,
        InvestorType.SCOUT,
        50_000,
        200_000,
        LeadPreference.FOLLOW,
        True,
        15,
        1,
        "European founders building global companies.",
        [InvestmentStage.PRE_SEED, InvestmentStage.SEED],
        [saas, fintech, consumer],
        [london, berlin],
    )
    _add_person_profile(
        james,
        InvestorType.VC_FIRM,
        250_000,
        5_000_000,
        LeadPreference.LEAD,
        True,
        65,
        14,
        "Consumer and marketplace magic. Seed through Series A.",
        [InvestmentStage.SEED, InvestmentStage.SERIES_A],
        [consumer, fintech, saas],
        [ny, sf],
    )

    session.flush()

    # ------------------------------------------------------------------
    # Affiliations (persons → orgs)
    # ------------------------------------------------------------------

    def _aff(person, org, role, title=None):
        a = Affiliation(
            person_id=person.id,
            organization_id=org.id,
            role=role,
            title=title,
            is_current=True,
        )
        session.add(a)
        counts["affiliations"] += 1

    _aff(sarah, sequoia, AffiliationRole.PARTNER, "Partner")
    _aff(priya, a16z, AffiliationRole.PRINCIPAL, "Principal")
    _aff(jessica, gv, AffiliationRole.PARTNER, "Partner")
    _aff(rachel, mv_seed, AffiliationRole.GP, "General Partner")
    _aff(tom, atomic, AffiliationRole.FOUNDER, "Founding Partner")
    _aff(nina, yc, AffiliationRole.SCOUT, "Scout")
    _aff(james, first_round, AffiliationRole.PARTNER, "Partner")
    _aff(carlos, general_catalyst, AffiliationRole.PARTNER, "Partner")
    _aff(oliver, techstars, AffiliationRole.ADVISOR, "Mentor / Advisor")

    session.flush()

    session.commit()

    return counts
