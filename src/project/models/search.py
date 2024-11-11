from typing import TYPE_CHECKING

from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

# from . import User
from ..extensions import db
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    desc,
    event,
    exists,
    func,
    text,
    update,
)

from ..utils.enums import SearchHistoryType
if TYPE_CHECKING:
    from .user import User


class SearchHistory(MappedAsDataclass, db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id'))
    user: Mapped["User"] = relationship("User", back_populates="search_histories", init=False)
    query: Mapped[str] = mapped_column(String)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), init=False)
    type: Mapped[str| None] = mapped_column(SQLEnum(SearchHistoryType), nullable=True)

