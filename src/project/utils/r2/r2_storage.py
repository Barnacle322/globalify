"""Cloudflare R2 image storage — env-gated with local-dev fallback.

When R2 credentials are present (_R2_ACCOUNT_ID, _R2_ACCESS_KEY_ID,
_R2_SECRET_ACCESS_KEY, _R2_BUCKET), files are stored in R2 via the
S3-compatible API (boto3, endpoint_url per CF docs).

When credentials are absent (dev / CI / test), files are written to
``instance/uploads/<key>`` on the local filesystem and served by the
``/uploads/<path>`` dev route registered in the app factory.

**Important:** only the storage key (e.g. ``images/<uuid>.jpg``) is stored
in the database — never a full URL.  Call ``public_url(key)`` at render time
to resolve the appropriate URL for the current environment.

Pillow note: the old google_storage.py did HEIC→JPEG/resize via Pillow, but
Pillow was removed during Phase 1a.  This module accepts raw bytes as-is.
If Pillow processing is re-added in future, do it in the caller before
passing bytes here.
"""

from __future__ import annotations

import pathlib
from uuid import uuid4

import boto3  # noqa: F401 — imported as module attr so tests can monkeypatch

from ...config import Settings

# ---------------------------------------------------------------------------
# Module-level state (allows monkeypatching in tests)
# ---------------------------------------------------------------------------

_settings: Settings = Settings()  # refreshed via monkeypatch in tests

# Resolved lazily; reset to None by tests that need to inspect construction
_s3_client = None

# Local dev upload directory (relative to project root ``instance/``).
# Override in tests via monkeypatch: ``monkeypatch.setattr(r2_storage, "UPLOADS_DIR", tmp_path)``
UPLOADS_DIR: pathlib.Path = pathlib.Path("instance") / "uploads"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_s3():
    """Return the cached boto3 S3 client, building it on first call."""
    global _s3_client  # noqa: PLW0603
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            endpoint_url=f"https://{_settings.r2_account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=_settings.r2_access_key_id,
            aws_secret_access_key=_settings.r2_secret_access_key,
            region_name="auto",
        )
    return _s3_client


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def upload_image(
    data: bytes,
    content_type: str = "image/jpeg",
    prefix: str = "images",
) -> str:
    """Upload image bytes and return the storage key (not a URL).

    Args:
        data: Raw image bytes.
        content_type: MIME type, default ``image/jpeg``.
        prefix: Key prefix / "folder", default ``images``.

    Returns:
        Storage key, e.g. ``images/<uuid32>.jpg``.
    """
    key = f"{prefix}/{uuid4().hex}.jpg"

    if _settings.r2_is_configured:
        _get_s3().put_object(
            Bucket=_settings.r2_bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
    else:
        dest = UPLOADS_DIR / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)

    return key


def delete_object(key: str) -> None:
    """Delete an object by storage key.

    Silently ignores missing objects in both R2 and local-dev modes.
    """
    if _settings.r2_is_configured:
        _get_s3().delete_object(
            Bucket=_settings.r2_bucket,
            Key=key,
        )
    else:
        target = UPLOADS_DIR / key
        try:
            target.unlink()
        except FileNotFoundError:
            pass


def public_url(key: str) -> str:
    """Resolve a storage key to a public-facing URL.

    - R2 configured **and** ``r2_public_domain`` set → ``https://<domain>/<key>``
    - Otherwise → ``/uploads/<key>`` (served by the dev route)
    """
    if _settings.r2_is_configured and _settings.r2_public_domain:
        return f"https://{_settings.r2_public_domain}/{key}"
    return f"/uploads/{key}"
