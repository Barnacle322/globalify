"""Collector base: NormalizedRecord, CollectStats, Collector ABC, REGISTRY."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass

from ..utils.enums import EntityType

log = logging.getLogger(__name__)

REGISTRY: dict[str, type[Collector]] = {}


def register(cls: type[Collector]) -> type[Collector]:
    REGISTRY[cls.name] = cls
    return cls


@dataclass
class NormalizedRecord:
    entity_type: EntityType
    source_id: str
    name: str
    website: str | None = None
    email: str | None = None
    source_url: str | None = None
    extra: dict | None = None


@dataclass
class CollectStats:
    created: int = 0
    updated: int = 0
    skipped: int = 0


class Collector(ABC):
    name: str

    @abstractmethod
    def fetch(self, limit: int) -> Iterable: ...

    @abstractmethod
    def parse(self, raw) -> NormalizedRecord | None: ...

    def run(self, limit: int = 50, dry_run: bool = False) -> CollectStats:
        from ..extensions import db
        from ..models.entity import Organization, Person

        stats = CollectStats()
        touched: set[tuple[EntityType, int]] = set()

        for raw in self.fetch(limit):
            record = self.parse(raw)
            if record is None:
                stats.skipped += 1
                continue

            if dry_run:
                stats.created += 1  # count as would-be created for dry_run reporting
                continue

            defaults: dict = {}
            if record.website:
                defaults["website"] = record.website
            if record.email:
                defaults["email"] = record.email
            if record.source_url:
                defaults["source_url"] = record.source_url
            if record.extra:
                defaults.update(record.extra)

            if record.entity_type == EntityType.ORG:
                entity, created = Organization.upsert_from_source(
                    self.name, record.source_id, name=record.name, defaults=defaults or None
                )
            else:
                entity, created = Person.upsert_from_source(
                    self.name, record.source_id, name=record.name, defaults=defaults or None
                )

            if created:
                stats.created += 1
            else:
                stats.updated += 1

            touched.add((record.entity_type, entity.id))

        if not dry_run:
            db.session.commit()
            from ..models import entity_search as _es

            for et, eid in touched:
                try:
                    _es.sync_one(et, eid)
                except Exception:
                    log.warning("Typesense sync failed for %s:%s — DB write preserved", et, eid)

        return stats
