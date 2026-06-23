# App-side Gemini Embeddings (real semantic/hybrid search)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** Replace the (broken + server-heavy) Typesense auto-embedder with **application-side** embeddings using Google `gemini-embedding-001` on the **free Gemini API tier**, indexed into Typesense as raw vectors, with hybrid (keyword+vector) search and a graceful **keyword-only fallback**. Real semantic search, no model running on our server, swappable later.

**Why app-side:** Typesense's built-in Gemini-API-key embedder only supports the old `embedding-gecko-001`; the good models need the paid GCP Vertex service-account path. Computing embeddings in Flask (free Gemini API key, no billing) and indexing them as a plain `float[]` field sidesteps that entirely and unlocks the best model for $0.

**Architecture:** A `utils/embeddings/` client calls Gemini, returning L2-normalized 768-dim vectors (MRL-truncated) with `task_type` asymmetry (RETRIEVAL_DOCUMENT for docs, RETRIEVAL_QUERY for queries). The Typesense `embedding` field becomes `float[]`+`num_dim` (no `embed` config). At index time the doc carries its vector; at query time we embed the query and pass an explicit `vector_query` for hybrid. Everything is **provider-gated**: default `none` = keyword-only (zero embedding, lightest); `gemini` = app-side semantic. Any embed failure/rate-limit degrades to keyword-only.

**Tech Stack:** Flask, `google-genai` SDK (or REST fallback), Typesense v30 (external vectors + hybrid `vector_query`), pydantic-settings.

## Global Constraints

- **Branch:** `feat/gemini-embeddings` (off `main`). Never commit to `main`.
- **Free-tier-first + fail-safe:** the embedder is gated on `EMBEDDING_PROVIDER`. Default `none` → NO embedding field in the schema, NO vector query, pure keyword search (this is also the weak-server-safe default). `gemini` requires `GEMINI_API_KEY`. ANY embed error / 429 / missing key at runtime → log + fall back to keyword-only (never raise into a request or lose a DB write).
- **Model contract:** `gemini-embedding-001`, `output_dimensionality=768`, **L2-normalize app-side** (Gemini returns unnormalized vectors when output_dimensionality≠3072), `task_type=RETRIEVAL_DOCUMENT` for indexing and `RETRIEVAL_QUERY` for queries. Dimension is configurable (`EMBEDDING_DIM`, default 768) and is the `num_dim` of the Typesense field — they MUST match.
- **No live network in tests:** mock the Gemini client/HTTP; the suite + CI pass offline with no key. Live embedding is verified manually once a key is present.
- **Remove the dead paths:** delete the `minilm` / `google/text-embedding-004` `_build_embed_config` auto-embed config and the `embedding:([], …)` auto-embed query (both the `entity_search.get_search` copy and the `SearchBuilder.search` copy).
- **Verification gate (every task):** `FLASK_ENV=testing SECRET_KEY=x uv run pytest` green offline; `uv run ruff check . && uv run ruff format --check .` clean (`target-version=py313`); app imports + `db.create_all`.
- **Commits:** conventional subject; trailer `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

## Task 1: Gemini embedding client + config

**Files:** `pyproject.toml` (+`google-genai`), `src/project/config.py` (embedding settings), `src/project/utils/embeddings/__init__.py` + `gemini.py`, `tests/test_embeddings.py`.

- [ ] **Step 1:** `uv add google-genai` (the official unified SDK). If it doesn't resolve on 3.14, implement via `requests` against `https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:batchEmbedContents?key=…` and NOTE the choice.
- [ ] **Step 2:** `config.py` — add `embedding_provider: str` (alias `_EMBEDDING_PROVIDER`, default `"none"`; values none|gemini), `embedding_model: str` (alias `_EMBEDDING_MODEL`, default `"gemini-embedding-001"`), `embedding_dim: int` (alias `_EMBEDDING_DIM`, default `768`), and reuse `GEMINI_API_KEY` (add `gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")`). Add `embeddings_enabled` property → `embedding_provider == "gemini" and bool(gemini_api_key)`.
- [ ] **Step 3:** `utils/embeddings/gemini.py`:
  - `embed_texts(texts: list[str], *, task_type: str) -> list[list[float]] | None` — if `not settings.embeddings_enabled` return `None`; else lazily build a `genai.Client(api_key=…)`, call embed for the batch with `model=settings.embedding_model`, `config={"task_type": task_type, "output_dimensionality": settings.embedding_dim}`, then **L2-normalize** each returned vector to unit length; return the list of vectors. Batch internally (chunks of ≤100). On ANY exception / rate-limit → `current_app.logger.warning(...)` + return `None` (the fallback signal). Never raise.
  - `embed_query(text) -> list[float] | None` = `embed_texts([text], task_type="RETRIEVAL_QUERY")` → first vector or None.
  - `embed_documents(texts) -> list[list[float]] | None` = `embed_texts(texts, task_type="RETRIEVAL_DOCUMENT")`.
  - A pure `_l2_normalize(vec) -> list[float]` helper (guard the zero-vector case).
