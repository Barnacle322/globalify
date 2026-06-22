"""Public SSR browse pages — /investors and /firms.

Both routes are fully public (no auth required). They call entity_search.get_search
and degrade gracefully to empty results if Typesense is unavailable.
"""

from __future__ import annotations

import logging

from flask import Blueprint, abort, render_template, request

from ..models import entity_search
from ..models.entity import Organization, Person, load_profile_bundle
from ..utils.enums import EntityType
from ..utils.funcs import generate_pagination

log = logging.getLogger(__name__)

public = Blueprint("public", __name__)

PER_PAGE = 18


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

    return render_template(
        "browse/list.html",
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

    return render_template(
        "browse/list.html",
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
    )


# ---------------------------------------------------------------------------
# Profile pages
# ---------------------------------------------------------------------------


@public.get("/investors/<slug>")
def investor_profile(slug: str):
    """SSR profile page for a single investor (Person entity)."""
    person = Person.get_by_slug(slug)
    if person is None:
        abort(404)

    bundle = load_profile_bundle(EntityType.PERSON, person.id)
    profile = bundle["profile"]
    affiliations = bundle["affiliations"]

    # Build a helper object that the JSON-LD partial expects
    # (person model uses first_name/last_name; partial expects .full_name etc.)
    full_name = f"{person.first_name} {person.last_name or ''}".strip()

    # Primary affiliation for JSON-LD worksFor
    # Use SimpleNamespace so closures over local vars work without class-body scoping issues.
    from types import SimpleNamespace

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

    # Pro-gating: contact never emitted for anonymous/non-Pro users.
    # Pro billing not yet built — treat all viewers as non-Pro.
    viewer_is_pro = False

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


@public.get("/firms/<slug>")
def firm_profile(slug: str):
    """SSR profile page for a single investment firm (Organization entity)."""
    org = Organization.get_by_slug(slug)
    if org is None:
        abort(404)

    bundle = load_profile_bundle(EntityType.ORG, org.id)
    profile = bundle["profile"]
    affiliations = bundle["affiliations"]

    from types import SimpleNamespace

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

    # Build affiliations list for JSON-LD member list
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

    return render_template(
        "profiles/organization.html",
        org=org,
        org_proxy=org_proxy,
        bundle=bundle,
        profile=profile,
        affiliations=affiliations,
        aff_proxies=aff_proxies,
        viewer_is_pro=viewer_is_pro,
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
