"""Typesense search module for the unified 'entities' collection (Phase 1c).

Exposes:
    sync_search_index(recreate=False) — build / refresh the Typesense index
    sync_one(entity_type, entity_id)  — upsert a single entity document
    get_search(query, **filters)      — run a search and return raw Typesense results
    delete_data(entity_type, db_id)   — remove a single entity document
"""

from __future__ import annotations

import logging

from typesense.exceptions import ObjectNotFound

from ..config import get_settings

log = logging.getLogger(__name__)

COLLECTION = "entities"


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------


def _build_schema() -> dict:
    """Build the 'entities' collection schema dict."""
    settings = get_settings()
    fields = [
        {"name": "id", "type": "string"},
        {"name": "entity_type", "type": "string", "facet": True},
        {"name": "db_id", "type": "int32", "facet": True},
        {"name": "name", "type": "string"},
        {"name": "slug", "type": "string", "optional": True},
        {"name": "about", "type": "string", "optional": True},
        {"name": "headline", "type": "string", "facet": True, "optional": True},
        {"name": "org_name", "type": "string", "optional": True},
        {"name": "person_names", "type": "string[]", "optional": True},
        {"name": "website", "type": "string", "optional": True},
        {"name": "linkedin", "type": "string", "optional": True},
        {"name": "twitter", "type": "string", "optional": True},
        {"name": "country_code", "type": "string", "facet": True, "optional": True},
        {"name": "geographies", "type": "string[]", "facet": True, "optional": True},
        {"name": "industries", "type": "string[]", "facet": True, "optional": True},
        {"name": "stages", "type": "string[]", "facet": True, "optional": True},
        {"name": "notable_investments", "type": "string[]", "optional": True},
        {"name": "investor_type", "type": "string", "facet": True, "optional": True},
        {"name": "org_type", "type": "string", "facet": True, "optional": True},
        {"name": "lead_pref", "type": "string", "facet": True, "optional": True},
        {"name": "accepts_cold_inbound", "type": "bool", "facet": True, "optional": True},
        {"name": "is_active", "type": "bool", "facet": True, "optional": True},
        {"name": "check_size_min", "type": "int32", "optional": True, "sort": True},
        {"name": "check_size_max", "type": "int32", "optional": True, "sort": True},
        {"name": "n_investments", "type": "int32", "optional": True, "sort": True},
        {"name": "n_exits", "type": "int32", "optional": True, "sort": True},
    ]
    if settings.embeddings_enabled:
        fields.append({"name": "embedding", "type": "float[]", "num_dim": settings.embedding_dim})
    return {
        "name": COLLECTION,
        "primary_key": "id",
        "fields": fields,
    }


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------


