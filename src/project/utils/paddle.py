"""Paddle Billing helpers.

SDK choice: neither `paddle-billing` nor the official SDK resolved cleanly
(paddle-python-sdk installed but lacks stable webhook-signature tooling we
can audit). All webhook verification is implemented with stdlib `hmac` /
`hashlib` so the algorithm is hand-verifiable.  API calls (if any) use
`requests`, though the current webhook flow needs none.

Paddle webhook signature format (from docs):
  Header:  Paddle-Signature: ts=<unix_epoch>;h1=<sha256_hex>
  Payload: signed_payload = ts_bytes + b":" + raw_body
  HMAC:    HMAC-SHA256(webhook_secret, signed_payload)
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------


def verify_signature(
    raw_body: bytes,
    sig_header: str | None,
    secret: str,
    tolerance_seconds: int = 5,
) -> bool:
    """Return True iff *sig_header* is a valid Paddle signature for *raw_body*.

    Args:
        raw_body: The exact bytes received (before any JSON parsing).
        sig_header: The value of the ``Paddle-Signature`` HTTP header.
        secret: The destination (webhook endpoint) secret from the Paddle
            dashboard (plain string, not base64).
        tolerance_seconds: Maximum allowed drift between the request timestamp
            and wall-clock time.  Pass a large value in tests that pre-build
            payloads; set tight (e.g. 5 s) in production.

    Returns:
        ``True`` on success, ``False`` on any verification failure (including
        parse errors) — never raises.
    """
    if not sig_header:
        return False

    try:
        ts_part: str | None = None
        h1_part: str | None = None

        for part in sig_header.split(";"):
            key, _, value = part.partition("=")
            if key.strip() == "ts":
                ts_part = value.strip()
            elif key.strip() == "h1":
                h1_part = value.strip()

        if ts_part is None or h1_part is None:
            logger.debug("Paddle signature header missing ts or h1")
            return False

        ts = int(ts_part)
    except (ValueError, AttributeError) as exc:
        logger.debug("Failed to parse Paddle-Signature header: %s", exc)
        return False

    # Reject replays / clock skew
    now = int(time.time())
    if abs(now - ts) > tolerance_seconds:
        logger.debug("Paddle signature timestamp drift too large: ts=%d now=%d", ts, now)
        return False

    # Reconstruct the signed payload exactly as Paddle does
    signed_payload = f"{ts}:".encode() + raw_body
    expected = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected, h1_part):
        logger.debug("Paddle signature HMAC mismatch")
        return False

    return True


# ---------------------------------------------------------------------------
# Event dispatch
# ---------------------------------------------------------------------------


def handle_event(event: dict[str, Any], price_id_lifetime: str | None = None) -> None:
    """Dispatch a verified Paddle event to the appropriate handler.

    Called after the webhook route has:
    1. Verified the signature.
    2. Checked the event has not been processed before (idempotency).

    Args:
        event: Decoded JSON event dict.
        price_id_lifetime: The configured lifetime price ID to detect one-time
            purchases.  If None, ``transaction.completed`` is a no-op for
            lifetime grants.
    """
    event_type: str = event.get("event_type", "")
    data: dict[str, Any] = event.get("data", {})

    logger.info("Paddle event: type=%s id=%s", event_type, event.get("event_id"))

    if event_type == "transaction.completed":
        _handle_transaction_completed(data, price_id_lifetime)
    elif event_type in ("subscription.created", "subscription.activated"):
        _handle_subscription_grant(data)
    elif event_type == "subscription.updated":
        _handle_subscription_updated(data)
    elif event_type == "subscription.canceled":
        _handle_subscription_canceled(data)
    else:
        logger.info("Unhandled Paddle event type: %s", event_type)


# ---------------------------------------------------------------------------
# Internal handlers
# ---------------------------------------------------------------------------


def _resolve_user(data: dict[str, Any]):
    """Return the User (or None) from custom_data.user_id or paddle_customer_id."""
    from project.models.user import User, UserPayment

    # Prefer explicit user_id passed as customData
    custom_data = data.get("custom_data") or {}
    raw_user_id = custom_data.get("user_id")
    if raw_user_id is not None:
        try:
            user_id = int(raw_user_id)
        except TypeError, ValueError:
            logger.warning("Paddle event: invalid user_id in custom_data: %r", raw_user_id)
            return None

        user = User.get_by_id(user_id)
        if user is None:
            logger.warning("Paddle event: user_id=%d not found", user_id)
        return user

    # Fall back to paddle_customer_id
    customer_id = data.get("customer_id")
    if customer_id:
        payment = UserPayment.get_by_paddle_customer_id(customer_id)
        if payment:
            return payment.user
        logger.warning("Paddle event: no user for customer_id=%s", customer_id)

    return None


def _ensure_payment(user) -> Any:
    """Return the user's UserPayment, creating one if absent."""
    from project.extensions import db
    from project.models.user import UserPayment

    if user.user_payment is None:
        payment = UserPayment(user=user)
        db.session.add(payment)
        db.session.flush()
        return payment
    return user.user_payment


