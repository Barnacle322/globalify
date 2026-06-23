"""Gemini-backed embedding client with graceful fallback.

When ``_EMBEDDING_PROVIDER`` is ``gemini`` and ``GEMINI_API_KEY`` is set,
``embed_texts`` calls the Gemini API (``gemini-embedding-001`` by default)
and returns L2-normalised vectors ready for Typesense cosine similarity.

When embeddings are disabled (default provider ``none``, or the key is absent)
every public function returns ``None`` without touching the network.  On any
API error or quota hit (429) the function also returns ``None`` and logs a
warning — it never raises into the caller.
"""

from __future__ import annotations

import math

from flask import current_app
from google import genai
from google.genai import types

from ...config import get_settings

# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _l2_normalize(vec: list[float]) -> list[float]:
    """Return *vec* scaled to unit length (L2 norm = 1).

    If the norm is zero (zero vector) the original vector is returned unchanged
    to avoid a division-by-zero error.
    """
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0.0:
        return vec
    return [x / norm for x in vec]


# ---------------------------------------------------------------------------
# Public embedding API
# ---------------------------------------------------------------------------


def embed_texts(texts: list[str], *, task_type: str) -> list[list[float]] | None:
    """Embed *texts* using the configured Gemini model.

    Parameters
    ----------
    texts:
        Strings to embed.  Order is preserved in the output.
    task_type:
        Gemini retrieval task type — ``"RETRIEVAL_DOCUMENT"`` for indexing,
        ``"RETRIEVAL_QUERY"`` for search queries.

    Returns
    -------
    list[list[float]] | None
        L2-normalised embedding vectors (one per input text), or ``None`` when
        embeddings are disabled or the API call fails.
    """
    settings = get_settings()
    if not settings.embeddings_enabled:
        return None

    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        embed_config = types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=settings.embedding_dim,
        )

        vectors: list[list[float]] = []
        batch_size = 100

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = client.models.embed_content(
                model=settings.embedding_model,
                contents=batch,
                config=embed_config,
            )
            for embedding in response.embeddings:
                vectors.append(_l2_normalize(list(embedding.values)))

        return vectors

    except Exception as exc:  # noqa: BLE001
        current_app.logger.warning("gemini embed failed: %s", exc)
        return None


def embed_documents(texts: list[str]) -> list[list[float]] | None:
    """Embed *texts* for indexing (``RETRIEVAL_DOCUMENT`` task type).

    Returns L2-normalised vectors or ``None`` on failure/disabled.
    """
    return embed_texts(texts, task_type="RETRIEVAL_DOCUMENT")


def embed_query(text: str) -> list[float] | None:
    """Embed a single search *query* (``RETRIEVAL_QUERY`` task type).

    Returns a single L2-normalised vector or ``None`` on failure/disabled.
    """
    result = embed_texts([text], task_type="RETRIEVAL_QUERY")
    if result is None:
        return None
    return result[0]
