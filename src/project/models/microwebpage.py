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
    Boolean
)
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from ..extensions import db

if TYPE_CHECKING:
    from .user import Company


class MicroWebPage(MappedAsDataclass, db.Model, unsafe_hash=True):
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    company_id: Mapped[int] = mapped_column(ForeignKey("company.id", ondelete="CASCADE"), unique=True, nullable=False)
    company: Mapped["Company"] = relationship("Company", back_populates="microwebpage", single_parent=True)
    logo_url: Mapped[str | None] = mapped_column(String, nullable=True, default=None)

    #Hero section
    hero_title: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    hero_subtitle: Mapped[str | None] = mapped_column(String, nullable=True, default=None)

    #Logo Clouds section
    logo_cloud_title: Mapped[str | None] = mapped_column(String, nullable=True, default=None)

    #Benefit section
    benefit_title: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    benefit_subtitle: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    benefit_statement: Mapped[list[dict[str, str]]] = mapped_column(JSON, nullable=True, default=None)

    #Statistic section
    stat_title: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    stat_subtitle: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    statistics: Mapped[list[dict[str, str]]] = mapped_column(JSON, nullable=True, default=None)

    #Mission section
    mission_title: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    mission_statement: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    leadership_title: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    leadership_subtitle: Mapped[str | None] = mapped_column(String, nullable=True, default=None)

    # Customer Testimonials section:
    customer_testimonials_title: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    customer_testimonials_subtitle: Mapped[str | None] = mapped_column(String, nullable=True, default=None)

    #FAQ section
    faq_title: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    faq: Mapped[list[dict[str, str]]] = mapped_column(JSON, nullable=True, default=None)

    #About section
    about_title: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    about_subtitle: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    about_statement: Mapped[list[dict[str, str]]] = mapped_column(JSON, nullable=True, default=None)

    #Values section
    values_title: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    values_subtitle: Mapped[str| None] = mapped_column(String, nullable=True, default=None)
    values_statement: Mapped[list[dict[str, str]]] = mapped_column(JSON, nullable=True, default=None)

    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
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
    customers: Mapped[list["WebpageCompanyCustomer"]] = relationship(
        "WebpageCompanyCustomer",
        back_populates="micro_webpage",
        cascade="all, delete-orphan",
        default_factory=list
    )

    @staticmethod
    def get_by_id(id: int) -> "MicroWebPage":
        return db.session.scalar(db.select(MicroWebPage).where(MicroWebPage.id == id))


class WebpageMedia(MappedAsDataclass, db.Model, unsafe_hash=True,):
    id: Mapped[int] = mapped_column(primary_key=True, init=False, )
    micro_webpage_id: Mapped[int] = mapped_column(ForeignKey("micro_web_page.id"), nullable=False)
    micro_webpage: Mapped["MicroWebPage"] = relationship("MicroWebPage", back_populates="webpage_media")
    press_kit_url: Mapped[str | None] = mapped_column(String)
    picture_url: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    logo_url: Mapped[str | None] = mapped_column(String, nullable=True, default=None)


class WebpageCompanyEmployee(MappedAsDataclass, db.Model, unsafe_hash=True):
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    micro_webpage_id: Mapped[int] = mapped_column(ForeignKey("micro_web_page.id"), nullable=False)
    micro_webpage: Mapped["MicroWebPage"] = relationship("MicroWebPage", back_populates="employees")

    first_name: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    last_name: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    position: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    picture_url: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)


class WebpageCompanyCustomer(MappedAsDataclass, db.Model, unsafe_hash=True):
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    micro_webpage_id: Mapped[int] = mapped_column(ForeignKey("micro_web_page.id"), nullable=False)
    micro_webpage: Mapped["MicroWebPage"] = relationship("MicroWebPage", back_populates="customers")

    first_name: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    last_name: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    position: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    picture_url: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
