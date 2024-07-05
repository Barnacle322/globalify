from __future__ import annotations

import datetime
import re
from collections.abc import Sequence
from sqlite3 import Connection as SQLite3Connection
from uuid import uuid4

from flask_login import UserMixin
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, desc, event, func, or_, text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Mapped, MappedAsDataclass, backref, joinedload, mapped_column, relationship, validates

from ..extensions import db
from ..utils import suggestion
from ..utils.enums import CompanyRole, NotificationDestination, OauthProvider, RequestStatus, Tier
from .helpers import Country, Industry, Round


class User(UserMixin, MappedAsDataclass, db.Model, unsafe_hash=True):
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

    oauth_provider: Mapped[OauthProvider] = mapped_column(SQLEnum(OauthProvider))
    id: Mapped[int] = mapped_column(Integer, init=False, primary_key=True)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

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


class UserInfo(MappedAsDataclass, db.Model, unsafe_hash=True):
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

    user: Mapped[User] = relationship(User, backref=backref("user_info", passive_deletes=True, uselist=False))

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


class UserPayment(MappedAsDataclass, db.Model, unsafe_hash=True):
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

    user: Mapped[User] = relationship(User, backref=backref("user_payment", passive_deletes=True, uselist=False))

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

    def sanitize(self):
        subscription = {
            "created": self.created,
            "expires_at": self.expires_at.date(),  # type: ignore
            "is_active": self.is_active,
            "tier": self.tier,
            "subscription_id": self.subscription_id,
        }
        return subscription


class Notification(MappedAsDataclass, db.Model, unsafe_hash=True):
    user: Mapped[User] = relationship(User, backref=backref("notifications", passive_deletes=True))

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, init=False
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, init=False)
    json_data: Mapped[dict] = mapped_column(JSON, nullable=True, default=False)
    destination: Mapped[NotificationDestination] = mapped_column(
        SQLEnum(NotificationDestination), nullable=True, default=NotificationDestination.SEARCH
    )
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    @classmethod
    def get_by_id(cls, id: int) -> Notification | None:
        return db.session.scalar(db.select(cls).where(cls.id == id))

    @staticmethod
    def get_by_user_id(user_id: int) -> Notification | None:
        return db.session.scalar(db.select(Notification).where(Notification.user_id == user_id))

    @staticmethod
    def get_unread(
        user_id: int, destination: NotificationDestination, is_read: bool = False
    ) -> Sequence[Notification] | None:
        return db.session.scalars(
            db.select(Notification)
            .where(
                Notification.user_id == user_id,
                or_(Notification.destination == destination, Notification.destination == NotificationDestination.ALL),
                Notification.is_read.is_(is_read),
            )
            .order_by(desc(Notification.created_at))
        ).all()

    @staticmethod
    def mark_notifications_as_read(user_id: int, destination: NotificationDestination) -> None:
        unread_notifications = db.session.scalars(
            db.select(Notification).where(
                Notification.user_id == user_id,
                or_(Notification.destination == destination, Notification.destination == NotificationDestination.ALL),
                Notification.is_read.is_(False),
            )
        ).all()
        for notification in unread_notifications:
            notification.is_read = True
        db.session.commit()


class EmailVerification(MappedAsDataclass, db.Model, unsafe_hash=True):
    """
    Represents email verification information.

    Attributes:
        id (int): The verification ID.
        user_id (int): The ID of the user associated with the verification.
        token (str): The unique token generated for email verification.
        created_at (datetime.datetime): The date and time when the verification was created.
    """

    user: Mapped[User] = relationship(User, backref=backref("email_verifications", passive_deletes=True), init=False)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, init=False
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    token: Mapped[str] = mapped_column(String, nullable=False, insert_default=lambda: str(uuid4()), init=False)
    is_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

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
                email_verification.is_expired = True
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


class Company(MappedAsDataclass, db.Model, unsafe_hash=True):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True, init=False)
    number_of_employees: Mapped[int | None] = mapped_column(Integer, nullable=True, init=False)
    website_url: Mapped[str | None] = mapped_column(String, nullable=True, init=False)
    picture_url: Mapped[str | None] = mapped_column(String, nullable=True, init=False)
    country_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("country.id"), nullable=True, init=False)
    preferred_round_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("round.id"), nullable=True, init=False)
    industry_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("industry.id"), nullable=True, init=False)
    _coordinates: Mapped[str | None] = mapped_column(String, nullable=True, init=False)

    country: Mapped[Country] = relationship(init=False)
    preferred_round: Mapped[Round] = relationship(init=False)
    industry: Mapped[Industry] = relationship(init=False)

    @property
    def coordinates(self):
        return self._coordinates

    @coordinates.setter
    def coordinates(self, coordinates: str) -> None:
        self._coordinates = suggestion.geocode_location(coordinates)["coordinates"]  # type: ignore

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


