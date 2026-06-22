"""Tests for the Resend-gated email utilities.

TDD: written before the implementation.
Run `uv run pytest tests/test_email.py -v` to see them fail, then pass once
the implementation is in place.

Three scenarios:
  a) No _RESEND_API_KEY set → stub logs + returns True; resend.Emails.send NOT called.
  b) Key set + monkeypatched resend.Emails.send → called once with correct params.
  c) send_magic_link → renders template (link appears in HTML) then calls send_email.
"""

from __future__ import annotations

import logging

import pytest

# ---------------------------------------------------------------------------
# Helpers / shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def app_ctx(app):
    """Push an application context so Flask's current_app is available."""
    with app.app_context():
        yield app


# ---------------------------------------------------------------------------
# (a) No API key set → stub path
# ---------------------------------------------------------------------------


class TestSendEmailStub:
    """When no _RESEND_API_KEY is configured, send_email must use the stub."""

    def test_returns_true_without_api_key(self, app_ctx, monkeypatch):
        """send_email must return True even without an API key (stub mode)."""
        # Ensure no key in settings
        import project.utils.email.resend_client as rc
        from project.config import Settings

        monkeypatch.setattr(rc, "get_settings", lambda: Settings(SECRET_KEY="test", FLASK_ENV="testing"))

        from project.utils.email.resend_client import send_email

        result = send_email("x@y.com", "Subject", "<p>Hello</p>")
        assert result is True

    def test_logs_stub_message(self, app_ctx, monkeypatch, caplog):
        """send_email must log '[email stub]' when no API key is set."""
        import project.utils.email.resend_client as rc
        from project.config import Settings

        monkeypatch.setattr(rc, "get_settings", lambda: Settings(SECRET_KEY="test", FLASK_ENV="testing"))

        from project.utils.email.resend_client import send_email

        with caplog.at_level(logging.INFO, logger="project"):
            send_email("x@y.com", "My Subject", "<p>Hello</p>")

        assert any("[email stub]" in r.message for r in caplog.records), (
            f"Expected '[email stub]' in logs; got: {[r.message for r in caplog.records]}"
        )

    def test_does_not_call_resend_send(self, app_ctx, monkeypatch):
        """send_email must NOT call resend.Emails.send when no API key is set."""
        import resend

        import project.utils.email.resend_client as rc
        from project.config import Settings

        monkeypatch.setattr(rc, "get_settings", lambda: Settings(SECRET_KEY="test", FLASK_ENV="testing"))

        called = []

        def boom(*args, **kwargs):
            called.append((args, kwargs))
            raise AssertionError("resend.Emails.send must not be called in stub mode")

        monkeypatch.setattr(resend.Emails, "send", staticmethod(boom))

        from project.utils.email.resend_client import send_email

        # Must not raise — boom should never be reached
        result = send_email("x@y.com", "Subject", "<p>hi</p>")
        assert result is True
        assert called == [], "resend.Emails.send was called despite no API key"


# ---------------------------------------------------------------------------
# (b) Key is set → real Resend path (monkeypatched)
# ---------------------------------------------------------------------------


class TestSendEmailWithKey:
    """When _RESEND_API_KEY is set, send_email must call resend.Emails.send."""

    def test_calls_resend_send_once(self, app_ctx, monkeypatch):
        """send_email must call resend.Emails.send exactly once."""
        import resend

        import project.utils.email.resend_client as rc
        from project.config import Settings

        fake_settings = Settings(
            SECRET_KEY="test",
            FLASK_ENV="testing",
            _RESEND_API_KEY="re_test_key_123",
            _EMAIL_FROM="Globalify <noreply@mail.globalify.xyz>",
        )
        monkeypatch.setattr(rc, "get_settings", lambda: fake_settings)

        calls = []

        def fake_send(params):
            calls.append(params)
            return {"id": "fake-message-id"}

        monkeypatch.setattr(resend.Emails, "send", staticmethod(fake_send))

        from project.utils.email.resend_client import send_email

        result = send_email("recipient@example.com", "Test Subject", "<p>Test</p>")
        assert result is True
        assert len(calls) == 1

    def test_sends_correct_params(self, app_ctx, monkeypatch):
        """resend.Emails.send must receive correct from/to/subject/html params."""
        import resend

        import project.utils.email.resend_client as rc
        from project.config import Settings

        fake_settings = Settings(
            SECRET_KEY="test",
            FLASK_ENV="testing",
            _RESEND_API_KEY="re_test_key_123",
            _EMAIL_FROM="Globalify <noreply@mail.globalify.xyz>",
        )
        monkeypatch.setattr(rc, "get_settings", lambda: fake_settings)

        captured = {}

        def fake_send(params):
            captured.update(params)
            return {"id": "fake-id"}

        monkeypatch.setattr(resend.Emails, "send", staticmethod(fake_send))

        from project.utils.email.resend_client import send_email

        send_email("user@test.com", "Hello Subject", "<h1>Body</h1>")

        assert captured["from"] == "Globalify <noreply@mail.globalify.xyz>"
        assert captured["to"] == ["user@test.com"]
        assert captured["subject"] == "Hello Subject"
        assert captured["html"] == "<h1>Body</h1>"


# ---------------------------------------------------------------------------
# (c) send_magic_link renders template + link appears in HTML
# ---------------------------------------------------------------------------


class TestSendMagicLink:
    """send_magic_link must render the email template and include the link."""

    def test_link_in_rendered_html(self, app_ctx, monkeypatch):
        """The magic link URL must appear in the HTML passed to send_email."""
        import project.utils.email as email_pkg
        import project.utils.email.resend_client as rc
        from project.config import Settings

        # Stub settings so we don't need a real API key
        monkeypatch.setattr(rc, "get_settings", lambda: Settings(SECRET_KEY="test", FLASK_ENV="testing"))

        captured_html = []

        def fake_send_email(to, subject, html):
            captured_html.append(html)
            return True

        monkeypatch.setattr(email_pkg, "send_email", fake_send_email)

        from project.utils.email import send_magic_link

        magic_url = "https://globalify.xyz/auth/verify?token=TESTTOKEN123"
        send_magic_link("user@example.com", magic_url)

        assert len(captured_html) == 1, "send_email was not called"
        assert magic_url in captured_html[0], (
            f"Magic link URL not found in rendered HTML. Got: {captured_html[0][:300]}"
        )

    def test_subject_is_correct(self, app_ctx, monkeypatch):
        """send_magic_link must send with the correct subject line."""
        import project.utils.email as email_pkg
        import project.utils.email.resend_client as rc
        from project.config import Settings

        monkeypatch.setattr(rc, "get_settings", lambda: Settings(SECRET_KEY="test", FLASK_ENV="testing"))

        captured = []

        def fake_send_email(to, subject, html):
            captured.append({"to": to, "subject": subject, "html": html})
            return True

        monkeypatch.setattr(email_pkg, "send_email", fake_send_email)

        from project.utils.email import send_magic_link

        send_magic_link("user@example.com", "https://example.com/verify?token=abc")

        assert len(captured) == 1
        assert captured[0]["to"] == "user@example.com"
        assert "Globalify" in captured[0]["subject"] or "login" in captured[0]["subject"].lower()
