from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from ..extensions import db
from ..utils.enums import SearchHistoryType

if TYPE_CHECKING:
    from .user import User


class SearchHistory(MappedAsDataclass, db.Model, unsafe_hash=True):
    user: Mapped[User] = relationship("User", back_populates="search_histories", init=False, uselist=False)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    query: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), init=False)
    type: Mapped[SearchHistoryType] = mapped_column(SQLEnum(SearchHistoryType), nullable=True)

    @staticmethod
    def paginate_history(
        user, search_type: bool | SearchHistoryType = False, search_string: str = "", offset: int = 0, limit: int = 20
    ):
        base_query = db.select(SearchHistory).where(SearchHistory.user_id == user.id)

        if search_string:
            base_query = base_query.where(SearchHistory.query.ilike(f"%{search_string}%"))

        if search_type:
            base_query = base_query.where(SearchHistory.type == search_type)

        search_histories = db.session.scalars(
            base_query.order_by(SearchHistory.created_at.desc()).offset(offset).limit(limit)
        ).all()

        return search_histories
