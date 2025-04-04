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
    assets: Mapped[str] = mapped_column(String(200), nullable=True)
    mission_statement: Mapped[str | None] = mapped_column(Text)
    awards: Mapped[str | None] = mapped_column(Text)
    partnerships: Mapped[str | None] = mapped_column(Text)
    team_description: Mapped[str | None] = mapped_column(Text)
    target_market: Mapped[str | None] = mapped_column(Text)
    customer_testimonials: Mapped[str | None] = mapped_column(Text)
    key_products: Mapped[str | None] = mapped_column(Text)
    founder_bio: Mapped[str | None] = mapped_column(Text)
    created: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), init=False)
    logo_url: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    photos: Mapped[list["WebpagePhoto"]] = relationship(
        "WebpagePhoto",
        back_populates="micro_webpage",
        cascade="all, delete-orphan",
        default_factory=list  # Default empty list
    )
    employees: Mapped[list["WebpageCompanyEmployee"]] = relationship(
        "WebpageCompanyEmployee",
        back_populates="micro_webpage",
        cascade="all, delete-orphan",
        default_factory=list  # Default empty list
    )

    @staticmethod
    def get_by_id(id: int) -> MicroWebPage:
        return db.session.scalar(db.select(MicroWebPage).where(MicroWebPage.id == id))


class WebpagePhoto(MappedAsDataclass, db.Model, unsafe_hash=True):
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    micro_webpage_id: Mapped[int] = mapped_column(ForeignKey("micro_web_page.id"), nullable=False)
    micro_webpage: Mapped["MicroWebPage"] = relationship("MicroWebPage", back_populates="photos")

    picture_url: Mapped[str | None] = mapped_column(String, nullable=True, default=None)


class WebpageCompanyEmployee(MappedAsDataclass, db.Model, unsafe_hash=True):
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    micro_webpage_id: Mapped[int] = mapped_column(ForeignKey("micro_web_page.id"), nullable=False)
    micro_webpage: Mapped["MicroWebPage"] = relationship("MicroWebPage", back_populates="employees")
    first_name: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    last_name: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    position: Mapped[str | None] = mapped_column(String, nullable=True, default=None)

