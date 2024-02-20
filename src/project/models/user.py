from __future__ import annotations

import datetime
import re
from collections.abc import Sequence
from sqlite3 import Connection as SQLite3Connection
from uuid import uuid4

from flask_login import UserMixin
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, desc, event, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship, validates

from ..extensions import db
from ..utils.enums import NotificationDestination, OauthProvider, Tier
from ..utils.suggestion import geocode_location
from .helpers import Country, Industry, Round


class User(UserMixin, db.Model):
    """
    User model representing a user in the database.

    Attributes:
        id (Mapped[int]): Unique identifier for the user, serves as the primary key.
        type (Mapped[str]): String indicating the type of the user, used for polymorphic identity.
        email (Mapped[str]): The email address of the user, must be unique and is non-nullable.
        is_verified (Mapped[bool]): Boolean flag indicating if the user's email is verified.
        is_admin (Mapped[bool]): Boolean flag indicating if the user has admin privileges.
        oauth_provider (Mapped[OauthProvider]): The OAuth provider used to authenticate the user, non-nullable.


    Relationships:
        user_info (relationship): Defines a one-to-one or one-to-many relationship with the UserInfo model.
        user_payment (relationship): Defines a one-to-one or one-to-many relationship with the UserPayment model.
        company (relationship): Defines a one-to-one or one-to-many relationship with the Company model.

    The declared_attr decorator is used to create the relationships dynamically based on the class name, with cascading delete.
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    oauth_provider: Mapped[OauthProvider] = mapped_column(SQLEnum(OauthProvider))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<User {self.email} | {self.type}>"

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


class UserInfo(db.Model):
    """
    Represents additional information about a user.

    Attributes:
        id (int): The unique identifier for the user info.
        first_name (str | None): The first name of the user.
        last_name (str | None): The last name of the user.
        username (str | None): The username of the user.
        bio (str | None): The bio of the user.
        linkedin_url (str | None): The LinkedIn profile URL of the user.
        instagram_url (str | None): The Instagram profile URL of the user.
        twitter_url (str | None): The Twitter profile URL of the user.
        picture_url (str | None): The Google storage blob ID for the user's profile picture.
        is_complete (bool): Indicates if the user's profile is complete.
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    first_name: Mapped[str | None] = mapped_column(String, nullable=True)
    last_name: Mapped[str | None] = mapped_column(String, nullable=True)
    username: Mapped[str | None] = mapped_column(String, nullable=True)
    bio: Mapped[str | None] = mapped_column(String, nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String, nullable=True)
    instagram_url: Mapped[str | None] = mapped_column(String, nullable=True)
    twitter_url: Mapped[str | None] = mapped_column(String, nullable=True)
    picture_url: Mapped[str | None] = mapped_column(String, nullable=True)
    is_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user: Mapped[User] = relationship(User, backref=backref("user_info", passive_deletes=True))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<UserInfo: {self.username} | {'Complete' if self.is_complete else 'Incomplete'}>"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

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


