"""Tests for the Gemini embedding client.

TDD: written before the implementation.

Scenarios:
  a) _l2_normalize math — [3,4] → [0.6, 0.8]; zero vector → no crash.
  b) embeddings_enabled=False (default provider "none") → embed_texts returns None,
     no genai.Client constructed.
  c) embeddings_enabled=True + monkeypatched client returning raw vectors →
     embed_documents normalizes; embed_query uses RETRIEVAL_QUERY.
  d) Client that raises → embed_documents returns None (fallback, no re-raise).
"""

from __future__ import annotations

import math

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def app_ctx(app):
    """Push an application context so Flask's current_app is available."""
    with app.app_context():
        yield app


def _make_settings(*, provider="none", key=None, model="gemini-embedding-001", dim=768):
    """Build a Settings instance with embedding fields set."""
    from project.config import Settings

    kwargs: dict = {"SECRET_KEY": "test", "FLASK_ENV": "testing"}
    kwargs["_EMBEDDING_PROVIDER"] = provider
    kwargs["_EMBEDDING_MODEL"] = model
    kwargs["_EMBEDDING_DIM"] = dim
    if key is not None:
        kwargs["GEMINI_API_KEY"] = key
    return Settings(**kwargs)


# ---------------------------------------------------------------------------
# (a) _l2_normalize
# ---------------------------------------------------------------------------


class TestL2Normalize:
    def test_unit_normalizes_vector(self):
        from project.utils.embeddings.gemini import _l2_normalize

        result = _l2_normalize([3.0, 4.0])
        assert result == pytest.approx([0.6, 0.8], abs=1e-7)

    def test_result_is_unit_length(self):
        from project.utils.embeddings.gemini import _l2_normalize

        result = _l2_normalize([3.0, 4.0])
        norm = math.sqrt(sum(x**2 for x in result))
        assert norm == pytest.approx(1.0, abs=1e-7)

    def test_zero_vector_no_crash(self):
        from project.utils.embeddings.gemini import _l2_normalize

        result = _l2_normalize([0.0, 0.0])
        assert result == [0.0, 0.0]

    def test_already_unit_vector_unchanged(self):
        from project.utils.embeddings.gemini import _l2_normalize

        vec = [1.0, 0.0, 0.0]
        result = _l2_normalize(vec)
        assert result == pytest.approx([1.0, 0.0, 0.0], abs=1e-7)


# ---------------------------------------------------------------------------
# (b) embeddings_enabled=False → no client built, returns None
# ---------------------------------------------------------------------------


class TestEmbeddingsDisabled:
    def test_embed_texts_returns_none_when_disabled(self, app_ctx, monkeypatch):
        """embed_texts must return None when embeddings_enabled is False."""
        import project.utils.embeddings.gemini as gem_mod

        disabled_settings = _make_settings(provider="none")
        monkeypatch.setattr(gem_mod, "get_settings", lambda: disabled_settings)

        from project.utils.embeddings.gemini import embed_texts

        result = embed_texts(["hello"], task_type="RETRIEVAL_DOCUMENT")
        assert result is None

    def test_no_client_constructed_when_disabled(self, app_ctx, monkeypatch):
        """genai.Client must NOT be called when embeddings are disabled."""
        from google import genai

        import project.utils.embeddings.gemini as gem_mod

        disabled_settings = _make_settings(provider="none")
        monkeypatch.setattr(gem_mod, "get_settings", lambda: disabled_settings)

        called = []

        def boom(*args, **kwargs):
            called.append((args, kwargs))
            raise AssertionError("genai.Client must not be constructed when embeddings disabled")

        monkeypatch.setattr(genai, "Client", boom)

        from project.utils.embeddings.gemini import embed_texts

        result = embed_texts(["hello"], task_type="RETRIEVAL_DOCUMENT")
        assert result is None
        assert called == [], "genai.Client was constructed despite embeddings being disabled"


# ---------------------------------------------------------------------------
# (c) embeddings_enabled=True + fake client → normalized output, correct task_type
# ---------------------------------------------------------------------------


class _FakeEmbedding:
    """Mimics a single embedding value container."""

    def __init__(self, values):
        self.values = values


class _FakeEmbedResponse:
    """Mimics the response object returned by genai.models.embed_content."""

    def __init__(self, raw_vectors):
        self.embeddings = [_FakeEmbedding(v) for v in raw_vectors]


class _FakeModels:
    """Mimics the genai.Client().models namespace."""

    def __init__(self, raw_vectors, capture_list):
        self._raw = raw_vectors
        self._capture = capture_list

    def embed_content(self, *, model, contents, config):
        self._capture.append({"model": model, "contents": contents, "config": config})
        return _FakeEmbedResponse(self._raw)


class _FakeClient:
    def __init__(self, raw_vectors, capture_list):
        self.models = _FakeModels(raw_vectors, capture_list)


