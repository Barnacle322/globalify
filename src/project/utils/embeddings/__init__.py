"""App-side embedding utilities.

Public API
----------
embed_documents(texts)  ->  list[list[float]] | None
embed_query(text)       ->  list[float] | None
embed_texts(texts, *, task_type)  ->  list[list[float]] | None
"""

from .gemini import embed_documents, embed_query, embed_texts

__all__ = ["embed_documents", "embed_query", "embed_texts"]
