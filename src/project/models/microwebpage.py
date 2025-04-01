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
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from ..extensions import db

if TYPE_CHECKING:
    from .user import Company




class MicroWebPage(MappedAsDataclass, db.Model, unsafe_hash=True):
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("company.id", ondelete="CASCADE"), unique=True, nullable=False)
    company: Mapped["Company"] = relationship("Company", back_populates="microwebpage", single_parent=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    logo_url: Mapped[str] = mapped_column(String(500), nullable=True)
    website_url: Mapped[str] = mapped_column(String(500), nullable=True)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[str] = mapped_column(db.DateTime, server_default=db.func.now())
    employee_number: Mapped[int] = mapped_column(Integer, nullable=True, default=0)

    @staticmethod
    def get_by_id(id: int) -> MicroWebPage:
        return db.session.scalar(db.select(MicroWebPage).where(MicroWebPage.id == id))


