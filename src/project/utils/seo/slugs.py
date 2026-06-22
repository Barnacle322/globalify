"""Facet slug codec and registry for programmatic SEO pages (Phase 2c Task 1).

Public API
----------
enum_to_slug(value)         str  → hyphenated slug ("pre_seed" → "pre-seed")
slug_to_enum_value(slug)    str  → underscore value ("pre-seed" → "pre_seed")

SEO_FACETS                  dict mapping facet-family keys to filter metadata

classify_segment(slug, entity_kind) → (facet_field, value, segment_type) | None
    segment_type ∈ {"type", "stage", "sector", "geo"}

CANONICAL_ORDER             tuple defining canonical URL segment order
order_segments(classified)  → (ordered_list, warnings)

build_facet_canonical(entity_kind, classified) → absolute URL string

Notes
-----
- ORM models are imported lazily inside functions to avoid circular-import issues
  at module load time.
- The `entity_kind` parameter accepts an EntityType enum member or its string value.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Primitive codec
# ---------------------------------------------------------------------------


def enum_to_slug(value: str) -> str:
    """Convert an enum value string to a URL-safe hyphenated slug.

    "pre_seed" → "pre-seed"
    "series_d_plus" → "series-d-plus"
    "vc_firm" → "vc-firm"
    """
    return value.replace("_", "-")


def slug_to_enum_value(slug: str) -> str:
    """Convert a URL slug back to an enum value string.

    "pre-seed" → "pre_seed"
    "series-d-plus" → "series_d_plus"
    "vc-firm" → "vc_firm"
    """
    return slug.replace("-", "_")


# ---------------------------------------------------------------------------
# SEO_FACETS registry
# ---------------------------------------------------------------------------
# Maps each facet family to the Typesense filter field name and enum class.
# Sector (industries) and geo (geographies) are resolved dynamically via DB.


def _get_facets() -> dict:
    """Build SEO_FACETS lazily to avoid importing enums at module top if not needed."""
    from ..enums import InvestmentStage, InvestorType, OrgType

    return {
        "investor_type": {
            "field": "investor_type",
            "enum": InvestorType,
            "segment_type": "type",
        },
        "stages": {
            "field": "stages",
            "enum": InvestmentStage,
            "segment_type": "stage",
        },
        "org_type": {
            "field": "org_type",
            "enum": OrgType,
            "segment_type": "type",
        },
    }


# Eagerly-computed singleton (safe because enums are plain StrEnum — no DB touch)
SEO_FACETS: dict = _get_facets()


# ---------------------------------------------------------------------------
# classify_segment
# ---------------------------------------------------------------------------


def classify_segment(
    slug: str,
    entity_kind=None,
) -> tuple[str, str, str] | None:
    """Classify a URL path segment into a (facet_field, value, segment_type) triple.

    Resolution order:
    1. Enum facets relevant to entity_kind:
       - PERSON: InvestorType (→ "type") then InvestmentStage (→ "stage")
       - ORG:    OrgType (→ "type") then InvestmentStage (→ "stage")
       - None:   tries all three enum families
    2. Sector: Industry.get_by_slug (→ "sector", field "industries")
    3. Geo: Geography by slug (→ "geo", field "geographies")

    Returns None for unknown slugs.
    """
    from ..enums import EntityType, InvestmentStage, InvestorType, OrgType

    enum_value = slug_to_enum_value(slug)

    # Normalise entity_kind to EntityType or None
    if entity_kind is not None and not isinstance(entity_kind, EntityType):
        try:
            entity_kind = EntityType(str(entity_kind))
        except ValueError:
            entity_kind = None

    # Determine which enum families to try for "type" vs "stage"
    if entity_kind == EntityType.PERSON:
        type_enum_families = [("investor_type", InvestorType)]
    elif entity_kind == EntityType.ORG:
        type_enum_families = [("org_type", OrgType)]
    else:
        # Try both
        type_enum_families = [("investor_type", InvestorType), ("org_type", OrgType)]

    # Try type enums first
    for field, enum_cls in type_enum_families:
        try:
            enum_cls(enum_value)
            return (field, enum_value, "type")
        except ValueError:
            pass

    # Try stage enum
    try:
        InvestmentStage(enum_value)
        return ("stages", enum_value, "stage")
    except ValueError:
        pass

    # Try sector via DB (lazy import to avoid circular)
    try:
        from ...models.helpers import Industry  # noqa: PLC0415

        industry = Industry.get_by_slug(slug)
        if industry is not None:
            return ("industries", slug, "sector")
    except Exception:
        pass

    # Try geo via DB (lazy import)
    try:
        geo = _get_geography_by_slug(slug)
        if geo is not None:
            return ("geographies", slug, "geo")
    except Exception:
        pass

    return None


def _get_geography_by_slug(slug: str):
    """Fetch a Geography by slug; returns None if not found or outside app context."""
    try:
        from ...extensions import db
        from ...models.entity import Geography

        return db.session.scalar(db.select(Geography).where(Geography.slug == slug))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Canonical ordering
# ---------------------------------------------------------------------------

CANONICAL_ORDER: tuple[str, ...] = ("type", "stage", "sector", "geo")


def order_segments(
    classified: list[tuple[str, str, str]],
) -> tuple[list[tuple[str, str, str]], list[str]]:
    """Sort classified segments into canonical order and collect warnings.

    Args:
        classified: list of (facet_field, value, segment_type) triples.

    Returns:
        (ordered, warnings) where:
        - ordered is sorted by CANONICAL_ORDER position
        - warnings is a list of human-readable warning strings for:
            * duplicate segment_type entries
            * input that was not already in canonical order
    """
    warnings: list[str] = []

    # Detect duplicates
    seen_types: dict[str, int] = {}
    for _, _, seg_type in classified:
        seen_types[seg_type] = seen_types.get(seg_type, 0) + 1
    for seg_type, count in seen_types.items():
        if count > 1:
            warnings.append(f"Duplicate segment type: {seg_type!r} appears {count} times")

    # Sort by canonical order (unknown types go to the end)
    def _order_key(item: tuple[str, str, str]) -> int:
        seg_type = item[2]
        try:
            return CANONICAL_ORDER.index(seg_type)
        except ValueError:
            return len(CANONICAL_ORDER)

    ordered = sorted(classified, key=_order_key)

    # Detect mis-order in the original input (compare original vs sorted)
    original_positions = [_order_key(item) for item in classified]
    if original_positions != sorted(original_positions):
        warnings.append(f"Input segments were not in canonical order; expected order: {list(CANONICAL_ORDER)}")

    return ordered, warnings


# ---------------------------------------------------------------------------
# build_facet_canonical
# ---------------------------------------------------------------------------


def build_facet_canonical(entity_kind, classified: list[tuple[str, str, str]]) -> str:
    """Build an absolute canonical URL for a faceted investor/firm page.

    The URL is always in canonical segment order (type → stage → sector → geo).
    Values stored as enum underscore strings are converted to hyphenated slugs.

    Examples:
        PERSON, [("investor_type","angel","type"), ("stages","seed","stage")]
            → "https://globalify.xyz/investors/angel/seed"
        ORG, [("org_type","vc_firm","type")]
            → "https://globalify.xyz/firms/vc-firm"
    """
    from ..enums import EntityType

    if entity_kind is not None and not isinstance(entity_kind, EntityType):
        try:
            entity_kind = EntityType(str(entity_kind))
        except ValueError:
            entity_kind = None

    base_path = "investors" if entity_kind == EntityType.PERSON else "firms"

    # Sort into canonical order
    ordered, _ = order_segments(classified)

    # Convert values to URL slugs (underscore → hyphen)
    segments = [enum_to_slug(value) for _, value, _ in ordered]

    path = "/".join(segments)
    if path:
        return f"https://globalify.xyz/{base_path}/{path}"
    return f"https://globalify.xyz/{base_path}"
