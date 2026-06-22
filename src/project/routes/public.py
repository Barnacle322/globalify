"""Public SSR browse pages — /investors and /firms.

Both routes are fully public (no auth required). They call entity_search.get_search
and degrade gracefully to empty results if Typesense is unavailable.
"""

from __future__ import annotations

import logging

from flask import Blueprint, render_template, request

from ..models import entity_search
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
