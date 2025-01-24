from __future__ import annotations

import datetime
from collections.abc import Sequence
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from ..extensions import db
from ..utils.enums import SenderType

if TYPE_CHECKING:
    from ..models import User


class Chat(MappedAsDataclass, db.Model, unsafe_hash=True):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    created: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), init=False)

    user: Mapped[User] = relationship("User", back_populates="messages", init=False)

    messages: Mapped[list[Message]] = relationship("Message", back_populates="chat", init=False)

    @staticmethod
    def get_all() -> Sequence[Chat] | None:
        return db.session.scalars(db.select(Chat)).all()

    @staticmethod
    def get_by_id(id: int) -> Chat | None:
        return db.session.scalar(db.select(Chat).where(Chat.id == id))

    @staticmethod
    def get_by_user_id(user_id: int) -> Chat | None:
        return db.session.scalar(db.select(Chat).where(Chat.user_id == user_id))

    @staticmethod
    def get_all_by_user_id(user_id: int) -> Sequence[Chat] | None:
        return db.session.scalars(db.select(Chat).where(Chat.user_id == user_id).order_by(Chat.created.desc())).all()


class Message(MappedAsDataclass, db.Model, unsafe_hash=True):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    chat_id: Mapped[int] = mapped_column(Integer, ForeignKey("chat.id"), nullable=False)
    message: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[SenderType] = mapped_column(Enum(SenderType), nullable=False, default=SenderType.USER)
    created: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), init=False)

    chat: Mapped[Chat] = relationship("Chat", back_populates="messages", init=False)

    @staticmethod
    def get_all() -> Sequence[Message] | None:
        return db.session.scalars(db.select(Message)).all()

    @staticmethod
    def get_by_id(id: int) -> Message | None:
        return db.session.scalar(db.select(Message).where(Message.id == id))

    @staticmethod
    def get_by_chat_id(chat_id: int) -> Sequence[Message] | None:
        return db.session.scalars(db.select(Message).where(Message.chat_id == chat_id)).all()
