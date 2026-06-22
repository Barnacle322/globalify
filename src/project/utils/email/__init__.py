"""Email utilities.

Phase 3: send_magic_link renders a Jinja2 HTML email template and dispatches
it via the env-gated Resend client (resend_client.py).  When no
``_RESEND_API_KEY`` is configured (dev / CI), the client stubs the send and
logs the intent — no credentials required.
"""

from flask import render_template

from .resend_client import send_email


def send_magic_link(email: str, link: str) -> None:
    """Send a magic-link login email to *email*.

    Renders ``email/magic_link.html`` with the login *link*, then hands off to
    the Resend-gated ``send_email`` helper.  Falls back to a log stub when no
    API key is configured.
    """
    html = render_template("email/magic_link.html", link=link)
    send_email(email, "Your Globalify login link", html)
