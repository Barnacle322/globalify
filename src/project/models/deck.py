from __future__ import annotations

import datetime
import json
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
    name: Mapped[str] = mapped_column(String, nullable=True, init=False)
    hash: Mapped[str] = mapped_column(String, nullable=False)
    # picture_url: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), init=False
    )

    users: Mapped[list[User]] = relationship(
        "User", secondary=user_deck_association, back_populates="decks", uselist=True, init=False
    )
    feedbacks: Mapped[list[Feedback]] = relationship(back_populates="deck", cascade="all, delete-orphan", init=False)

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

    @property
    def overall_score(self) -> float:
        if self.feedbacks:
            return sum([feedback.overall_score for feedback in self.feedbacks]) / len(self.feedbacks)
        return 0


class Feedback(MappedAsDataclass, db.Model, unsafe_hash=True):
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
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), init=False
    )  # default order
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), init=False
    )  # default order

    user: Mapped[User] = relationship(back_populates="feedbacks", uselist=False, init=False)
    deck: Mapped[Deck] = relationship(back_populates="feedbacks", uselist=False, init=False)

    @staticmethod
    def get_by_id(id: int) -> Feedback | None:
        return db.session.scalar(db.select(Feedback).where(Feedback.id == id))

    @staticmethod
    def get_by_user_id(id: int) -> Sequence[Feedback] | None:
        return db.session.scalars(db.select(Feedback).where(Feedback.user_id == id)).all()

    @staticmethod
    def get_all() -> Sequence[Feedback] | None:
        return db.session.scalars(db.select(Feedback)).all()

    @staticmethod
    def get_by_deck_id(deck_id: int) -> Sequence[Feedback] | None:
        return db.session.scalars(db.select(Feedback).where(Feedback.deck_id == deck_id)).all()

    @staticmethod
    def get_latest_by_deck_id(deck_id: int) -> Feedback | None:
        return db.session.scalar(
            db.select(Feedback).where(Feedback.deck_id == deck_id).order_by(desc(Feedback.created_at))
        )

    @staticmethod
    def get_by_deck_user_and_goals(
        deck_id: int,
        user_id: int,
        audience: str,
        formality: str,
        domain: str,
    ) -> Feedback | None:
        return db.session.scalar(
            db.select(Feedback).where(
                Feedback.deck_id == deck_id,
                Feedback.user_id == user_id,
                Feedback.audience == audience,
                Feedback.formality == formality,
                Feedback.domain == domain,
            )
        )

    @staticmethod
    def get_by_deck_user_sorted(
        deck_id: int,
        user_id: int,
    ) -> Sequence[Feedback] | None:
        return db.session.scalars(
            db.select(Feedback)
            .where(
                Feedback.deck_id == deck_id,
                Feedback.user_id == user_id,
            )
            .order_by(desc(Feedback.created_at))
        ).all()

    @property
    def overall_score(self) -> float:
        if self:
            return (
                (self.clarity_score or 0)
                + (self.grammar_score or 0)
                + (self.design_score or 0)
                + (self.storytelling_score or 0)
                + (self.engagement_score or 0)
            ) / 5.0
        return 0

    @classmethod
    def create_from_json(cls, analysis_data: dict, goals: dict[str, str], current_user: User) -> Feedback | None:
        try:
            scores = analysis_data.get("feedback", {})
            page_feedback_list = analysis_data.get("page_feedback", [])

            # Создаем объект Feedback
            feedback = cls(
                audience=goals["audience"],
                formality=goals["formality"],
                domain=goals["domain"],
                agent=goals["agent"],
                clarity_score=scores.get("clarity"),
                grammar_score=scores.get("grammar"),
                design_score=scores.get("design"),
                storytelling_score=scores.get("storytelling"),
                engagement_score=scores.get("engagement"),
                recommendation=analysis_data.get("recommendation", ""),
                page_feedback=page_feedback_list,
            )
            feedback.user = current_user

            return feedback

        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            db.session.rollback()
            return None
        except Exception as e:
            print(f"Error creating feedback: {e}")
            db.session.rollback()
            return None
