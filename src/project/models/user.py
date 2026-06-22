from __future__ import annotations

import datetime
import re
import uuid
from collections.abc import Sequence
from sqlite3 import Connection as SQLite3Connection
from typing import TYPE_CHECKING
from uuid import uuid4

from flask_login import UserMixin
from slugify import slugify
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    desc,
    event,
    func,
    text,
    update,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship, validates

from ..extensions import db
from ..utils.enums import Tier

if TYPE_CHECKING:
    from .claim import ClaimRequest, ClaimVerification
    from .search import SearchHistory


class User(UserMixin, MappedAsDataclass, db.Model, unsafe_hash=True):
    user_info: Mapped[UserInfo] = relationship(
        "UserInfo", back_populates="user", uselist=False, init=False, lazy="joined"
    )
    user_payment: Mapped[UserPayment] = relationship("UserPayment", back_populates="user", uselist=False, init=False)
    notifications: Mapped[list[Notification]] = relationship("Notification", back_populates="user", init=False)
    email_verifications: Mapped[list[EmailVerification]] = relationship(
        "EmailVerification", back_populates="user", init=False
    )

    claim_requests: Mapped[list[ClaimRequest]] = relationship(
        "ClaimRequest", back_populates="user", uselist=True, init=False
    )
    claim_verifications: Mapped[list[ClaimVerification]] = relationship(
        "ClaimVerification", back_populates="user", init=False
    )

    search_histories: Mapped[list[SearchHistory]] = relationship(
        "SearchHistory", back_populates="user", uselist=True, init=False
    )
    id: Mapped[int] = mapped_column(Integer, init=False, primary_key=True)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    last_login: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True, init=False)
    created_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), init=False
    )
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))

    @staticmethod
    def delete_by_id(id: int) -> None:
        """
        Deletes the user and all associated data.
        This includes the `UserInfo`, `UserPayment`, and `Company` objects.
        """
        if user := User.get_by_id(id):
            db.session.delete(user)
            db.session.commit()

    @staticmethod
    def get_by_id(id: int) -> User | None:
        return db.session.scalar(db.select(User).where(User.id == id))

    @staticmethod
    def get_by_email(email: str) -> User | None:
        return db.session.scalar(db.select(User).where(User.email == email))

    @staticmethod
    def get_all() -> Sequence[User]:
        return db.session.scalars(db.select(User)).all()

    @staticmethod
    def update_last_login(user_id: int) -> None:
        db.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                last_login=func.now(),
            )
        )
        db.session.commit()

    @property
    def is_pro(self) -> bool:
        if self.user_payment is None:
            return False
        if not self.user_payment.is_pro:
            return False
        expires = self.user_payment.pro_expires_at
        if expires is None:
            return True
        return expires > datetime.datetime.utcnow()


