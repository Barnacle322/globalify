"""Public SSR browse pages — /investors and /firms.

Both routes are fully public (no auth required). They call entity_search.get_search
and degrade gracefully to empty results if Typesense is unavailable.
"""

from __future__ import annotations

import logging

from flask import Blueprint, abort, redirect, render_template, request
from flask_login import current_user, login_required

from ..extensions import db
from ..models import entity_search
from ..models.entity import EntityBookmark, Organization, Person, load_profile_bundle
from ..utils.enums import EntityType
from ..utils.funcs import generate_pagination
from ..utils.seo.slugs import build_facet_canonical, classify_segment, order_segments

log = logging.getLogger(__name__)

public = Blueprint("public", __name__)

PER_PAGE = 18

# Minimum result count to allow indexing a facet page
MIN_FACET_RESULTS = 3


def _parse_filters() -> dict:
    """Parse shared filter/sort query params used by both browse routes."""
    stages = request.args.getlist("round") or None
    industries = request.args.getlist("industry") or None
    geo_slugs = request.args.getlist("country") or None
    investor_types = request.args.getlist("investor_type") or None

    return {
        "query": request.args.get("q", request.args.get("search", "")).strip() or "*",
        "stages": stages,
        "industries": industries,
        "geographies": geo_slugs,
        "investor_type": investor_types,
        "check_size_min": request.args.get("min_investment", type=int),
        "check_size_max": request.args.get("max_investment", type=int),
        "sort_by": request.args.get("sort_field"),
        "sort_desc": request.args.get("descending", False, type=bool),
    }


def _hits_to_entities(hits: list) -> list[dict]:
    """Extract display fields from Typesense hit documents."""
    return [
        {
            "id": hit.get("document", {}).get("db_id"),
            "name": hit.get("document", {}).get("name", ""),
            "slug": hit.get("document", {}).get("slug"),
            "headline": hit.get("document", {}).get("headline"),
            "org_name": hit.get("document", {}).get("org_name"),
            "about": hit.get("document", {}).get("about"),
            "industries": hit.get("document", {}).get("industries", []),
            "stages": hit.get("document", {}).get("stages", []),
            "geographies": hit.get("document", {}).get("geographies", []),
            "country_code": hit.get("document", {}).get("country_code"),
            "check_size_min": hit.get("document", {}).get("check_size_min"),
            "check_size_max": hit.get("document", {}).get("check_size_max"),
            "n_investments": hit.get("document", {}).get("n_investments"),
            "n_exits": hit.get("document", {}).get("n_exits"),
            "investor_type": hit.get("document", {}).get("investor_type"),
            "person_names": hit.get("document", {}).get("person_names", []),
        }
        for hit in hits
    ]


