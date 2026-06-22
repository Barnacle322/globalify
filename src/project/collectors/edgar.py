"""SEC EDGAR Form D collector.

Fetches venture-capital Form D filings from the EDGAR full-text search API,
normalises each filer into a NormalizedRecord, and relies on the base run()
for upsert + Typesense sync.

Polite: sends an identified User-Agent per SEC fair-access policy, and
honours a short delay between paginated requests.
"""

from __future__ import annotations

import logging
import re
import time

import requests

from ..config import get_settings
from ..utils.enums import EntityType
from .base import Collector, NormalizedRecord, register

log = logging.getLogger(__name__)

_EDGAR_FTS_URL = "https://efts.sec.gov/LATEST/search-index?q=%22venture+capital%22&forms=D"
_CIK_SUFFIX_RE = re.compile(r"\s*\(CIK\s+\d+\)\s*$", re.IGNORECASE)


def _clean_name(raw: str) -> str:
    """Strip trailing (CIK …) suffix and normalise case."""
    name = _CIK_SUFFIX_RE.sub("", raw).strip()
    if name == name.upper() and name:
        name = name.title()
    return name


@register
class EdgarCollector(Collector):
    name = "edgar"

    def fetch(self, limit: int):
        """GET the EDGAR FTS endpoint and yield up to *limit* hit dicts.

        On any network / HTTP / JSON error, log a warning and yield nothing
        so the CLI never crashes.
        """
        try:
            ua = get_settings().edgar_user_agent
            resp = requests.get(
                _EDGAR_FTS_URL,
                headers={"User-Agent": ua},
                timeout=15,
            )
            if resp.status_code != 200:
                log.warning("EDGAR FTS returned HTTP %s — skipping", resp.status_code)
                return
            data = resp.json()
            hits = data.get("hits", {}).get("hits", [])
            for hit in hits[:limit]:
                yield hit
                if limit > 10:  # polite delay only when paginating
                    time.sleep(0.2)
        except Exception as exc:
            log.warning("EDGAR fetch failed: %s", exc)

    def parse(self, hit) -> NormalizedRecord | None:
        """Extract CIK + issuer name from an EDGAR FTS hit.

        Returns None if either is missing (the base run() counts it as skipped).
        """
        source = hit.get("_source", {})

        # CIK — prefer _source.cik; fall back to stripping it from _id
        cik: str = (source.get("cik") or "").strip()
        if not cik:
            # _id looks like "0001234567-23-000001"; first segment is the CIK
            parts = hit.get("_id", "").split("-")
            cik = parts[0].strip() if parts else ""
        if not cik:
            return None

        display_names: list = source.get("display_names") or []
        raw_name = display_names[0].strip() if display_names else ""
        if not raw_name:
            return None

        name = _clean_name(raw_name)
        if not name:
            return None

        source_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}"
        return NormalizedRecord(
            entity_type=EntityType.ORG,
            source_id=cik,
            name=name,
            source_url=source_url,
        )
