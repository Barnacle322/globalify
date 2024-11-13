from __future__ import annotations

import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import (
    Mapped,
    MappedAsDataclass,
    mapped_column,
    relationship,
)

from ..extensions import db


class Investment(MappedAsDataclass, db.Model, unsafe_hash=True):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    funding_round_id: Mapped[int] = mapped_column(Integer, ForeignKey("funding_round.id"), nullable=False)
    investor_id: Mapped[int] = mapped_column(Integer, ForeignKey("investor.id"), nullable=False)
    is_lead_investor: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    funding_round: Mapped[FundingRound] = relationship("FundingRound", back_populates="investments", init=False)


class FundingRound(MappedAsDataclass, db.Model, unsafe_hash=True):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_name: Mapped[str] = mapped_column(String, nullable=False)
    announced_date: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    investments: Mapped[Investment] = relationship("Investment", back_populates="funding_round", init=False)

    @staticmethod
    def get_by_id(id: int) -> FundingRound | None:
        return db.session.scalar(db.select(FundingRound).where(FundingRound.id == id))
