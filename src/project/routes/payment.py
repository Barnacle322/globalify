"""Paddle Billing routes.

Endpoints:
  POST /payment/webhook  — Paddle webhook receiver (CSRF-exempt, signature-verified)
"""

from __future__ import annotations

import json
import logging

from flask import Blueprint, request
from sqlalchemy.exc import IntegrityError

from ..extensions import csrf, db

logger = logging.getLogger(__name__)

payment = Blueprint("payment", __name__, url_prefix="/payment")


@payment.route("/webhook", methods=["POST"])
@csrf.exempt
def paddle_webhook():
    """Receive and process Paddle webhook events.

    Security:
    - Raw request bytes are read BEFORE any JSON parsing.
    - If the webhook secret is configured, the Paddle-Signature header is
      verified with HMAC-SHA256 + timing-safe compare.  A missing or invalid
      signature returns 400 so Paddle does NOT retry with a bad payload.
    - Idempotency is enforced via the ProcessedWebhook table (unique event_id).
      Duplicate deliveries are silently ignored (200).
    - Handler exceptions return 500 so Paddle retries the delivery.
    """
    from ..config import get_settings
    from ..models.webhook import ProcessedWebhook
    from ..utils.paddle import handle_event, verify_signature

    cfg = get_settings()

    # ------------------------------------------------------------------ #
    # 1. Read raw bytes FIRST — before any framework body parsing.        #
    # ------------------------------------------------------------------ #
    raw = request.get_data()

    # ------------------------------------------------------------------ #
    # 2. Signature verification (only when secret is configured).         #
    # ------------------------------------------------------------------ #
    if cfg.paddle_webhook_is_configured:
        sig_header = request.headers.get("Paddle-Signature")
        if not verify_signature(raw, sig_header, cfg.paddle_webhook_secret):
            logger.warning("Paddle webhook: signature verification failed")
            return ("", 400)
    else:
        logger.debug("Paddle webhook secret not configured — skipping signature check (no-op)")
        return ("", 200)

    # ------------------------------------------------------------------ #
    # 3. Parse JSON.                                                       #
    # ------------------------------------------------------------------ #
    try:
        event = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Paddle webhook: invalid JSON body: %s", exc)
        return ("", 400)

    event_id = event.get("event_id")
    if not event_id:
        logger.warning("Paddle webhook: event missing event_id — rejecting")
        return ("", 400)

    # ------------------------------------------------------------------ #
    # 4. Idempotency — skip already-processed events.                     #
    # ------------------------------------------------------------------ #
    try:
        record = ProcessedWebhook(event_id=event_id)
        db.session.add(record)
        db.session.flush()  # raises IntegrityError on duplicate unique constraint
    except IntegrityError:
        db.session.rollback()
        logger.info("Paddle webhook: duplicate event_id=%s — skipping (idempotent)", event_id)
        return ("", 200)

    # ------------------------------------------------------------------ #
    # 5. Dispatch to handler.  Non-2xx on error so Paddle retries.        #
    # ------------------------------------------------------------------ #
    try:
        handle_event(event, price_id_lifetime=cfg.paddle_price_id_lifetime)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Paddle webhook: unhandled error processing event_id=%s", event_id)
        return ("", 500)

    return ("", 200)
