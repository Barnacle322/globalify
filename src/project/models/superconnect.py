from __future__ import annotations

import datetime
from collections.abc import Sequence
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, desc, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship, validates

from src.project.models.helpers import Industry

from ..extensions import db
from ..utils.enums import EventStatus, EventType, QualificationType

if TYPE_CHECKING:
    from .user import User


expert_industry = db.Table(
    "expert_industry",
    Column("expert_id", Integer, ForeignKey("expert.id"), primary_key=True),
    Column("industry_id", Integer, ForeignKey("industry.id"), primary_key=True),
)


class Expert(MappedAsDataclass, db.Model, unsafe_hash=True):
    user: Mapped[User | None] = relationship("User", back_populates="expert", uselist=False)
    qualifications: Mapped[list[Qualification]] = relationship(
        "Qualification", back_populates="expert", uselist=True, init=False
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=True)
    bio: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    description: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    picture_url: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    current_position_id: Mapped[int] = mapped_column(Integer, nullable=True, default=None)
    industries: Mapped[list[Industry]] = relationship(secondary=expert_industry, nullable=True, default=None)  # Maybe??
    # minimum_notice_minutes: Mapped[int] = mapped_column(Integer, default=60)
    # minimum_free_time: Mapped[int] = mapped_column(Integer, default=15)
    created_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), init=False
    )

    # time_slots: Mapped[list[TimeSlot]] = relationship("TimeSlot", back_populates="expert", uselist=True, init=False)
    # events: Mapped[list[Event]] = relationship("Events", back_populates="expert", uselist=True, init=False)

    # def __repr__(self):
    #     return f"<Exper {self.user.user_info.first_name} {self.user.user_info.last_name}>"

    # @property
    # def full_name(self) -> str:
    #     return f"{self.user.user_info.first_name} {self.user.user_info.last_name or ''}"

    @validates("industries")  # limit??
    def validate_industries(self, key, industries):
        if len(industries) > 5:
            raise ValueError("An expert can have at most 5 industries.")
        return industries

    @staticmethod
    def get_by_id(id: int) -> Expert | None:
        return db.session.scalar(db.select(Expert).where(Expert.id == id))

    @staticmethod
    def get_all() -> Sequence[Expert] | None:
        return (db.session.scalars(db.select(Expert))).all()


class Qualification(MappedAsDataclass, db.Model, unsafe_hash=True):
    expert: Mapped[Expert] = relationship("Expert", back_populates="qualifications", init=False)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    expert_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("expert.id", ondelete="CASCADE"), nullable=False, init=False
    )
    type: Mapped[QualificationType] = mapped_column(SQLEnum(QualificationType), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    start_date: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    company_id: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    company_name: Mapped[str | None] = mapped_column(String, nullable=False, default=None)
    company_description: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    company_url: Mapped[str | None] = mapped_column(String, nullable=True, default=None)


# Change name
# class Event(MappedAsDataclass, db.Model, unsafe_hash=True):
#     expert: Mapped[Expert] = relationship("Expert", back_populates="events")
#     user: Mapped[User] = relationship("User", back_populates="events")
#     time_slot: Mapped[TimeSlot] = relationship("TimeSlot", back_populates="event")

#     id: Mapped[int] = mapped_column(Integer, primary_key=True)
#     expert_id: Mapped[int] = mapped_column(Integer, ForeignKey("expert.id", ondelete="CASCADE"), nullable=False)
#     user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
#     time_slot_id: Mapped[int] = mapped_column(Integer, ForeignKey("time_slot.id"), nullable=False)
#     title: Mapped[str] = mapped_column(String, nullable=False)
#     description: Mapped[str | None] = mapped_column(String, nullable=True)
#     url: Mapped[str] = mapped_column(String, nullable=False)
#     location_url: Mapped[str] = mapped_column(String, nullable=False)
#     created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
#     updated_at: Mapped[datetime.datetime] = mapped_column(
#         DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
#     )
#     type: Mapped[EventType] = mapped_column(SQLEnum(EventType), nullable=False, default=EventType.SHORT)
#     status: Mapped[EventStatus] = mapped_column(SQLEnum(EventStatus), nullable=True, default=EventStatus.UNCONFIRMED)

#     @staticmethod
#     def get_by_id(event_id: int) -> Event | None:
#         return db.session.scalar(db.select(Event).where(Event.id == event_id))

#     @staticmethod
#     def get_all() -> Sequence[Event] | None:
#         return (db.session.scalars(db.select(Event))).all()

#     @staticmethod
#     def get_all_by_user_id(user_id: int) -> Sequence[Event] | None:
#         return db.session.scalars((db.select(Event).where(Event.user_id == user_id)).order_by(Event.updated_at)).all()

#     @staticmethod
#     def get_all_by_user_id_and_status(user_id: int, status: str) -> Sequence[Event] | None:
#         return db.session.scalars(
#             db.select(Event)
#             .join(Event)
#             .where(Event.user_id == user_id, Event.status.is_(status))
#             .order_by(desc(Event.created_at))
#         ).all()

#     @staticmethod
#     def get_all_upcoming_by_user_id(user_id: int) -> Sequence[Event] | None:
#         return db.session.scalars(
#             db.select(Event)
#             .join(TimeSlot, Event.time_slot_id == TimeSlot.id)
#             .where(Event.user_id == user_id, TimeSlot.start_time > func.now())
#             .order_by(TimeSlot.start_time.asc())
#         ).all()

#     @staticmethod
#     def get_all_past_bookings_by_user_id(user_id: int) -> Sequence[Event] | None:
#         return db.session.scalars(
#             db.select(Event)
#             .join(TimeSlot, Event.time_slot_id == TimeSlot.id)
#             .where(Event.user_id == user_id, TimeSlot.start_time < func.now())
#             .order_by(Event.created_at.desc())
#         ).all()


# class TimeSlot(MappedAsDataclass, db.Model, unsafe_hash=True):
#     expert: Mapped[Expert] = relationship("Expert", back_populates="time_slots")
#     event: Mapped[Event] = relationship("Event", back_populates="time_slot", uselist=False)

#     id: Mapped[int] = mapped_column(Integer, primary_key=True)
#     expert_id: Mapped[int] = mapped_column(Integer, ForeignKey("expert.id", ondelete="CASCADE"), nullable=False)
#     start_time: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
#     end_time: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
#     is_booked: Mapped[bool] = mapped_column(Boolean, default=False)
