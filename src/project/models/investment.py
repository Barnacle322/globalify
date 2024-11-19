from __future__ import annotations

import datetime
from collections.abc import Sequence
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, asc, desc, func
from sqlalchemy.orm import (
    Mapped,
    MappedAsDataclass,
    aliased,
    joinedload,
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

    @staticmethod
    def get_all() -> Sequence[Investment] | None:
        return db.session.scalars(db.select(Investment)).all()

    @staticmethod
    def get_by_investor_id(
        investor_id: int, sort_by: str | None = None, descending: bool = False
    ) -> Sequence[Investment] | None:
        query = db.select(Investment).where(Investment.investor_id == investor_id)

        if sort_by:
            if sort_by == "announced_date":
                funding_round_alias = aliased(FundingRound)
                query = query.join(funding_round_alias, Investment.funding_round)
                query = query.options(joinedload(Investment.funding_round))
                if descending:
                    query = query.order_by(desc(funding_round_alias.announced_date))
                else:
                    query = query.order_by(asc(funding_round_alias.announced_date))
            else:
                if descending:
                    query = query.order_by(desc(getattr(Investment, sort_by)))
                else:
                    query = query.order_by(asc(getattr(Investment, sort_by)))

        return db.session.scalars(query).all()


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
