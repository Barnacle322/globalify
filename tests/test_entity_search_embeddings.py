"""Tests for embedding integration in entity_search.py.

Exercises:
  a) Schema: with embeddings_enabled=True, the schema includes a float[] embedding
     field with the correct num_dim and NO 'embed' key.
     With disabled, no embedding field is present at all.
  b) Query — hybrid: embed_query returns a vector → vector_query is set in params
     and embedding is NOT in query_by.
  c) Query — fallback: embed_query returns None → no vector_query in params.
  d) Query — disabled: embeddings_enabled=False → no vector_query, no embedding in query_by.

All tests run offline — no Typesense or Gemini network required.
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings(*, provider="none", key=None, dim=768, threshold=0.30):
    """Build a Settings instance with embedding fields configured."""
    from project.config import Settings

    kwargs: dict = {"SECRET_KEY": "test", "FLASK_ENV": "testing"}
    kwargs["_EMBEDDING_PROVIDER"] = provider
    kwargs["_EMBEDDING_DIM"] = dim
    kwargs["_EMBEDDING_DISTANCE_THRESHOLD"] = threshold
    if key is not None:
        kwargs["GEMINI_API_KEY"] = key
    return Settings(**kwargs)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def app_ctx(app):
    with app.app_context():
        yield app


# ---------------------------------------------------------------------------
# (a) Schema tests
# ---------------------------------------------------------------------------


class TestSchema:
    def test_schema_has_embedding_field_when_enabled(self, app_ctx, monkeypatch):
        """When embeddings_enabled=True, schema includes float[] embedding with num_dim."""
        import project.models.entity_search as es_mod

        enabled_settings = _make_settings(provider="gemini", key="fake-key", dim=768)
        monkeypatch.setattr(es_mod, "get_settings", lambda: enabled_settings)

        schema = es_mod._build_schema()
        embedding_fields = [f for f in schema["fields"] if f["name"] == "embedding"]
        assert len(embedding_fields) == 1, "Expected exactly one embedding field"
        emb = embedding_fields[0]
        assert emb["type"] == "float[]"
        assert emb["num_dim"] == 768
        assert "embed" not in emb, "embedding field must NOT have an 'embed' key (app-side, not auto-embed)"

    def test_schema_no_embedding_field_when_disabled(self, app_ctx, monkeypatch):
        """When embeddings_enabled=False, schema has NO embedding field at all."""
        import project.models.entity_search as es_mod

        disabled_settings = _make_settings(provider="none")
        monkeypatch.setattr(es_mod, "get_settings", lambda: disabled_settings)

        schema = es_mod._build_schema()
        embedding_fields = [f for f in schema["fields"] if f["name"] == "embedding"]
        assert embedding_fields == [], "Expected no embedding field when embeddings disabled"

    def test_schema_embedding_respects_dim(self, app_ctx, monkeypatch):
        """The embedding field uses the configured embedding_dim."""
        import project.models.entity_search as es_mod

        settings = _make_settings(provider="gemini", key="k", dim=1536)
        monkeypatch.setattr(es_mod, "get_settings", lambda: settings)

        schema = es_mod._build_schema()
        emb = next(f for f in schema["fields"] if f["name"] == "embedding")
        assert emb["num_dim"] == 1536


# ---------------------------------------------------------------------------
# (b) Query — hybrid path (embed_query returns a vector)
# ---------------------------------------------------------------------------


class TestGetSearchHybrid:
    """get_search with embeddings enabled + embed_query returning a real vector."""

    def _run_get_search(self, app_ctx, monkeypatch, *, query="vc investor", threshold=0.30):
        """Monkeypatch settings + embeddings + Typesense client; return captured params."""
        import project.models.entity_search as es_mod
        import project.utils.embeddings as embed_mod

        fake_vec = [0.1, 0.2, 0.3]

        enabled_settings = _make_settings(provider="gemini", key="fake-key", threshold=threshold)
        monkeypatch.setattr(es_mod, "get_settings", lambda: enabled_settings)
        monkeypatch.setattr(embed_mod, "embed_query", lambda text: fake_vec)

        captured = {}

        class _FakeDocuments:
            def search(self, params):
                captured.update(params)
                captured["__via__"] = "documents_search"
                return {"found": 0, "page": 1, "hits": []}

        class _FakeCollection:
            documents = _FakeDocuments()

        class _FakeCollections:
            def __getitem__(self, name):
                return _FakeCollection()

        class _FakeMultiSearch:
            def perform(self, search_requests, common_params):
                params = dict(search_requests["searches"][0])
                params.pop("collection", None)
                captured.update(params)
                captured["__via__"] = "multi_search"
                return {"results": [{"found": 0, "page": 1, "hits": []}]}

        class _FakeClient:
            collections = _FakeCollections()
            multi_search = _FakeMultiSearch()

        monkeypatch.setattr(es_mod, "client", _FakeClient(), raising=False)

        # Also patch the client imported inside get_search via typesense_search
        import project.utils.typesense_helpers.typesense_search as ts_mod

        monkeypatch.setattr(ts_mod, "client", _FakeClient())

        es_mod.get_search(query=query)
        return captured, fake_vec

    def test_vector_query_is_set(self, app_ctx, monkeypatch):
        """vector_query param must be set when embed_query returns a vector."""
        params, _ = self._run_get_search(app_ctx, monkeypatch)
        assert "vector_query" in params, "Expected vector_query in Typesense params"

    def test_vector_query_starts_with_embedding(self, app_ctx, monkeypatch):
        """vector_query must start with 'embedding:([' and contain the vector values."""
        params, fake_vec = self._run_get_search(app_ctx, monkeypatch)
        vq = params["vector_query"]
        assert vq.startswith("embedding:(["), f"Unexpected vector_query format: {vq}"
        # First component of the vector must appear in the string
        assert repr(float(fake_vec[0])) in vq, f"Vector value not in query: {vq}"

    def test_vector_query_contains_distance_threshold(self, app_ctx, monkeypatch):
        """vector_query must include the configured distance_threshold."""
        params, _ = self._run_get_search(app_ctx, monkeypatch, threshold=0.25)
        vq = params["vector_query"]
        assert "distance_threshold:0.25" in vq, f"distance_threshold missing or wrong: {vq}"

    def test_exclude_fields_set_to_embedding(self, app_ctx, monkeypatch):
        """exclude_fields must be 'embedding' so the large vector is not returned."""
        params, _ = self._run_get_search(app_ctx, monkeypatch)
        assert params.get("exclude_fields") == "embedding"

    def test_embedding_not_in_query_by(self, app_ctx, monkeypatch):
        """'embedding' must NOT appear in the keyword query_by list."""
        params, _ = self._run_get_search(app_ctx, monkeypatch)
        query_by = params.get("query_by", "")
        assert "embedding" not in query_by, f"'embedding' should not be in query_by: {query_by}"

    def test_vector_query_routes_via_multi_search(self, app_ctx, monkeypatch):
        """A vector_query must be sent via multi_search (POST body), NOT documents.search
        (GET): a full embedding vector exceeds Typesense's 4000-char GET URL limit and 400s.
        Regression test for that bug (found in live verification)."""
        params, _ = self._run_get_search(app_ctx, monkeypatch)
        assert params.get("__via__") == "multi_search", "vector_query must route via multi_search (POST)"

    def test_wildcard_query_skips_vector(self, app_ctx, monkeypatch):
        """A wildcard '*' query must NOT produce a vector_query."""
        params, _ = self._run_get_search(app_ctx, monkeypatch, query="*")
        assert "vector_query" not in params, "vector_query should not be set for wildcard query"

    def test_empty_query_skips_vector(self, app_ctx, monkeypatch):
        """An empty query string must NOT produce a vector_query."""
        params, _ = self._run_get_search(app_ctx, monkeypatch, query="")
        assert "vector_query" not in params, "vector_query should not be set for empty query"


# ---------------------------------------------------------------------------
# (c) Query — fallback: embed_query returns None
# ---------------------------------------------------------------------------


class TestGetSearchFallback:
    """get_search with embeddings enabled but embed_query returning None."""

    def test_no_vector_query_when_embed_query_fails(self, app_ctx, monkeypatch):
        """When embed_query returns None, no vector_query is set (keyword fallback)."""
        import project.models.entity_search as es_mod
        import project.utils.embeddings as embed_mod

        enabled_settings = _make_settings(provider="gemini", key="fake-key")
        monkeypatch.setattr(es_mod, "get_settings", lambda: enabled_settings)
        monkeypatch.setattr(embed_mod, "embed_query", lambda text: None)

        captured = {}

        class _FakeDocuments:
            def search(self, params):
                captured.update(params)
                return {"found": 0, "page": 1, "hits": []}

        class _FakeCollection:
            documents = _FakeDocuments()

        class _FakeCollections:
            def __getitem__(self, name):
                return _FakeCollection()

        class _FakeClient:
            collections = _FakeCollections()

        import project.utils.typesense_helpers.typesense_search as ts_mod

        monkeypatch.setattr(ts_mod, "client", _FakeClient())

        es_mod.get_search(query="fintech")
        assert "vector_query" not in captured, "No vector_query expected when embed_query returns None"
        assert "exclude_fields" not in captured, "No exclude_fields expected on keyword fallback"


# ---------------------------------------------------------------------------
# (d) Query — embeddings disabled
# ---------------------------------------------------------------------------


class TestGetSearchDisabled:
    """get_search with embeddings_enabled=False (default provider=none)."""

    def test_no_vector_query_when_disabled(self, app_ctx, monkeypatch):
        """No vector_query is set when embeddings are disabled."""
        import project.models.entity_search as es_mod

        disabled_settings = _make_settings(provider="none")
        monkeypatch.setattr(es_mod, "get_settings", lambda: disabled_settings)

        captured = {}

        class _FakeDocuments:
            def search(self, params):
                captured.update(params)
                return {"found": 0, "page": 1, "hits": []}

        class _FakeCollection:
            documents = _FakeDocuments()

        class _FakeCollections:
            def __getitem__(self, name):
                return _FakeCollection()

        class _FakeClient:
            collections = _FakeCollections()

        import project.utils.typesense_helpers.typesense_search as ts_mod

        monkeypatch.setattr(ts_mod, "client", _FakeClient())

        es_mod.get_search(query="saas investor")
        assert "vector_query" not in captured

    def test_embedding_not_in_query_by_when_disabled(self, app_ctx, monkeypatch):
        """'embedding' must not appear in query_by even when the query text is non-empty."""
        import project.models.entity_search as es_mod

        disabled_settings = _make_settings(provider="none")
        monkeypatch.setattr(es_mod, "get_settings", lambda: disabled_settings)

        captured = {}

        class _FakeDocuments:
            def search(self, params):
                captured.update(params)
                return {"found": 0, "page": 1, "hits": []}

        class _FakeCollection:
            documents = _FakeDocuments()

        class _FakeCollections:
            def __getitem__(self, name):
                return _FakeCollection()

        class _FakeClient:
            collections = _FakeCollections()

        import project.utils.typesense_helpers.typesense_search as ts_mod

        monkeypatch.setattr(ts_mod, "client", _FakeClient())

        es_mod.get_search(query="climate tech")
        query_by = captured.get("query_by", "")
        assert "embedding" not in query_by


# ---------------------------------------------------------------------------
# (e) _attach_embeddings helper
# ---------------------------------------------------------------------------


class TestAttachEmbeddings:
    """Unit tests for the _attach_embeddings helper."""

    def test_attaches_vectors_to_docs(self, app_ctx, monkeypatch):
        """_attach_embeddings must set doc['embedding'] for each doc."""
        import project.models.entity_search as es_mod
        import project.utils.embeddings as embed_mod

        fake_vecs = [[0.1, 0.2], [0.3, 0.4]]
        monkeypatch.setattr(embed_mod, "embed_documents", lambda texts: fake_vecs)

        docs = [{"name": "Alice", "about": "angel"}, {"name": "Acme"}]
        es_mod._attach_embeddings(docs)

        assert docs[0]["embedding"] == [0.1, 0.2]
        assert docs[1]["embedding"] == [0.3, 0.4]

    def test_no_embedding_key_when_embed_returns_none(self, app_ctx, monkeypatch):
        """When embed_documents returns None, docs must NOT have an 'embedding' key."""
        import project.models.entity_search as es_mod
        import project.utils.embeddings as embed_mod

        monkeypatch.setattr(embed_mod, "embed_documents", lambda texts: None)

        docs = [{"name": "Alice"}]
        es_mod._attach_embeddings(docs)

        assert "embedding" not in docs[0]

    def test_does_not_drop_docs_on_failure(self, app_ctx, monkeypatch):
        """_attach_embeddings must not remove or reduce the docs list on API failure."""
        import project.models.entity_search as es_mod
        import project.utils.embeddings as embed_mod

        monkeypatch.setattr(embed_mod, "embed_documents", lambda texts: None)

        docs = [{"name": "A"}, {"name": "B"}, {"name": "C"}]
        es_mod._attach_embeddings(docs)

        assert len(docs) == 3
