from __future__ import annotations

import datetime
from collections.abc import Sequence
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import (
    Mapped,
    MappedAsDataclass,
    mapped_column,
    relationship,
)

from ..extensions import db

if TYPE_CHECKING:
    from . import User


class PitchDeck(MappedAsDataclass, db.Model, unsafe_hash=True):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    unique_id: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[str | None] = mapped_column(String, nullable=False)
    overall_recommendation: Mapped[str | None] = mapped_column(String, nullable=False)
    created: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), init=False)

    user: Mapped[User] = relationship("User", back_populates="pitch_deck", init=False)
    scores: Mapped[Scores] = relationship(
        back_populates="pitch_deck", uselist=False, cascade="all, delete-orphan", init=False
    )
    deck_lists: Mapped[list[DeckList]] = relationship(
        "DeckList", back_populates="pitch_deck", cascade="all, delete-orphan", init=False
    )

    @staticmethod
    def get_all() -> Sequence[PitchDeck] | None:
        return db.session.scalars(db.select(PitchDeck)).all()

    @staticmethod
    def get_by_id(id: int) -> PitchDeck | None:
        return db.session.scalar(db.select(PitchDeck).where(PitchDeck.id == id))

    @staticmethod
    def get_by_user_id(user_id: int) -> Sequence[PitchDeck] | None:
        return db.session.scalars(db.select(PitchDeck).where(PitchDeck.user_id == user_id)).all()


class Scores(MappedAsDataclass, db.Model, unsafe_hash=True):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    pitch_deck_id: Mapped[int] = mapped_column(Integer, ForeignKey("pitch_deck.id"), init=False)
    clarity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    grammary: Mapped[int | None] = mapped_column(Integer, nullable=True)
    storytelling: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completeness: Mapped[int | None] = mapped_column(Integer, nullable=True)
    engagement: Mapped[int | None] = mapped_column(Integer, nullable=True)

    pitch_deck: Mapped[PitchDeck] = relationship(back_populates="scores")

    @staticmethod
    def get_by_id(id: int) -> Scores | None:
        return db.session.scalar(db.select(Scores).where(Scores.id == id))

    @staticmethod
    def get_all() -> Sequence[Scores] | None:
        return db.session.scalars(db.select(Scores)).all()

    @staticmethod
    def get_by_pitch_deck_id(pitch_deck_id: int) -> Sequence[Scores] | None:
        return db.session.scalars(db.select(Scores).where(Scores.pitch_deck_id == pitch_deck_id)).all()


class DeckList(MappedAsDataclass, db.Model, unsafe_hash=True):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    pitch_deck_id: Mapped[int] = mapped_column(Integer, ForeignKey("pitch_deck.id"), init=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    feed_back: Mapped[str | None] = mapped_column(String, nullable=False)

    pitch_deck: Mapped[PitchDeck] = relationship("PitchDeck", back_populates="deck_lists")

    @staticmethod
    def get_by_id(id: int) -> DeckList | None:
        return db.session.scalar(db.select(DeckList).where(DeckList.id == id))

    @staticmethod
    def get_all() -> Sequence[DeckList] | None:
        return db.session.scalars(db.select(DeckList)).all()

    @staticmethod
    def get_by_pitch_deck_id(pitch_deck_id: int) -> Sequence[DeckList] | None:
        return db.session.scalars(db.select(DeckList).where(DeckList.pitch_deck_id == pitch_deck_id)).all()
