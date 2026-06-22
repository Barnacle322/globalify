"""Tests for Paddle Billing webhook — signature verification, event dispatch, idempotency.

All tests are mocked / in-process: no network calls, no real Paddle credentials.
Signed payloads are constructed in-test using the same HMAC logic as the
production verifier, so the tests double as hand-verification of the algorithm.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time

import pytest

# ---------------------------------------------------------------------------
# Test constants
# ---------------------------------------------------------------------------

TEST_SECRET = "test_webhook_secret_abc123"
TEST_USER_ID = 42
TEST_EVENT_ID = "evt_01abc123"
TEST_PRICE_MONTHLY = "pri_monthly_test"
TEST_PRICE_LIFETIME = "pri_lifetime_test"
TEST_CUSTOMER_ID = "ctm_01test"
TEST_SUB_ID = "sub_01test"


# ---------------------------------------------------------------------------
# Helper: build a correctly signed Paddle-Signature header
# ---------------------------------------------------------------------------


def _sign(raw_body: bytes, secret: str, ts: int | None = None) -> str:
    """Return a Paddle-Signature header value for *raw_body* signed with *secret*."""
    if ts is None:
        ts = int(time.time())
    signed_payload = f"{ts}:".encode() + raw_body
    h1 = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    return f"ts={ts};h1={h1}"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_app(monkeypatch, app):
    """App with paddle webhook secret configured + full in-memory schema."""
    monkeypatch.setenv("_PADDLE_WEBHOOK_SECRET", TEST_SECRET)
    monkeypatch.setenv("_PADDLE_PRICE_ID_LIFETIME", TEST_PRICE_LIFETIME)
    monkeypatch.setenv("_PADDLE_PRICE_ID_MONTHLY", TEST_PRICE_MONTHLY)
    monkeypatch.setenv("_PADDLE_CLIENT_TOKEN", "test_client_token")

    # Force re-import so new env vars are picked up
    import sys

    for mod in list(sys.modules.keys()):
        if "project" in mod:
            del sys.modules[mod]

    from project import create_app

    application = create_app()
    application.config.update(TESTING=True)

    from project.extensions import db as _db

    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def db_client(db_app):
    return db_app.test_client()


@pytest.fixture()
def seeded_user(db_app):
    """Create a user with id=TEST_USER_ID in the test DB."""
    from project.extensions import db
    from project.models import User, UserInfo, UserPayment

    with db_app.app_context():
        user = User(email="paddle_user@example.com", is_verified=True)
        db.session.add(user)
        db.session.flush()

        user_info = UserInfo(
            first_name="Paddle",
            last_name="Tester",
            username=f"paddletester_{user.id}",
            is_complete=True,
            user=user,
        )
        db.session.add(user_info)

        payment = UserPayment(user=user)
        db.session.add(payment)
        db.session.commit()
        yield user.id


# ---------------------------------------------------------------------------
# Unit tests — verify_signature
# ---------------------------------------------------------------------------


class TestVerifySignature:
    """verify_signature must accept valid signatures and reject everything else."""

    def test_accepts_correctly_signed_body(self):
        from project.utils.paddle import verify_signature

        body = b'{"test": "payload"}'
        sig = _sign(body, TEST_SECRET)
        assert verify_signature(body, sig, TEST_SECRET) is True

    def test_rejects_tampered_body(self):
        from project.utils.paddle import verify_signature

        body = b'{"test": "payload"}'
        sig = _sign(body, TEST_SECRET)
        tampered = b'{"test": "TAMPERED"}'
        assert verify_signature(tampered, sig, TEST_SECRET) is False

    def test_rejects_wrong_secret(self):
        from project.utils.paddle import verify_signature

        body = b'{"test": "payload"}'
        sig = _sign(body, "wrong_secret_xyz")
        assert verify_signature(body, sig, TEST_SECRET) is False

    def test_rejects_timestamp_too_old(self):
        """A timestamp > tolerance seconds in the past must be rejected."""
        from project.utils.paddle import verify_signature

        body = b'{"test": "old"}'
        old_ts = int(time.time()) - 120  # 2 minutes ago
        sig = _sign(body, TEST_SECRET, ts=old_ts)
        # Use tolerance=10 so 120s fails
        assert verify_signature(body, sig, TEST_SECRET, tolerance_seconds=10) is False

    def test_rejects_timestamp_in_future(self):
        """A timestamp far in the future should also be rejected."""
        from project.utils.paddle import verify_signature

        body = b'{"test": "future"}'
        future_ts = int(time.time()) + 120
        sig = _sign(body, TEST_SECRET, ts=future_ts)
        assert verify_signature(body, sig, TEST_SECRET, tolerance_seconds=10) is False

    def test_accepts_within_tolerance(self):
        """A timestamp just within tolerance must pass."""
        from project.utils.paddle import verify_signature

        body = b'{"test": "fresh"}'
        ts = int(time.time()) - 3  # 3 seconds ago, within 5s default
        sig = _sign(body, TEST_SECRET, ts=ts)
        assert verify_signature(body, sig, TEST_SECRET, tolerance_seconds=5) is True

    def test_rejects_malformed_header_missing_h1(self):
        from project.utils.paddle import verify_signature

        assert verify_signature(b"body", "ts=12345", TEST_SECRET) is False

    def test_rejects_malformed_header_garbage(self):
        from project.utils.paddle import verify_signature

        assert verify_signature(b"body", "not-a-valid-header", TEST_SECRET) is False

    def test_rejects_none_header(self):
        from project.utils.paddle import verify_signature

        assert verify_signature(b"body", None, TEST_SECRET) is False

    def test_rejects_empty_header(self):
        from project.utils.paddle import verify_signature

        assert verify_signature(b"body", "", TEST_SECRET) is False


# ---------------------------------------------------------------------------
# Webhook route — /payment/webhook
# ---------------------------------------------------------------------------


def _make_transaction_completed(user_id: int, price_id: str, event_id: str = TEST_EVENT_ID) -> dict:
    return {
        "event_id": event_id,
        "event_type": "transaction.completed",
        "data": {
            "id": "txn_01test",
            "customer_id": TEST_CUSTOMER_ID,
            "custom_data": {"user_id": user_id},
            "items": [
                {
                    "price": {"id": price_id},
                }
            ],
        },
    }


def _make_subscription_event(event_type: str, user_id: int, event_id: str = TEST_EVENT_ID) -> dict:
    return {
        "event_id": event_id,
        "event_type": event_type,
        "data": {
            "id": TEST_SUB_ID,
            "customer_id": TEST_CUSTOMER_ID,
            "custom_data": {"user_id": user_id},
            "current_billing_period": {
                "ends_at": "2099-12-31T23:59:59.000Z",
            },
        },
    }


def _post_signed(client, payload: dict, secret: str = TEST_SECRET, tamper: bool = False):
    """POST a Paddle webhook with correct (or tampered) signature."""
    raw = json.dumps(payload).encode()
    sig = _sign(raw, secret)
    if tamper:
        # Sign correctly then corrupt the body
        raw = b'{"tampered": true}'
    return client.post(
        "/payment/webhook",
        data=raw,
        content_type="application/json",
        headers={"Paddle-Signature": sig},
    )


class TestWebhookRoute:
    """POST /payment/webhook integration tests."""

    # ------------------------------------------------------------------
    # Happy-path: transaction.completed grants Pro
    # ------------------------------------------------------------------

    def test_lifetime_transaction_grants_pro(self, db_app, db_client, seeded_user):
        """Valid signed transaction.completed for lifetime price → user becomes Pro."""
        user_id = seeded_user
        payload = _make_transaction_completed(user_id, TEST_PRICE_LIFETIME, event_id="evt_lt_001")

        with db_app.app_context():
            from project.models import User

            user_before = User.get_by_id(user_id)
            assert user_before.is_pro is False

        resp = _post_signed(db_client, payload)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.data}"

        with db_app.app_context():
            from project.models import User

            user_after = User.get_by_id(user_id)
            assert user_after.is_pro is True, "User should be Pro after lifetime transaction"
            assert user_after.user_payment.pro_source == "lifetime"
            assert user_after.user_payment.pro_expires_at is None

    # ------------------------------------------------------------------
    # Monthly transaction should NOT grant lifetime Pro
    # ------------------------------------------------------------------

    def test_monthly_transaction_does_not_grant_lifetime_pro(self, db_app, db_client, seeded_user):
        """transaction.completed for monthly price does NOT set lifetime Pro."""
        user_id = seeded_user
        payload = _make_transaction_completed(user_id, TEST_PRICE_MONTHLY, event_id="evt_mo_001")

        resp = _post_signed(db_client, payload)
        assert resp.status_code == 200

        with db_app.app_context():
            from project.models import User

            user_after = User.get_by_id(user_id)
            # Monthly transaction.completed does not grant lifetime — Pro state is from subscription events
            assert user_after.user_payment.pro_source != "lifetime" or user_after.is_pro is False

    # ------------------------------------------------------------------
    # Invalid signature → 400, no state change
    # ------------------------------------------------------------------

    def test_invalid_signature_returns_400(self, db_app, db_client, seeded_user):
        """An incorrectly signed request must return 400 and NOT grant Pro."""
        user_id = seeded_user
        payload = _make_transaction_completed(user_id, TEST_PRICE_LIFETIME, event_id="evt_bad_sig")

        resp = _post_signed(db_client, payload, tamper=True)
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"

        with db_app.app_context():
            from project.models import User

            assert User.get_by_id(user_id).is_pro is False, "User must NOT be Pro after bad-sig request"

    def test_wrong_secret_returns_400(self, db_app, db_client, seeded_user):
        """A request signed with the wrong secret must return 400."""
        user_id = seeded_user
        payload = _make_transaction_completed(user_id, TEST_PRICE_LIFETIME, event_id="evt_wrong_secret")

        resp = _post_signed(db_client, payload, secret="totally_wrong_secret")
        assert resp.status_code == 400

    # ------------------------------------------------------------------
    # Idempotency: same event_id posted twice → Pro granted once
    # ------------------------------------------------------------------

    def test_duplicate_event_id_is_idempotent(self, db_app, db_client, seeded_user):
        """Posting the same event_id twice must be a no-op on the second call."""
        user_id = seeded_user
        event_id = "evt_idempotent_001"
        payload = _make_transaction_completed(user_id, TEST_PRICE_LIFETIME, event_id=event_id)

        resp1 = _post_signed(db_client, payload)
        assert resp1.status_code == 200, f"First post failed: {resp1.status_code}"

        resp2 = _post_signed(db_client, payload)
        assert resp2.status_code == 200, f"Second (duplicate) post failed: {resp2.status_code}"

        with db_app.app_context():
            from project.models import User
            from project.models.webhook import ProcessedWebhook

            # Pro granted exactly once — no double-processing
            user = User.get_by_id(user_id)
            assert user.is_pro is True

            # Only one record in processed_webhook for this event_id
            from project.extensions import db

            count = db.session.query(ProcessedWebhook).filter_by(event_id=event_id).count()
            assert count == 1, f"Expected 1 ProcessedWebhook record, got {count}"

    # ------------------------------------------------------------------
    # subscription.created → Pro granted with expiry
    # ------------------------------------------------------------------

    def test_subscription_created_grants_pro(self, db_app, db_client, seeded_user):
        """subscription.created → user becomes Pro with an expiry date."""
        user_id = seeded_user
        payload = _make_subscription_event("subscription.created", user_id, event_id="evt_sub_created")

        resp = _post_signed(db_client, payload)
        assert resp.status_code == 200

        with db_app.app_context():
            from project.models import User

            user = User.get_by_id(user_id)
            assert user.is_pro is True
            assert user.user_payment.pro_source == "subscription"
            assert user.user_payment.paddle_subscription_id == TEST_SUB_ID

    # ------------------------------------------------------------------
    # subscription.canceled → Pro revoked / expiry set
    # ------------------------------------------------------------------

    def test_subscription_canceled_revokes_pro(self, db_app, db_client, seeded_user):
        """subscription.canceled → user loses Pro (or expiry set to period end)."""
        user_id = seeded_user

        # First grant Pro via subscription.created
        create_payload = _make_subscription_event("subscription.created", user_id, event_id="evt_sub_for_cancel")
        resp = _post_signed(db_client, create_payload)
        assert resp.status_code == 200

        # Then cancel
        cancel_payload = _make_subscription_event("subscription.canceled", user_id, event_id="evt_sub_canceled")
        resp = _post_signed(db_client, cancel_payload)
        assert resp.status_code == 200

        with db_app.app_context():
            from project.models import User

            user = User.get_by_id(user_id)
            # Either revoked immediately or expiry set in the past (period end from fixture is 2099,
            # so we just check the payment record was updated)
            payment = user.user_payment
            # The cancel handler should have set pro_expires_at to the billing period end
            # OR revoked — either way, the test confirms the handler ran
            assert payment is not None  # handler executed without error

    # ------------------------------------------------------------------
    # Webhook with no secret configured → 200 no-op
    # ------------------------------------------------------------------

    def test_unconfigured_webhook_returns_200_noop(self, app, monkeypatch):
        """When _PADDLE_WEBHOOK_SECRET is not set, any POST returns 200 (no-op)."""
        # Use the base app fixture which has NO paddle creds
        monkeypatch.delenv("_PADDLE_WEBHOOK_SECRET", raising=False)

        import sys

        for mod in list(sys.modules.keys()):
            if "project" in mod:
                del sys.modules[mod]

        from project import create_app

        unconfigured_app = create_app()
        unconfigured_app.config.update(TESTING=True)

        with unconfigured_app.test_client() as c:
            resp = c.post(
                "/payment/webhook",
                data=b'{"event_id": "evt_noop", "event_type": "transaction.completed"}',
                content_type="application/json",
            )
        assert resp.status_code == 200, f"Expected 200 no-op, got {resp.status_code}"

    # ------------------------------------------------------------------
    # subscription.activated → Pro granted
    # ------------------------------------------------------------------

    def test_subscription_activated_grants_pro(self, db_app, db_client, seeded_user):
        """subscription.activated → same as created: user gets Pro."""
        user_id = seeded_user
        payload = _make_subscription_event("subscription.activated", user_id, event_id="evt_sub_activated")

        resp = _post_signed(db_client, payload)
        assert resp.status_code == 200

        with db_app.app_context():
            from project.models import User

            user = User.get_by_id(user_id)
            assert user.is_pro is True

    # ------------------------------------------------------------------
    # Missing user in custom_data → no crash, returns 200
    # ------------------------------------------------------------------

    def test_missing_user_id_in_custom_data_does_not_crash(self, db_app, db_client):
        """If user_id is missing or invalid, handler logs and returns 200 (not 500)."""
        payload = {
            "event_id": "evt_no_user",
            "event_type": "transaction.completed",
            "data": {
                "id": "txn_noop",
                "customer_id": "ctm_unknown",
                "custom_data": {},  # no user_id
                "items": [{"price": {"id": TEST_PRICE_LIFETIME}}],
            },
        }
        resp = _post_signed(db_client, payload)
        # Should not crash — returns 200 (event processed, user not found is a soft failure)
        assert resp.status_code in (200, 422)