class UserCompany(MappedAsDataclass, db.Model, unsafe_hash=True):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("company.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[CompanyRole] = mapped_column(SQLEnum(CompanyRole), nullable=False, default=CompanyRole.EMPLOYEE)
    is_accepted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user: Mapped[User] = relationship(
        User, backref=backref("user_company", passive_deletes=True, uselist=True), init=False
    )
    company: Mapped[Company] = relationship(
        Company, backref=backref("user_company", passive_deletes=True, uselist=True), init=False
    )

    @staticmethod
    def get_by_user_id(user_id: int) -> Sequence[UserCompany]:
        return db.session.scalars(db.select(UserCompany).where(UserCompany.user_id == user_id)).all()

    @staticmethod
    def get_by_company_id(company_id: int) -> Sequence[UserCompany]:
        return db.session.scalars(db.select(UserCompany).where(UserCompany.company_id == company_id)).all()

    @staticmethod
    def get_all() -> Sequence[UserCompany]:
        return db.session.scalars(db.select(UserCompany)).all()

    @staticmethod
    def get_members(company_id: int):
        results = db.session.execute(
            db.select(User, UserCompany)
            .join(UserCompany, UserCompany.user_id == User.id)
            .where(UserCompany.company_id == company_id)
        ).all()

        return results

    @staticmethod
    def get_by_user_id_and_company_id(user_id: int, company_id: int) -> UserCompany | None:
        return db.session.scalar(
            db.select(UserCompany).where(
                UserCompany.user_id == user_id, UserCompany.company_id == company_id, UserCompany.is_accepted.is_(False)
            )
        )


class CompanyInvitation(MappedAsDataclass, db.Model, unsafe_hash=True):
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), init=False
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("company.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[CompanyRole] = mapped_column(SQLEnum(CompanyRole), nullable=False, default=CompanyRole.EMPLOYEE)
    is_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    company: Mapped[Company] = relationship(
        Company, backref=backref("company_invitation", passive_deletes=True, uselist=True), init=False
    )

    def is_expired(self) -> bool:
        expiration_time = self.created_at + datetime.timedelta(days=7)
        return datetime.datetime.now(datetime.UTC) > expiration_time.replace(tzinfo=datetime.UTC)

    @staticmethod
    def get_by_id(id: int) -> CompanyInvitation | None:
        return db.session.scalar(db.select(CompanyInvitation).where(CompanyInvitation.id == id))

    @staticmethod
    def get_by_email(email: str):
        results = db.session.execute(
            db.select(Company, CompanyInvitation)
            .join(CompanyInvitation, CompanyInvitation.company_id == Company.id)
            .where(CompanyInvitation.email == email, CompanyInvitation.is_used.is_(False))
        ).all()
        return results

    @staticmethod
    def get_by_company_id(company_id: int) -> Sequence[CompanyInvitation]:
        return db.session.scalars(db.select(CompanyInvitation).where(CompanyInvitation.company_id == company_id)).all()

    @staticmethod
    def get_by_company_id_and_email(company_id: int, email: str) -> CompanyInvitation | None:
        return db.session.scalar(
            db.select(CompanyInvitation).where(
                CompanyInvitation.company_id == company_id, CompanyInvitation.email == email
            )
        )


class ClaimRequest(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)

    investor_id: Mapped[int] = mapped_column(Integer, ForeignKey("investor.id"), nullable=False)
    status: Mapped[RequestStatus] = mapped_column(SQLEnum(RequestStatus), nullable=False, default=RequestStatus.PENDING)
    status_info: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    approved_by: Mapped[int] = mapped_column(Integer, nullable=True, default=None)
    approved_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    email: Mapped[str] = mapped_column(String, nullable=True, default=None)
    requested_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    user: Mapped[User] = relationship(User, backref=backref("claim_request", uselist=False))
    investor: Mapped[Investor] = relationship("Investor", backref=backref("claim_request", uselist=False))  # type: ignore # noqa: F821

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<ClaimRequest {self.id}>"

    @staticmethod
    def get_by_id(id: int) -> ClaimRequest | None:
        return db.session.scalar(db.select(ClaimRequest).where(ClaimRequest.id == id))

    @staticmethod
    def get_by_user_id(user_id: int) -> ClaimRequest | None:
        return db.session.scalar(db.select(ClaimRequest).where(ClaimRequest.user_id == user_id))

    @staticmethod
    def get_by_investor_id(investor_id: int) -> ClaimRequest | None:
        return db.session.scalar(db.select(ClaimRequest).where(ClaimRequest.investor_id == investor_id))

    @staticmethod
    def get_all() -> Sequence[ClaimRequest]:
        return db.session.scalars(
            db.select(ClaimRequest).options(joinedload(ClaimRequest.user), joinedload(ClaimRequest.investor))
        ).all()


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, SQLite3Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()
