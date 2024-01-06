from __future__ import annotations

import datetime
import re
from uuid import uuid4

from flask_login import UserMixin
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Mapped, backref, declared_attr, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from ..utils.status_enum import OauthProvider, Tier
from .helpers import Country, Industry, Round


class User(UserMixin, db.Model):
    """
    Base class for a user in the application.
    This should not be used directly to instantiate a user. Instead, use one of the subclasses.
    Although, this can be used to query for users.
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __mapper_args__ = {"polymorphic_identity": "user", "polymorphic_on": type}

    @declared_attr
    def user_info(cls):  # noqa: N805
        return relationship("UserInfo", backref=backref(cls.__name__.lower(), cascade="all, delete"), lazy=True)

    @declared_attr
    def user_payment(cls):  # noqa: N805
        return relationship("UserPayment", backref=backref(cls.__name__.lower(), cascade="all, delete"), lazy=True)

    @declared_attr
    def company(cls):  # noqa: N805
        return relationship("Company", backref=backref(cls.__name__.lower(), cascade="all, delete"), lazy=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<User {self.email} | {self.type}>"

    @classmethod
    def get_by_id(cls, id: int) -> User | None:
        """
        Retrieves a user by their ID.

        Args:
            id (int): The ID of the user.

        Returns:
            User | None: The user with the specified ID, or None if not found.

        """
        try:
            user = cls.query.filter(cls.id == id).first()
            return user
        except NoResultFound:
            return None

    @classmethod
    def get_by_email(cls, email: str) -> User | None:
        """
        Retrieves a user by their email address.

        Args:
            email (str): The email address of the user.

        Returns:
            User | None: The user with the specified email address, or None if not found.

        """
        try:
            user = cls.query.filter(cls.email == email).first()
            return user
        except NoResultFound:
            return None

    @classmethod
    def get_all(cls):
        try:
            users = cls.query.all()
            return users
        except NoResultFound:
            return None


class UserOauth(User):
    """
    Implements a user in the application that uses OAuth for authentication.

    Attributes:
        id (int): The unique identifier for the user.
        email (str): The email address of the user.
        oauth_provider (OauthProvider): The OAuth provider used by the user.
        is_verified (bool): Indicates if the user's email address is verified.
        is_admin (bool): Indicates if the user has administrative privileges.

    """

    oauth_provider: Mapped[OauthProvider] = mapped_column(SQLEnum(OauthProvider), nullable=True)

    __mapper_args__ = {
        "polymorphic_identity": "user_oauth",
    }

    @staticmethod
    def signed_with_oauth(email: str) -> bool:
        """
        Checks if a user is signed in with an OAuth provider.

        Args:
            email (str): The email address of the user.

        Returns:
            OauthProvider: The OAuth provider used by the user, or OauthProvider.REGULAR if not found.

        """
        try:
            user = UserOauth.query.filter(User.email == email).first()
            if not user:
                return False
            return user.oauth_provider
        except NoResultFound:
            return False


class UserRegular(User):
    """
    Implements a user in the application that uses email and password for authentication.

    Attributes:
        id (int): The unique identifier for the user.
        email (str): The email address of the user.
        password_hash (str | None): The hashed password of the user.
        is_verified (bool): Indicates if the user's email address is verified.
        is_admin (bool): Indicates if the user has administrative privileges.

    """

    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)

    __mapper_args__ = {
        "polymorphic_identity": "user_regular",
    }

    @property
    def password(self) -> None:
        """
        The password property.

        Raises:
            AttributeError: If an attempt is made to read the password.

        """
        raise AttributeError("Password is not a readable attribute.")

    @password.setter
    def password(self, password: str) -> None:
        """
        Sets the password for the user.

        Args:
            password (str): The password to set.

        """
        self.password_hash = generate_password_hash(password, "scrypt")

    def verify_password(self, password: str) -> bool:
        """
        Verifies if the provided password matches the user's password.

        Args:
            password (str): The password to verify.

        Returns:
            bool: True if the passwords match, False otherwise.

        """
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)


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
        pfp_uuid (str | None): The Google storage blob ID for the user's profile picture.
        is_complete (bool): Indicates if the user's profile is complete.
        language (str): The language preference of the user.

    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False, unique=True)
    first_name: Mapped[str | None] = mapped_column(String, nullable=True)
    last_name: Mapped[str | None] = mapped_column(String, nullable=True)
    username: Mapped[str | None] = mapped_column(String, nullable=True)
    bio: Mapped[str | None] = mapped_column(String, nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String, nullable=True)
    instagram_url: Mapped[str | None] = mapped_column(String, nullable=True)
    twitter_url: Mapped[str | None] = mapped_column(String, nullable=True)
    pfp_uuid: Mapped[str | None] = mapped_column(String, nullable=True)
    is_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    language: Mapped[str] = mapped_column(String, nullable=True, default="English")

    # user: Mapped[User] = relationship("User", backref=backref("user_info", cascade="all, delete"), lazy=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<UserInfo: {self.username} | {'Complete' if self.is_complete else 'Incomplete'}>"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def linkedin(self):
        return self.linkedin_url

    @property
    def instagram(self):
        return self.instagram_url

    @property
    def twitter(self):
        return self.twitter_url

    @linkedin.setter
    def linkedin(self, linkedin) -> None:
        """
        Sets the LinkedIn profile URL for the user.

        Args:
            linkedin (str): The LinkedIn profile URL to set.

        Raises:
            ValueError: If the provided LinkedIn URL is invalid.

        """
        if not linkedin:
            self.linkedin_url = None
            return None
        if re.match(r"^(https?:\/\/)?(www\.)?linkedin\.com\/in\/[\w-]+\/?$", linkedin, re.IGNORECASE):
            self.linkedin_url = linkedin
        else:
            raise ValueError("Invalid linkedin url.")

    @instagram.setter
    def instagram(self, instagram) -> None:
        """
        Sets the Instagram profile URL for the user.

        Args:
            instagram (str): The Instagram profile URL to set.

        Raises:
            ValueError: If the provided Instagram URL is invalid.

        """
        if not instagram:
            self.instagram_url = None
            return None
        if re.match(r"^(https?:\/\/)?(www\.)?instagram\.com\/[\w.-]+\/?$", instagram, re.IGNORECASE):
            self.instagram_url = instagram
        else:
            raise ValueError("Invalid instagram url.")

    @twitter.setter
    def twitter(self, twitter) -> None:
        """
        Sets the Twitter profile URL for the user.

        Args:
            twitter (str): The Twitter profile URL to set.

        Raises:
            ValueError: If the provided Twitter URL is invalid.

        """
        if not twitter:
            self.twitter_url = None
            return None
        if re.match(r"^(https?:\/\/)?((www\.)?twitter\.com|(www\.)?x\.com)\/[A-Za-z0-9_]+\/?$", twitter, re.IGNORECASE):
            self.twitter_url = twitter
        else:
            raise ValueError("Invalid twitter url.")

    def sanitize(self):
        """
        Returns a dictionary representation of the UserInfo object.

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
            "pfp": self.pfp_uuid,
        }
        return user_info

    @staticmethod
    def get_by_user_id(user_id: int) -> UserInfo | None:
        """
        Retrieves a UserInfo object by user ID.

        Args:
            user_id (int): The user ID.

        Returns:
            UserInfo | None: The UserInfo object corresponding to the user ID, or None if not found.

        """
        try:
            user_info = UserInfo.query.filter(UserInfo.user_id == user_id).first()
            return user_info
        except NoResultFound:
            return None

    @staticmethod
    def get_all() -> list[UserInfo] | None:
        """
        Retrieves all UserInfo objects.

        Returns:
            list[UserInfo]: A list of UserInfo objects.

        """
        try:
            user_info = UserInfo.query.all()
            return user_info
        except NoResultFound:
            return None

    @staticmethod
    def is_taken(username: str | None) -> bool:
        """
        Checks if a username is taken by another user.

        Args:
            username (str | None): The username to check.

        Returns:
            bool: True if the username is taken, False otherwise.

        """
        try:
            user_info = UserInfo.query.filter(UserInfo.username == username).first()
            return True if user_info else False
        except NoResultFound:
            return False


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
        user (User): The user associated with the payment.

    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False, unique=True)
    customer_id: Mapped[str] = mapped_column(String, nullable=True)
    subscription_id: Mapped[str] = mapped_column(String, nullable=True)
    created: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tier: Mapped[Tier] = mapped_column(SQLEnum(Tier), nullable=False, default=Tier.FREE)

    # user: Mapped[User] = relationship("User", backref=backref("user_payment", cascade="all, delete"), lazy=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<UserPayment: {self.customer_id} | {'Active' if self.is_active else 'Inactive'}>"

    @property
    def created_epoch(self) -> datetime.datetime | None:
        """
        Returns the created date and time in epoch format.

        Returns:
            DateTime | None: The created date and time in epoch format.

        """
        return self.created

    @property
    def expires_at_epoch(self) -> datetime.datetime | None:
        """
        Returns the expiration date and time in epoch format.

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

        Returns:
            None

        """
        self.created = datetime.datetime.utcfromtimestamp(created_epoch)

    @expires_at_epoch.setter
    def expires_at_epoch(self, expires_at_epoch: int) -> None:
        """
        Sets the expiration date and time using the provided epoch value.

        Args:
            expires_at_epoch (int): The epoch value representing the expiration date and time.

        Returns:
            None

        """
        self.expires_at = datetime.datetime.utcfromtimestamp(expires_at_epoch)

    def is_expired(self) -> bool:
        """
        Checks if the payment has expired.

        Returns:
            bool: True if the payment has expired, False otherwise.

        """
        if self.expires_at:
            return self.expires_at < datetime.datetime.utcnow()
        return True

    @staticmethod
    def get_by_customer_id(customer_id: str) -> UserPayment | None:
        """
        Retrieves a UserPayment object by customer ID.

        Args:
            customer_id (str): The customer ID.

        Returns:
            UserPayment | None: The UserPayment object corresponding to the customer ID, or None if not found.

        """
        try:
            user_payment = UserPayment.query.filter(UserPayment.customer_id == customer_id).first()
            return user_payment
        except NoResultFound:
            return None

    @staticmethod
    def get_by_user_id(user_id: int) -> UserPayment | None:
        """
        Retrieves a UserPayment object by user ID.

        Args:
            user_id (int): The user ID.

        Returns:
            UserPayment | None: The UserPayment object corresponding to the user ID, or None if not found.

        """
        try:
            user_payment = UserPayment.query.filter(UserPayment.user_id == user_id).first()
            return user_payment
        except NoResultFound:
            return None

    def sanitize(self):
        """
        Returns a sanitized dictionary representation of the UserPayment object.

        Returns:
            dict: A dictionary representing the sanitized UserPayment object.

        """
        subscription = {
            "created": self.created,
            "expires_at": self.expires_at.date(),  # type: ignore
            "is_acrive": self.is_active,
            "tier": self.tier,
            "subscription_id": self.subscription_id,
        }
        return subscription


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
        downloaded (bool): Indicates whether the charge has been downloaded.

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
        """
        Retrieves a waitlist charge by ID.

        Args:
            id (int): The ID of the waitlist charge.

        Returns:
            WaitlistCharge | None: The waitlist charge corresponding to the ID, or None if not found.

        """
        try:
            waitlist_charge = WaitlistCharge.query.filter(WaitlistCharge.id == id).first()
            return waitlist_charge
        except NoResultFound:
            return None

    @staticmethod
    def get_by_customer_id(customer_id: str) -> WaitlistCharge | None:
        """
        Retrieves a waitlist charge by customer ID.

        Args:
            customer_id (str): The customer ID.

        Returns:
            WaitlistCharge | None: The waitlist charge corresponding to the customer ID, or None if not found.

        """
        try:
            waitlist_charge = WaitlistCharge.query.filter(WaitlistCharge.stripe_customer_id == customer_id).first()
            return waitlist_charge
        except NoResultFound:
            return None

    @staticmethod
    def get_by_charge_id(charge_id: str) -> WaitlistCharge | None:
        """
        Retrieves a waitlist charge by charge ID.

        Args:
            charge_id (str): The charge ID.

        Returns:
            WaitlistCharge | None: The waitlist charge corresponding to the charge ID, or None if not found.

        """
        try:
            waitlist_charge = WaitlistCharge.query.filter(WaitlistCharge.charge_id == charge_id).first()
            return waitlist_charge
        except NoResultFound:
            return None

    @staticmethod
    def get_by_customer_email(customer_email: str) -> WaitlistCharge | None:
        """
        Retrieves a waitlist charge by customer email.

        Args:
            customer_email (str): The email of the customer.

        Returns:
            WaitlistCharge | None: The waitlist charge corresponding to the customer email, or None if not found.

        """
        try:
            waitlist_charge = WaitlistCharge.query.filter(WaitlistCharge.customer_email == customer_email).first()
            return waitlist_charge
        except NoResultFound:
            return None

    @staticmethod
    def get_by_random_key(random_key: str) -> WaitlistCharge | None:
        """
        Retrieves a waitlist charge by random key.

        Args:
            random_key (str): The random key.

        Returns:
            WaitlistCharge | None: The waitlist charge corresponding to the random key, or None if not found.

        """
        try:
            waitlist_charge = WaitlistCharge.query.filter(WaitlistCharge.random_key == random_key).first()
            return waitlist_charge
        except NoResultFound:
            return None


