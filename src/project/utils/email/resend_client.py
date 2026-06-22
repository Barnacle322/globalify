"""Resend-backed email sender with env-gated fallback.

When ``_RESEND_API_KEY`` is set in the environment (or .env), emails are
dispatched via the ``resend`` Python SDK.  When the key is absent (local dev,
CI, tests) the function logs the intent and returns True without touching the
network.

Retry policy: a single retry on HTTP 429, honouring the ``ratelimit-reset``
header when present (fallback: 1-second sleep).  All other errors are caught,
logged, and False is returned so the caller never sees an exception.
"""

from __future__ import annotations

import logging
import time

import resend
from flask import current_app

from ...config import get_settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, html: str) -> bool:
    """Send a transactional email.

    Returns True on success (or in stub mode).  Returns False if the Resend
    API call fails after one retry.  Never raises into the caller.
    """
    settings = get_settings()

    if not settings.email_is_configured:
        current_app.logger.info("[email stub] to=%s subject=%s", to, subject)
        return True

    resend.api_key = settings.resend_api_key

    params: resend.Emails.SendParams = {
        "from": settings.email_from,
        "to": [to],
        "subject": subject,
        "html": html,
    }

    try:
        resend.Emails.send(params)
        return True
    except Exception as exc:  # noqa: BLE001
        # Check for rate-limit and retry once
        if _is_rate_limit(exc):
            wait = _rate_limit_wait(exc)
            current_app.logger.warning("[email] rate-limited; retrying in %.1fs (to=%s)", wait, to)
            time.sleep(wait)
            try:
                resend.Emails.send(params)
                return True
            except Exception as retry_exc:  # noqa: BLE001
                current_app.logger.error("[email] send failed after retry (to=%s): %s", to, retry_exc)
                return False
        else:
            current_app.logger.error("[email] send failed (to=%s): %s", to, exc)
            return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_rate_limit(exc: Exception) -> bool:
    """Return True if *exc* looks like a 429 rate-limit response."""
    msg = str(exc).lower()
    return "429" in msg or "rate" in msg


def _rate_limit_wait(exc: Exception) -> float:
    """Extract the wait time (seconds) from a rate-limit error, default 1 s."""
    # The resend SDK may expose a response object with headers.
    response = getattr(exc, "response", None)
    if response is not None:
        headers = getattr(response, "headers", {}) or {}
        reset = headers.get("ratelimit-reset") or headers.get("x-ratelimit-reset")
        if reset and _to_float(reset) is not None:
            return max(0.0, _to_float(reset) - time.time())
    return 1.0


def _to_float(value: object) -> float | None:
    """Safely convert *value* to float; return None on failure."""
    try:
        return float(value)  # type: ignore[arg-type]
    except Exception:  # noqa: BLE001
        return None
