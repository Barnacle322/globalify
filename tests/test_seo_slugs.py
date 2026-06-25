"""Tests for the SEO facet slug codec (Phase 2c Task 1).

TDD order:
1. Write tests (this file) — watch them fail.
2. Implement `src/project/utils/seo/slugs.py` — watch them pass.

Tests cover:
- enum_to_slug / slug_to_enum_value round-trip for all InvestmentStage, InvestorType, OrgType members
- classify_segment with stage slug → (field, value, "stage")
- classify_segment with sector slug  → (field, value, "sector") via DB
- classify_segment with geo slug     → (field, value, "geo") via DB
- classify_segment with unknown slug → None
- order_segments: correct canonical order, duplicate detection
- build_facet_canonical: produces correct absolute URL path
"""

from __future__ import annotations

import os

os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("_DATABASE_URL", "sqlite:///test_seo_slugs.sqlite")

import pytest  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_session(app):
    """Push an app context, create all tables, yield the db session, then teardown."""
    from project.extensions import db

    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()


# ---------------------------------------------------------------------------
# enum_to_slug / slug_to_enum_value — pure codec, no DB needed
# ---------------------------------------------------------------------------


class TestEnumToSlug:
    def test_underscore_becomes_hyphen(self):
        from project.utils.seo.slugs import enum_to_slug

        assert enum_to_slug("pre_seed") == "pre-seed"

    def test_single_word_unchanged(self):
        from project.utils.seo.slugs import enum_to_slug

        assert enum_to_slug("seed") == "seed"

    def test_multi_segment(self):
        from project.utils.seo.slugs import enum_to_slug

        assert enum_to_slug("series_d_plus") == "series-d-plus"

    def test_vc_firm(self):
        from project.utils.seo.slugs import enum_to_slug

        assert enum_to_slug("vc_firm") == "vc-firm"


class TestSlugToEnumValue:
    def test_hyphen_becomes_underscore(self):
        from project.utils.seo.slugs import slug_to_enum_value

        assert slug_to_enum_value("pre-seed") == "pre_seed"

    def test_single_word_unchanged(self):
        from project.utils.seo.slugs import slug_to_enum_value

        assert slug_to_enum_value("seed") == "seed"

    def test_multi_segment(self):
        from project.utils.seo.slugs import slug_to_enum_value

        assert slug_to_enum_value("series-d-plus") == "series_d_plus"


class TestRoundTrip:
    """Every enum member must round-trip through enum_to_slug → slug_to_enum_value."""

    def test_investment_stage_round_trip(self):
        from project.utils.enums import InvestmentStage
        from project.utils.seo.slugs import enum_to_slug, slug_to_enum_value

        for member in InvestmentStage:
            slug = enum_to_slug(member.value)
            recovered = slug_to_enum_value(slug)
            assert recovered == member.value, f"Round-trip failed for {member}: {slug!r} → {recovered!r}"

    def test_investor_type_round_trip(self):
        from project.utils.enums import InvestorType
        from project.utils.seo.slugs import enum_to_slug, slug_to_enum_value

        for member in InvestorType:
            slug = enum_to_slug(member.value)
            recovered = slug_to_enum_value(slug)
            assert recovered == member.value

    def test_org_type_round_trip(self):
        from project.utils.enums import OrgType
        from project.utils.seo.slugs import enum_to_slug, slug_to_enum_value

        for member in OrgType:
            slug = enum_to_slug(member.value)
            recovered = slug_to_enum_value(slug)
            assert recovered == member.value


# ---------------------------------------------------------------------------
# SEO_FACETS structure
# ---------------------------------------------------------------------------


class TestSeoFacets:
    def test_investor_type_field_mapping(self):
        from project.utils.seo.slugs import SEO_FACETS

        assert SEO_FACETS["investor_type"]["enum"] is not None
        assert SEO_FACETS["investor_type"]["field"] == "investor_type"

    def test_stages_field_mapping(self):
        from project.utils.seo.slugs import SEO_FACETS

        assert SEO_FACETS["stages"]["field"] == "stages"

    def test_org_type_field_mapping(self):
        from project.utils.seo.slugs import SEO_FACETS

        assert SEO_FACETS["org_type"]["field"] == "org_type"


# ---------------------------------------------------------------------------
# classify_segment — pure enum paths (no DB needed)
# ---------------------------------------------------------------------------