class UserInfo(MappedAsDataclass, db.Model, unsafe_hash=True):
    user: Mapped[User] = relationship(User, back_populates="user_info", uselist=False)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, unique=True, init=False
    )
    first_name: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    last_name: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    username: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    bio: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    linkedin_url: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    instagram_url: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    twitter_url: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    picture_url: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    is_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    email_public: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"), default=False)
    linkedin_public: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"), default=False)
    instagram_public: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"), default=False)
    twitter_public: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"), default=False)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def set_username(self) -> None:
        def format_username(first_name: str | None, last_name: str | None) -> str:
            base_username = slugify(f"{first_name}{last_name}")
            base_username = re.sub(r"[^a-zA-Z0-9]", "", base_username)[:16]
            base_username = f"{base_username}{uuid.uuid4().hex[:4]}"
            return base_username

        counter = 0
        while True and counter < 10:
            counter += 1
            base_username = format_username(self.first_name, self.last_name)
            existing_username = UserInfo.get_by_username(base_username)

            if not existing_username:
                self.username = base_username
                try:
                    db.session.commit()
                    break
                except IntegrityError:
                    db.session.rollback()

    @validates("linkedin_url")
    def validate_linkedin(self, key, linkedin):
        if not linkedin:
            return None
        if not re.match(r"^(https?:\/\/)?(www\.)?linkedin\.com\/in\/[\w-]+\/?$", linkedin, re.IGNORECASE):
            raise ValueError(
                "Invalid LinkedIn URL format. Ensure it follows the pattern: https://www.linkedin.com/in/username."
            )
        return linkedin

    @validates("instagram_url")
    def validate_instagram(self, key, instagram):
        if not instagram:
            return None
        if not re.match(r"^(https?:\/\/)?(www\.)?instagram\.com\/[\w.-]+\/?$", instagram, re.IGNORECASE):
            raise ValueError(
                "Invalid Instagram URL format. Ensure it follows the pattern: https://www.instagram.com/username."
            )
        return instagram

    @validates("twitter_url")
    def validate_twitter(self, key, twitter):
        if not twitter:
            return None
        if not re.match(
            r"^(https?:\/\/)?((www\.)?twitter\.com|(www\.)?x\.com)\/[A-Za-z0-9_]+\/?$", twitter, re.IGNORECASE
        ):
            raise ValueError("Invalid Twitter URL format. Ensure it follows the pattern: https://twitter.com/username.")
        return twitter

    def sanitize(self):
        """
        Returns:
            dict[str, str]: A dictionary representing the UserInfo without any sensitive info.
        """
        user_info = {
            "user_id": self.user_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "linkedin": self.linkedin_url,
            "instagram": self.instagram_url,
            "twitter": self.twitter_url,
            "bio": self.bio,
            "pfp": self.picture_url,
        }
        return user_info

    @staticmethod
    def get_all() -> Sequence[UserInfo] | None:
        return db.session.scalars(db.select(UserInfo)).all()

    @staticmethod
    def get_by_user_id(user_id: int) -> UserInfo | None:
        return db.session.scalar(db.select(UserInfo).where(UserInfo.user_id == user_id))

    @staticmethod
    def is_taken(username: str | None) -> bool:
        user_info = db.session.scalar(db.select(UserInfo).where(UserInfo.username == username))
        return True if user_info else False

    @staticmethod
    def get_by_username(username: str) -> UserInfo | None:
        return db.session.scalar(db.select(UserInfo).where(UserInfo.username == username))


class UserPayment(MappedAsDataclass, db.Model, unsafe_hash=True):
    user: Mapped[User] = relationship(User, back_populates="user_payment", uselist=False)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, unique=True, init=False
    )
    customer_id: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    subscription_id: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    created: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    expires_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tier: Mapped[Tier] = mapped_column(SQLEnum(Tier), nullable=False, default=Tier.FREE)
    is_pro: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    pro_source: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    pro_expires_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    paddle_customer_id: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    paddle_subscription_id: Mapped[str | None] = mapped_column(String, nullable=True, default=None)

    def grant_pro(self, source: str, expires_at: datetime.datetime | None = None) -> None:
        self.is_pro = True
        self.pro_source = source
        self.pro_expires_at = expires_at
        db.session.commit()

    def revoke_pro(self) -> None:
        self.is_pro = False
        db.session.commit()

    @property
    def created_epoch(self) -> datetime.datetime | None:
        return self.created

    @property
    def expires_at_epoch(self) -> datetime.datetime | None:
        return self.expires_at

    @created_epoch.setter
    def created_epoch(self, created_epoch: int) -> None:
        self.created = datetime.datetime.fromtimestamp(created_epoch, tz=datetime.UTC)

    @expires_at_epoch.setter
    def expires_at_epoch(self, expires_at_epoch: int) -> None:
        self.expires_at = datetime.datetime.fromtimestamp(expires_at_epoch, tz=datetime.UTC)

    def is_expired(self) -> bool:
        if not self.expires_at:
            return True
        return self.expires_at.replace(tzinfo=datetime.UTC) < datetime.datetime.now(tz=datetime.UTC)

    @staticmethod
    def get_by_customer_id(customer_id: str) -> UserPayment | None:
        return db.session.scalar(db.select(UserPayment).where(UserPayment.customer_id == customer_id))

    @staticmethod
    def get_by_subscription_id(subscription_id: str) -> UserPayment | None:
        return db.session.scalar(db.select(UserPayment).where(UserPayment.subscription_id == subscription_id))

    @staticmethod
    def get_by_user_id(user_id: int) -> UserPayment | None:
        return db.session.scalar(db.select(UserPayment).where(UserPayment.user_id == user_id))

    @staticmethod
    def get_by_customer_email(email: str) -> UserPayment | None:
        return db.session.scalar(
            db.select(UserPayment).join(User).where(User.email == email).order_by(desc(UserPayment.created))
        )

    def sanitize(self):
        subscription = {
            "created": self.created,
            "expires_at": self.expires_at.date() if self.expires_at else None,
            "is_active": self.is_active,
            "tier": self.tier,
            "subscription_id": self.subscription_id,
        }
        return subscription


