"""Email utilities.

Phase 2e: stub implementation — logs the magic link to the app logger.
Phase 3 will replace send_magic_link with a real Resend API call.
"""

from flask import current_app


def send_magic_link(email: str, link: str) -> None:
    """Send a magic-link login email to *email*.

    Currently STUBBED: logs the link at INFO level so developers can click
    through during local development / tests without a real mail provider.
    """
    # TODO(phase-3): send via Resend — replace the log line below with an
    #   actual HTTP call to the Resend API (or the resend-python SDK).
    current_app.logger.info("magic link for %s: %s", email, link)
