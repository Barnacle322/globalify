from __future__ import annotations

import datetime
from collections.abc import Sequence
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from ..extensions import db
from ..utils.enums import EntityType, RequestStatus

if TYPE_CHECKING:
    from .user import User


class ClaimVerification(MappedAsDataclass, db.Model, unsafe_hash=True):
    user: Mapped[User] = relationship("User", back_populates="claim_verifications", init=False)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    token: Mapped[str] = mapped_column(String, nullable=False, insert_default=lambda: str(uuid4()), init=False)
    is_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, init=False
    )
    # Polymorphic entity reference (Phase 1b)
    entity_type: Mapped[EntityType | None] = mapped_column(
        SQLEnum(EntityType, name="entity_type"), nullable=True, default=None, kw_only=True
    )
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None, kw_only=True)

    @property
    def is_expired(self) -> bool:
        expiration_time = self.created_at + datetime.timedelta(minutes=5)
        return datetime.datetime.now(datetime.UTC) > expiration_time.replace(tzinfo=datetime.UTC)

    @property
    def is_resendable(self) -> bool:
        expiration_time = self.created_at + datetime.timedelta(minutes=1)
        return datetime.datetime.now(datetime.UTC) > expiration_time.replace(tzinfo=datetime.UTC)

    @staticmethod
    def expire_all_by_user_id(user_id: int) -> None:
        try:
            claim_verifications = db.session.scalars(
                db.select(ClaimVerification).where(ClaimVerification.user_id == user_id)
            ).all()
            for claim_verification in claim_verifications:
                claim_verification.is_expired = True
            db.session.commit()
        except Exception:
            db.session.rollback()

    @staticmethod
    def get_by_token(token: str) -> ClaimVerification | None:
        return db.session.scalar(db.select(ClaimVerification).where(ClaimVerification.token == token))

    @staticmethod
    def get_last_unused_by_user_id(user_id: int) -> ClaimVerification | None:
        last_verification = db.session.scalar(
            db.select(ClaimVerification)
            .where(ClaimVerification.user_id == user_id)
            .where(ClaimVerification.is_used.is_(False))
            .order_by(ClaimVerification.created_at.desc())
        )
        return last_verification


class ClaimRequest(db.Model):
    user: Mapped[User] = relationship("User", back_populates="claim_requests", uselist=False)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    # Polymorphic entity reference (Phase 1b)
    entity_type: Mapped[EntityType | None] = mapped_column(
        SQLEnum(EntityType, name="entity_type"), nullable=True, default=None
    )
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    status: Mapped[RequestStatus] = mapped_column(SQLEnum(RequestStatus), nullable=False, default=RequestStatus.PENDING)
    status_info: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    approved_by: Mapped[int] = mapped_column(Integer, nullable=True, default=None)
    approved_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    email: Mapped[str] = mapped_column(String, nullable=True, default=None)
    requested_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<ClaimRequest {self.id}>"

    @staticmethod
    def get_by_id(id: int) -> ClaimRequest | None:
        return db.session.scalar(db.select(ClaimRequest).where(ClaimRequest.id == id))

    @staticmethod
    def get_by_user_id(user_id: int) -> ClaimRequest | None:
        return db.session.scalar(db.select(ClaimRequest).where(ClaimRequest.user_id == user_id))

    @staticmethod
    def get_all() -> Sequence[ClaimRequest]:
        """Return all ClaimRequests (ORM only — no raw table() literals)."""
        return db.session.scalars(db.select(ClaimRequest)).unique().all()

    @staticmethod
    def get_pending_by_user_id(user_id: int) -> Sequence[ClaimRequest]:
        """Return pending requests for a user (ORM only — no raw table() literals)."""
        return db.session.scalars(
            db.select(ClaimRequest)
            .where(ClaimRequest.user_id == user_id)
            .where(ClaimRequest.status == RequestStatus.PENDING)
        ).all()
