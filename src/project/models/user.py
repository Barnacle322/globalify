from __future__ import annotations

import datetime
import json
import re
import uuid
from collections.abc import Generator, Sequence
from sqlite3 import Connection as SQLite3Connection
from typing import Any
from uuid import uuid4

from flask_login import UserMixin
from geopy.distance import geodesic
from more_itertools import chunked
from slugify import slugify
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, desc, event, func, or_, text, update
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, MappedAsDataclass, backref, joinedload, mapped_column, relationship, validates

from ..extensions import db
from ..utils import suggestion
from ..utils.enums import CompanyRole, NotificationDestination, OauthProvider, RequestStatus, Tier
from ..utils.suggestion import COMPANY_WEIGHTS, geocode_location
from ..utils.typesense_helpers.typesense_search import (
    SearchBuilder,
    create_schema,
    create_synonyms,
    delete_documents,
    delete_schema,
    upsert_documents,
)
from .helpers import Country, Industry, Round


class User(UserMixin, MappedAsDataclass, db.Model, unsafe_hash=True):
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
    refuse_all_invitations: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false"), default=False
    )

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
            return
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

    @staticmethod
    def get_by_customer_email(email: str) -> UserPayment | None:
        return db.session.scalar(
            db.select(UserPayment).join(User).where(User.email == email).order_by(desc(UserPayment.created))
        )

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
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    token: Mapped[str] = mapped_column(String, nullable=False, insert_default=lambda: str(uuid4()), init=False)
    is_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, init=False
    )

    user: Mapped[User] = relationship(User, backref=backref("email_verifications", passive_deletes=True), init=False)

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


class ClaimVerification(MappedAsDataclass, db.Model, unsafe_hash=True):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    token: Mapped[str] = mapped_column(String, nullable=False, insert_default=lambda: str(uuid4()), init=False)
    is_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, init=False
    )
    investor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("investor.id", ondelete="CASCADE"), nullable=False, kw_only=True
    )

    user: Mapped[User] = relationship(User, backref=backref("claim_verifications", passive_deletes=True), init=False)

    investor: Mapped[Investor] = relationship(  # type: ignore # noqa: F821
        "Investor", backref=backref("claim_verifications", passive_deletes=True), init=False
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
            claim_verifications = db.session.scalars(
                db.select(ClaimVerification).where(ClaimVerification.user_id == user_id)
            ).all()
            for claim_verification in claim_verifications:
                claim_verification.is_expired = True
            db.session.commit()
        except Exception:
            db.session.rollback()

    @staticmethod
    def get_by_token(token: str) -> ClaimVerification | None:
        return db.session.scalar(db.select(ClaimVerification).where(ClaimVerification.token == token))

    @staticmethod
    def get_last_unused_by_user_id(user_id: int) -> ClaimVerification | None:
        last_verification = db.session.scalar(
            db.select(ClaimVerification)
            .where(ClaimVerification.user_id == user_id)
            .where(ClaimVerification.is_used.is_(False))
            .order_by(ClaimVerification.created_at.desc())
        )
        return last_verification


class CompanySuggestionBuilder:
    def __init__(self, company_list: list[dict], investor: Investor | None):  # noqa: F821 # type: ignore
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
    search_index: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

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

    def set_slug(self):
        base_slug = slugify(f"{self.name}")
        unique_slug = base_slug
        attempt = 0

        while True:
            if db.session.scalar(db.select(Company).where(Company.slug == unique_slug)) is not None:
                unique_slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"
                attempt += 1
            else:
                try:
                    self.slug = unique_slug
                    db.session.commit()
                    break
                except IntegrityError:
                    db.session.rollback()
                    unique_slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"
                    attempt += 1
                except Exception as e:
                    print(f"An error occurred: {e}")
                    break

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
    def get_suggestions(investor: Investor | None, quantity: int) -> Sequence[Company] | None:  # type: ignore # noqa: F821
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

    @classmethod
    def get_search(
        cls,
        query_string: str,
        query_by: list[str],
        sort_by: str | None = None,
        sort_desc: bool = False,
        countries: list[str] | None = None,
        preferred_rounds: list[str] | None = None,
        industries: list[str] | None = None,
        per_page: int = 12,
        page: int = 1,
    ):
        try:
            results = (
                SearchBuilder("companies")
                .query(query_string)
                .query_by(query_by)
                .filter_by_round(preferred_rounds)
                .filter_by_industry(industries)
                .filter_by_countries(countries)
                .filter_by_public(True)
                .sort_by(sort_by, sort_desc)
                .page(page, per_page)
                .search()
            )
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
                    "preferred_round": hit.get("preferred_round", []),
                    "industry": hit.get("industry", []),
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
                    {"name": "description", "type": "string"},
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


class UserCompany(MappedAsDataclass, db.Model, unsafe_hash=True):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("company.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[CompanyRole] = mapped_column(SQLEnum(CompanyRole), nullable=False, default=CompanyRole.TEAM)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user: Mapped[User] = relationship(
        User, backref=backref("user_company", passive_deletes=True, uselist=True), init=False
    )
    company: Mapped[Company] = relationship(
        Company, backref=backref("user_company", passive_deletes=True, uselist=True), init=False
    )

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
    def get_primary_by_user_id(user_id: int) -> UserCompany | None:
        return db.session.scalar(
            db.select(UserCompany).where(UserCompany.user_id == user_id, UserCompany.is_primary.is_(True))
        )

    @staticmethod
    def get_by_user_id(user_id: int) -> Sequence[UserCompany]:
        return db.session.scalars(
            db.select(UserCompany).where(UserCompany.user_id == user_id).order_by(UserCompany.is_primary.desc())
        ).all()

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
    def get_by_user_id_and_company_id(user_id: int, company_id: int, get_accepted: bool = False) -> UserCompany | None:
        return db.session.scalar(
            db.select(UserCompany).where(
                UserCompany.user_id == user_id,
                UserCompany.company_id == company_id,
            )
        )

    @staticmethod
    def get_by_company_id_and_role(company_id: int, role: CompanyRole) -> Sequence[UserCompany]:
        return db.session.scalars(
            db.select(UserCompany).where(
                UserCompany.company_id == company_id,
                UserCompany.role == role,
            )
        ).all()

    @staticmethod
    def get_by_company_id_and_email(company_id: int, email: str) -> UserCompany | None:
        return db.session.scalar(
            db.select(UserCompany).join(User).where(UserCompany.company_id == company_id, User.email == email)
        )


class CompanyInvitation(MappedAsDataclass, db.Model, unsafe_hash=True):
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), init=False
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("company.id", ondelete="CASCADE"), nullable=False)
    invited_by: Mapped[int] = mapped_column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[CompanyRole] = mapped_column(SQLEnum(CompanyRole), nullable=False, default=CompanyRole.TEAM)
    message: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    is_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    company: Mapped[Company] = relationship(
        Company, backref=backref("company_invitation", passive_deletes=True, uselist=True), init=False
    )

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
