from __future__ import annotations

import datetime
import random
from uuid import uuid4

import pycountry
from flask_login import UserMixin
from flask_sqlalchemy.pagination import Pagination
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, and_, desc, event, or_
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db
from .utils.fake_data import (
    get_companies,
    get_emails,
    get_job_positions,
    get_last_names,
    get_names,
    get_websites,
)
from .utils.info_lists import aggregate as industry_aggregate
from .utils.status_enum import OauthProvider, Tier


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
    linkedin: Mapped[str | None] = mapped_column(String, nullable=True)
    instagram: Mapped[str | None] = mapped_column(String, nullable=True)
    twitter: Mapped[str | None] = mapped_column(String, nullable=True)
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
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def sanitize(self) -> dict[str, str]:
        user_info = {
            "user_id": self.user_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "linkedin": self.linkedin,
            "instagram": self.instagram,
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


class Industry(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    category: Mapped[str] = mapped_column(String, nullable=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<Industry {self.name}>"

    @staticmethod
    def get_all():
        try:
            industries: list[Industry] = Industry.query.all()

            industry_dict = {category: [] for category in list(map(lambda x: x.category, industries))}
            for industry in industries:
                industry_dict[industry.category].append(industry)
            return industry_dict
        except NoResultFound:
            return {}

    @staticmethod
    def get_by_id(id: int) -> Industry | None:
        try:
            industry = Industry.query.filter(Industry.id == id).first()
            return industry
        except NoResultFound:
            return None

    @staticmethod
    def get_by_name(name: str) -> Industry | None:
        try:
            industry = Industry.query.filter(Industry.name == name).first()
            return industry
        except NoResultFound:
            return None

    @staticmethod
    def populate() -> None:
        try:
            for category, industries in industry_aggregate.items():
                db.session.add_all(list(map(lambda x: Industry(name=x, category=category), industries)))
            db.session.commit()
        except Exception:
            db.session.rollback()


class Round(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<Round {self.name}>"

    @staticmethod
    def get_all() -> list[Round]:
        try:
            rounds: list[Round] = Round.query.all()
            return rounds
        except NoResultFound:
            return []

    @staticmethod
    def get_by_id(id: int) -> Round | None:
        try:
            investment_round = Round.query.filter(Round.id == id).first()
            return investment_round
        except NoResultFound:
            return None

    @staticmethod
    def get_by_name(name: str) -> Round | None:
        try:
            investment_round = Round.query.filter(Round.name == name).first()
            return investment_round
        except NoResultFound:
            return None

    @staticmethod
    def populate() -> None:
        try:
            round_list = ["Pre-Seed", "Seed", "Series A", "Series B", "Series C"]
            db.session.add_all(list(map(lambda x: Round(name=x), round_list)))
            db.session.commit()
        except Exception:
            db.session.rollback()


class Country(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    code: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<Country {self.name}>"

    @staticmethod
    def get_all() -> list[Country]:
        try:
            countries: list[Country] = Country.query.all()
            return countries
        except NoResultFound:
            return []

    @staticmethod
    def get_by_code(code: str) -> Country | None:
        try:
            country = Country.query.filter(Country.code == code).first()
            return country
        except NoResultFound:
            return None

    @staticmethod
    def get_by_id(id: int) -> Country | None:
        try:
            country = Country.query.filter(Country.id == id).first()
            return country
        except NoResultFound:
            return None

    @staticmethod
    def populate() -> None:
        try:
            country_list: list[Country] = []
            for country in pycountry.countries:
                country_list.append(Country(name=country.name, code=country.alpha_2))
            db.session.add_all(country_list)
            db.session.commit()
        except Exception:
            db.session.rollback()


investor_round = db.Table(
    "investor_round",
    Column("investor_id", Integer, ForeignKey("investor.id"), primary_key=True),
    Column("round_id", Integer, ForeignKey("round.id"), primary_key=True),
)

investor_industry = db.Table(
    "investor_industry",
    Column("investor_id", Integer, ForeignKey("investor.id"), primary_key=True),
    Column("industry_id", Integer, ForeignKey("industry.id"), primary_key=True),
)

investment_firm_round = db.Table(
    "investment_firm_round",
    Column(
        "investment_firm_id",
        Integer,
        ForeignKey("investment_firm.id"),
        primary_key=True,
    ),
    Column("round_id", Integer, ForeignKey("round.id"), primary_key=True),
)

investment_firm_industry = db.Table(
    "investment_firm_industry",
    Column(
        "investment_firm_id",
        Integer,
        ForeignKey("investment_firm.id"),
        primary_key=True,
    ),
    Column("industry_id", Integer, ForeignKey("industry.id"), primary_key=True),
)


class Investor(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[str] = mapped_column(String, nullable=True)
    firm_name: Mapped[str] = mapped_column(String, nullable=True)
    about: Mapped[str] = mapped_column(String, nullable=True)
    position: Mapped[str] = mapped_column(String, nullable=True)
    website: Mapped[str] = mapped_column(String, nullable=True)
    linkedin: Mapped[str] = mapped_column(String, nullable=True)
    twitter: Mapped[str] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String, nullable=True, unique=True)
    phone_number: Mapped[str] = mapped_column(String, nullable=True)
    n_investments: Mapped[int] = mapped_column(Integer, nullable=True)
    n_exits: Mapped[int] = mapped_column(Integer, nullable=True)
    min_investment: Mapped[int] = mapped_column(Integer, nullable=True)
    max_investment: Mapped[int] = mapped_column(Integer, nullable=True)
    location: Mapped[str] = mapped_column(String, nullable=True)

    rounds: Mapped[list[Round]] = relationship(secondary=investor_round)
    industries: Mapped[list[Industry]] = relationship(secondary=investor_industry)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<Investor {self.first_name} {self.last_name}>"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @staticmethod
    def get_all() -> list[Investor]:
        try:
            investors: list[Investor] = Investor.query.all()
            return investors
        except NoResultFound:
            return []

    @staticmethod
    def get_pagination(
        page: int = 1,
        per_page: int = 10,
        error_out: bool = False,
        query: str = "",
        filter_fields: list[str] | None = None,
        rounds: list[Round] | None = None,
        industries: list[Industry] | None = None,
        use_and_rounds: bool | None = None,
        use_and_industries: bool | None = None,
        sort_field: str | None = None,
        descending: bool | None = None,
        min_investment: int | None = None,
        max_investment: int | None = None,
    ) -> Pagination | list[None]:
        class QueryBuilder:
            def __init__(self, base_query):
                self.query = base_query

            def apply_search_filters(self, query_string, filter_fields):
                if query_string:
                    if query_string and filter_fields:
                        filter_conditions = []
                        for field in filter_fields:
                            if hasattr(Investor, field):
                                filter_conditions.append(getattr(Investor, field).ilike(f"%{query_string}%"))
                        if filter_conditions:
                            self.query = self.query.filter(or_(*filter_conditions))
                    else:
                        self.query = self.query.filter(or_(
                                Investor.first_name.ilike(f"%{query_string}%"),
                                Investor.last_name.ilike(f"%{query_string}%"),
                                Investor.firm_name.ilike(f"%{query_string}%"),
                                Investor.position.ilike(f"%{query_string}%"),
                                Investor.about.ilike(f"%{query_string}%"),
                        )
                    )

                return self

            def apply_sorting(self, sort_field, descending):
                if sort_field and hasattr(Investor, sort_field):
                    self.query = (
                        self.query.order_by(desc(sort_field)) if descending else self.query.order_by(sort_field)
                    )
                return self

            def filter_by_rounds(self, rounds, use_and_rounds):
                if rounds:
                    round_filters = [Investor.rounds.any(Round.id == round_obj.id) for round_obj in rounds]
                    condition = and_(*round_filters) if use_and_rounds else or_(*round_filters)
                    self.query = self.query.filter(condition)
                return self

            def filter_by_industries(self, industries, use_and_industries):
                if industries:
                    industry_filters = [Investor.industries.any(Industry.id == industry_obj.id) for industry_obj in industries]
                    condition = and_(*industry_filters) if use_and_industries else or_(*industry_filters)
                    self.query = self.query.filter(condition)
                return self

            def filter_by_investment_range(self, min_investment, max_investment):
                if min_investment and max_investment:
                    investment_filters = and_(
                        Investor.min_investment >= min_investment, Investor.max_investment <= max_investment
                    )
                    self.query = self.query.filter(investment_filters)
                elif min_investment:
                    self.query = self.query.filter(Investor.min_investment >= min_investment)
                elif max_investment:
                    self.query = self.query.filter(Investor.max_investment <= max_investment)
                return self

            def build(self):
                return self.query

        try:
            query_builder = (
                QueryBuilder(Investor.query)
                .apply_search_filters(query, filter_fields)
                .apply_sorting(sort_field, descending)
                .filter_by_rounds(rounds, use_and_rounds)
                .filter_by_industries(industries, use_and_industries)
                .filter_by_investment_range(min_investment, max_investment)
            )
            investors = query_builder.build().paginate(page=page, per_page=per_page, error_out=error_out)

            return investors
        # NOTE: Not sure what exception is thrown when the query return no results
        except Exception:
            return []

    @staticmethod
    def get_by_id(id: int) -> Investor | None:
        try:
            investor = Investor.query.filter(Investor.id == id).one()
            return investor
        except NoResultFound:
            return None

    @staticmethod
    def get_by_email(email: str) -> Investor | None:
        try:
            investor = Investor.query.filter(Investor.email == email).first()
            return investor
        except NoResultFound:
            return None

    @staticmethod
    def populate():
        try:
            investor_list = []
            firstnames = get_names(50)
            lastnames = get_last_names(50)
            emails = get_emails(50)
            websites = get_websites(50)
            job_positions = get_job_positions(50)
            companies = get_companies(50)
            for i in range(1, 50):
                num_rounds = random.randint(1, 5)
                rounds = [Round.get_by_id(random.randint(1, 5)) for _ in range(num_rounds)]
                num_industries = random.randint(1, 6)
                industries = [Industry.get_by_id(random.randint(1, 92)) for _ in range(num_industries)]
                min_investment = random.randrange(100000, 50000001, 100000)
                max_investment = random.randrange(min_investment, 50000001, 100000)
                investor_list.append(
                    Investor(
                        first_name=f"{firstnames[i]}",
                        last_name=f"{lastnames[i]}",
                        about=f"{firstnames[i]} is a {job_positions[i]} at {companies[i]}. Also lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip",
                        firm_name=f"{companies[i]}",
                        position=f"{job_positions[i]}",
                        website=f"{websites[i]}",
                        email=f"{str(i) + emails[i]}",
                        rounds=list(set(rounds)),
                        industries=list(set(industries)),
                        min_investment=min_investment,
                        max_investment=max_investment,
                    )
                )
            db.session.add_all(investor_list)
            db.session.commit()
        except Exception:
            db.session.rollback()


class InvestmentFirm(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=True)
    about: Mapped[str] = mapped_column(String, nullable=True)
    website: Mapped[str] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String, nullable=True, unique=True)
    phone_number: Mapped[str] = mapped_column(String, nullable=True)
    n_investments: Mapped[int] = mapped_column(Integer, nullable=True)
    n_exits: Mapped[int] = mapped_column(Integer, nullable=True)
    n_employees: Mapped[int] = mapped_column(Integer, nullable=True)
    min_investment: Mapped[str] = mapped_column(String, nullable=True)
    max_investment: Mapped[str] = mapped_column(String, nullable=True)

    rounds: Mapped[list[Round]] = relationship(secondary=investment_firm_round)
    industries: Mapped[list[Industry]] = relationship(secondary=investment_firm_industry)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<InvestmentFirm {self.name}>"

    @staticmethod
    def get_all() -> list[InvestmentFirm]:
        try:
            firms: list[InvestmentFirm] = InvestmentFirm.query.all()
            return firms
        except NoResultFound:
            return []

    @staticmethod
    def get_pagination(
        page: int = 1,
        per_page: int = 10,
        error_out: bool = False,
        query: str = "",
    ):
        try:
            if query == "":
                firms = InvestmentFirm.query.paginate(page=page, per_page=per_page, error_out=error_out)
            else:
                firms = InvestmentFirm.query.filter(
                    InvestmentFirm.name.icontains(query) | InvestmentFirm.about.icontains(query)
                ).paginate(page=page, per_page=per_page, error_out=error_out)

            return firms
        except NoResultFound:
            return []

    @staticmethod
    def get_by_id(id: int) -> InvestmentFirm | None:
        try:
            firm = InvestmentFirm.query.filter(InvestmentFirm.id == id).one()
            return firm
        except NoResultFound:
            return None

    @staticmethod
    def get_by_email(email: str) -> InvestmentFirm | None:
        try:
            firm = InvestmentFirm.query.filter(InvestmentFirm.email == email).first()
            return firm
        except NoResultFound:
            return None


@event.listens_for(Country.__table__, "after_create")  # type: ignore
def populate_country(*args, **kwargs):
    Country.populate()


@event.listens_for(Round.__table__, "after_create")  # type: ignore
def populate_round(*args, **kwargs):
    Round.populate()


@event.listens_for(Industry.__table__, "after_create")  # type: ignore
def populate_industry(*args, **kwargs):
    Industry.populate()


# @event.listens_for(Investor.__table__, "after_create")  # type: ignore
# def populate_investor(*args, **kwargs):
#     Investor.populate()
