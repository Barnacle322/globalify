from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    JSON,
    String,
    func,
    Text,
)
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from ..extensions import db

if TYPE_CHECKING:
    from .user import Company


class MicroWebPage(MappedAsDataclass, db.Model, unsafe_hash=True):
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    company_id: Mapped[int] = mapped_column(ForeignKey("company.id", ondelete="CASCADE"), unique=True, nullable=False)
    company: Mapped["Company"] = relationship("Company", back_populates="microwebpage", single_parent=True)

    #First stage fields

    hero_title: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    hero_subtitle: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    mission_title: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    mission_statement: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    leadership_title: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    leadership_subtitle: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    financial_highlights: Mapped[dict] = mapped_column(JSON, nullable=True, default=None)
    customer_testimonials_title: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    customer_testimonials_subtitle: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    customer_testimonials: Mapped[list[dict[str, str]]] = mapped_column(JSON, nullable=True, default=None)
    logo_url: Mapped[str | None] = mapped_column(String, nullable=True, default=None)



    #Second stage fields
    faq: Mapped[list[dict[str, str]]] = mapped_column(JSON, nullable=True, default=None)
    awards: Mapped[list[dict[str, str]]] = mapped_column(JSON, nullable=True, default=None)
    team_title: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    team_subtitle: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    partnerships: Mapped[list[dict[str, str]]] = mapped_column(JSON, nullable=True, default=None)
    sustainability_initiatives: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    legal_structure: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    year_founded: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=None)
    tech_stack: Mapped[list[str]] = mapped_column(JSON, nullable=True, default=None)
    key_products: Mapped[list[dict[str, str]]] = mapped_column(JSON, nullable=True, default=None)
    founder_bio: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    business_model: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    intellectual_property: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    assets: Mapped[str | None] = mapped_column(String(200), nullable=True, default=None)
    target_market: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    market_positioning: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    revenue_streams: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    user_growth: Mapped[list[dict[str, str]]] = mapped_column(JSON, nullable=True, default=None)
    created: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), init=False)

    webpage_media: Mapped[list["WebpageMedia"]] = relationship(
        "WebpageMedia",
        back_populates="micro_webpage",
        cascade="all, delete-orphan",
        default_factory=list
    )

    employees: Mapped[list["WebpageCompanyEmployee"]] = relationship(
        "WebpageCompanyEmployee",
        back_populates="micro_webpage",
        cascade="all, delete-orphan",
        default_factory=list
    )

    @staticmethod
    def get_by_id(id: int) -> "MicroWebPage":
        return db.session.scalar(db.select(MicroWebPage).where(MicroWebPage.id == id))


class WebpageMedia(MappedAsDataclass, db.Model, unsafe_hash=True):
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    micro_webpage_id: Mapped[int] = mapped_column(ForeignKey("micro_web_page.id"), nullable=False)
    micro_webpage: Mapped["MicroWebPage"] = relationship("MicroWebPage", back_populates="webpage_media")
    press_kit_url: Mapped[str | None] = mapped_column(String)
    picture_url: Mapped[str | None] = mapped_column(String, nullable=True, default=None)


class WebpageCompanyEmployee(MappedAsDataclass, db.Model, unsafe_hash=True):
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    micro_webpage_id: Mapped[int] = mapped_column(ForeignKey("micro_web_page.id"), nullable=False)
    micro_webpage: Mapped["MicroWebPage"] = relationship("MicroWebPage", back_populates="employees")

    first_name: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    last_name: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    position: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)

