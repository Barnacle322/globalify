"""Tests for entity search (entity_search.py) — Typesense v30 Docker-gated.

Automatically skipped when Typesense is not reachable.

Start Docker:
    mkdir -p /tmp/ts-c2
    docker run -d --name ts-c2 -p 18108:8108 -v /tmp/ts-c2:/data \\
        typesense/typesense:30.2 --data-dir /data --api-key=xyz --enable-cors

Run:
    _TYPESENSE_HOST=localhost _TYPESENSE_PORT=18108 _TYPESENSE_API_KEY=xyz \\
    uv run pytest tests/test_entity_search.py -v

Teardown:
    docker rm -f ts-c2 && rm -rf /tmp/ts-c2
"""

from __future__ import annotations

import os
import sys

# Set env vars before any project import so the Typesense client is created
# with the correct host/port/key.  Use setdefault so external env vars win.
os.environ.setdefault("_TYPESENSE_HOST", "127.0.0.1")
os.environ.setdefault("_TYPESENSE_PORT", "8108")
os.environ.setdefault("_TYPESENSE_API_KEY", "xyz")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("_DATABASE_URL", "sqlite:///test_entity_search_db.sqlite")

import pytest


def _typesense_reachable() -> bool:
    """Return True if Typesense is listening at the configured host/port."""
    import socket

    host = os.getenv("_TYPESENSE_HOST", "127.0.0.1")
    port = int(os.getenv("_TYPESENSE_PORT", "8108"))
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False


pytestmark = pytest.mark.skipif(
    not _typesense_reachable(),
    reason=(
        f"Typesense not reachable at "
        f"{os.getenv('_TYPESENSE_HOST', '127.0.0.1')}:"
        f"{os.getenv('_TYPESENSE_PORT', '8108')} — start Docker first"
    ),
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def app_ctx():
    """App context with a fresh SQLite DB for the entire test module.

    Forces the Typesense client to be re-created with the correct env vars
    in case another test module imported project first with default settings.
    """
    # Remove any cached typesense / entity_search modules so the client
    # re-initialises with the env vars set above.
    for key in list(sys.modules.keys()):
        if "typesense_search" in key or "entity_search" in key:
            del sys.modules[key]

    from project import create_app

    app = create_app()
    # TESTING=False so Flask doesn't suppress errors; we want real Typesense.
    app.config.update(TESTING=False)

    with app.app_context():
        from project.extensions import db

        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope="module")
def seeded_data(app_ctx):
    """Seed Person and Organization rows with full profiles/facets/affiliations."""
    from project.extensions import db
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
    )
    from project.models.helpers import Industry
    from project.utils.enums import (
        AffiliationRole,
        EntityType,
        InvestmentStage,
        InvestorType,
        LeadPreference,
        OrgType,
    )

    with app_ctx.app_context():
        # Geography
        geo_us = Geography(slug="us-country-ts", name="United States", type="country", country_code="US")
        geo_uk = Geography(slug="gb-country-ts", name="United Kingdom", type="country", country_code="GB")
        db.session.add_all([geo_us, geo_uk])
        db.session.flush()

        # Industry — reuse existing row or create one
        industry = db.session.scalar(db.select(Industry).limit(1))
        if industry is None:
            industry = Industry(name="SaaS", category="Technology")
            db.session.add(industry)
            db.session.flush()

        # Notable investment
        notable = NotableInvestment(name="TestCorp")
        db.session.add(notable)
        db.session.flush()

        # Person: Alice
        alice = Person(
            first_name="Alice",
            last_name="Venture",
            slug="alice-venture-ts",
            about="Angel investor focused on SaaS",
            headline="Angel Investor",
            is_public=True,
            is_approved=True,
        )
        db.session.add(alice)
        db.session.flush()

        # Org: Acme Capital
        acme = Organization(
            name="Acme Capital",
            slug="acme-capital-ts",
            org_type=OrgType.VC_FIRM,
            about="Early stage VC",
            is_public=True,
            is_approved=True,
        )
        db.session.add(acme)
        db.session.flush()

        # Affiliation: Alice -> Acme
        db.session.add(Affiliation(person_id=alice.id, organization_id=acme.id, role=AffiliationRole.GP))

        # InvestorProfiles
        db.session.add(
            InvestorProfile(
                entity_type=EntityType.PERSON,
                entity_id=alice.id,
                investor_type=InvestorType.ANGEL,
                min_investment=10000,
                max_investment=100000,
                lead_pref=LeadPreference.LEAD,
                accepts_cold_inbound=True,
                is_active=True,
            )
        )
        db.session.add(
            InvestorProfile(
                entity_type=EntityType.ORG,
                entity_id=acme.id,
                investor_type=InvestorType.VC_FIRM,
                n_investments=25,
                n_exits=5,
                lead_pref=LeadPreference.LEAD,
                accepts_cold_inbound=False,
                is_active=True,
            )
        )

        # Geographies
        db.session.add(EntityGeography(entity_type=EntityType.PERSON, entity_id=alice.id, geography_id=geo_us.id))
        db.session.add(EntityGeography(entity_type=EntityType.ORG, entity_id=acme.id, geography_id=geo_uk.id))

        # Industries
        db.session.add(EntityIndustry(entity_type=EntityType.PERSON, entity_id=alice.id, industry_id=industry.id))
        db.session.add(EntityIndustry(entity_type=EntityType.ORG, entity_id=acme.id, industry_id=industry.id))

        # Stages
        db.session.add(EntityStage(entity_type=EntityType.PERSON, entity_id=alice.id, stage=InvestmentStage.SEED))
        db.session.add(EntityStage(entity_type=EntityType.ORG, entity_id=acme.id, stage=InvestmentStage.SERIES_A))

        # Notables (person only)
        db.session.add(
            EntityNotable(
                entity_type=EntityType.PERSON,
                entity_id=alice.id,
                notable_investment_id=notable.id,
            )
        )

        db.session.commit()

        return {
            "alice_id": alice.id,
            "acme_id": acme.id,
            "geo_us_id": geo_us.id,
            "geo_uk_id": geo_uk.id,
        }