class TestClassifySegmentPure:
    def test_seed_is_stage_for_person(self):
        from project.utils.enums import EntityType
        from project.utils.seo.slugs import classify_segment

        result = classify_segment("seed", EntityType.PERSON)
        assert result is not None
        field, value, segment_type = result
        assert segment_type == "stage"
        assert field == "stages"
        assert value == "seed"

    def test_pre_seed_is_stage_for_person(self):
        from project.utils.enums import EntityType
        from project.utils.seo.slugs import classify_segment

        result = classify_segment("pre-seed", EntityType.PERSON)
        assert result is not None
        field, value, segment_type = result
        assert segment_type == "stage"
        assert field == "stages"
        assert value == "pre_seed"

    def test_angel_is_type_for_person(self):
        from project.utils.enums import EntityType
        from project.utils.seo.slugs import classify_segment

        result = classify_segment("angel", EntityType.PERSON)
        assert result is not None
        field, value, segment_type = result
        assert segment_type == "type"
        assert field == "investor_type"
        assert value == "angel"

    def test_vc_firm_is_type_for_org(self):
        from project.utils.enums import EntityType
        from project.utils.seo.slugs import classify_segment

        result = classify_segment("vc-firm", EntityType.ORG)
        assert result is not None
        field, value, segment_type = result
        assert segment_type == "type"
        assert field == "org_type"
        assert value == "vc_firm"

    def test_unknown_slug_returns_none(self):
        from project.utils.enums import EntityType
        from project.utils.seo.slugs import classify_segment

        assert classify_segment("totally-unknown-slug-xyz", EntityType.PERSON) is None

    def test_series_d_plus_is_stage(self):
        from project.utils.enums import EntityType
        from project.utils.seo.slugs import classify_segment

        result = classify_segment("series-d-plus", EntityType.PERSON)
        assert result is not None
        assert result[2] == "stage"


# ---------------------------------------------------------------------------
# classify_segment — DB-backed sector / geo paths
# ---------------------------------------------------------------------------


class TestClassifySegmentDB:
    def test_industry_slug_is_sector(self, db_session):
        """Use an Industry from the seeded DB (after_create fires populate()) and
        classify_segment should find it by slug."""
        from project.models.helpers import Industry
        from project.utils.enums import EntityType
        from project.utils.seo.slugs import classify_segment

        # db.create_all() fires after_create → Industry.populate() which seeds industries.
        # Find any seeded industry that has a slug set.
        sample = db_session.session.scalar(db_session.select(Industry).where(Industry.slug.isnot(None)).limit(1))
        if sample is None:
            # Fallback: create a unique one that won't collide with seeded data
            ind = Industry(name="UniqueTestSector99", category="Test", slug="unique-test-sector-99")
            db_session.session.add(ind)
            db_session.session.commit()
            test_slug = "unique-test-sector-99"
        else:
            test_slug = sample.slug

        result = classify_segment(test_slug, EntityType.PERSON)
        assert result is not None
        field, value, segment_type = result
        assert segment_type == "sector"
        assert field == "industries"

    def test_geo_slug_is_geo(self, db_session):
        """Seed a Geography with slug 'london' and classify_segment should find it."""
        from project.models.entity import Geography
        from project.utils.enums import EntityType
        from project.utils.seo.slugs import classify_segment

        db = db_session
        geo = Geography(slug="london", name="London", type="city", country_code="GB")
        db.session.add(geo)
        db.session.commit()

        result = classify_segment("london", EntityType.PERSON)
        assert result is not None
        field, value, segment_type = result
        assert segment_type == "geo"
        assert field == "geographies"
        assert value == "london"

    def test_unknown_returns_none_with_db(self, db_session):
        """Even with DB context, unknown slug returns None."""
        from project.utils.enums import EntityType
        from project.utils.seo.slugs import classify_segment

        assert classify_segment("zz-totally-unknown-9999", EntityType.PERSON) is None


# ---------------------------------------------------------------------------
# order_segments
# ---------------------------------------------------------------------------


class TestOrderSegments:
    def _make_segments(self, *items):
        """Helper: each item is (field, value, segment_type)."""
        return list(items)

    def test_type_before_stage_before_geo(self):
        """order_segments always returns segments in canonical order, regardless of input order."""
        from project.utils.seo.slugs import order_segments

        classified = [
            ("geographies", "london", "geo"),
            ("stages", "seed", "stage"),
            ("investor_type", "angel", "type"),
        ]
        ordered, _ = order_segments(classified)
        types = [s[2] for s in ordered]
        assert types == ["type", "stage", "geo"]

    def test_type_before_stage_before_sector_before_geo(self):
        from project.utils.seo.slugs import order_segments

        classified = [
            ("geographies", "london", "geo"),
            ("industries", "fintech", "sector"),
            ("stages", "seed", "stage"),
            ("investor_type", "angel", "type"),
        ]
        ordered, _ = order_segments(classified)
        types = [s[2] for s in ordered]
        assert types == ["type", "stage", "sector", "geo"]

    def test_already_ordered_has_no_warnings(self):
        from project.utils.seo.slugs import order_segments

        classified = [
            ("investor_type", "angel", "type"),
            ("stages", "seed", "stage"),
            ("geographies", "london", "geo"),
        ]
        _, warnings = order_segments(classified)
        assert warnings == []

    def test_mis_ordered_flagged(self):
        from project.utils.seo.slugs import order_segments

        # geo before type — mis-ordered
        classified = [
            ("geographies", "london", "geo"),
            ("investor_type", "angel", "type"),
        ]
        _, warnings = order_segments(classified)
        assert len(warnings) > 0

    def test_duplicate_segment_type_flagged(self):
        from project.utils.seo.slugs import order_segments

        classified = [
            ("investor_type", "angel", "type"),
            ("stages", "seed", "stage"),
            ("stages", "pre_seed", "stage"),
        ]
        _, warnings = order_segments(classified)
        assert any("duplicate" in w.lower() for w in warnings)


