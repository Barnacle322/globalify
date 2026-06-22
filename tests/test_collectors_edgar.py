"""Tests for the SEC EDGAR Form D collector.

All tests run fully offline — fetch() is monkeypatched to yield fixture hits.
No Docker / Typesense required (sync_one is also patched via the autouse
fixture below).
"""

from __future__ import annotations

import json
import os

os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("_DATABASE_URL", "sqlite:///test_edgar.sqlite")

from pathlib import Path

import pytest

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "edgar_formd.json"


def _load_fixture_hits() -> list:
    data = json.loads(FIXTURE_PATH.read_text())
    return data["hits"]["hits"]


@pytest.fixture()
def db_session(app):
    from project.extensions import db

    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()


@pytest.fixture(autouse=True)
def _patch_sync_one(monkeypatch):
    """Guard: replace sync_one so no Typesense Docker is needed."""
    import project.models.entity_search as es

    monkeypatch.setattr(es, "sync_one", lambda *a, **kw: None)


# ---------------------------------------------------------------------------
# parse() unit tests — no DB, no network
# ---------------------------------------------------------------------------


class TestEdgarParse:
    def test_normal_hit_returns_record(self):
        from project.collectors.edgar import EdgarCollector

        collector = EdgarCollector()
        hit = {
            "_id": "0001234567-23-000001",
            "_source": {
                "cik": "0001234567",
                "display_names": ["SEQUOIA CAPITAL OPERATIONS LLC (CIK 0001234567)"],
            },
        }
        record = collector.parse(hit)
        assert record is not None
        assert record.source_id == "0001234567"
        # CIK suffix stripped; ALL-CAPS → title-cased
        assert record.name == "Sequoia Capital Operations Llc"
        assert "0001234567" in record.source_url
        assert record.source_url.startswith("https://www.sec.gov")

    def test_mixed_case_name_preserved(self):
        from project.collectors.edgar import EdgarCollector

        collector = EdgarCollector()
        hit = {
            "_id": "0001891234-23-000099",
            "_source": {
                "cik": "0001891234",
                "display_names": ["Andreessen Horowitz Fund VI LP (CIK 0001891234)"],
            },
        }
        record = collector.parse(hit)
        assert record is not None
        # Mixed case → kept as-is (after stripping suffix)
        assert record.name == "Andreessen Horowitz Fund VI LP"

    def test_missing_cik_returns_none(self):
        from project.collectors.edgar import EdgarCollector

        collector = EdgarCollector()
        hit = {
            "_id": "",
            "_source": {
                "cik": "",
                "display_names": ["MISSING CIK FUND LP"],
            },
        }
        result = collector.parse(hit)
        assert result is None

    def test_empty_display_names_returns_none(self):
        from project.collectors.edgar import EdgarCollector

        collector = EdgarCollector()
        hit = {
            "_id": "0002000000-23-000400",
            "_source": {
                "cik": "0002000000",
                "display_names": [],
            },
        }
        result = collector.parse(hit)
        assert result is None

    def test_cik_fallback_from_id(self):
        """When _source.cik is absent, CIK is derived from the _id prefix."""
        from project.collectors.edgar import EdgarCollector

        collector = EdgarCollector()
        hit = {
            "_id": "0009876543-23-000001",
            "_source": {
                "display_names": ["ACME VENTURES LLC (CIK 0009876543)"],
            },
        }
        record = collector.parse(hit)
        assert record is not None
        assert record.source_id == "0009876543"

    def test_entity_type_is_org(self):
        from project.collectors.edgar import EdgarCollector
        from project.utils.enums import EntityType

        collector = EdgarCollector()
        hit = {
            "_id": "0001234567-23-000001",
            "_source": {
                "cik": "0001234567",
                "display_names": ["ACME FUND LP (CIK 0001234567)"],
            },
        }
        record = collector.parse(hit)
        assert record is not None
        assert record.entity_type == EntityType.ORG


# ---------------------------------------------------------------------------
# run() integration tests — DB in-memory, fetch monkeypatched
# ---------------------------------------------------------------------------


class TestEdgarRun:
    @pytest.fixture()
    def _patch_fetch(self, monkeypatch):
        """Replace EdgarCollector.fetch with fixture data (no network)."""
        hits = _load_fixture_hits()

        def _fake_fetch(self, limit: int):
            yield from hits[:limit]

        import project.collectors.edgar as edgar_mod

        monkeypatch.setattr(edgar_mod.EdgarCollector, "fetch", _fake_fetch)

    def test_run_creates_orgs(self, db_session, _patch_fetch):
        from project.collectors.edgar import EdgarCollector
        from project.extensions import db
        from project.models.entity import Organization

        collector = EdgarCollector()
        stats = collector.run(dry_run=False)

        # Fixture has 6 hits: 4 valid + 1 missing CIK + 1 empty display_names
        assert stats.created == 4
        assert stats.skipped == 2

        orgs = db.session.query(Organization).filter_by(source="edgar").all()
        assert len(orgs) == 4
        for org in orgs:
            assert org.is_public is True
            assert org.source == "edgar"
            assert org.source_id is not None

    def test_run_source_id_is_cik(self, db_session, _patch_fetch):
        from project.collectors.edgar import EdgarCollector
        from project.extensions import db
        from project.models.entity import Organization

        EdgarCollector().run(dry_run=False)
        org = db.session.query(Organization).filter_by(source="edgar", source_id="0001234567").one()
        assert org.name == "Sequoia Capital Operations Llc"
        assert "0001234567" in org.source_url

    def test_run_is_idempotent(self, db_session, _patch_fetch):
        from project.collectors.edgar import EdgarCollector
        from project.extensions import db
        from project.models.entity import Organization

        c = EdgarCollector()
        c.run(dry_run=False)
        c.run(dry_run=False)

        count = db.session.query(Organization).filter_by(source="edgar").count()
        assert count == 4  # no duplicates

    def test_dry_run_writes_nothing(self, db_session, _patch_fetch):
        from project.collectors.edgar import EdgarCollector
        from project.extensions import db
        from project.models.entity import Organization

        before = db.session.query(Organization).filter_by(source="edgar").count()
        stats = EdgarCollector().run(dry_run=True)
        after = db.session.query(Organization).filter_by(source="edgar").count()

        assert after == before
        # dry_run counts would-be creates (valid hits only)
        assert stats.created == 4

    def test_run_with_limit(self, db_session, _patch_fetch):
        from project.collectors.edgar import EdgarCollector
        from project.extensions import db
        from project.models.entity import Organization

        EdgarCollector().run(limit=2, dry_run=False)
        count = db.session.query(Organization).filter_by(source="edgar").count()
        assert count == 2


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class TestEdgarRegistry:
    def test_edgar_in_registry(self):
        from project.collectors import REGISTRY

        assert "edgar" in REGISTRY

    def test_registry_returns_edgar_collector_class(self):
        from project.collectors import REGISTRY
        from project.collectors.edgar import EdgarCollector

        assert REGISTRY["edgar"] is EdgarCollector
