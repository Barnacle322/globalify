from __future__ import annotations

import datetime
import re
from collections.abc import Sequence
from sqlite3 import Connection as SQLite3Connection
from uuid import uuid4

from flask_login import UserMixin
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, event
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship, validates

from ..extensions import db
from ..utils.enums import OauthProvider, Tier
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

    @classmethod
    def delete_by_id(cls, id: int) -> None:
        """
        Deletes the user and all associated data.
        This includes the `UserInfo`, `UserPayment`, and `Company` objects.
        """
        if user := cls.get_by_id(id):
            db.session.delete(user)
            db.session.commit()

    @classmethod
    def get_by_id(cls, id: int) -> User | None:
        return db.session.scalar(db.select(cls).where(cls.id == id))

    @classmethod
    def get_by_email(cls, email: str) -> User | None:
        return db.session.scalar(db.select(cls).where(cls.email == email))

    @classmethod
    def get_all(cls) -> Sequence[User]:
        return db.session.scalars(db.select(cls)).all()


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
            dict[str, str]: A dictionary representing the UserInfo object.

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
        """
        Returns:
            DateTime | None: The created date and time in epoch format.

        """
        return self.created

    @property
    def expires_at_epoch(self) -> datetime.datetime | None:
        """
        Returns:
            DateTime | None: The expiration date and time in epoch format.

        """
        return self.expires_at

    @created_epoch.setter
    def created_epoch(self, created_epoch: int) -> None:
        """
        Sets the created date and time using the provided epoch value.

        Args:
            created_epoch (int): The epoch value representing the created date and time.

        """
        self.created = datetime.datetime.fromtimestamp(created_epoch, tz=datetime.UTC)

    @expires_at_epoch.setter
    def expires_at_epoch(self, expires_at_epoch: int) -> None:
        """
        Sets the expiration date and time using the provided epoch value.

        Args:
            expires_at_epoch (int): The epoch value representing the expiration date and time.

        """
        self.expires_at = datetime.datetime.fromtimestamp(expires_at_epoch, tz=datetime.UTC)

    def is_expired(self) -> bool:
        """
        Checks if the payment has expired.

        Returns:
            bool: True if the payment has expired, False otherwise.

        """
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
        DateTime, nullable=False, default=datetime.datetime.now(datetime.UTC)
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
            # EmailVerification.query.filter_by(user_id=user_id).update({EmailVerification.is_expired: True})
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
        """
        Retrieves an email verification record by token.

        Args:
            token (str): The verification token.

        Returns:
            EmailVerification | None: The email verification record or None if not found.
        """
        return db.session.scalar(db.select(EmailVerification).where(EmailVerification.token == token))


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
    website: Mapped[str] = mapped_column(String, nullable=True)
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