class UserPayment(db.Model):
    """
    Represents user payment information.

    Attributes:
        id (int): The payment ID.
        customer_id (str): The customer ID associated with the payment.
        subscription_id (str): The subscription ID associated with the payment.
        created (datetime.datetime | None): The date and time when the payment was created.
        expires_at (datetime.datetime | None): The date and time when the payment expires.
        is_active (bool): Indicates whether the payment is active or not.
        tier (Tier): The subscription tier associated with the payment.
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    customer_id: Mapped[str] = mapped_column(String, nullable=True)
    subscription_id: Mapped[str] = mapped_column(String, nullable=True)
    created: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tier: Mapped[Tier] = mapped_column(SQLEnum(Tier), nullable=False, default=Tier.FREE)

    user: Mapped[User] = relationship(User, backref=backref("user_payment", passive_deletes=True))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<UserPayment: {self.customer_id} | {'Active' if self.is_active else 'Inactive'}>"

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
    def get_by_user_id(user_id: int) -> UserPayment | None:
        return db.session.scalar(db.select(UserPayment).where(UserPayment.user_id == user_id))

    def sanitize(self):
        subscription = {
            "created": self.created,
            "expires_at": self.expires_at.date(),  # type: ignore
            "is_active": self.is_active,
            "tier": self.tier,
            "subscription_id": self.subscription_id,
        }
        return subscription


class Notification(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    json_data: Mapped[dict] = mapped_column(JSON, nullable=True, default={})
    destination: Mapped[NotificationDestination] = mapped_column(
        SQLEnum(NotificationDestination), nullable=True, default=NotificationDestination.SEARCH
    )
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(User, backref=backref("notifications", passive_deletes=True))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<Notification {self.created_at}>"

    @staticmethod
    def create_notification(
        user_id: int,
        title: str,
        msg: str,
        destination: NotificationDestination,
        icon_url: str = "",
        button_text: str = "",
        button_url: str = "",
        button_text2: str = "",
        button_url2: str = "",
    ):
        notification = Notification(
            user_id=user_id,
            json_data={
                "title": title,
                "msg": msg,
                "buttons": [
                    {
                        "text": button_text,
                        "url": button_url,
                    },
                    {
                        "text": button_text2,
                        "url": button_url2,
                    },
                ],
                "icon_url": icon_url,
            },
            destination=destination,
        )
        db.session.add(notification)
        db.session.commit()
        return notification

    @classmethod
    def get_by_id(cls, id: int) -> Notification | None:
        return db.session.scalar(db.select(cls).where(cls.id == id))

    @staticmethod
    def get_by_user_id(user_id: int) -> Notification | None:
        return db.session.scalar(db.select(Notification).where(Notification.user_id == user_id))

    @staticmethod
    def fetch_notifications(
        user_id: int, destination: NotificationDestination, is_read: bool = 0
    ) -> Sequence[Notification] | None:
        return db.session.scalars(
            db.select(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.destination == destination,
                Notification.is_read == is_read,
            )
            .order_by(desc(Notification.created_at))
        ).all()

    @staticmethod
    def mark_notifications_as_read(user_id: int, destination: NotificationDestination) -> None:
        unread_notifications = db.session.scalars(
            db.select(Notification).where(
                Notification.user_id == user_id, Notification.destination == destination, Notification.is_read == 0
            )
        ).all()
        print(unread_notifications)
        for notification in unread_notifications:
            notification.is_read = True
        db.session.commit()


class EmailVerification(db.Model):
    """
    Represents email verification information.

    Attributes:
        id (int): The verification ID.
        user_id (int): The ID of the user associated with the verification.
        token (str): The unique token generated for email verification.
        created_at (datetime.datetime): The date and time when the verification was created.
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    token: Mapped[str] = mapped_column(String, nullable=False, default=lambda: str(uuid4()))
    is_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_expired: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<EmailVerification token created at {self.created_at}"

    @staticmethod
    def deactivate_user_tokens(user_id: int) -> None:
        """
        Set is_expired=True for all EmailVerification records associated with the given user_id.

        Args:
            user_id (int): The ID of the user for whom to set EmailVerification records as expired.
        """
        try:
            email_verifications = db.session.scalars(
                db.select(EmailVerification).where(EmailVerification.user_id == user_id)
            ).all()
            for email_verification in email_verifications:
                email_verification.is_expired = True
            db.session.commit()
        except Exception:
            db.session.rollback()

    @staticmethod
    def get_by_token(token: str) -> EmailVerification | None:
        return db.session.scalar(db.select(EmailVerification).where(EmailVerification.token == token))

    @staticmethod
    def fetch_email_verification(user_id: int) -> EmailVerification | None:
        last_verification = db.session.scalar(
            db.select(EmailVerification)
            .where(
                EmailVerification.user_id == user_id,
            )
            .order_by(EmailVerification.created_at.desc())
        )
        return last_verification