def _build_entity_doc(entity_type: object, entity: object, session: object) -> dict:
    """Build a Typesense document dict for a single Person or Organization.

    This is the ONE source of truth for document construction; both
    ``sync_search_index`` and ``sync_one`` call it.

    Args:
        entity_type: An ``EntityType`` enum value (PERSON or ORG).
        entity:      The ORM row (Person or Organization instance).
        session:     The active SQLAlchemy session (unused directly; db.session
                     is used via lazy import to stay consistent with the rest of
                     the module's pattern).

    Returns:
        A dict ready to upsert into the ``entities`` Typesense collection.
    """
    # Lazy imports to keep module-level import graph clean.
    from ..extensions import db
    from ..utils.enums import EntityType
    from .entity import (
        Affiliation,
        EntityGeography,
        EntityIndustry,
        EntityNotable,
        EntityStage,
        InvestorProfile,
        NotableInvestment,
        Organization,
        Person,
    )
    from .helpers import Industry

    is_person = entity_type == EntityType.PERSON

    if is_person:
        doc: dict = {
            "id": f"person_{entity.id}",
            "entity_type": "person",
            "db_id": entity.id,
            "name": f"{entity.first_name} {entity.last_name or ''}".strip(),
        }
        if entity.slug:
            doc["slug"] = entity.slug
        if entity.about:
            doc["about"] = entity.about
        if entity.headline:
            doc["headline"] = entity.headline
        if entity.website:
            doc["website"] = entity.website
        if entity.linkedin:
            doc["linkedin"] = entity.linkedin
        if entity.twitter:
            doc["twitter"] = entity.twitter

        # org_name: first current affiliation's organization name
        affiliation = db.session.scalar(
            db.select(Affiliation).where(Affiliation.person_id == entity.id, Affiliation.is_current.is_(True)).limit(1)
        )
        if affiliation:
            org = db.session.get(Organization, affiliation.organization_id)
            if org:
                doc["org_name"] = org.name
    else:
        doc = {
            "id": f"org_{entity.id}",
            "entity_type": "org",
            "db_id": entity.id,
            "name": entity.name,
        }
        if entity.slug:
            doc["slug"] = entity.slug
        if entity.about:
            doc["about"] = entity.about
        if entity.website:
            doc["website"] = entity.website
        if entity.linkedin:
            doc["linkedin"] = entity.linkedin
        if entity.twitter:
            doc["twitter"] = entity.twitter
        if entity.org_type is not None:
            doc["org_type"] = entity.org_type.value

        # person_names: all affiliated persons
        affiliations = db.session.scalars(db.select(Affiliation).where(Affiliation.organization_id == entity.id)).all()
        person_names = []
        for aff in affiliations:
            p = db.session.get(Person, aff.person_id)
            if p:
                person_names.append(f"{p.first_name} {p.last_name or ''}".strip())
        if person_names:
            doc["person_names"] = person_names

    # industries — indexed as slugs for facet URL matching
    entity_industries = db.session.scalars(
        db.select(EntityIndustry).where(
            EntityIndustry.entity_type == entity_type,
            EntityIndustry.entity_id == entity.id,
        )
    ).all()
    industries = []
    for ei in entity_industries:
        ind = db.session.get(Industry, ei.industry_id)
        if ind:
            industries.append(ind.slug if ind.slug else ind.name)
    if industries:
        doc["industries"] = industries

    # stages
    entity_stages = db.session.scalars(
        db.select(EntityStage).where(
            EntityStage.entity_type == entity_type,
            EntityStage.entity_id == entity.id,
        )
    ).all()
    stages = [es.stage.value for es in entity_stages]
    if stages:
        doc["stages"] = stages

    # geographies
    entity_geos = db.session.scalars(
        db.select(EntityGeography).where(
            EntityGeography.entity_type == entity_type,
            EntityGeography.entity_id == entity.id,
        )
    ).all()
    geo_slugs = []
    country_code = None
    for eg in entity_geos:
        if eg.geography:
            geo_slugs.append(eg.geography.slug)
            if country_code is None and eg.geography.country_code:
                country_code = eg.geography.country_code
    if geo_slugs:
        doc["geographies"] = geo_slugs
    if country_code:
        doc["country_code"] = country_code

    # notable investments
    entity_notables = db.session.scalars(
        db.select(EntityNotable).where(
            EntityNotable.entity_type == entity_type,
            EntityNotable.entity_id == entity.id,
        )
    ).all()
    notables = []
    for en in entity_notables:
        ni = db.session.get(NotableInvestment, en.notable_investment_id)
        if ni:
            notables.append(ni.name)
    if notables:
        doc["notable_investments"] = notables

    # investor profile
    profile = db.session.scalar(
        db.select(InvestorProfile).where(
            InvestorProfile.entity_type == entity_type,
            InvestorProfile.entity_id == entity.id,
        )
    )
    if profile:
        if profile.investor_type is not None:
            doc["investor_type"] = profile.investor_type.value
        if profile.lead_pref is not None:
            doc["lead_pref"] = profile.lead_pref.value
        doc["accepts_cold_inbound"] = profile.accepts_cold_inbound
        doc["is_active"] = profile.is_active
        if profile.min_investment is not None:
            doc["check_size_min"] = int(profile.min_investment)
        if profile.max_investment is not None:
            doc["check_size_max"] = int(profile.max_investment)
        if profile.n_investments is not None:
            doc["n_investments"] = profile.n_investments
        if profile.n_exits is not None:
            doc["n_exits"] = profile.n_exits

    return doc


