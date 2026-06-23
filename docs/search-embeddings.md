# Search Embeddings: App-Side Gemini + Keyword Fallback

## How it works

Globalify uses a **hybrid search** strategy: keyword scoring (BM25 via Typesense) is
combined with semantic vector search when embeddings are configured.

### Embedding generation

Vectors are generated **app-side** using the Gemini API
(`gemini-embedding-001`, 768 dimensions by default, L2-normalised) before
being pushed to Typesense.  Typesense stores the vectors as a plain `float[]`
field and uses them for cosine-similarity ranking via its external-vector query
path — it does **not** call any model itself.

This approach:
- Works on the Gemini free tier (no billing required to try).
- Produces 768-dim normalised vectors suitable for cosine similarity.
- Is provider-agnostic: the `_EMBEDDING_PROVIDER` switch controls which
  client is used; adding a new provider is a one-file change in
  `utils/embeddings/`.

### Keyword fallback

The embedding field is **optional at every level**:

| Condition | Behaviour |
|-----------|-----------|
| `_EMBEDDING_PROVIDER=none` (default) | Collection has no `embedding` field; all searches are keyword-only. |
| Provider enabled but API call fails (quota, network) | `embed_query` / `embed_documents` return `None`; search falls back to keyword-only for that request / batch without dropping any document. |
| Provider enabled, API succeeds | Hybrid: keyword fields ranked by BM25 + cosine similarity via `vector_query`; the raw embedding vector is excluded from returned documents (`exclude_fields=embedding`). |

### Index flow

`sync_search_index(recreate=True)` or `flask setup`:

1. Builds the Typesense collection schema — includes the `embedding float[]`
   field only when `embeddings_enabled` is True.
2. For each batch of Person / Organization rows, builds the document dict then
   calls `embeddings.embed_documents([joined_text, ...])` in a single batch
   (one API call per 100 docs).
3. Attaches `doc["embedding"] = vector` for each doc, then upserts to
   Typesense.

`sync_one(entity_type, entity_id)` follows the same logic for single-entity
updates (e.g. profile saves).

The text fed to the embedding model is the same fields Typesense previously
used for auto-embedding: `name`, `about`, `headline`, `industries`,
`geographies` — joined with spaces.

### Query flow

`get_search(query, ...)`:

1. Builds keyword `query_by` over `name, about, headline, org_name,
   person_names, industries` with BM25 weights.
2. If `embeddings_enabled` and `query` is non-empty / non-wildcard:
   - Calls `embeddings.embed_query(query)`.
   - If a vector is returned, adds `vector_query` to the Typesense params for
     hybrid ranking.
3. If `embed_query` returns `None` (disabled / failure): no `vector_query` is
   added — pure keyword search.

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `_EMBEDDING_PROVIDER` | `none` | Set to `gemini` to enable semantic search. |
| `GEMINI_API_KEY` | _(unset)_ | Required when provider is `gemini`. |
| `_EMBEDDING_MODEL` | `gemini-embedding-001` | Gemini model name. |
| `_EMBEDDING_DIM` | `768` | Output vector dimensions. |
| `_EMBEDDING_DISTANCE_THRESHOLD` | `0.55` | Max cosine distance for a vector match (lower = stricter). Calibrated live against `gemini-embedding-001` (relevant matches land ~0.36–0.45); `0.30` was too strict. Tune per corpus. |

## Changing provider or dimension

Typesense collection schemas are immutable once created.  After changing
`_EMBEDDING_PROVIDER` or `_EMBEDDING_DIM`:

1. Recreate the collection and reindex all entities:
   ```bash
   flask setup
   ```
   Or from a Python shell:
   ```python
   from project.models.entity_search import sync_search_index
   sync_search_index(recreate=True)
   ```
2. Adjust `_EMBEDDING_DISTANCE_THRESHOLD` to taste — run a few representative
   queries against the new vectors and tune until precision/recall feels right.
