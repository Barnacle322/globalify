"""Data-driven XML sitemaps + robots.txt (Phase 2c Task 3).

Routes
------
GET /sitemap.xml          – <sitemapindex> listing all child sitemaps
GET /sitemap-investors-<n>.xml  – <urlset> for Person rows (50 k / chunk)
GET /sitemap-firms-<n>.xml      – <urlset> for Organization rows (50 k / chunk)
GET /sitemap-facets.xml         – <urlset> for canonical single-facet pages
GET /robots.txt           – plain-text robots file (replaces main.robots)
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

from flask import Blueprint, abort, make_response

from ..extensions import db
from ..models.entity import Geography, Organization, Person
from ..models.helpers import Industry
from ..utils.enums import InvestmentStage, InvestorType, OrgType
from ..utils.seo.slugs import enum_to_slug

sitemap_bp = Blueprint("sitemap", __name__)

BASE_URL = "https://globalify.org"
CHUNK_SIZE = 50_000
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _xml_response(xml_bytes: bytes) -> object:
    resp = make_response(xml_bytes)
    resp.headers["Content-Type"] = "application/xml; charset=utf-8"
    return resp


def _count_public_approved(model) -> int:
    return (
        db.session.scalar(
            db.select(db.func.count())
            .select_from(model)
            .where(
                model.is_public.is_(True),
                model.is_approved.is_(True),
            )
        )
        or 0
    )


def _chunks_needed(total: int) -> int:
    return max(1, math.ceil(total / CHUNK_SIZE))


def _w3c_date(dt) -> str:
    """Return a W3C date string (YYYY-MM-DD) from a datetime or None."""
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%d")


def _build_urlset(urls: list[dict]) -> bytes:
    """Build a <urlset> XML document from a list of dicts with keys loc, lastmod."""
    root = ET.Element("urlset", xmlns=SITEMAP_NS)
    for entry in urls:
        url_el = ET.SubElement(root, "url")
        loc_el = ET.SubElement(url_el, "loc")
        loc_el.text = escape(entry["loc"])
        if entry.get("lastmod"):
            lm_el = ET.SubElement(url_el, "lastmod")
            lm_el.text = entry["lastmod"]
    return ET.tostring(root, encoding="unicode").encode("utf-8")


# ---------------------------------------------------------------------------
# /sitemap.xml  –  sitemapindex
# ---------------------------------------------------------------------------


@sitemap_bp.get("/sitemap.xml")
def sitemap_index():
    person_count = _count_public_approved(Person)
    org_count = _count_public_approved(Organization)

    investor_chunks = _chunks_needed(person_count)
    firm_chunks = _chunks_needed(org_count)

    root = ET.Element("sitemapindex", xmlns=SITEMAP_NS)

    for n in range(1, investor_chunks + 1):
        sm = ET.SubElement(root, "sitemap")
        loc = ET.SubElement(sm, "loc")
        loc.text = f"{BASE_URL}/sitemap-investors-{n}.xml"

    for n in range(1, firm_chunks + 1):
        sm = ET.SubElement(root, "sitemap")
        loc = ET.SubElement(sm, "loc")
        loc.text = f"{BASE_URL}/sitemap-firms-{n}.xml"

    sm = ET.SubElement(root, "sitemap")
    loc = ET.SubElement(sm, "loc")
    loc.text = f"{BASE_URL}/sitemap-facets.xml"

    xml_bytes = ET.tostring(root, encoding="unicode").encode("utf-8")
    return _xml_response(xml_bytes)


# ---------------------------------------------------------------------------
# /sitemap-investors-<n>.xml
# ---------------------------------------------------------------------------


@sitemap_bp.get("/sitemap-investors-<int:n>.xml")
def sitemap_investors(n: int):
    total = _count_public_approved(Person)
    chunks = _chunks_needed(total)

    if n < 1 or n > chunks:
        abort(404)

    offset = (n - 1) * CHUNK_SIZE
    rows = db.session.scalars(
        db.select(Person)
        .where(Person.is_public.is_(True), Person.is_approved.is_(True))
        .order_by(Person.id)
        .offset(offset)
        .limit(CHUNK_SIZE)
    ).all()

    urls = [
        {
            "loc": f"{BASE_URL}/investors/{escape(p.slug)}",
            "lastmod": _w3c_date(getattr(p, "updated_at", None) or p.created_at),
        }
        for p in rows
    ]
    return _xml_response(_build_urlset(urls))


# ---------------------------------------------------------------------------
# /sitemap-firms-<n>.xml
# ---------------------------------------------------------------------------


@sitemap_bp.get("/sitemap-firms-<int:n>.xml")
def sitemap_firms(n: int):
    total = _count_public_approved(Organization)
    chunks = _chunks_needed(total)

    if n < 1 or n > chunks:
        abort(404)

    offset = (n - 1) * CHUNK_SIZE
    rows = db.session.scalars(
        db.select(Organization)
        .where(Organization.is_public.is_(True), Organization.is_approved.is_(True))
        .order_by(Organization.id)
        .offset(offset)
        .limit(CHUNK_SIZE)
    ).all()

    urls = [
        {
            "loc": f"{BASE_URL}/firms/{escape(o.slug)}",
            "lastmod": _w3c_date(getattr(o, "updated_at", None) or o.created_at),
        }
        for o in rows
    ]
    return _xml_response(_build_urlset(urls))


# ---------------------------------------------------------------------------
# /sitemap-facets.xml
# ---------------------------------------------------------------------------


@sitemap_bp.get("/sitemap-facets.xml")
def sitemap_facets():
    urls: list[dict] = []

    # --- Investor (PERSON) facets: InvestorType slugs ---
    for member in InvestorType:
        slug = enum_to_slug(member.value)
        urls.append({"loc": f"{BASE_URL}/investors/{escape(slug)}", "lastmod": ""})

    # --- Investor (PERSON) facets: InvestmentStage slugs ---
    for member in InvestmentStage:
        slug = enum_to_slug(member.value)
        urls.append({"loc": f"{BASE_URL}/investors/{escape(slug)}", "lastmod": ""})

    # --- Firm (ORG) facets: OrgType slugs ---
    for member in OrgType:
        slug = enum_to_slug(member.value)
        urls.append({"loc": f"{BASE_URL}/firms/{escape(slug)}", "lastmod": ""})

    # --- Firm (ORG) facets: InvestmentStage slugs ---
    for member in InvestmentStage:
        slug = enum_to_slug(member.value)
        urls.append({"loc": f"{BASE_URL}/firms/{escape(slug)}", "lastmod": ""})

    # --- Sector facets: Industry slugs (both /investors/ and /firms/) ---
    industries = db.session.scalars(db.select(Industry).where(Industry.slug.isnot(None))).all()
    for ind in industries:
        if ind.slug:
            urls.append({"loc": f"{BASE_URL}/investors/{escape(ind.slug)}", "lastmod": ""})
            urls.append({"loc": f"{BASE_URL}/firms/{escape(ind.slug)}", "lastmod": ""})

    # --- Geo facets: Geography slugs (both /investors/ and /firms/) ---
    geos = db.session.scalars(db.select(Geography).where(Geography.slug.isnot(None))).all()
    for geo in geos:
        if geo.slug:
            urls.append({"loc": f"{BASE_URL}/investors/{escape(geo.slug)}", "lastmod": ""})
            urls.append({"loc": f"{BASE_URL}/firms/{escape(geo.slug)}", "lastmod": ""})

    # Drop entries without a lastmod (set to None for cleaner XML — omit lastmod element)
    # _build_urlset already handles empty lastmod by omitting the element
    return _xml_response(_build_urlset(urls))


# ---------------------------------------------------------------------------
# /robots.txt
# ---------------------------------------------------------------------------


@sitemap_bp.get("/robots.txt")
def robots():
    robots_txt = (
        "User-agent: *\n"
        "Disallow: /admin\n"
        "Disallow: /settings\n"
        "Disallow: /login\n"
        "Disallow: /claim\n"
        "Disallow: /payment\n"
        "Disallow: /*?*\n"
        "\n"
        f"Sitemap: {BASE_URL}/sitemap.xml\n"
    )
    resp = make_response(robots_txt)
    resp.headers["Content-Type"] = "text/plain; charset=utf-8"
    return resp