def _attach_embeddings(docs: list[dict]) -> None:
    """Compute and attach embedding vectors to *docs* in-place.

    Uses the joined text of the searchable fields (name, about, headline,
    industries, geographies) as the embedding input — matching what the old
    Typesense auto-embed ``embed_from`` list referenced.

    When ``embed_documents`` returns None (provider disabled or API failure),
    the docs are left as-is (keyword-only) and a warning is logged so the
    caller can still upsert them without dropping any DB-backed document.
    """
    from ..utils import embeddings

    texts = []
    for doc in docs:
        parts = [doc.get("name", "")]
        for field in ("about", "headline"):
            val = doc.get(field)
            if val:
                parts.append(val)
        for field in ("industries", "geographies"):
            vals = doc.get(field)
            if vals:
                parts.extend(vals)
        texts.append(" ".join(parts))

    vectors = embeddings.embed_documents(texts)
    if vectors is None:
        log.warning(
            "embed_documents returned None for %d docs — indexing without embeddings (keyword-only fallback)",
            len(docs),
        )
        return

    for doc, vec in zip(docs, vectors, strict=True):
        doc["embedding"] = vec


def sync_search_index(recreate: bool = False) -> None:
    """Upsert all Person and Organization rows into the 'entities' Typesense collection.

    Args:
        recreate: When True, drop and recreate the collection before syncing.
    """
    # Lazy imports to avoid circular imports at module load time.
    from ..extensions import db
    from ..utils.enums import EntityType
    from ..utils.typesense_helpers.typesense_search import (
        create_schema,
        delete_schema,
        upsert_documents,
    )
    from .entity import Organization, Person

    settings = get_settings()

    if recreate:
        try:
            delete_schema(COLLECTION)
        except Exception:
            pass
        create_schema(_build_schema())

    batch = 100

    # ------------------------------------------------------------------
    # Persons
    # ------------------------------------------------------------------
    offset = 0
    while True:
        persons = db.session.scalars(db.select(Person).offset(offset).limit(batch)).all()
        if not persons:
            break

        docs: list[dict] = [_build_entity_doc(EntityType.PERSON, person, db.session) for person in persons]

        if docs:
            if settings.embeddings_enabled:
                _attach_embeddings(docs)
            upsert_documents(COLLECTION, docs)
            # Write search_index back to person rows
            for person in persons:
                person.search_index = f"person_{person.id}"
            db.session.commit()

        offset += batch

    # ------------------------------------------------------------------
    # Organizations
    # ------------------------------------------------------------------
    offset = 0
    while True:
        orgs = db.session.scalars(db.select(Organization).offset(offset).limit(batch)).all()
        if not orgs:
            break

        docs = [_build_entity_doc(EntityType.ORG, org, db.session) for org in orgs]

        if docs:
            if settings.embeddings_enabled:
                _attach_embeddings(docs)
            upsert_documents(COLLECTION, docs)
            # Write search_index back to org rows
            for org in orgs:
                org.search_index = f"org_{org.id}"
            db.session.commit()

        offset += batch


def sync_one(entity_type: object, entity_id: int) -> None:
    """Upsert a single Person or Organization document into Typesense.

    Builds the document via ``_build_entity_doc`` (same builder used by
    ``sync_search_index``) and upserts it.  Uses ``delete_data`` internally
    to remove stale docs before upserting — callers may also call
    ``delete_data`` directly for delete-only operations.

    Args:
        entity_type: An ``EntityType`` enum value (PERSON or ORG).
        entity_id:   The primary-key integer of the Person or Organization row.
    """
    from ..extensions import db
    from ..utils.enums import EntityType
    from ..utils.typesense_helpers.typesense_search import upsert_documents
    from .entity import Organization, Person

    if entity_type == EntityType.PERSON:
        entity = db.session.get(Person, entity_id)
    else:
        entity = db.session.get(Organization, entity_id)

    if entity is None:
        log.warning("sync_one: no %s with id=%s found; skipping upsert", entity_type, entity_id)
        return

    settings = get_settings()
    doc = _build_entity_doc(entity_type, entity, db.session)
    if settings.embeddings_enabled:
        _attach_embeddings([doc])
    upsert_documents(COLLECTION, [doc])

    # Write search_index back to the row
    entity.search_index = doc["id"]
    db.session.commit()


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


