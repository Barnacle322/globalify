# Phase 6 — Automated Data Collectors (public-domain sources)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** Build the pipeline that grows the directory automatically from open/public-domain sources — a collector framework with source-provenance + idempotent upsert into the entity model, and a concrete **SEC EDGAR** collector (public domain, no API key). This is the freshness/coverage engine the SEO strategy depends on.

**Architecture:** A `collectors/` package with an abstract `Collector` (fetch → parse → normalize → upsert → sync). Entities gain provenance columns (`source`, `source_id`, `source_url`, `last_synced_at`) with a unique `(source, source_id)`; an idempotent `upsert_from_source` finds-or-creates and updates WITHOUT clobbering claimed/edited records (`user_id` set ⇒ a human owns it ⇒ don't overwrite). A `flask collect <source> [--limit N] [--dry-run]` CLI runs a collector and re-syncs Typesense for touched entities. Collectors are polite (config `User-Agent`, rate-limited) and **fixture-tested** — no live network in CI. Design reference: master spec **§8 (data collectors)** + `docs/pivot-research.md`.

**Tech Stack:** Flask CLI, SQLAlchemy/Alembic, `requests`, SEC EDGAR (submissions + full-text-search JSON APIs), Typesense sync.

## Global Constraints

- **Branch:** `revamp/pivot-design`. Never `main`.
- **Public-domain / openly-licensed sources only.** SEC EDGAR is US-government public domain. Be polite: a descriptive `User-Agent` with contact (SEC requires it), rate-limit, incremental. NO scraping of TOS-restricted/proprietary sites.
- **Idempotent + non-destructive:** upsert keyed on `(source, source_id)`; re-running a collector must NOT duplicate rows and must NOT overwrite a CLAIMED entity (`user_id` set) or human-edited fields. New rows are `is_public=True`, slugged via the existing `set_slug`.
- **No live network in tests:** collectors are tested against committed fixtures (a saved real EDGAR JSON response). The live fetch path is exercised only by `flask collect` manually. `pytest`/CI must pass offline.
- **Verification gate (every task):** `FLASK_ENV=testing SECRET_KEY=x uv run pytest` green; `uv run ruff check . && uv run ruff format --check .` clean (`target-version=py313`; parenthesized `except (A, B):`); app imports + `db.create_all`.
- **Commits:** conventional subject; trailer `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

## Task 1: Collector framework + provenance + idempotent upsert + CLI

**Files:** `models/entity.py` (provenance cols + `upsert_from_source` on `Person` + `Organization`) + Alembic, `src/project/collectors/__init__.py` + `base.py` (+ a `sample.py` fixture collector to prove the pipeline), `src/project/__init__.py` (the `collect` CLI), `tests/test_collectors.py`.

- [ ] **Step 1:** Add to BOTH `Person` and `Organization`: `source: Mapped[str | None]` (default None), `source_id: Mapped[str | None]` (default None), `source_url: Mapped[str | None]` (default None), `last_synced_at: Mapped[datetime | None]` (default None), and a table `UniqueConstraint("source", "source_id", name="uq_<table>_source")`. Alembic revision (chain off head `h2i3j4k5l6m7`). (Nullable so existing/seed/manual rows are unaffected; the unique constraint only bites when both are set — confirm NULLs don't collide on your DB, which they don't in Postgres/sqlite.)
- [ ] **Step 2:** `Organization.upsert_from_source(source, source_id, *, name, defaults: dict) -> tuple[Organization, bool]` (and the `Person` analogue): look up by `(source, source_id)`; if found → if `org.user_id` is set (claimed) leave content alone (only bump `last_synced_at`); else update the provided mutable fields (name/website/etc. that are still empty or source-owned) — do NOT clobber a non-null human value unless it's still source-owned; set `last_synced_at`. If not found → create with `is_public=True`, `set_slug()`, provenance set. Return `(entity, created)`. Idempotent: a second identical call updates in place, returns `created=False`, no duplicate.
- [ ] **Step 3:** `collectors/base.py`: a `@dataclass NormalizedRecord` (entity_type: EntityType, source_id: str, name: str, website/email/source_url/extra: dict|None) and `class Collector(ABC)` with `name: str`, `fetch(self, limit) -> Iterable[raw]`, `parse(self, raw) -> NormalizedRecord | None`, and a concrete `run(self, limit, dry_run) -> CollectStats` that iterates fetch→parse→ (dry_run: count only | else upsert_from_source + collect touched ids), then if not dry_run syncs Typesense for the touched entities (`entity_search.sync_one(...)`), returning stats (created/updated/skipped). A `REGISTRY: dict[str, type[Collector]]`.
- [ ] **Step 4:** `collectors/sample.py`: a trivial `SampleCollector` whose `fetch` yields a few in-memory dicts (no network) → proves the pipeline end-to-end (used by tests + a smoke `flask collect sample`). Register it.
- [ ] **Step 5:** `collect` CLI in `__init__.py`: `flask collect <source> [--limit N] [--dry-run]` → resolve from `REGISTRY`, run, echo the stats. (Mirror the existing `setup`/`reindex` CLI style.)
- [ ] **Step 6:** `tests/test_collectors.py`: `upsert_from_source` creates then updates-in-place (no dup, `created` flips True→False); a claimed entity (`user_id` set) is NOT content-overwritten on re-collect (only `last_synced_at` bumps); `SampleCollector.run(dry_run=True)` writes nothing; `run(dry_run=False)` creates the sample entities + sets provenance + is idempotent on a second run. (Typesense sync mocked/guarded — no Docker needed.) Write tests first, run (fail), implement, green.
- [ ] **Step 7: Gate. Commit** (`feat(collectors): framework + source-provenance + idempotent upsert + collect CLI`).

---

## Task 2: SEC EDGAR collector

**Files:** `config.py` (`edgar_user_agent`), `src/project/collectors/edgar.py`, `tests/fixtures/edgar_*.json` (committed real sample), `tests/test_collectors_edgar.py`.

- [ ] **Step 1:** config: `edgar_user_agent: str` (alias `_EDGAR_USER_AGENT`, default `"Globalify Directory contact@globalify.xyz"`) — SEC requires a descriptive UA with contact. (No secret; just identification.)
- [ ] **Step 2:** `collectors/edgar.py` — `class EdgarCollector(Collector)` (`name="edgar"`):
  - `fetch(limit)`: GET the EDGAR full-text search API for Form D filings — `https://efts.sec.gov/LATEST/search-index?q=%22venture+capital%22&forms=D` (or the documented `https://www.sec.gov/cgi-bin/...`; pick the stable JSON one) with the `User-Agent` header from config + a polite delay; yield up to `limit` hits. Wrap in try/except → on network error log + yield nothing (never crash the CLI).
  - `parse(hit)`: extract the issuer/filer display name + CIK from a hit; build a `NormalizedRecord(entity_type=ORG, source_id=<CIK>, name=<issuer>, source_url=<the EDGAR filing URL>)`. Skip hits with no usable name/CIK (return None). Normalize the name (strip, title-case if SCREAMING).
  - Rely on the base `run()` for upsert + sync.
- [ ] **Step 3:** Commit a REAL sample response to `tests/fixtures/edgar_formd.json` (a trimmed actual EDGAR FTS JSON — a handful of hits). The test feeds this fixture to `parse`/`run` (monkeypatch `fetch` to read the fixture, NOT the network).
- [ ] **Step 4:** `tests/test_collectors_edgar.py`: `parse` maps a fixture hit → a correct `NormalizedRecord` (CIK as source_id, issuer as name, the filing URL); a hit missing a name/CIK → None (skipped); `EdgarCollector.run(dry_run=False)` over the fixture creates `Organization`s with `source="edgar"` + the CIK as `source_id`, and a second run is idempotent (updates, no dups). NO network (monkeypatch `fetch`). Write tests first, run (fail), implement, green.
- [ ] **Step 5:** Register `EdgarCollector` in the `REGISTRY`. Confirm `flask collect edgar --dry-run --limit 5` resolves (offline dry-run counts via the fixture path OR document that the live run needs network).
- [ ] **Step 6: Gate. Commit** (`feat(collectors): SEC EDGAR Form D collector (fixture-tested, polite UA)`).

---

## Self-Review

**Coverage (spec §8):** collector framework + provenance + idempotent non-destructive upsert + CLI (T1) · SEC EDGAR concrete collector, fixture-tested + polite (T2). Proves the end-to-end pipeline (fetch→normalize→upsert→search-sync) with a real open source.

**Deferred (documented, not silently dropped):** additional sources (Crunchbase Open Data Map, OpenCorporates, 13F institutional managers, national company registries) — each a new `Collector` subclass behind the same framework; a scheduled/cron runner (the CLI is invocable from any scheduler now); entity de-duplication/merge across sources (same fund from EDGAR + another source) — a later reconciliation pass keyed on name+domain; richer facet extraction (industries/stages/geographies) from filings — best-effort minimal now.

**Risk control:** public-domain source only (SEC), polite identified UA + rate-limit, fixture-tested so CI is offline + deterministic; upsert is idempotent and refuses to overwrite claimed/human-edited entities (the claim work from Phase 5 is protected); new rows are public + slugged via the existing helper; collectors never run automatically — only via the explicit `flask collect` CLI.
