"""Sample collector: in-memory fake data to prove the pipeline."""

from __future__ import annotations

from ..utils.enums import EntityType
from .base import Collector, NormalizedRecord, register

_SAMPLE_DATA = [
    {"id": "sample-001", "name": "Sequoia Capital Demo", "website": "https://sequoia.example.com"},
    {"id": "sample-002", "name": "Benchmark Demo", "website": "https://benchmark.example.com"},
    {"id": "sample-003", "name": "Andreessen Horowitz Demo", "website": "https://a16z.example.com"},
]


@register
class SampleCollector(Collector):
    name = "sample"

    def fetch(self, limit: int):
        return _SAMPLE_DATA[:limit]

    def parse(self, raw) -> NormalizedRecord | None:
        return NormalizedRecord(
            entity_type=EntityType.ORG,
            source_id=raw["id"],
            name=raw["name"],
            website=raw.get("website"),
        )