@public.get("/investors")
def investors():
    """Public SSR investor directory (EntityType.PERSON)."""
    page = request.args.get("page", 1, type=int)
    filters = _parse_filters()

    try:
        result = entity_search.get_search(
            query=filters["query"],
            entity_type=EntityType.PERSON,
            stages=filters["stages"],
            industries=filters["industries"],
            geographies=filters["geographies"],
            investor_type=filters["investor_type"],
            check_size_min=filters["check_size_min"],
            check_size_max=filters["check_size_max"],
            sort_by=filters["sort_by"],
            sort_desc=filters["sort_desc"],
            page=page,
            per_page=PER_PAGE,
        )
    except Exception:
        log.warning("Typesense unavailable — degrading /investors to empty results")
        result = {"found": 0, "page": page, "hits": []}

    found = result.get("found", 0)
    result_page = int(result.get("page", page))
    total_pages = max((found + PER_PAGE - 1) // PER_PAGE, 1)
    pagination = generate_pagination(result_page, total_pages)
    entities = _hits_to_entities(result.get("hits", []))

    if current_user.is_authenticated:
        all_bms = EntityBookmark.get_by_user_id(current_user.id)
        bookmark_ids = {bm.entity_id for bm in all_bms if bm.entity_type == EntityType.PERSON}
    else:
        bookmark_ids = set()

    template = "browse/_results.html" if request.headers.get("HX-Request") else "browse/list.html"
    return render_template(
        template,
        entities=entities,
        entity_type=EntityType.PERSON,
        heading="Investors",
        page_title="Investors",
        meta_description=(
            "Browse the global investor directory on Globalify. "
            "Discover angels, VCs, and partners actively investing worldwide."
        ),
        canonical_path="/investors",
        found=found,
        page=result_page,
        total_pages=total_pages,
        pagination=pagination,
        query=filters["query"] if filters["query"] != "*" else "",
        bookmark_ids=bookmark_ids,
    )


@public.get("/firms")
def firms():
    """Public SSR investment firm directory (EntityType.ORG)."""
    page = request.args.get("page", 1, type=int)
    filters = _parse_filters()

    try:
        result = entity_search.get_search(
            query=filters["query"],
            entity_type=EntityType.ORG,
            stages=filters["stages"],
            industries=filters["industries"],
            geographies=filters["geographies"],
            investor_type=filters["investor_type"],
            check_size_min=filters["check_size_min"],
            check_size_max=filters["check_size_max"],
            sort_by=filters["sort_by"],
            sort_desc=filters["sort_desc"],
            page=page,
            per_page=PER_PAGE,
        )
    except Exception:
        log.warning("Typesense unavailable — degrading /firms to empty results")
        result = {"found": 0, "page": page, "hits": []}

    found = result.get("found", 0)
    result_page = int(result.get("page", page))
    total_pages = max((found + PER_PAGE - 1) // PER_PAGE, 1)
    pagination = generate_pagination(result_page, total_pages)
    entities = _hits_to_entities(result.get("hits", []))

    if current_user.is_authenticated:
        all_bms = EntityBookmark.get_by_user_id(current_user.id)
        bookmark_ids = {bm.entity_id for bm in all_bms if bm.entity_type == EntityType.ORG}
    else:
        bookmark_ids = set()

    template = "browse/_results.html" if request.headers.get("HX-Request") else "browse/list.html"
    return render_template(
        template,
        entities=entities,
        entity_type=EntityType.ORG,
        heading="Investment Firms",
        page_title="Investment Firms",
        meta_description=(
            "Browse investment firms and venture capital funds on Globalify — the open global investor directory."
        ),
        canonical_path="/firms",
        found=found,
        page=result_page,
        total_pages=total_pages,
        pagination=pagination,
        query=filters["query"] if filters["query"] != "*" else "",
        bookmark_ids=bookmark_ids,
    )


# ---------------------------------------------------------------------------
# Facet heading helpers
# ---------------------------------------------------------------------------

_SEGMENT_LABELS: dict[str, str] = {
    # investor_type / org_type shared values
    "angel": "Angel",
    "vc": "VC",
    "corporate": "Corporate",
    "angel_syndicate": "Angel Syndicate",
    "angel_group": "Angel Group",
    "angel_network": "Angel Network",
    "scout": "Scout",
    "vc_firm": "VC Firm",
    "micro_vc": "Micro-VC",
    "growth_equity": "Growth Equity",
    "corporate_vc": "Corporate VC",
    "family_office": "Family Office",
    "accelerator": "Accelerator",
    "incubator": "Incubator",
    "venture_studio": "Venture Studio",
    "private_equity": "Private Equity",
    "pe_firm": "PE Firm",
    "venture_debt": "Venture Debt",
    "crowdfunding_platform": "Crowdfunding Platform",
    "grant_program": "Grant Program",
    "government_program": "Government Program",
    "government": "Government",
    "search_fund": "Search Fund",
    "fund_of_funds": "Fund of Funds",
    "lp_fund_of_funds": "LP / Fund of Funds",
    "limited_partner": "Limited Partner",
    "hedge_fund": "Hedge Fund",
    "syndicate": "Syndicate",
    # stage values
    "pre_seed": "Pre-Seed",
    "seed": "Seed",
    "series_a": "Series A",
    "series_b": "Series B",
    "series_c": "Series C",
    "series_d_plus": "Series D+",
    "growth": "Growth",
    "late_stage": "Late-Stage",
}


def _label(value: str) -> str:
    """Return a human-readable label for an enum value or slug."""
    return _SEGMENT_LABELS.get(value, value.replace("_", " ").replace("-", " ").title())


def _build_facet_heading(classified: list[tuple[str, str, str]], entity_kind) -> tuple[str, str]:
    """Return (h1_heading, intro_sentence) for a facet page.

    Examples:
        [("stages", "seed", "stage")]               → "Seed-stage Investors"
        [("industries", "fintech", "sector")]        → "Fintech Investors"
        [("stages", "seed", "stage"), ("industries", "fintech", "sector")]
                                                     → "Seed-stage Fintech Investors"
        [("geographies", "london", "geo")]           → "Investors in London"
    """
    from ..utils.enums import EntityType

    entity_word = "Investors" if entity_kind == EntityType.PERSON else "Investment Firms"

    # Map segments to display parts
    type_label = None
    stage_label = None
    sector_label = None
    geo_label = None

    for _facet_field, value, seg_type in classified:
        if seg_type == "type":
            type_label = _label(value)
        elif seg_type == "stage":
            stage_label = _label(value)
        elif seg_type == "sector":
            sector_label = _label(value)
        elif seg_type == "geo":
            geo_label = _label(value)

    # Build heading
    parts = []
    if type_label:
        parts.append(type_label)
    if stage_label:
        parts.append(f"{stage_label}-stage")
    if sector_label:
        parts.append(sector_label)
    parts.append(entity_word)

    heading = " ".join(parts)
    if geo_label:
        heading += f" in {geo_label}"

    # Build short intro sentence
    intro = f"Browse {heading.lower()} on Globalify — the open global investor directory."

    return heading, intro


# ---------------------------------------------------------------------------
# Facet filter builder
# ---------------------------------------------------------------------------


def _classified_to_filters(classified: list[tuple[str, str, str]]) -> dict:
    """Map classified (facet_field, value, segment_type) triples to get_search kwargs."""
    filters: dict[str, list[str]] = {}
    for facet_field, value, _seg_type in classified:
        if facet_field not in filters:
            filters[facet_field] = []
        filters[facet_field].append(value)

    # Translate facet_field keys to get_search param names
    result: dict = {}
    if "stages" in filters:
        result["stages"] = filters["stages"]
    if "industries" in filters:
        result["industries"] = filters["industries"]
    if "geographies" in filters:
        result["geographies"] = filters["geographies"]
    if "investor_type" in filters:
        result["investor_type"] = filters["investor_type"]
    if "org_type" in filters:
        result["org_type"] = filters["org_type"]
    return result


# ---------------------------------------------------------------------------
# Facet page renderer (shared between investors + firms resolver)
# ---------------------------------------------------------------------------


def _render_facet_page(
    classified: list[tuple[str, str, str]],
    entity_kind,
    page: int,
) -> str:
    """Build and render a facet browse page."""
    heading, intro = _build_facet_heading(classified, entity_kind)
    canonical_url = build_facet_canonical(entity_kind, classified)
    canonical_path = "/" + canonical_url.split("globalify.xyz/", 1)[-1]

    filters = _classified_to_filters(classified)

    try:
        result = entity_search.get_search(
            query="*",
            entity_type=entity_kind.value if hasattr(entity_kind, "value") else str(entity_kind),
            page=page,
            per_page=PER_PAGE,
            **filters,
        )
    except Exception:
        log.warning("Typesense unavailable — degrading facet page to empty results")
        result = {"found": 0, "page": page, "hits": []}

    found = result.get("found", 0)
    result_page = int(result.get("page", page))
    total_pages = max((found + PER_PAGE - 1) // PER_PAGE, 1)
    pagination = generate_pagination(result_page, total_pages)
    entities = _hits_to_entities(result.get("hits", []))

    if current_user.is_authenticated:
        all_bms = EntityBookmark.get_by_user_id(current_user.id)
        bookmark_ids = {bm.entity_id for bm in all_bms if bm.entity_type == entity_kind}
    else:
        bookmark_ids = set()

    # Robots policy
    n_facets = len(classified)
    if n_facets >= 3 or result_page > 1 or found < MIN_FACET_RESULTS:
        robots = "noindex,follow"
    else:
        robots = "index,follow"

    # BreadcrumbList JSON-LD context
    base_url = "https://globalify.xyz"
    base_name = "Investors" if entity_kind == EntityType.PERSON else "Investment Firms"
    base_path = "/investors" if entity_kind == EntityType.PERSON else "/firms"
    breadcrumbs = [
        {"name": "Home", "url": f"{base_url}/"},
        {"name": base_name, "url": f"{base_url}{base_path}"},
        {"name": heading, "url": canonical_url},
    ]

    page_title = heading
    meta_description = intro

    template = "browse/_results.html" if request.headers.get("HX-Request") else "browse/list.html"
    return render_template(
        template,
        entities=entities,
        entity_type=entity_kind,
        heading=heading,
        facet_intro=intro,
        page_title=page_title,
        meta_description=meta_description,
        canonical_path=canonical_path,
        canonical_full=canonical_url,
        robots=robots,
        found=found,
        page=result_page,
        total_pages=total_pages,
        pagination=pagination,
        query="",
        breadcrumbs=breadcrumbs,
        bookmark_ids=bookmark_ids,
    )


# ---------------------------------------------------------------------------
# Profile pages (unified <path:path> resolvers)
# ---------------------------------------------------------------------------


@public.get("/investors/<path:path>", endpoint="investor_profile")
def investor_resolver(path: str):
    """Unified resolver: /investors/<path> → facet page OR person profile OR 404."""
    segments = [s for s in path.split("/") if s]

    if len(segments) == 1:
        seg = segments[0]
        classification = classify_segment(seg, EntityType.PERSON)
        if classification is not None:
            # Single-facet page
            page = request.args.get("page", 1, type=int)
            return _render_facet_page([classification], EntityType.PERSON, page)

        # Try profile
        person = Person.get_by_slug(seg)
        if person is not None:
            return _render_person_profile(person)

        abort(404)

    # Multiple segments → must all be valid facets
    classified = []
    for seg in segments:
        c = classify_segment(seg, EntityType.PERSON)
        if c is None:
            abort(404)
        classified.append(c)

    # Canonical redirect if out of order or has duplicate facet types
    ordered, warnings = order_segments(classified)
    ordered_slugs = [s.replace("_", "-") for _, s, _ in ordered]
    input_slugs = segments

    if warnings or ordered_slugs != input_slugs:
        canonical_url = build_facet_canonical(EntityType.PERSON, classified)
        return redirect(canonical_url, 301)

    page = request.args.get("page", 1, type=int)
    return _render_facet_page(ordered, EntityType.PERSON, page)


@public.get("/firms/<path:path>", endpoint="firm_profile")
def firm_resolver(path: str):
    """Unified resolver: /firms/<path> → facet page OR org profile OR 404."""
    segments = [s for s in path.split("/") if s]

    if len(segments) == 1:
        seg = segments[0]
        classification = classify_segment(seg, EntityType.ORG)
        if classification is not None:
            # Single-facet page
            page = request.args.get("page", 1, type=int)
            return _render_facet_page([classification], EntityType.ORG, page)

        # Try profile
        org = Organization.get_by_slug(seg)
        if org is not None:
            return _render_org_profile(org)

        abort(404)

    # Multiple segments → must all be valid facets
    classified = []
    for seg in segments:
        c = classify_segment(seg, EntityType.ORG)
        if c is None:
            abort(404)
        classified.append(c)

    # Canonical redirect if out of order or has duplicate facet types
    ordered, warnings = order_segments(classified)
    ordered_slugs = [s.replace("_", "-") for _, s, _ in ordered]
    input_slugs = segments

    if warnings or ordered_slugs != input_slugs:
        canonical_url = build_facet_canonical(EntityType.ORG, classified)
        return redirect(canonical_url, 301)

    page = request.args.get("page", 1, type=int)
    return _render_facet_page(ordered, EntityType.ORG, page)


# ---------------------------------------------------------------------------
# Profile render helpers
# ---------------------------------------------------------------------------


def _render_person_profile(person: Person):
    """Render person profile page (identical to 2b implementation)."""
    from types import SimpleNamespace

    bundle = load_profile_bundle(EntityType.PERSON, person.id)
    profile = bundle["profile"]
    affiliations = bundle["affiliations"]

    full_name = f"{person.first_name} {person.last_name or ''}".strip()

    primary_aff = None
    if affiliations:
        current_affs = [a for a in affiliations if a.is_current]
        primary_raw = current_affs[0] if current_affs else affiliations[0]
        primary_aff = SimpleNamespace(
            title=primary_raw.title,
            org_name=primary_raw.organization.name if primary_raw.organization else "",
            org_slug=primary_raw.organization.slug if primary_raw.organization else "",
        )

    person_proxy = SimpleNamespace(
        slug=person.slug,
        full_name=full_name,
        headline=person.headline,
        website_url=person.website,
        linkedin_url=person.linkedin,
        twitter_url=person.twitter,
        location_name=bundle["geographies"][0].name if bundle["geographies"] else None,
    )

    meta_desc = person.headline or (
        person.about[:140] if person.about else f"{full_name} investor profile on Globalify"
    )

    viewer_is_pro = False

    is_bookmarked = False
    if current_user.is_authenticated:
        is_bookmarked = EntityBookmark.exists(current_user.id, EntityType.PERSON, person.id)

    return render_template(
        "profiles/person.html",
        person=person,
        person_proxy=person_proxy,
        full_name=full_name,
        bundle=bundle,
        profile=profile,
        affiliations=affiliations,
        primary_aff=primary_aff,
        viewer_is_pro=viewer_is_pro,
        is_bookmarked=is_bookmarked,
        page_title=full_name,
        meta_description=meta_desc,
        canonical=f"https://globalify.xyz/investors/{person.slug}",
        breadcrumbs=[
            {"name": "Home", "url": "https://globalify.xyz/"},
            {"name": "Investors", "url": "https://globalify.xyz/investors"},
            {"name": full_name, "url": f"https://globalify.xyz/investors/{person.slug}"},
        ],
        affiliation=primary_aff,
    )


def _render_org_profile(org: Organization):
    """Render org profile page (identical to 2b implementation)."""
    from types import SimpleNamespace

    bundle = load_profile_bundle(EntityType.ORG, org.id)
    profile = bundle["profile"]
    affiliations = bundle["affiliations"]

    org_proxy = SimpleNamespace(
        name=org.name,
        slug=org.slug,
        description=org.about or "",
        website_url=org.website,
        linkedin_url=org.linkedin,
        twitter_url=org.twitter,
        location_name=bundle["geographies"][0].name if bundle["geographies"] else None,
        founded_year=None,  # not in model yet
    )

    aff_proxies = []
    for aff in affiliations:
        p = aff.person
        if p:
            aff_proxies.append(
                SimpleNamespace(
                    full_name=f"{p.first_name} {p.last_name or ''}".strip(),
                    slug=p.slug,
                )
            )

    meta_desc = org.about[:140] if org.about else f"{org.name} investment firm profile on Globalify"

    viewer_is_pro = False

    is_bookmarked = False
    if current_user.is_authenticated:
        is_bookmarked = EntityBookmark.exists(current_user.id, EntityType.ORG, org.id)

    return render_template(
        "profiles/organization.html",
        org=org,
        org_proxy=org_proxy,
        bundle=bundle,
        profile=profile,
        affiliations=affiliations,
        aff_proxies=aff_proxies,
        viewer_is_pro=viewer_is_pro,
        is_bookmarked=is_bookmarked,
        page_title=org.name,
        meta_description=meta_desc,
        canonical=f"https://globalify.xyz/firms/{org.slug}",
        breadcrumbs=[
            {"name": "Home", "url": "https://globalify.xyz/"},
            {"name": "Investment Firms", "url": "https://globalify.xyz/firms"},
            {"name": org.name, "url": f"https://globalify.xyz/firms/{org.slug}"},
        ],
    )


# ---------------------------------------------------------------------------
# Legacy 301 redirects — preserve query string
# ---------------------------------------------------------------------------


# NOTE: legacy /investor/<slug> and /investment-firm/<slug> 301 redirects are
# handled by the existing main.investor_slug and main.investment_firm_slug routes
# in routes/main.py (which now issue 301 → /investors/<slug> and /firms/<slug>).
# Adding duplicate rules here would cause a Flask AssertionError at startup.
#
# NOTE: /search and /search/investment-firms legacy redirects are handled inside
# the search blueprint (search.investor_search and search.search_investment_firms)
# which remain the canonical handlers for those paths; adding duplicate rules here
# would cause a Flask AssertionError at startup.


# ---------------------------------------------------------------------------
# Bookmark toggle
# ---------------------------------------------------------------------------


@public.post("/bookmarks/<entity_type_str>/<int:entity_id>")
@login_required
def toggle_bookmark(entity_type_str: str, entity_id: int):
    """Toggle EntityBookmark for the current user.

    URL param entity_type_str must be "person" or "org".
    If HX-Request: returns rendered _bookmark_button.html partial.
    Otherwise: redirects back to referrer.
    """
    if entity_type_str not in ("person", "org"):
        abort(404)

    entity_type = EntityType.PERSON if entity_type_str == "person" else EntityType.ORG

    # Verify entity exists
    if entity_type == EntityType.PERSON:
        entity = Person.get_by_id(entity_id)
    else:
        entity = Organization.get_by_id(entity_id)

    if not entity:
        abort(404)

    bookmarked: bool
    if EntityBookmark.exists(current_user.id, entity_type, entity_id):
        existing = db.session.scalar(
            db.select(EntityBookmark).where(
                EntityBookmark.user_id == current_user.id,
                EntityBookmark.entity_type == entity_type,
                EntityBookmark.entity_id == entity_id,
            )
        )
        db.session.delete(existing)
        db.session.commit()
        bookmarked = False
    else:
        new_bookmark = EntityBookmark(
            user_id=current_user.id,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        db.session.add(new_bookmark)
        db.session.commit()
        bookmarked = True

    if request.headers.get("HX-Request"):
        return render_template(
            "partials/_bookmark_button.html",
            entity_type_str=entity_type_str,
            entity_id=entity_id,
            bookmarked=bookmarked,
        )

    return redirect(request.referrer or "/")