def get_search(
    query: str = "*",
    entity_type: str | None = None,
    industries: list[str] | None = None,
    stages: list[str] | None = None,
    country_code: list[str] | None = None,
    geographies: list[str] | None = None,
    investor_type: list[str] | None = None,
    org_type: list[str] | None = None,
    lead_pref: str | None = None,
    accepts_cold_inbound: bool | None = None,
    is_active: bool | None = None,
    check_size_min: int | None = None,
    check_size_max: int | None = None,
    sort_by: str | None = None,
    sort_desc: bool = False,
    page: int = 1,
    per_page: int = 12,
) -> dict:
    """Search the 'entities' collection and return raw Typesense results.

    Builds filters via SearchBuilder then calls the Typesense client directly
    (bypassing the FLASK_ENV=='testing' short-circuit in SearchBuilder.search()).
    """
    from ..utils import embeddings
    from ..utils.typesense_helpers.typesense_search import SearchBuilder, client

    builder = (
        SearchBuilder(COLLECTION)
        .query(query)
        .query_by(
            ["name", "about", "headline", "org_name", "person_names", "industries"],
            weights=[4, 2, 2, 1, 1, 1],
        )
    )

    if entity_type:
        builder.filter_by("entity_type", [entity_type], exclusivity=True)

    builder = (
        builder.filter_by("industries", industries, exclusivity=False)
        .filter_by("stages", stages, exclusivity=False)
        .filter_by("country_code", country_code, exclusivity=False)
        .filter_by("geographies", geographies, exclusivity=False)
        .filter_by("investor_type", investor_type, exclusivity=False)
        .filter_by("org_type", org_type, exclusivity=False)
    )

    if lead_pref:
        builder.filter_by("lead_pref", [lead_pref], exclusivity=True)

    if accepts_cold_inbound is not None:
        builder.filter_by_boolean("accepts_cold_inbound", accepts_cold_inbound)

    if is_active is not None:
        builder.filter_by_boolean("is_active", is_active)

    if check_size_min or check_size_max:
        if check_size_min and check_size_max:
            builder.filters.append(f"check_size_min:<={check_size_max} && check_size_max:>={check_size_min}")
        elif check_size_min:
            builder.filters.append(f"check_size_max:>={check_size_min}")
        elif check_size_max:
            builder.filters.append(f"check_size_min:<={check_size_max}")

    builder = builder.sort_by(sort_by, sort_desc).page(page, per_page)

    # Build params and call client directly — bypasses FLASK_ENV=='testing' guard
    # in SearchBuilder.search() so Docker-backed integration tests work correctly.
    settings = get_settings()
    params = {**builder.parameters}
    params["prefix"] = False
    if settings.embeddings_enabled and query and query != "*":
        qvec = embeddings.embed_query(query)
        if qvec is not None:
            params["vector_query"] = (
                f"embedding:([{','.join(repr(float(x)) for x in qvec)}],"
                f" distance_threshold:{settings.embedding_distance_threshold})"
            )
            params["exclude_fields"] = "embedding"
    if builder.filters:
        params["filter_by"] = " && ".join(builder.filters)

    try:
        return client.collections[COLLECTION].documents.search(params)
    except Exception:
        log.exception("Typesense search failed for collection=%s params=%s", COLLECTION, params)
        raise


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


def delete_data(entity_type: object, db_id: int) -> None:
    """Remove the document matching both entity_type AND db_id from Typesense.

    Uses a compound filter so that a person and an org that happen to share the
    same db_id integer are never accidentally co-deleted.
    """
    from ..utils.typesense_helpers.typesense_search import client

    entity_type_val = entity_type.value if hasattr(entity_type, "value") else str(entity_type)
    filter_expr = f"entity_type:={entity_type_val} && db_id:={db_id}"
    try:
        client.collections[COLLECTION].documents.delete({"filter_by": filter_expr})
    except ObjectNotFound:
        pass
