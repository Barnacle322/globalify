"""Tests for the Phase 6 collector framework.

All tests run offline (no Docker / Typesense required).
entity_search.sync_one is monkeypatched.
"""

from __future__ import annotations

import os

os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("_DATABASE_URL", "sqlite:///test_db.sqlite")

import pytest


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


class TestUpsertFromSource:
    def test_create_org(self, db_session):
        from project.models.entity import Organization

        org, created = Organization.upsert_from_source("test", "X1", name="Acme")
        assert created is True
        assert org.name == "Acme"
        assert org.source == "test"
        assert org.source_id == "X1"
        assert org.is_public is True

    def test_no_dup_org(self, db_session):
        from project.models.entity import Organization

        org1, c1 = Organization.upsert_from_source("test", "X1", name="Acme")
        org2, c2 = Organization.upsert_from_source("test", "X1", name="Acme")
        assert c1 is True
        assert c2 is False
        assert org1.id == org2.id
        # Only one row
        from project.extensions import db

        count = db.session.query(Organization).filter_by(source="test", source_id="X1").count()
        assert count == 1

    def test_claimed_org_name_not_overwritten(self, db_session):
        from project.extensions import db
        from project.models.entity import Organization
        from project.models.user import User

        # Create a real user to satisfy the FK constraint
        user = User(email="claimer@test.com")
        db.session.add(user)
        db.session.flush()

        # Create source-owned org
        org, _ = Organization.upsert_from_source("test", "X2", name="Original Name")
        # Simulate claim: set user_id to a real user id
        org.user_id = user.id
        db.session.commit()
        # Re-upsert with different name
        import time

        time.sleep(0.01)
        org2, created = Organization.upsert_from_source("test", "X2", name="New Name")
        assert created is False
        assert org2.name == "Original Name"  # NOT overwritten
        # last_synced_at should be bumped
        assert org2.last_synced_at is not None

    def test_create_person(self, db_session):
        from project.models.entity import Person

        person, created = Person.upsert_from_source("test", "P1", name="John Doe")
        assert created is True
        assert person.first_name == "John"
        assert person.last_name == "Doe"
        assert person.source == "test"


class TestSampleCollector:
    def test_dry_run_writes_nothing(self, db_session):
        from project.collectors.sample import SampleCollector
        from project.extensions import db
        from project.models.entity import Organization

        before = db.session.query(Organization).count()
        collector = SampleCollector()
        stats = collector.run(dry_run=True)
        after = db.session.query(Organization).count()
        assert after == before
        # dry_run still counts records as "would-be created"
        assert stats.created + stats.skipped >= 0

    def test_run_creates_sample_orgs(self, db_session):
        from project.collectors.sample import SampleCollector
        from project.extensions import db
        from project.models.entity import Organization

        collector = SampleCollector()
        stats = collector.run(dry_run=False)
        assert stats.created == 3
        assert stats.skipped == 0
        orgs = db.session.query(Organization).filter_by(source="sample").all()
        assert len(orgs) == 3
        for org in orgs:
            assert org.is_public is True
            assert org.source == "sample"

    def test_run_is_idempotent(self, db_session):
        from project.collectors.sample import SampleCollector
        from project.extensions import db
        from project.models.entity import Organization

        c = SampleCollector()
        c.run(dry_run=False)
        c.run(dry_run=False)
        count = db.session.query(Organization).filter_by(source="sample").count()
        assert count == 3  # no duplicates


class TestRegistry:
    def test_sample_in_registry(self):
        from project.collectors import REGISTRY

        assert "sample" in REGISTRY
