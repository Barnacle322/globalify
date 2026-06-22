"""LoginToken — stateful magic-link token model.

Design decisions:
- **Find-or-create User on POST /login** (not on verify): The user row exists
  before the token is stored so the FK is non-nullable.  This is simpler, and
  a magic-link IS the verification proof (is_verified is set True on verify).
- **Token hash stored, never the raw token**: Only sha256(raw) is persisted.
  The one logger.info stub in utils/email/ prints the raw link for dev — that
  is the only place the raw token ever appears outside this classmethod.
"""

from __future__ import annotations

import datetime
import hashlib
import secrets

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from ..extensions import db


class LoginToken(MappedAsDataclass, db.Model, unsafe_hash=True):
    """Single-use, short-lived login token (magic link)."""

    __tablename__ = "login_token"

    # ---- fields without defaults (must appear before fields with defaults) ----
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String, nullable=False)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # ---- fields with defaults ----
    purpose: Mapped[str] = mapped_column(String, nullable=False, default="login")
    consumed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, init=False
    )

    # Relationship back to User (lazy so it doesn't break MappedAsDataclass).
    user: Mapped[User] = relationship("User", lazy="select", init=False)  # noqa: F821

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _hash(raw: str) -> str:
        return hashlib.sha256(raw.encode()).hexdigest()

    # ------------------------------------------------------------------
    # Class-level API
    # ------------------------------------------------------------------

    @classmethod
    def issue(
        cls,
        user: User,  # noqa: F821
        purpose: str = "login",
        ttl_minutes: int = 30,
    ) -> str:
        """Generate a raw URL-safe token, persist its SHA-256 hash, and return
        the raw token for embedding in the magic-link URL.

        The raw token is returned to the caller; it is NEVER stored in the DB.
        """
        raw = secrets.token_urlsafe(32)
        token_hash = cls._hash(raw)
        now = datetime.datetime.now(datetime.UTC)
        expires_at = now + datetime.timedelta(minutes=ttl_minutes)

        record = cls(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            purpose=purpose,
        )
        db.session.add(record)
        db.session.commit()
        return raw

    @classmethod
    def verify_and_consume(cls, raw_token: str, purpose: str = "login") -> User | None:  # noqa: F821
        """Hash the raw token, look up an unconsumed + unexpired row for the
        given purpose, mark it consumed, and return the associated User.

        Returns None on any failure (expired, consumed, wrong purpose, not found).
        """
        token_hash = cls._hash(raw_token)
        now = datetime.datetime.now(datetime.UTC)

        record: LoginToken | None = db.session.scalar(
            db.select(cls).where(
                cls.token_hash == token_hash,
                cls.purpose == purpose,
                cls.consumed_at.is_(None),
                cls.expires_at > now,
            )
        )

        if record is None:
            return None

        record.consumed_at = now
        db.session.commit()
        return record.user
