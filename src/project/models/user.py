from __future__ import annotations

import datetime
import json
import re
import uuid
from collections.abc import Generator, Sequence
from sqlite3 import Connection as SQLite3Connection
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from flask_login import UserMixin
from geopy.distance import geodesic
from more_itertools import chunked
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
    exists,
    func,
    text,
    update,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, MappedAsDataclass, joinedload, mapped_column, relationship, validates

from ..extensions import db
from ..utils import suggestion
from ..utils.enums import CompanyRole, OauthProvider, Tier
from ..utils.suggestion import COMPANY_WEIGHTS
from ..utils.typesense_helpers.typesense_search import (
    SearchBuilder,
    create_schema,
    create_synonyms,
    delete_documents,
    delete_schema,
    upsert_documents,
)
from .helpers import Country, Industry, Round

if TYPE_CHECKING:
    from .claim import ClaimRequest, ClaimVerification
    from .investment import FundingRound
    from .investor import InvestmentFirmBookmark, Investor, InvestorBackup, InvestorBookmark, NotableInvestment
    from .search import SearchHistory


class User(UserMixin, MappedAsDataclass, db.Model, unsafe_hash=True):
    user_info: Mapped[UserInfo] = relationship(
        "UserInfo", back_populates="user", uselist=False, init=False, lazy="joined"
    )
    user_payment: Mapped[UserPayment] = relationship("UserPayment", back_populates="user", uselist=False, init=False)
    user_companies: Mapped[list[UserCompany]] = relationship(
        "UserCompany", back_populates="user", uselist=True, init=False, lazy="joined"
    )
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

    investor: Mapped[Investor] = relationship("Investor", back_populates="user", uselist=False, init=False)
    investor_backup: Mapped[InvestorBackup | None] = relationship(
        "InvestorBackup", back_populates="user", uselist=False, init=False
    )

    company_bookmarks: Mapped[list[CompanyBookmark]] = relationship(
        "CompanyBookmark", back_populates="user", uselist=True, init=False
    )
    investor_bookmarks: Mapped[list[InvestorBookmark]] = relationship(
        "InvestorBookmark", back_populates="user", uselist=True, init=False
    )
    investment_firm_bookmarks: Mapped[list[InvestmentFirmBookmark]] = relationship(
        "InvestmentFirmBookmark", back_populates="user", uselist=True, init=False
    )

    search_histories: Mapped[list[SearchHistory]] = relationship(
        "SearchHistory", back_populates="user", uselist=True, init=False
    )
    oauth_provider: Mapped[OauthProvider] = mapped_column(SQLEnum(OauthProvider))
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
    refuse_all_invitations: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false"), default=False
    )

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


class CompanySuggestionBuilder:
    def __init__(self, company_list: list[dict], investor: Investor | None):
        self.company_list = company_list
        self.investor = investor

    def calculate_all_scores(self):
        for company in self.company_list:
            try:
                bias_score = (company["bias"] / 100) if company["bias"] else 0
            except Exception as e:
                print(f"An error occurred while calculating bias score: {e}")
                bias_score = 0

            try:
                if self.investor.coordinates and company["coordinates"]:  # type: ignore
                    distance = float(geodesic(self.investor.coordinates, company["coordinates"]).kilometers)  # type: ignore
                    location_score = 1 - (distance / 20038)
                else:
                    location_score = 0
            except Exception as e:
                print(f"An error occurred while calculating location score: {e}")
                location_score = 0

            try:
                if company["industry"] in [industry.name for industry in self.investor.industries]:  # type: ignore
                    industry_score = 1
                else:
                    industry_score = 0
            except Exception as e:
                print(f"An error occurred while calculating industry score: {e}")
                industry_score = 0

            try:
                if company["preferred_round"] in [round.name for round in self.investor.rounds]:  # type: ignore
                    round_score = 1
                else:
                    round_score = 0
            except Exception as e:
                print(f"An error occurred while calculating round score: {e}")
                round_score = 0

            try:
                total_score = (
                    COMPANY_WEIGHTS["bias"] * bias_score
                    + COMPANY_WEIGHTS["location"] * location_score
                    + COMPANY_WEIGHTS["industry"] * industry_score
                    + COMPANY_WEIGHTS["round"] * round_score
                )
                company["total_score"] = total_score
            except Exception as e:
                print(f"An error occurred while calculating total score: {e}")
                company["total_score"] = 0
        return self

    def sort_by_score(self):
        self.company_list = sorted(self.company_list, key=lambda x: x["total_score"], reverse=True)
        return self

    def get_id_list(self, quantity: int):
        return [company["id"] for company in self.company_list[:quantity]]