- [ ] **Step 4:** `tests/test_embeddings.py` (mock the SDK/HTTP — NO network): provider `none` → `embed_texts` returns None, makes no client call; with provider gemini + key + a monkeypatched client returning known raw vectors → `embed_documents` returns **L2-normalized** vectors (assert norm≈1.0) and was called with `task_type=RETRIEVAL_DOCUMENT` + `output_dimensionality=768`; `embed_query` uses `RETRIEVAL_QUERY`; a client that raises → returns None (fallback); `_l2_normalize` math (incl. zero vector). Write tests first, run (fail), implement, green.
- [ ] **Step 5: Gate. Commit** (`feat(search): app-side Gemini embedding client (free-tier, normalized, task-typed)`).

---

## Task 2: Wire embeddings into Typesense schema + index + hybrid query (+ remove dead auto-embed)

**Files:** `src/project/models/entity_search.py` (schema, `_build_entity_doc`/sync, `get_search`), `src/project/utils/typesense_helpers/typesense_search.py` (the `SearchBuilder.search` auto-embed branch), `tests/test_entity_search*.py` (extend; Docker-gated e2e where present), `docs/search-embeddings.md`.

- [ ] **Step 1: Schema.** Replace `_build_embed_config()` usage: when `settings.embeddings_enabled`, the `embedding` field is `{"name":"embedding","type":"float[]","num_dim": settings.embedding_dim}` (NO `embed` key). When NOT enabled, **omit the embedding field entirely** (keyword-only collection). Delete `_build_embed_config`.
- [ ] **Step 2: Index.** In `sync_search_index(recreate=…)` and `sync_one(...)`: when `embeddings_enabled`, compute document vectors via `embeddings.embed_documents([...])` over the same text the old `embed_from` used (`name, about, headline, industries, geographies` joined) — batch across the docs being synced — and attach `doc["embedding"] = vector` for each. If `embed_documents` returns None (failure/disabled), index the docs WITHOUT an embedding field (keyword-only) and log — never drop the DB-backed doc. (Collectors' `sync_one` path inherits this automatically.)
- [ ] **Step 3: Query (hybrid + fallback).** In `get_search`:
  - Remove `"embedding"` from the keyword `query_by` list (and its weight) — keyword fields only now.
  - When `embeddings_enabled` and there's a query string: `qvec = embeddings.embed_query(query)`; if `qvec` is not None, set `params["vector_query"] = f"embedding:({json.dumps(qvec)}, distance_threshold:{settings.embedding_distance_threshold})"` (add `embedding_distance_threshold: float`, alias `_EMBEDDING_DISTANCE_THRESHOLD`, default `0.30`) and `params["exclude_fields"] = "embedding"`. If `qvec` is None (failure/throttle) OR not enabled → NO vector_query (pure keyword). 
  - Remove the old `if "embedding" in params.get("query_by", ""): vector_query = embedding:([], …)` block.
- [ ] **Step 4:** Mirror-remove the dead `([], …)` auto-embed branch in `SearchBuilder.search` (`typesense_search.py:~98`) so nothing re-injects the auto-embed query.
- [ ] **Step 5:** `docs/search-embeddings.md` — how it works (app-side gemini, free tier, 768-dim normalized, hybrid + fallback), the env vars (`_EMBEDDING_PROVIDER`, `GEMINI_API_KEY`, `_EMBEDDING_DIM`, `_EMBEDDING_DISTANCE_THRESHOLD`), and the "recreate collection + reindex when you change provider/dim" note. Update `.env.example` with the new vars.
- [ ] **Step 6:** Tests: schema HAS the `float[] num_dim` embedding field when enabled and OMITS it when `none` (monkeypatch settings both ways); `get_search` with embeddings enabled + a monkeypatched `embed_query` returning a vector sets a `vector_query` with that vector + `exclude_fields=embedding`; with `embed_query`→None it sets NO vector_query (keyword fallback); with provider none, no embedding in `query_by` and no vector_query. Extend the Docker-gated e2e if present (still runs keyword-only without a key). Offline. Write tests first where practical, green.
- [ ] **Step 7: Gate** (pytest offline green incl. `test_db_metadata_creates_all_tables`, `test_no_url_for_to_unregistered_endpoints`; ruff; import). **Commit** (`feat(search): hybrid Gemini vector search with keyword fallback; drop dead auto-embed`).

---

## Self-Review

**Coverage:** Gemini client (T1) · schema/index/query wiring + dead-path removal (T2). Real semantic+keyword hybrid on the free tier, keyword-only when unconfigured or throttled.

**Live verification (deferred — needs the key):** with a real `GEMINI_API_KEY` + `_EMBEDDING_PROVIDER=gemini`, recreate the collection on Docker Typesense, `flask reindex`, and run semantic/multilingual/typo/exact-name queries to tune `_EMBEDDING_DISTANCE_THRESHOLD` + the keyword/vector balance against real results.

**Deferred:** query-embedding cache (cut free-tier query calls on repeated searches); per-field embedding weighting; alternative providers (OpenAI/Cloudflare-OpenAI-compat) — trivial to add behind the same `EMBEDDING_PROVIDER` switch later.

**Risk control:** provider-gated (default keyword-only = no server load, no key); every embed path fails to keyword-only (no hard failures, no lost DB writes); no live network in tests; dimension/num_dim kept in lockstep; normalization handled app-side (correct cosine); changing provider/dim documented as a recreate+reindex.