class TestEmbeddingsEnabled:
    def _patch(self, monkeypatch, raw_vectors, key="fake-key"):
        """Monkeypatch settings + genai.Client; return (calls list, settings)."""
        from google import genai

        import project.utils.embeddings.gemini as gem_mod

        settings = _make_settings(provider="gemini", key=key)
        monkeypatch.setattr(gem_mod, "get_settings", lambda: settings)

        calls = []
        fake_client = _FakeClient(raw_vectors, calls)
        monkeypatch.setattr(genai, "Client", lambda api_key: fake_client)

        return calls, settings

    def test_embed_documents_normalizes_vectors(self, app_ctx, monkeypatch):
        """embed_documents must return L2-normalized vectors (norm≈1.0)."""
        raw = [[3.0, 4.0]]
        calls, _ = self._patch(monkeypatch, raw)

        from project.utils.embeddings.gemini import embed_documents

        result = embed_documents(["acme"])
        assert result is not None
        assert len(result) == 1
        assert result[0] == pytest.approx([0.6, 0.8], abs=1e-7)
        norm = math.sqrt(sum(x**2 for x in result[0]))
        assert norm == pytest.approx(1.0, abs=1e-7)

    def test_embed_documents_uses_retrieval_document_task(self, app_ctx, monkeypatch):
        """embed_documents must call the API with task_type=RETRIEVAL_DOCUMENT."""
        raw = [[3.0, 4.0]]
        calls, settings = self._patch(monkeypatch, raw)

        from project.utils.embeddings.gemini import embed_documents

        embed_documents(["acme"])
        assert len(calls) == 1
        cfg = calls[0]["config"]
        assert cfg.task_type == "RETRIEVAL_DOCUMENT"

    def test_embed_documents_passes_output_dimensionality(self, app_ctx, monkeypatch):
        """embed_documents must pass output_dimensionality=768 (from config)."""
        raw = [[3.0, 4.0]]
        calls, settings = self._patch(monkeypatch, raw)

        from project.utils.embeddings.gemini import embed_documents

        embed_documents(["acme"])
        assert len(calls) == 1
        cfg = calls[0]["config"]
        assert cfg.output_dimensionality == settings.embedding_dim

    def test_embed_query_uses_retrieval_query_task(self, app_ctx, monkeypatch):
        """embed_query must call the API with task_type=RETRIEVAL_QUERY."""
        raw = [[3.0, 4.0]]
        calls, _ = self._patch(monkeypatch, raw)

        from project.utils.embeddings.gemini import embed_query

        result = embed_query("acme")
        assert result is not None
        assert result == pytest.approx([0.6, 0.8], abs=1e-7)
        assert len(calls) == 1
        cfg = calls[0]["config"]
        assert cfg.task_type == "RETRIEVAL_QUERY"

    def test_embed_query_returns_single_vector(self, app_ctx, monkeypatch):
        """embed_query must return a single flat list[float], not list[list[float]]."""
        raw = [[1.0, 0.0]]
        self._patch(monkeypatch, raw)

        from project.utils.embeddings.gemini import embed_query

        result = embed_query("test")
        assert result is not None
        assert isinstance(result, list)
        assert isinstance(result[0], float)

    def test_embed_texts_order_preserving(self, app_ctx, monkeypatch):
        """embed_texts must return vectors in the same order as input texts."""
        raw = [[3.0, 4.0], [0.0, 5.0]]
        self._patch(monkeypatch, raw)

        from project.utils.embeddings.gemini import embed_documents

        result = embed_documents(["first", "second"])
        assert result is not None
        assert len(result) == 2
        # first: [3,4]/5 → [0.6, 0.8]
        assert result[0] == pytest.approx([0.6, 0.8], abs=1e-7)
        # second: [0,5]/5 → [0.0, 1.0]
        assert result[1] == pytest.approx([0.0, 1.0], abs=1e-7)


# ---------------------------------------------------------------------------
# (d) Client raises → fallback (returns None, does not re-raise)
# ---------------------------------------------------------------------------


class TestEmbeddingsFallback:
    def test_returns_none_on_client_exception(self, app_ctx, monkeypatch):
        """embed_documents must return None if the API call raises (any exception)."""
        from google import genai

        import project.utils.embeddings.gemini as gem_mod

        settings = _make_settings(provider="gemini", key="fake-key")
        monkeypatch.setattr(gem_mod, "get_settings", lambda: settings)

        class _ExplodingModels:
            def embed_content(self, **kwargs):
                raise RuntimeError("quota exceeded / 429 / network blip")

        class _ExplodingClient:
            models = _ExplodingModels()

        monkeypatch.setattr(genai, "Client", lambda api_key: _ExplodingClient())

        from project.utils.embeddings.gemini import embed_documents

        result = embed_documents(["any text"])
        assert result is None

    def test_does_not_raise_on_client_exception(self, app_ctx, monkeypatch):
        """embed_documents must never propagate an exception."""
        from google import genai

        import project.utils.embeddings.gemini as gem_mod

        settings = _make_settings(provider="gemini", key="fake-key")
        monkeypatch.setattr(gem_mod, "get_settings", lambda: settings)

        class _ExplodingModels:
            def embed_content(self, **kwargs):
                raise Exception("unexpected failure")

        class _ExplodingClient:
            models = _ExplodingModels()

        monkeypatch.setattr(genai, "Client", lambda api_key: _ExplodingClient())

        from project.utils.embeddings.gemini import embed_documents

        # Must not raise
        embed_documents(["any text"])