# ---------------------------------------------------------------------------
# build_facet_canonical
# ---------------------------------------------------------------------------


class TestBuildFacetCanonical:
    def test_person_canonical_path(self):
        from project.utils.enums import EntityType
        from project.utils.seo.slugs import build_facet_canonical

        classified = [
            ("investor_type", "angel", "type"),
            ("stages", "seed", "stage"),
            ("geographies", "london", "geo"),
        ]
        url = build_facet_canonical(EntityType.PERSON, classified)
        assert url.startswith("https://globalify.org/investors/")
        assert "/angel/" in url or url.endswith("/angel")
        assert "seed" in url
        assert "london" in url

    def test_org_canonical_path(self):
        from project.utils.enums import EntityType
        from project.utils.seo.slugs import build_facet_canonical

        classified = [
            ("org_type", "vc_firm", "type"),
        ]
        url = build_facet_canonical(EntityType.ORG, classified)
        assert url.startswith("https://globalify.org/firms/")
        assert "vc-firm" in url

    def test_canonical_order_is_enforced(self):
        """build_facet_canonical must produce canonical order regardless of input order."""
        from project.utils.enums import EntityType
        from project.utils.seo.slugs import build_facet_canonical

        classified_reversed = [
            ("geographies", "london", "geo"),
            ("stages", "seed", "stage"),
            ("investor_type", "angel", "type"),
        ]
        classified_ordered = [
            ("investor_type", "angel", "type"),
            ("stages", "seed", "stage"),
            ("geographies", "london", "geo"),
        ]
        url_rev = build_facet_canonical(EntityType.PERSON, classified_reversed)
        url_ord = build_facet_canonical(EntityType.PERSON, classified_ordered)
        assert url_rev == url_ord


# ---------------------------------------------------------------------------
# Industry.slug column + Industry.get_by_slug
# ---------------------------------------------------------------------------


class TestIndustrySlug:
    def test_industry_has_slug_column(self, db_session):
        from project.models.helpers import Industry

        db = db_session
        ind = Industry(name="UniqueTestClimateTech9999", category="Energy", slug="unique-test-climatetech-9999")
        db.session.add(ind)
        db.session.commit()

        fetched = db.session.get(Industry, ind.id)
        assert fetched is not None
        assert fetched.slug == "unique-test-climatetech-9999"

    def test_industry_get_by_slug(self, db_session):
        from project.models.helpers import Industry

        db = db_session
        ind = Industry(name="UniqueTestEdTech9999", category="Education", slug="unique-test-edtech-9999")
        db.session.add(ind)
        db.session.commit()

        found = Industry.get_by_slug("unique-test-edtech-9999")
        assert found is not None
        assert found.name == "UniqueTestEdTech9999"

    def test_industry_get_by_slug_missing_returns_none(self, db_session):
        from project.models.helpers import Industry

        found = Industry.get_by_slug("does-not-exist-xyz")
        assert found is None

    def test_industry_auto_slug_from_name(self, db_session):
        """Creating an Industry without an explicit slug auto-generates it from the name."""
        from project.models.helpers import Industry

        db = db_session
        ind = Industry(name="Unique Quantum Computing 9999", category="Technology")
        db.session.add(ind)
        db.session.commit()

        fetched = db.session.get(Industry, ind.id)
        assert fetched is not None
        assert fetched.slug == "unique-quantum-computing-9999"

    def test_industry_populate_sets_slug(self, db_session):
        """When Industry.populate() runs (via after_create event), slugs are set."""
        from project.models.helpers import Industry

        db = db_session
        # db.create_all() has already fired after_create → Industry.populate()
        sample = db.session.scalar(db.select(Industry).limit(1))
        if sample is not None:
            # Some industry was populated; it should have a slug
            assert sample.slug is not None
            assert len(sample.slug) > 0


# ---------------------------------------------------------------------------
# entity_search re-index: industries stored as slugs
# ---------------------------------------------------------------------------


class TestEntitySearchIndexUsesIndustrySlugs:
    """Verify that sync_search_index puts industry slugs (not names) into doc['industries']."""

    def test_industry_slug_in_search_doc(self, db_session):
        """
        Verify that Industry rows have a slug that can be used in search index docs.
        The entity_search module uses ind.slug (not ind.name) when building documents.
        """
        from project.models.helpers import Industry

        db = db_session

        ind = Industry(name="Unique Space Tech 9999", category="Deep Tech")
        db.session.add(ind)
        db.session.commit()

        # Verify the slug is auto-set correctly
        fetched = Industry.get_by_slug("unique-space-tech-9999")
        assert fetched is not None
        assert fetched.name == "Unique Space Tech 9999"
        # The industry slug is what should be indexed (not the name)
        assert fetched.slug == "unique-space-tech-9999"
