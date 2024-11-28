import datetime
from typing import TYPE_CHECKING, Sequence

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from ..extensions import db
from ..utils.enums import SearchHistoryType

if TYPE_CHECKING:
    from .user import User


class SearchHistory(MappedAsDataclass, db.Model, unsafe_hash=True):
    user: Mapped["User"] = relationship("User", back_populates="search_histories", init=False, uselist=False)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    query: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now(), init=False)
    type: Mapped[SearchHistoryType] = mapped_column(SQLEnum(SearchHistoryType), nullable=True)

    __table_args__ = (UniqueConstraint("user_id", "query", name="user_query"),)


    @staticmethod
    def get_search_history(user, search_type):
        search_history = db.session.scalars(
            db.select(SearchHistory)
            .where(SearchHistory.user_id == user.id, SearchHistory.type == search_type)
            .order_by(SearchHistory.created_at.desc())
            .limit(5)
        ).all()
        return search_history


    @staticmethod
    def get_search_histories_json(user, offset: int = 1, limit: int = 20):
        search_histories = db.session.scalars(
            db.select(SearchHistory)
            .where(SearchHistory.user_id == user.id)
            .order_by(SearchHistory.created_at.desc()).offset(offset).limit(limit)
        ).all()
        return search_histories
