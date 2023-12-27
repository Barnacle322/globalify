from __future__ import annotations

import datetime
import re
from uuid import uuid4

from flask_login import UserMixin
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from src.project.models.helpers import Country, Industry, Round

from ..extensions import db
from ..utils.status_enum import OauthProvider, Tier


class User(UserMixin, db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    oauth_provider: Mapped[OauthProvider] = mapped_column(SQLEnum(OauthProvider), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<User {self.email}>"

    @property
    def password(self) -> None:
        raise AttributeError("Password is not a readable attribute.")

    @password.setter
    def password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password, "scrypt")

    def verify_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def get_by_id(id: int) -> User | None:
        try:
            user = User.query.filter(User.id == id).first()
            return user
        except NoResultFound:
            return None

    @staticmethod
    def get_by_email(email: str) -> User | None:
        try:
            user = User.query.filter(User.email == email).first()
            return user
        except NoResultFound:
            return None

    @staticmethod
    def signed_with_oauth(email: str) -> OauthProvider:
        try:
            user = User.query.filter(User.email == email).first()
            if not user:
                return OauthProvider.REGULAR
            return user.oauth_provider
        except NoResultFound:
            return OauthProvider.REGULAR

    def uses_oauth(self) -> bool:
        return self.oauth_provider != OauthProvider.REGULAR


class UserInfo(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False, unique=True)
    first_name: Mapped[str | None] = mapped_column(String, nullable=True)
    last_name: Mapped[str | None] = mapped_column(String, nullable=True)
    username: Mapped[str | None] = mapped_column(String, nullable=True)
    bio: Mapped[str | None] = mapped_column(String, nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String, nullable=True)
    instagram_url: Mapped[str | None] = mapped_column(String, nullable=True)
    twitter_url: Mapped[str | None] = mapped_column(String, nullable=True)
    # Google storage blob id
    pfp_uuid: Mapped[str | None] = mapped_column(String, nullable=True)
    is_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    language: Mapped[str] = mapped_column(String, nullable=True, default="English")

    user: Mapped[User] = relationship("User", backref=backref("user_info", cascade="all, delete"), lazy=True)

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
        if not linkedin:
            self.linkedin_url = None
            return None
        if re.match(r"^(https?:\/\/)?(www\.)?linkedin\.com\/in\/[\w-]+\/?$", linkedin, re.IGNORECASE):
            self.linkedin_url = linkedin
        else:
            raise ValueError("Invalid linkedin url.")

    @instagram.setter
    def instagram(self, instagram) -> None:
        if not instagram:
            self.instagram_url = None
            return None
        if re.match(r"^(https?:\/\/)?(www\.)?instagram\.com\/[\w.-]+\/?$", instagram, re.IGNORECASE):
            self.instagram_url = instagram
        else:
            raise ValueError("Invalid instagram url.")

    @twitter.setter
    def twitter(self, twitter) -> None:
        if not twitter:
            self.twitter_url = None
            return None
        if re.match(r"^(https?:\/\/)?((www\.)?twitter\.com|(www\.)?x\.com)\/[A-Za-z0-9_]+\/?$", twitter, re.IGNORECASE):
            self.twitter_url = twitter
        else:
            raise ValueError("Invalid twitter url.")

    def sanitize(self) -> dict[str, str]:
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
    def get_by_user_id(id: int) -> UserInfo | None:
        try:
            user_info = UserInfo.query.filter(UserInfo.user_id == id).first()
            return user_info
        except NoResultFound:
            return None

    @staticmethod
    def is_taken(username: str | None) -> bool:
        try:
            user_info = UserInfo.query.filter(UserInfo.username == username).first()
            return True if user_info else False
        except NoResultFound:
            return False


class UserPayment(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False, unique=True)
    customer_id: Mapped[str] = mapped_column(String, nullable=True)
    subscription_id: Mapped[str] = mapped_column(String, nullable=True)
    created: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tier: Mapped[Tier] = mapped_column(SQLEnum(Tier), nullable=False, default=Tier.FREE)

    user: Mapped[User] = relationship("User", backref=backref("user_payment", cascade="all, delete"), lazy=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<UserPayment: {self.customer_id} | {'Active' if self.is_active else 'Inactive'}>"

    @property
    def created_epoch(self) -> DateTime | None:
        return self.created

    @property
    def expires_at_epoch(self) -> DateTime | None:
        return self.expires_at

    @created_epoch.setter
    def created_epoch(self, created_epoch: int) -> None:
        self.created = datetime.datetime.utcfromtimestamp(created_epoch)  # type: ignore

    @expires_at_epoch.setter
    def expires_at_epoch(self, expires_at_epoch: int) -> None:
        self.expires_at = datetime.datetime.utcfromtimestamp(expires_at_epoch)  # type: ignore

    def is_expired(self) -> bool:
        return self.expires_at < datetime.datetime.utcnow()  # type: ignore

    @staticmethod
    def get_by_customer_id(customer_id: str) -> UserPayment | None:
        try:
            user_payment = UserPayment.query.filter(UserPayment.customer_id == customer_id).first()
            return user_payment
        except NoResultFound:
            return None

    @staticmethod
    def get_by_user_id(user_id: int) -> UserPayment | None:
        try:
            user_payment = UserPayment.query.filter(UserPayment.user_id == user_id).first()
            return user_payment
        except NoResultFound:
            return None

    def sanitize(self):
        subscription = {
            "created": self.created,
            "expires_at": self.expires_at.date(),  # type: ignore
            "is_acrive": self.is_active,
            "tier": self.tier,
            "subscription_id": self.subscription_id,
        }
        return subscription


class WaitlistCharge(db.Model):
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
        try:
            waitlist_charge = WaitlistCharge.query.filter(WaitlistCharge.id == id).first()
            return waitlist_charge
        except NoResultFound:
            return None

    @staticmethod
    def get_by_customer_id(customer_id: str) -> WaitlistCharge | None:
        try:
            waitlist_charge = WaitlistCharge.query.filter(WaitlistCharge.stripe_customer_id == customer_id).first()
            return waitlist_charge
        except NoResultFound:
            return None

    @staticmethod
    def get_by_charge_id(charge_id: str) -> WaitlistCharge | None:
        try:
            waitlist_charge = WaitlistCharge.query.filter(WaitlistCharge.charge_id == charge_id).first()
            return waitlist_charge
        except NoResultFound:
            return None

    @staticmethod
    def get_by_customer_email(customer_email: str) -> WaitlistCharge | None:
        try:
            waitlist_charge = WaitlistCharge.query.filter(WaitlistCharge.customer_email == customer_email).first()
            return waitlist_charge
        except NoResultFound:
            return None

    @staticmethod
    def get_by_random_key(random_key: str) -> WaitlistCharge | None:
        try:
            waitlist_charge = WaitlistCharge.query.filter(WaitlistCharge.random_key == random_key).first()
            return waitlist_charge
        except NoResultFound:
            return None


class Waitlist(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def get_by_email(email: str):
        try:
            waitlist = Waitlist.query.filter(Waitlist.email == email).first()
            return waitlist
        except NoResultFound:
            return None


class Company(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    number_of_employees: Mapped[int] = mapped_column(Integer, nullable=True)
    website: Mapped[str] = mapped_column(String, nullable=True)
    # Google storage blob id
    pfp_uuid: Mapped[str] = mapped_column(String, nullable=True)
    country_id: Mapped[int] = mapped_column(Integer, ForeignKey("country.id"), nullable=True)
    preferred_round_id: Mapped[int] = mapped_column(Integer, ForeignKey("round.id"), nullable=True)
    industry_id: Mapped[int] = mapped_column(Integer, ForeignKey("industry.id"), nullable=True)

    user: Mapped[User] = relationship("User", backref=backref("company", cascade="all, delete"), lazy=True)
    country: Mapped[Country] = relationship()
    preferred_round: Mapped[Round] = relationship()
    industry: Mapped[Industry] = relationship()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<Company {self.name}>"

    @staticmethod
    def get_by_user_id(user_id: int) -> Company | None:
        try:
            company = Company.query.filter(Company.user_id == user_id).first()
            return company
        except NoResultFound:
            return None

    @staticmethod
    def get_by_id(id: int) -> Company | None:
        try:
            company = Company.query.filter(Company.id == id).first()
            return company
        except NoResultFound:
            return None