class Waitlist(db.Model):
    """
    Represents a waitlist entry.

    Attributes:
        id (int): The waitlist entry ID.
        email (str): The email associated with the waitlist entry.

    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def get_by_email(email: str):
        """
        Retrieves a waitlist entry by email.

        Args:
            email (str): The email associated with the waitlist entry.

        Returns:
            Waitlist | None: The waitlist entry corresponding to the email, or None if not found.

        """
        try:
            waitlist = Waitlist.query.filter(Waitlist.email == email).first()
            return waitlist
        except NoResultFound:
            return None


class Company(db.Model):
    """
    Represents a company.

    Attributes:
        id (int): The company ID.
        name (str): The name of the company.
        description (str): The description of the company.
        number_of_employees (int): The number of employees in the company.
        website (str): The website of the company.
        pfp_uuid (str): The Google storage blob ID.
        country_id (int): The ID of the country associated with the company.
        preferred_round_id (int): The ID of the preferred round associated with the company.
        industry_id (int): The ID of the industry associated with the company.

    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    number_of_employees: Mapped[int] = mapped_column(Integer, nullable=True)
    website: Mapped[str] = mapped_column(String, nullable=True)
    pfp_uuid: Mapped[str] = mapped_column(String, nullable=True)
    country_id: Mapped[int] = mapped_column(Integer, ForeignKey("country.id"), nullable=True)
    preferred_round_id: Mapped[int] = mapped_column(Integer, ForeignKey("round.id"), nullable=True)
    industry_id: Mapped[int] = mapped_column(Integer, ForeignKey("industry.id"), nullable=True)

    # user: Mapped[User] = relationship("User", backref=backref("company", cascade="all, delete"), lazy=True)
    country: Mapped[Country] = relationship()
    preferred_round: Mapped[Round] = relationship()
    industry: Mapped[Industry] = relationship()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<Company {self.name}>"

    @staticmethod
    def get_by_id(id: int) -> Company | None:
        """
        Retrieves a company by ID.

        Args:
            id (int): The ID of the company.

        Returns:
            Company | None: The company corresponding to the ID, or None if not found.

        """
        try:
            company = Company.query.filter(Company.id == id).first()
            return company
        except NoResultFound:
            return None

    @staticmethod
    def get_by_user_id(user_id: int) -> UserInfo | None:
        """
        Retrieves a UserInfo object by user ID.

        Args:
            user_id (int): The user ID.

        Returns:
            UserInfo | None: The UserInfo object corresponding to the user ID, or None if not found.

        """
        try:
            user_info = Company.query.filter(UserInfo.user_id == user_id).first()
            return user_info
        except NoResultFound:
            return None
