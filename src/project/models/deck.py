from __future__ import annotations

import datetime
from collections.abc import Sequence
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Table, desc, func
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
    hash: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    # picture_url: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), init=False)

    users: Mapped[list[User]] = relationship(
        "User", secondary=user_deck_association, back_populates="decks", uselist=True, init=False
    )
    scores: Mapped[list[Scores]] = relationship(back_populates="deck", cascade="all, delete-orphan", init=False)

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
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), init=False)
    audience: Mapped[str] = mapped_column(String, nullable=False)
    formality: Mapped[str] = mapped_column(String, nullable=False)
    domain: Mapped[str] = mapped_column(String, nullable=False)
    agent: Mapped[str] = mapped_column(String, nullable=False)
    clarity_score: Mapped[int] = mapped_column(Integer, nullable=False)
    grammar_score: Mapped[int] = mapped_column(Integer, nullable=False)
    design_score: Mapped[int] = mapped_column(Integer, nullable=False)
    storytelling_score: Mapped[int] = mapped_column(Integer, nullable=False)
    engagement_score: Mapped[int] = mapped_column(Integer, nullable=False)
    page_feedback: Mapped[dict] = mapped_column(JSON, nullable=False)
    recommendation: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), init=False) #default order

    user: Mapped[User] = relationship(back_populates="scores", uselist=False, init=False)
    deck: Mapped[Deck] = relationship(back_populates="scores", uselist=False, init=False)

    @staticmethod
    def get_by_id(id: int) -> Scores | None:
        return db.session.scalar(db.select(Scores).where(Scores.id == id))

    @staticmethod
    def get_all() -> Sequence[Scores] | None:
        return db.session.scalars(db.select(Scores)).all()

    @staticmethod
    def get_by_deck_id(deck_id: int) -> Sequence[Scores] | None:
        return db.session.scalars(db.select(Scores).where(Scores.deck_id == deck_id)).all()

    @staticmethod
    def get_by_deck_user_and_goals(
        deck_id: int,
        user_id: int,
        audience: str,
        formality: str,
        domain: str,
    ) -> Scores | None:
        return db.session.scalar(
            db.select(Scores).where(
                Scores.deck_id == deck_id,
                Scores.user_id == user_id,
                Scores.audience == audience,
                Scores.formality == formality,
                Scores.domain == domain,
            )
        )

    @staticmethod
    def get_by_deck_user_sorted(
        deck_id: int,
        user_id: int,
    ) -> Sequence[Scores] | None:
        return db.session.scalars(
            db.select(Scores)
            .where(
                Scores.deck_id == deck_id,
                Scores.user_id == user_id,
            )
            .order_by(desc(Scores.created_at))
        ).all()

    @property
    def overall_score(self) -> float:
        if self:
            return (
                (self.clarity or 0)
                + (self.grammar or 0)
                + (self.storytelling or 0)
                + (self.completeness or 0)
                + (self.engagement or 0)
            ) / 5.0
        return 0