@pytest.fixture(scope="module")
def synced(app_ctx, seeded_data):
    """Run sync_search_index(recreate=True) once for the entire module."""
    with app_ctx.app_context():
        from project.models.entity_search import sync_search_index

        sync_search_index(recreate=True)
    return seeded_data


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _wait_for_indexed(collection: str, expected_count: int, timeout: int = 30) -> bool:
    """Poll Typesense until at least *expected_count* docs are indexed."""
    import time

    from project.utils.typesense_helpers.typesense_search import client

    deadline = time.time() + timeout
    while time.time() < deadline:
        result = client.collections[collection].documents.search({"q": "*", "query_by": "name"})
        if result.get("found", 0) >= expected_count:
            return True
        time.sleep(0.5)
    return False


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_keyword_search_finds_person(app_ctx, synced):
    """A keyword query for 'Alice' should return Alice's person document."""
    with app_ctx.app_context():
        from project.models.entity_search import COLLECTION, get_search

        assert _wait_for_indexed(COLLECTION, 2), "Timed out waiting for documents to be indexed"

        results = get_search(query="Alice")
        hits = results.get("hits", [])
        names = [h["document"]["name"] for h in hits]
        assert any("Alice" in n for n in names), f"Expected 'Alice' in search results, got: {names}"


def test_entity_type_filter_person_only(app_ctx, synced):
    """entity_type=person filter must return only person documents."""
    with app_ctx.app_context():
        from project.models.entity_search import COLLECTION, get_search

        assert _wait_for_indexed(COLLECTION, 2)

        results = get_search(query="*", entity_type="person")
        hits = results.get("hits", [])
        assert len(hits) >= 1, "Expected at least one person result"
        for hit in hits:
            assert hit["document"]["entity_type"] == "person", f"Unexpected entity_type in hit: {hit['document']}"


def test_entity_type_filter_org_only(app_ctx, synced):
    """entity_type=org filter must return only org documents."""
    with app_ctx.app_context():
        from project.models.entity_search import COLLECTION, get_search

        assert _wait_for_indexed(COLLECTION, 2)

        results = get_search(query="*", entity_type="org")
        hits = results.get("hits", [])
        assert len(hits) >= 1, "Expected at least one org result"
        for hit in hits:
            assert hit["document"]["entity_type"] == "org", f"Unexpected entity_type in hit: {hit['document']}"


def test_country_code_filter_regression(app_ctx, synced):
    """country_code filter returns docs with matching code only (regression for old 'countries' field bug)."""
    with app_ctx.app_context():
        from project.models.entity_search import COLLECTION, get_search

        assert _wait_for_indexed(COLLECTION, 2)

        # Alice is in US
        results_us = get_search(query="*", country_code=["US"])
        hits_us = results_us.get("hits", [])
        assert len(hits_us) >= 1, "Expected at least one US entity"
        for hit in hits_us:
            assert hit["document"]["country_code"] == "US", f"Expected country_code=US, got: {hit['document']}"

        # Acme is in GB
        results_gb = get_search(query="*", country_code=["GB"])
        hits_gb = results_gb.get("hits", [])
        assert len(hits_gb) >= 1, "Expected at least one GB entity"
        for hit in hits_gb:
            assert hit["document"]["country_code"] == "GB", f"Expected country_code=GB, got: {hit['document']}"


def test_delete_data_isolation(app_ctx, synced):
    """delete_data(PERSON, alice_id) removes only Alice, NOT Acme (even if both share db_id)."""
    import time

    with app_ctx.app_context():
        from project.models.entity_search import COLLECTION, delete_data, get_search
        from project.utils.enums import EntityType

        assert _wait_for_indexed(COLLECTION, 2)

        alice_id = synced["alice_id"]
        acme_id = synced["acme_id"]

        # Both should exist before deletion
        before = get_search(query="*")
        assert before.get("found", 0) >= 2, "Expected at least 2 docs before delete"

        # Delete Alice (person only)
        delete_data(EntityType.PERSON, alice_id)
        time.sleep(0.5)  # brief propagation wait

        # Alice must be gone from person results
        after_persons = get_search(query="*", entity_type="person")
        person_db_ids = [h["document"]["db_id"] for h in after_persons.get("hits", [])]
        assert alice_id not in person_db_ids, (
            f"Alice (db_id={alice_id}) should be deleted but is still in persons: {person_db_ids}"
        )

        # Acme (org) must still exist
        after_orgs = get_search(query="*", entity_type="org")
        org_db_ids = [h["document"]["db_id"] for h in after_orgs.get("hits", [])]
        assert acme_id in org_db_ids, f"Acme (db_id={acme_id}) should still exist but not found in orgs: {org_db_ids}"
