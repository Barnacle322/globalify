from __future__ import annotations

import datetime
from collections.abc import Sequence
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, func
from sqlalchemy.orm import (
    Mapped,
    MappedAsDataclass,
    mapped_column,
    relationship,
)

from ..extensions import db

if TYPE_CHECKING:
    from ..models import Investor, Round


class Investment(MappedAsDataclass, db.Model, unsafe_hash=True):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    funding_round_id: Mapped[int] = mapped_column(Integer, ForeignKey("funding_round.id"), nullable=False)
    investor_id: Mapped[int] = mapped_column(Integer, ForeignKey("investor.id"), nullable=False)
    is_lead_investor: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    funding_round: Mapped[FundingRound] = relationship("FundingRound", back_populates="investments", init=False)
    investor: Mapped[Investor] = relationship("Investor", back_populates="investments", init=False)


class FundingRound(MappedAsDataclass, db.Model, unsafe_hash=True):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    organization_name: Mapped[str] = mapped_column(String, nullable=False)
    announced_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    round_id: Mapped[int] = mapped_column(Integer, ForeignKey("round.id"), nullable=False)

    investments: Mapped[Investment] = relationship("Investment", back_populates="funding_round", init=False)
    round: Mapped[Round] = relationship("Round", back_populates="funding_rounds", init=False)

    @staticmethod
    def get_by_id(id: int) -> FundingRound | None:
        return db.session.scalar(db.select(FundingRound).where(FundingRound.id == id))

    @staticmethod
    def get_all() -> Sequence[FundingRound] | None:
        return db.session.scalars(db.select(FundingRound)).all()
