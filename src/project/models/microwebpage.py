from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
    Text
)
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from ..extensions import db

if TYPE_CHECKING:
    from .user import Company




class MicroWebPage(MappedAsDataclass, db.Model, unsafe_hash=True):
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    company_id: Mapped[int] = mapped_column(ForeignKey("company.id", ondelete="CASCADE"), unique=True, nullable=False)
    company: Mapped["Company"] = relationship("Company", back_populates="microwebpage", single_parent=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    assets: Mapped[str] = mapped_column(String(200), nullable=False)
    created: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), init=False)



    @staticmethod
    def get_by_id(id: int) -> MicroWebPage:
        return db.session.scalar(db.select(MicroWebPage).where(MicroWebPage.id == id))