class Company(MappedAsDataclass, db.Model, unsafe_hash=True):
    user_companies: Mapped[list[UserCompany]] = relationship(
        "UserCompany", back_populates="company", uselist=True, init=False
    )
    company_invitations: Mapped[list[CompanyInvitation]] = relationship(
        "CompanyInvitation", back_populates="company", uselist=True, init=False
    )
    notable_investment: Mapped[NotableInvestment] = relationship(
        "NotableInvestment", back_populates="company", uselist=False, init=False
    )
    funding_rounds: Mapped[list[FundingRound]] = relationship(
        "FundingRound", back_populates="company", uselist=True, init=False
    )

    country: Mapped[Country] = relationship(init=False)
    preferred_round: Mapped[Round] = relationship(init=False)
    industry: Mapped[Industry] = relationship(init=False)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, nullable=True, unique=True, init=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True, init=False)
    number_of_employees: Mapped[int | None] = mapped_column(Integer, nullable=True, init=False)
    website_url: Mapped[str | None] = mapped_column(String, nullable=True, init=False)
    linkedin_url: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    instagram_url: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    twitter_url: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    picture_url: Mapped[str | None] = mapped_column(String, nullable=True, init=False)
    country_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("country.id"), nullable=True, init=False)
    preferred_round_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("round.id"), nullable=True, init=False)
    industry_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("industry.id"), nullable=True, init=False)
    _coordinates: Mapped[str | None] = mapped_column(String, nullable=True, init=False)
    search_index: Mapped[str | None] = mapped_column(String, nullable=True, init=False)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"), default=True)

    @property
    def coordinates(self):
        return self._coordinates

    @coordinates.setter
    def coordinates(self, coordinates: str) -> None:
        self._coordinates = suggestion.geocode_location(coordinates).get("coordinates")

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

    def set_slug(self):
        base_slug = slugify(f"{self.name}")

        existing_slug = db.session.scalar(db.select(Company).where(Company.slug == base_slug))

        if existing_slug:
            base_slug = f"{base_slug}-{uuid.uuid4().hex[:4]}"

        self.slug = base_slug

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            self.slug = f"{base_slug}-{uuid.uuid4().hex[:4]}"
            db.session.commit()

    @staticmethod
    def get_by_slug(slug: str) -> Company | None:
        return db.session.scalar(db.select(Company).where(Company.slug == slug))

    @staticmethod
    def get_all() -> Sequence[Company]:
        return db.session.scalars(db.select(Company)).all()

    @staticmethod
    def get_by_id(id: int) -> Company | None:
        return db.session.scalar(db.select(Company).where(Company.id == id))

    @staticmethod
    def get_by_id_list(ids: list[int]) -> Sequence[Company]:
        return db.session.scalars(db.select(Company).where(Company.id.in_(ids))).all()

    @staticmethod
    def get_suggestions(investor: Investor | None, quantity: int) -> Sequence[Company] | None:
        company_list = []
        for company in Company.get_all():
            company_info = {
                "id": company.id,
                "coordinates": company.coordinates,
                "preferred_round": company.preferred_round.name,
                "industry": company.industry.name,
                "description": company.description,
            }
            company_list.append(company_info)
        company_ids = (
            CompanySuggestionBuilder(company_list, investor)
            .calculate_all_scores()
            .sort_by_score()
            .get_id_list(quantity)
        )
        suggestions = Company.get_by_id_list(company_ids)
        suggestions_dict = {suggestion.id: suggestion for suggestion in suggestions}
        sorted_suggestions = [
            suggestions_dict[company_id] for company_id in company_ids if company_id in suggestions_dict
        ]
        return sorted_suggestions

    @staticmethod
    def get_search(
        query_string: str,
        query_by: list[str],
        sort_by: str | None = None,
        sort_desc: bool = False,
        countries: list[str] | None = None,
        preferred_rounds: list[str] | None = None,
        industries: list[str] | None = None,
        per_page: int = 12,
        page: int = 1,
        is_public: bool | None = None,
    ):
        try:
            search_builder = (
                SearchBuilder("companies")
                .query(query_string)
                .query_by(query_by)
                .filter_by("preferred_round", preferred_rounds, exclusivity=False)
                .filter_by("industry", industries, exclusivity=False)
                .filter_by("country", countries, exclusivity=False)
            )

            if is_public is not None:
                search_builder = search_builder.filter_by_boolean("is_public", is_public)

            search_builder = search_builder.sort_by(sort_by, sort_desc).page(page, per_page)
            results = search_builder.search()
        except Exception as e:
            print("An error occurred while searching for companies. Error:", e)
            results = {"found": 0, "page": page, "per_page": per_page, "hits": []}
            return results

        found = results.get("found", 0)
        page = results.get("page", 1)

        pages = found // per_page
        if found % per_page > 0:
            pages += 1

        company_list = []
        for hit in results.get("hits", []):
            hit = hit.get("document", {})
            company_list.append(
                {
                    "id": hit.get("db_id", 0),
                    "name": hit.get("name", ""),
                    "slug": hit.get("slug", ""),
                    "description": hit.get("description", ""),
                    "country": hit.get("country", ""),
                    "preferred_round": hit.get("preferred_round", ""),
                    "industry": hit.get("industry", ""),
                }
            )
        return {"companies": company_list, "found": found, "pages": pages, "page": page}

    @staticmethod
    def get_batches(batch_size: int = 100, stmt: Any = False) -> Generator[Sequence[Company], None, None]:
        stmt = db.select(Company.id) if isinstance(stmt, bool) else stmt

        ids_query = db.session.scalars(stmt).all()

        for ids in chunked(ids_query, batch_size):
            companies = (
                db.session.scalars(
                    db.select(Company)
                    .options(joinedload(Company.preferred_round), joinedload(Company.industry))
                    .where(Company.id.in_(ids))
                )
                .unique()
                .all()
            )
            yield companies

    def delete_data(self):
        delete_documents("companies", str(self.id))

    def upsert_data(self):
        company_object = {}
        if self.search_index:
            company_object["id"] = self.search_index
        company_object["db_id"] = self.id
        if self.name:
            company_object["name"] = self.name
        if self.slug:
            company_object["slug"] = self.slug
        if self.description:
            company_object["description"] = self.description
        if self.country:
            company_object["country"] = self.country.name
        if self.preferred_round:
            company_object["preferred_round"] = self.preferred_round.name
        if self.industry:
            company_object["industry"] = self.industry.name
        if self.is_public:
            company_object["is_public"] = self.is_public

        data = [company_object]

        if self.search_index:
            data[0]["id"] = self.search_index

        result = upsert_documents("companies", data)

        if json.loads(result[0].get("document", "{}")).get("id"):
            search_index = json.loads(result[0].get("document", "{}")).get("id")
        elif result[0].get("id"):
            search_index = result[0].get("id")
        else:
            search_index = None

        if not search_index:
            raise Exception("Search index not found")

        self.search_index = search_index
        db.session.commit()

    @staticmethod
    def sync_search_index(recreate: bool = False):
        if recreate:
            company_schema = {
                "name": "companies",
                "fields": [
                    {"name": "name", "type": "string"},
                    {
                        "name": "db_id",
                        "type": "int32",
                        "facet": True,
                    },
                    {"name": "slug", "type": "string", "optional": True},
                    {
                        "name": "description",
                        "type": "string",
                        "optional": True,
                    },
                    {"name": "country", "type": "string", "facet": True, "optional": True},
                    {"name": "preferred_round", "type": "string", "facet": True, "optional": True},
                    {"name": "industry", "type": "string", "facet": True, "optional": True},
                    {"name": "is_public", "type": "bool", "facet": True, "optional": True},
                    {
                        "name": "embedding",
                        "type": "float[]",
                        "embed": {
                            "from": [
                                "description",
                                "country",
                                "industry",
                                "preferred_round",
                            ],
                            "model_config": {"model_name": "ts/all-MiniLM-L12-v2"},
                        },
                        "optional": True,
                    },
                ],
                "primary_key": "db_id",
            }
            try:
                delete_schema("companies")
            except Exception:
                print("Schema does not exist")
            print("Creating schema")
            create_schema(company_schema)
            create_synonyms("companies")

        batch_count = 1
        for companies in Company.get_batches(batch_size=100):
            print(f"Processing batch {batch_count} of companies...")
            data = []
            for company in companies:
                company_object = {}
                if company.search_index and not recreate:
                    company_object["id"] = company.search_index
                company_object["db_id"] = company.id
                if company.name:
                    company_object["name"] = company.name
                if company.slug:
                    company_object["slug"] = company.slug
                if company.description:
                    company_object["description"] = company.description
                if company.country:
                    company_object["country"] = company.country.name
                if company.preferred_round:
                    company_object["preferred_round"] = company.preferred_round.name
                if company.industry:
                    company_object["industry"] = company.industry.name
                if company.is_public:
                    company_object["is_public"] = company.is_public
                data.append(company_object)

            print("Upserting documents")
            result = upsert_documents("companies", data)

            objects = []
            for index, obj in enumerate(result):
                if obj.get("id"):
                    objects.append((companies[index].id, obj.get("id")))
                else:
                    continue

            query = "UPDATE company SET search_index = CASE id "
            for db_id, search_index in objects:
                query += f"WHEN {db_id} THEN '{search_index}' "
            query += "END WHERE id IN (" + ",".join(str(t[0]) for t in objects) + ")"

            db.session.execute(db.text(query))
            db.session.commit()
            batch_count += 1