class WaitlistCharge(db.Model):
    """
    Represents a waitlist charge.

    Attributes:
        id (int): The waitlist charge ID.
        stripe_customer_id (str): The Stripe customer ID associated with the charge.
        charge_id (str): The charge ID.
        customer_email (str): The email of the customer associated with the charge.
        customer_name (str): The name of the customer associated with the charge.
        random_key (str): The randomly generated key.
        downloaded (bool): Indicates whether the product database has been downloaded.
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stripe_customer_id: Mapped[str] = mapped_column(String, nullable=False)
    charge_id: Mapped[str] = mapped_column(String, nullable=False)
    customer_email: Mapped[str] = mapped_column(String, nullable=False)
    customer_name: Mapped[str] = mapped_column(String, nullable=False)
    random_key: Mapped[str] = mapped_column(String, nullable=False, default=str(uuid4()))
    downloaded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<WaitlistCharge {self.customer_email} | {self.random_key}>"

    @staticmethod
    def get_by_id(id: int) -> WaitlistCharge | None:
        return db.session.scalar(db.select(WaitlistCharge).where(WaitlistCharge.id == id))

    @staticmethod
    def get_by_customer_id(customer_id: str) -> WaitlistCharge | None:
        return db.session.scalar(db.select(WaitlistCharge).where(WaitlistCharge.stripe_customer_id == customer_id))

    @staticmethod
    def get_by_charge_id(charge_id: str) -> WaitlistCharge | None:
        return db.session.scalar(db.select(WaitlistCharge).where(WaitlistCharge.charge_id == charge_id))

    @staticmethod
    def get_by_customer_email(customer_email: str) -> WaitlistCharge | None:
        return db.session.scalar(db.select(WaitlistCharge).where(WaitlistCharge.customer_email == customer_email))

    @staticmethod
    def get_by_random_key(random_key: str) -> WaitlistCharge | None:
        return db.session.scalar(db.select(WaitlistCharge).where(WaitlistCharge.random_key == random_key))


class Waitlist(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def get_by_email(email: str):
        return db.session.scalar(db.select(Waitlist).where(Waitlist.email == email))


class Company(db.Model):
    """
    SQLAlchemy model representing a company.

    Attributes:
        id (Mapped[int]): The primary key for the company record.
        user_id (Mapped[int]): A foreign key that may reference a user associated with the company, nullable.
        name (Mapped[str]): The name of the company, not nullable.
        description (Mapped[str]): A brief description of the company, nullable.
        number_of_employees (Mapped[int]): The number of employees at the company, nullable.
        website (Mapped[str]): The company's website URL, nullable.
        picture_url (Mapped[str]): A unique identifier for the company's profile picture, nullable.
        country_id (Mapped[int]): A foreign key that references the country the company is located in, nullable.
        preferred_round_id (Mapped[int]): A foreign key that references the company's preferred funding round, nullable.
        industry_id (Mapped[int]): A foreign key that references the industry the company operates in, nullable.

        country (Mapped[Country]): Relationship to the Country model.
        preferred_round (Mapped[Round]): Relationship to the Round model.
        industry (Mapped[Industry]): Relationship to the Industry model.
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    number_of_employees: Mapped[int] = mapped_column(Integer, nullable=True)
    website_url: Mapped[str] = mapped_column(String, nullable=True)
    picture_url: Mapped[str] = mapped_column(String, nullable=True)
    country_id: Mapped[int] = mapped_column(Integer, ForeignKey("country.id"), nullable=True)
    preferred_round_id: Mapped[int] = mapped_column(Integer, ForeignKey("round.id"), nullable=True)
    industry_id: Mapped[int] = mapped_column(Integer, ForeignKey("industry.id"), nullable=True)

    user: Mapped[User] = relationship(User, backref=backref("company", passive_deletes=True), lazy=True)
    country: Mapped[Country] = relationship()
    _coordinates: Mapped[str] = mapped_column(String, nullable=True)
    preferred_round: Mapped[Round] = relationship()
    industry: Mapped[Industry] = relationship()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<Company {self.name}>"

    @property
    def coordinates(self):
        return self._coordinates

    @coordinates.setter
    def coordinates(self, coordinates: str) -> None:
        self._coordinates = geocode_location(coordinates)["coordinates"]  # type: ignore

    @validates("website_url")
    def validate_website(self, key, website):
        if not website:
            return None
        if not re.match(r"^(https?:\/\/)?(www\.)?[\w.-]+\.[a-z]{2,}\/?[\w.-]*$", website, re.IGNORECASE):
            raise ValueError("Invalid website URL format. Ensure it follows the pattern: https://www.example.com.")
        return website

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

    @staticmethod
    def get_by_id(id: int) -> Company | None:
        return db.session.scalar(db.select(Company).where(Company.id == id))

    @staticmethod
    def get_by_user_id(user_id: int) -> Company | None:
        return db.session.scalar(db.select(Company).where(Company.user_id == user_id))


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, SQLite3Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()
