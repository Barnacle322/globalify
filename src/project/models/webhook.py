"""Idempotency table for Paddle webhook events.

Stores the event_id of every successfully processed webhook so that
re-deliveries (Paddle retries) are silently skipped rather than re-applied.
"""

from __future__ import annotations

import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from ..extensions import db


class ProcessedWebhook(MappedAsDataclass, db.Model, unsafe_hash=True):
    """One row per processed Paddle event_id."""

    __tablename__ = "processed_webhook"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    event_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    processed_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        init=False,
    )