class CompanyBookmark(MappedAsDataclass, db.Model, unsafe_hash=True):
    user: Mapped[User] = relationship(User, back_populates="company_bookmarks", uselist=False, init=False)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, init=False
    )
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("company.id"), nullable=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def get_by_user_id(user_id: int, offset: int = 1, limit: int = 10) -> Sequence[Company]:
        return (
            db.session.scalars(
                db.select(Company)
                .join(CompanyBookmark, CompanyBookmark.company_id == Company.id)
                .where(CompanyBookmark.user_id == user_id)
                .offset(offset)
                .limit(limit)
            )
            .unique()
            .all()
        )

    @staticmethod
    def get_id_list(user_id: int) -> Sequence[int]:
        return (
            db.session.execute(
                db.select(Company.id)
                .join(CompanyBookmark, CompanyBookmark.company_id == Company.id)
                .where(CompanyBookmark.user_id == user_id)
            )
            .scalars()
            .all()
        )

    @staticmethod
    def get_by_ids(company_id: int, user_id: int) -> CompanyBookmark | None:
        return db.session.scalars(
            db.select(CompanyBookmark).where(
                CompanyBookmark.company_id == company_id, CompanyBookmark.user_id == user_id
            )
        ).first()

    @staticmethod
    def exists(company_id: int, user_id: int) -> bool:
        return db.session.scalar(
            db.select(exists().where(CompanyBookmark.company_id == company_id, CompanyBookmark.user_id == user_id))
        )