class Notification(MappedAsDataclass, db.Model, unsafe_hash=True):
    user: Mapped[User] = relationship(User, back_populates="notifications")

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, init=False
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, init=False)
    json_data: Mapped[dict] = mapped_column(JSON, nullable=True, default=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "json_data": self.json_data,
            "is_read": self.is_read,
        }

    @staticmethod
    def get_by_id(id: int) -> Notification | None:
        return db.session.scalar(db.select(Notification).where(Notification.id == id))

    @staticmethod
    def get_by_user_id(
        user_id: int, offset: int = 1, limit: int = 10, get_read: bool = False
    ) -> Sequence[Notification]:
        return db.session.scalars(
            db.select(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(get_read))
            .order_by(desc(Notification.created_at))
            .limit(limit)
            .offset(abs(offset - 1) * limit)
        ).all()

    @staticmethod
    def mark_notifications_as_read(user_id: int) -> None:
        db.session.execute(update(Notification).where(Notification.user_id == user_id).values(is_read=True))
        db.session.commit()


class EmailVerification(MappedAsDataclass, db.Model, unsafe_hash=True):
    user: Mapped[User] = relationship(User, back_populates="email_verifications", uselist=True, init=False)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    token: Mapped[str] = mapped_column(String, nullable=False, insert_default=lambda: str(uuid4()), init=False)
    is_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, init=False
    )

    @property
    def is_expired(self) -> bool:
        expiration_time = self.created_at + datetime.timedelta(minutes=5)
        return datetime.datetime.now(datetime.UTC) > expiration_time.replace(tzinfo=datetime.UTC)

    @property
    def is_resendable(self) -> bool:
        expiration_time = self.created_at + datetime.timedelta(minutes=1)
        return datetime.datetime.now(datetime.UTC) > expiration_time.replace(tzinfo=datetime.UTC)

    @staticmethod
    def expire_all_by_user_id(user_id: int) -> None:
        try:
            email_verifications = db.session.scalars(
                db.select(EmailVerification).where(EmailVerification.user_id == user_id)
            ).all()
            for email_verification in email_verifications:
                email_verification.is_used = True
            db.session.commit()
        except Exception:
            db.session.rollback()

    @staticmethod
    def get_by_token(token: str) -> EmailVerification | None:
        return db.session.scalar(db.select(EmailVerification).where(EmailVerification.token == token))

    @staticmethod
    def get_last_unused_by_user_id(user_id: int) -> EmailVerification | None:
        last_verification = db.session.scalar(
            db.select(EmailVerification)
            .where(EmailVerification.user_id == user_id)
            .where(EmailVerification.is_used.is_(False))
            .order_by(EmailVerification.created_at.desc())
        )
        return last_verification


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, SQLite3Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()