def _handle_transaction_completed(data: dict[str, Any], price_id_lifetime: str | None) -> None:
    """Grant lifetime Pro if the transaction includes the lifetime price."""
    if not price_id_lifetime:
        logger.info("Paddle: no lifetime price configured, skipping transaction.completed")
        return

    items = data.get("items") or []
    price_ids = [item.get("price", {}).get("id") for item in items if isinstance(item, dict)]

    if price_id_lifetime not in price_ids:
        logger.info(
            "Paddle transaction.completed: lifetime price %s not in items %s — skipping",
            price_id_lifetime,
            price_ids,
        )
        return

    user = _resolve_user(data)
    if user is None:
        return

    payment = _ensure_payment(user)
    customer_id = data.get("customer_id")
    if customer_id:
        payment.paddle_customer_id = customer_id

    payment.grant_pro("lifetime", expires_at=None)
    logger.info("Paddle: granted lifetime Pro to user_id=%d", user.id)


def _handle_subscription_grant(data: dict[str, Any]) -> None:
    """Grant subscription Pro on subscription.created or subscription.activated."""

    user = _resolve_user(data)
    if user is None:
        return

    payment = _ensure_payment(user)

    customer_id = data.get("customer_id")
    if customer_id:
        payment.paddle_customer_id = customer_id

    sub_id = data.get("id")
    if sub_id:
        payment.paddle_subscription_id = sub_id

    # Parse period end for expiry
    expires_at = _parse_billing_period_end(data)
    payment.grant_pro("subscription", expires_at=expires_at)
    logger.info(
        "Paddle: granted subscription Pro to user_id=%d expires_at=%s",
        user.id,
        expires_at,
    )


def _handle_subscription_updated(data: dict[str, Any]) -> None:
    """Reconcile subscription state on update (renewals, pauses, resumes)."""

    user = _resolve_user(data)
    if user is None:
        return

    payment = _ensure_payment(user)

    # Update sub id in case it changed
    sub_id = data.get("id")
    if sub_id:
        payment.paddle_subscription_id = sub_id

    status = data.get("status", "")
    expires_at = _parse_billing_period_end(data)

    if status in ("active", "trialing"):
        payment.grant_pro("subscription", expires_at=expires_at)
    elif status == "paused":
        # Paused — access continues until period end
        if expires_at:
            payment.grant_pro("subscription", expires_at=expires_at)
    elif status in ("canceled", "past_due"):
        payment.revoke_pro()
    else:
        # Unknown status — update expiry if we have one, keep Pro
        if expires_at:
            from project.extensions import db

            payment.pro_expires_at = expires_at
            db.session.commit()

    logger.info("Paddle: subscription.updated for user_id=%d status=%s", user.id, status)


def _handle_subscription_canceled(data: dict[str, Any]) -> None:
    """Set expiry to billing period end (or immediately revoke) on cancellation."""
    import datetime

    user = _resolve_user(data)
    if user is None:
        return

    payment = _ensure_payment(user)

    # Honour the remaining period: keep Pro active until the period end
    expires_at = _parse_billing_period_end(data)
    if expires_at and expires_at > datetime.datetime.utcnow():
        from project.extensions import db

        payment.pro_expires_at = expires_at
        db.session.commit()
        logger.info(
            "Paddle: subscription.canceled for user_id=%d — Pro expires at %s",
            user.id,
            expires_at,
        )
    else:
        payment.revoke_pro()
        logger.info("Paddle: subscription.canceled for user_id=%d — Pro revoked immediately", user.id)


def _parse_billing_period_end(data: dict[str, Any]):
    """Parse current_billing_period.ends_at → datetime | None."""
    import datetime

    period = data.get("current_billing_period") or {}
    ends_at_str = period.get("ends_at")
    if not ends_at_str:
        return None
    try:
        # ISO 8601 with Z suffix (Python 3.11+ handles Z directly)
        ends_at_str = ends_at_str.replace("Z", "+00:00")
        dt = datetime.datetime.fromisoformat(ends_at_str)
        # Return naive UTC for consistency with existing codebase
        return dt.replace(tzinfo=None)
    except ValueError, AttributeError:
        logger.warning("Paddle: could not parse billing period ends_at: %r", ends_at_str)
        return None