class UserCompany(MappedAsDataclass, db.Model, unsafe_hash=True):
    user: Mapped[User] = relationship(User, back_populates="user_companies", uselist=True, init=False, lazy="joined")
    company: Mapped[Company] = relationship(
        Company, back_populates="user_companies", uselist=True, init=False, lazy="joined"
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    position: Mapped[str | None] = mapped_column(String, nullable=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("company.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[CompanyRole] = mapped_column(SQLEnum(CompanyRole), nullable=False, default=CompanyRole.TEAM)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    @property
    def get_primary(self):
        return self.is_primary

    @get_primary.setter
    def set_primary(self, user_id: int) -> None:
        db.session.execute(update(UserCompany).where(UserCompany.user_id == user_id).values(is_primary=False))
        self.is_primary = True
        db.session.commit()

    @staticmethod
    def get_by_id(id: int) -> UserCompany | None:
        return db.session.scalar(db.select(UserCompany).where(UserCompany.id == id))

    @staticmethod
    def get_user_ids_by_company_id(company_id: int) -> Sequence[int] | None:
        return db.session.scalars(db.select(UserCompany.user_id).where(UserCompany.company_id == company_id)).all()

    @staticmethod
    def get_company_ids_by_user_id(user_id: int) -> Sequence[int] | None:
        return db.session.scalars(db.select(UserCompany.company_id).where(UserCompany.user_id == user_id)).all()

    @staticmethod
    def get_primary_by_user_id(user_id: int) -> UserCompany | None:
        return db.session.scalar(
            db.select(UserCompany).where(UserCompany.user_id == user_id, UserCompany.is_primary.is_(True))
        )

    @staticmethod
    def get_by_user_id(user_id: int) -> Sequence[UserCompany]:
        return (
            db.session.scalars(
                db.select(UserCompany).where(UserCompany.user_id == user_id).order_by(UserCompany.is_primary.desc())
            )
            .unique()
            .all()
        )

    @staticmethod
    def get_by_company_id(company_id: int) -> Sequence[UserCompany]:
        return db.session.scalars(db.select(UserCompany).where(UserCompany.company_id == company_id)).unique().all()

    @staticmethod
    def get_all() -> Sequence[UserCompany]:
        return db.session.scalars(db.select(UserCompany)).all()

    @staticmethod
    def get_members(company_id: int):
        results = (
            db.session.execute(
                db.select(User, UserCompany)
                .join(UserCompany, UserCompany.user_id == User.id)
                .where(UserCompany.company_id == company_id)
            )
            .unique()
            .all()
        )
        return results

    @staticmethod
    def get_by_user_and_company_id(user_id: int, company_id: int) -> UserCompany | None:
        return db.session.scalar(
            db.select(UserCompany).where(
                UserCompany.user_id == user_id,
                UserCompany.company_id == company_id,
            )
        )

    @staticmethod
    def get_by_company_id_and_role(company_id: int, role: CompanyRole) -> Sequence[UserCompany]:
        return (
            db.session.scalars(
                db.select(UserCompany).where(
                    UserCompany.company_id == company_id,
                    UserCompany.role == role,
                )
            )
            .unique()
            .all()
        )

    @staticmethod
    def get_by_company_id_and_email(company_id: int, email: str) -> UserCompany | None:
        return db.session.scalar(
            db.select(UserCompany).join(User).where(UserCompany.company_id == company_id, User.email == email)
        )

    @staticmethod
    def set_private(company_id: int) -> None:
        db.session.execute(update(UserCompany).where(UserCompany.company_id == company_id).values(is_public=False))
        db.session.commit()


class CompanyInvitation(MappedAsDataclass, db.Model, unsafe_hash=True):
    company: Mapped[Company] = relationship(Company, back_populates="company_invitations", uselist=True, init=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), init=False
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    position: Mapped[str | None] = mapped_column(String, nullable=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("company.id", ondelete="CASCADE"), nullable=False)
    invited_by: Mapped[int] = mapped_column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[CompanyRole] = mapped_column(SQLEnum(CompanyRole), nullable=False, default=CompanyRole.TEAM)
    message: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    is_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    INVITATION_VALIDITY = 7

    def is_expired(self) -> bool:
        expiration_time = self.created_at + datetime.timedelta(days=self.INVITATION_VALIDITY)
        return datetime.datetime.now(datetime.UTC) > expiration_time.replace(tzinfo=datetime.UTC)

    @staticmethod
    def get_by_id(id: int) -> CompanyInvitation | None:
        return db.session.scalar(db.select(CompanyInvitation).where(CompanyInvitation.id == id))

    @staticmethod
    def get_by_email(email: str) -> Sequence[CompanyInvitation] | None:
        results = db.session.scalars(
            db.select(CompanyInvitation)
            .options(joinedload(CompanyInvitation.company))
            .where(CompanyInvitation.email == email, CompanyInvitation.is_used.is_(False))
        ).all()
        return results

    @staticmethod
    def get_by_company_id(company_id: int) -> Sequence[CompanyInvitation]:
        return db.session.scalars(
            db.select(CompanyInvitation).where(
                CompanyInvitation.company_id == company_id, CompanyInvitation.is_used.is_(False)
            )
        ).all()

    @staticmethod
    def get_by_company_id_and_email(company_id: int, email: str, get_used: bool = False) -> CompanyInvitation | None:
        return db.session.scalar(
            db.select(CompanyInvitation).where(
                CompanyInvitation.company_id == company_id,
                CompanyInvitation.email == email,
                CompanyInvitation.is_used.is_(get_used),
            )
        )


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, SQLite3Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()
