from __future__ import annotations

import datetime
from collections.abc import Sequence
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, exists, func
from sqlalchemy.orm import (
    Mapped,
    MappedAsDataclass,
    mapped_column,
    relationship,
)

from ..extensions import db

if TYPE_CHECKING:
    from . import User


class Deck(MappedAsDataclass, db.Model, unsafe_hash=True):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    overall_recommendation: Mapped[str | None] = mapped_column(String, nullable=False)
    json_feedback: Mapped[dict] = mapped_column(JSON, nullable=False, default=False)
    created: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), init=False)

    user: Mapped[User] = relationship("User", back_populates="deck", init=False)
    scores: Mapped[Scores] = relationship(
        back_populates="deck", uselist=False, cascade="all, delete-orphan", init=False
    )

    @staticmethod
    def get_all() -> Sequence[Deck] | None:
        return db.session.scalars(db.select(Deck)).all()

    @staticmethod
    def get_by_id(id: int) -> Deck | None:
        return db.session.scalar(db.select(Deck).where(Deck.id == id))

    @staticmethod
    def get_by_user_id(user_id: int) -> Sequence[Deck] | None:
        return db.session.scalars(db.select(Deck).where(Deck.user_id == user_id)).all()

    @staticmethod
    def check_hash(hash: str) -> bool:
        return db.session.scalar(db.select(exists().where(Deck.hash == hash)))


class Scores(MappedAsDataclass, db.Model, unsafe_hash=True):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    deck_id: Mapped[int] = mapped_column(Integer, ForeignKey("deck.id"), init=False)
    clarity: Mapped[int | None] = mapped_column(Integer, nullable=False)
    grammary: Mapped[int | None] = mapped_column(Integer, nullable=False)
    storytelling: Mapped[int | None] = mapped_column(Integer, nullable=False)
    completeness: Mapped[int | None] = mapped_column(Integer, nullable=False)
    engagement: Mapped[int | None] = mapped_column(Integer, nullable=False)

    deck: Mapped[Deck] = relationship(back_populates="scores")

    @staticmethod
    def get_by_id(id: int) -> Scores | None:
        return db.session.scalar(db.select(Scores).where(Scores.id == id))

    @staticmethod
    def get_all() -> Sequence[Scores] | None:
        return db.session.scalars(db.select(Scores)).all()

    @staticmethod
    def get_by_deck_id(deck_id: int) -> Sequence[Scores] | None:
        return db.session.scalars(db.select(Scores).where(Scores.deck_id == deck_id)).all()
