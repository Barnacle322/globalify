"""Cap captcha verification — self-hosted, reCAPTCHA-compatible siteverify.

When Cap env vars are absent (dev / CI / test), ``verify_captcha`` returns
``True`` immediately (skip-mode) so no Cap server is needed locally.

When Cap is configured, the function POSTs to ``{cap_api_endpoint}/siteverify``
with ``{secret, response}`` (reCAPTCHA-compatible), parses ``success`` from the
JSON response, and returns the boolean.  On any network error or timeout the
function logs and returns ``False`` (fail-closed when configured).

An absent or empty token when Cap is configured returns ``False`` without any
network call — there is nothing to verify.
"""

from __future__ import annotations

import logging

import requests  # noqa: F401 — imported as module attr so tests can monkeypatch

from ..config import Settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level state (allows monkeypatching in tests)
# ---------------------------------------------------------------------------

_settings: Settings = Settings()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def verify_captcha(token: str | None) -> bool:
    """Verify a Cap captcha token.

    Args:
        token: The ``cap-token`` value submitted by the browser widget, or
               ``None`` / empty string when the widget was absent.

    Returns:
        ``True``  — when Cap is not configured (skip-mode for dev/test/CI), or
                    when the siteverify endpoint confirms a valid token.
        ``False`` — when Cap is configured and the token is missing, invalid,
                    or the network call fails (fail-closed).
    """
    if not _settings.cap_is_configured:
        return True

    # Fail-closed: no token → don't bother calling the network.
    if not token:
        return False

    url = f"{_settings.cap_api_endpoint.rstrip('/')}/siteverify"
    try:
        response = requests.post(
            url,
            json={"secret": _settings.cap_secret, "response": token},
            timeout=5,
        )
        data = response.json()
        return bool(data.get("success", False))
    except Exception:
        logger.exception("Cap captcha verification failed (fail-closed)")
        return False
