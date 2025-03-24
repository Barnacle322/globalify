from __future__ import annotations

import datetime
from collections.abc import Sequence
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Table, func
from sqlalchemy.orm import (
    Mapped,
    MappedAsDataclass,
    mapped_column,
    relationship,
)

from ..extensions import db

if TYPE_CHECKING:
    from . import User


user_deck_association = Table(
    "user_deck",
    db.metadata,
    Column("user_id", Integer, ForeignKey("user.id"), primary_key=True),
    Column("deck_id", Integer, ForeignKey("deck.id"), primary_key=True),
)


class Deck(MappedAsDataclass, db.Model, unsafe_hash=True):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=False)
    # thumbnail_url: Mapped[str | None] = mapped_column(String, nullable=True)
    # file_format: Mapped[str | None] = mapped_column(String, nullable=True)
    overall_recommendation: Mapped[str | None] = mapped_column(String, nullable=False)
    json_feedback: Mapped[dict] = mapped_column(JSON, nullable=False, default=False)
    created: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), init=False)

    users: Mapped[list[User]] = relationship(
        "User", secondary=user_deck_association, back_populates="decks", uselist=True, init=False
    )
    scores: Mapped[Scores] = relationship(
        back_populates="deck", uselist=False, cascade="all, delete-orphan", init=False
    )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.overall_recommendation,
            "file_hash": self.hash,
            "created": self.created.isoformat(),
            "json_feedback": self.json_feedback,
        }

    @staticmethod
    def get_all() -> Sequence[Deck] | None:
        return db.session.scalars(db.select(Deck)).all()

    @staticmethod
    def get_by_id(id: int) -> Deck | None:
        return db.session.scalar(db.select(Deck).where(Deck.id == id))

    @staticmethod
    def get_by_user_id(user_id: int) -> Sequence[Deck] | None:
        return db.session.scalars(
            db.select(Deck).join(user_deck_association).filter(user_deck_association.c.user_id == user_id)
        ).all()

    @staticmethod
    def get_by_hash(hash: str) -> Deck:
        return db.session.scalar(db.select(Deck).where(Deck.hash == hash))


class Scores(MappedAsDataclass, db.Model, unsafe_hash=True):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    deck_id: Mapped[int] = mapped_column(Integer, ForeignKey("deck.id"), init=False)
    clarity: Mapped[int | None] = mapped_column(Integer, nullable=False)
    grammary: Mapped[int | None] = mapped_column(Integer, nullable=False)
    storytelling: Mapped[int | None] = mapped_column(Integer, nullable=False)
    completeness: Mapped[int | None] = mapped_column(Integer, nullable=False)
    engagement: Mapped[int | None] = mapped_column(Integer, nullable=False)

    deck: Mapped[Deck] = relationship(back_populates="scores")

    def to_dict(self):
        return {
            "clarity": self.clarity,
            "grammary": self.grammary,
            "storytelling": self.storytelling,
            "completeness": self.completeness,
            "engagement": self.engagement,
        }

    @staticmethod
    def get_by_id(id: int) -> Scores | None:
        return db.session.scalar(db.select(Scores).where(Scores.id == id))

    @staticmethod
    def get_all() -> Sequence[Scores] | None:
        return db.session.scalars(db.select(Scores)).all()

    @staticmethod
    def get_by_deck_id(deck_id: int) -> Sequence[Scores] | None:
        return db.session.scalars(db.select(Scores).where(Scores.deck_id == deck_id)).all()
