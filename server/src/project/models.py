from __future__ import annotations

import datetime
from typing import List, Union

import pycountry
from flask_login import UserMixin
from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as dbEnum
from sqlalchemy import ForeignKey, Integer, String, Text, event
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db
from .fake_data import (
    get_companies,
    get_emails,
    get_job_positions,
    get_last_names,
    get_names,
    get_websites,
)
from .utils import OauthProvider


class User(UserMixin, db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=True)
    oauth_provider: Mapped[OauthProvider] = mapped_column(
        dbEnum(OauthProvider), nullable=True
    )
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def __repr__(self):
        return f"<User {self.email}>"

    @property
    def password(self) -> None:
        raise AttributeError("Password is not a readable attribute.")

    @password.setter
    def password(self, password) -> None:
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password) -> bool:
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def get_by_id(id: int) -> Union[User, None]:
        try:
            user: User = User.query.filter(User.id == id).first()
            return user
        except NoResultFound:
            return None

    @staticmethod
    def get_by_email(email: str) -> Union[User, None]:
        try:
            user: User = User.query.filter(User.email == email).first()
            return user
        except NoResultFound:
            return None

    @staticmethod
    def signed_with_oauth(email: str) -> Union[bool, OauthProvider]:
        """
        Returns OauthProvider if signed with oauth, False otherwise or if user does not exist.
        """
        try:
            user: User = User.query.filter(User.email == email).first()
            return False if user.oauth_provider is None else user.oauth_provider
        except Exception:
            return False


class UserInfo(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id"), nullable=False, unique=True
    )
    user: Mapped[User] = relationship("User", backref="user_info", lazy=True)
    first_name: Mapped[str] = mapped_column(String, nullable=True)
    last_name: Mapped[str] = mapped_column(String, nullable=True)
    username: Mapped[str] = mapped_column(String, nullable=True)
    bio: Mapped[Text] = mapped_column(Text, nullable=True)
    linkedin: Mapped[str] = mapped_column(String, nullable=True)
    instagram: Mapped[str] = mapped_column(String, nullable=True)
    twitter: Mapped[str] = mapped_column(String, nullable=True)
    # Google storage blob id
    pfp_uuid: Mapped[String] = mapped_column(String, nullable=True)
    is_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def __repr__(self):
        return f"<UserInfo {self.username}>"

    @staticmethod
    def username_available(username: str) -> bool:
        try:
            user_info: UserInfo = UserInfo.query.filter(
                UserInfo.username == username
            ).first()
            return False if user_info else True
        except NoResultFound:
            return True

    @staticmethod
    def get_by_user_id(id: int) -> Union[UserInfo, None]:
        try:
            user_info = (
                db.session.query(UserInfo).filter(UserInfo.user_id == id).first()
            )
            return user_info
        except NoResultFound:
            return None

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


class UserPayment(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id"), nullable=False, unique=True
    )
    user: Mapped[User] = relationship("User", backref="user_payment", lazy=True)
    customer_id: Mapped[str] = mapped_column(String, nullable=False)
    subscription_id: Mapped[str] = mapped_column(String, nullable=True)
    created: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    @property
    def created_epoch(self) -> DateTime:
        return self.created

    @property
    def expires_at_epoch(self) -> DateTime:
        return self.expires_at

    @created_epoch.setter
    def created_epoch(self, created_epoch: int) -> None:
        self.created = datetime.datetime.utcfromtimestamp(created_epoch)  # type: ignore

    @expires_at_epoch.setter
    def expires_at_epoch(self, expires_at_epoch: int) -> None:
        self.expires_at = datetime.datetime.utcfromtimestamp(expires_at_epoch)  # type: ignore

    @staticmethod
    def get_by_customer_id(customer_id: str) -> Union[UserPayment, None]:
        try:
            user_payment: UserPayment = UserPayment.query.filter(
                UserPayment.customer_id == customer_id
            ).first()
            return user_payment
        except NoResultFound:
            return None

    @staticmethod
    def get_by_user_id(user_id: int) -> Union[UserPayment, None]:
        try:
            user_payment: UserPayment = UserPayment.query.filter(
                UserPayment.user_id == user_id
            ).first()
            return user_payment
        except NoResultFound:
            return None


company_industry = db.Table(
    "company_industry",
    Column("company_id", Integer, ForeignKey("company.id"), primary_key=True),
    Column("industry_id", Integer, ForeignKey("industry.id"), primary_key=True),
)


class Company(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    number_of_employees: Mapped[int] = mapped_column(Integer, nullable=True)
    website: Mapped[str] = mapped_column(String, nullable=True)
    # Google storage blob id
    pfp_uuid: Mapped[str] = mapped_column(String, nullable=True)
    country_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("country.id"), nullable=True
    )
    preferred_round_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("round.id"), nullable=True
    )
    industry_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("industry.id"), nullable=True
    )

    user: Mapped[User] = relationship("User", backref="company", lazy=True)
    country: Mapped[Country] = relationship()
    preferred_round: Mapped[Round] = relationship()
    industry: Mapped[Industry] = relationship()

    def __repr__(self):
        return f"<Company {self.name}>"

    @staticmethod
    def get_by_user_id(user_id: int) -> Union[Company, None]:
        try:
            company: Company = Company.query.filter(Company.user_id == user_id).first()
            return company
        except NoResultFound:
            return None

    @staticmethod
    def get_by_id(id: int) -> Union[Company, None]:
        try:
            company: Company = Company.query.filter(Company.id == id).first()
            return company
        except NoResultFound:
            return None


class Industry(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    category: Mapped[str] = mapped_column(String, nullable=False)

    def __repr__(self):
        return f"<Industry {self.name}>"

    @staticmethod
    def get_all():
        try:
            industries: List[Industry] = Industry.query.all()

            industry_dict = {
                category: [] for category in list(map(lambda x: x.category, industries))
            }
            for industry in industries:
                industry_dict[industry.category].append(industry)
            # A clever one-liner that does the same thing as the above for loop
            # industry_dict = {category: [industry.name for industry in industries if industry.category == category] for category in set(map(lambda x: x.category, industries))}
            return industry_dict
        except NoResultFound:
            return {}

    @staticmethod
    def get_by_id(id: int) -> Union[Industry, None]:
        try:
            industry: Industry = Industry.query.filter(Industry.id == id).first()
            return industry
        except NoResultFound:
            return None

    @staticmethod
    def get_by_name(name: str) -> Union[Industry, None]:
        try:
            industry: Industry = Industry.query.filter(Industry.name == name).first()
            return industry
        except NoResultFound:
            return None

    @staticmethod
    def populate() -> None:
        try:
            retail = [
                "Software",
                "Clothing and accessories",
                "Convenience stores",
                "Beauty products",
                "Home goods and furniture",
                "Home electronics",
                "Auto parts and accessories",
                "Jewelry Stores, Watches, Clocks, and Silverware Stores",
                "Precious Stones and Metals, Watches and Jewelry",
                "Other merchandise",
            ]

            digital_products = [
                "Software as a service",
                "Apps",
                "Books",
                "Music or other media",
                "Games",
                "Blogs and written content",
                "Other digital goods",
            ]

            food_and_drink = [
                "Restaurants and nightlife",
                "Grocery stores",
                "Caterers",
                "Other food and dining",
            ]

            professional_services = [
                "Consulting",
                "Printing and publishing",
                "Attorneys and lawyers",
                "Bankruptcy services",
                "Bail Bonds",
                "Accounting, auditing, or tax prep",
                "Computer repair",
                "Testing laboratories",
                "Auto services",
                "Car rentals",
                "Car sales",
                "Lead generation",
                "Direct marketing",
                "Utilities",
                "Government services",
                "Telemarketing",
                "Credit counseling or credit repair",
                "Mortgage consulting services",
                "Debt reduction services",
                "Warranty Services",
                "Other Marketing Services",
                "Other business services",
            ]

            membership_organzations = [
                "Civic, fraternal, or social associations",
                "Charities or social service organizations",
                "Religious organizations",
                "Country clubs",
                "Political organizations",
                "Other membership organizations",
            ]

            personal_services = [
                "Photography studios",
                "Health and beauty spas",
                "Salons or barbers",
                "Landscaping services",
                "Massage parlors",
                "Counseling services",
                "Health and wellness coaching",
                "Laundry or cleaning services",
                "Dating services",
                "Other personal services",
            ]

            transportation = [
                "Ridesharing",
                "Taxis and limos",
                "Courier services",
                "Parking lots",
                "Travel agencies",
                "Freight forwarders",
                "Shipping or forwarding",
                "Commuter transportation",
                "Cruise lines",
                "Airlines and air carriers",
                "Other transportation services",
            ]

            travel_and_lodging = [
                "Property rentals",
                "Hotels, inns, or motels",
                "Timeshares",
                "Other travel and lodging",
            ]

            medical_services = [
                "Medical devices",
                "Doctors and physicians",
                "Opticians and eyeglasses",
                "Dentists and orthodontists",
                "Chiropractors",
                "Nursing or personal care facilities",
                "Hospitals",
                "Personal fundraising or crowdfunding",
                "Mental health services",
                "Assisted living",
                "Veterinary services",
                "Medical organizations",
                "Telemedicine and Telehealth",
                "Other medical services",
            ]

            education = [
                "Child care services",
                "Colleges or universities",
                "Vocational schools or trade schools",
                "Elementary or secondary schools",
                "Other educational services",
            ]

            entertainment_and_recreation = [
                "Event ticketing",
                "Tourist attractions",
                "Recreational camps",
                "Musicians, bands, or orchestras",
                "Amusement parks, carnivals, or circuses",
                "Fortune tellers",
                "Movie theaters",
                "Betting or fantasy sports",
                "Lotteries",
                "Sports forecasting or prediction services",
                "Online gambling",
                "Other entertainment and recreation",
            ]

            building_services = [
                "General contractors",
                "Electrical contractors",
                "Carpentry contractors",
                "Special trade contractors",
                "Telecom services",
                "Telecom equipment",
                "A/C and heating contractors",
                "Other building services",
            ]

            financial_services = [
                "Insurance",
                "Security brokers or dealers",
                "Money orders",
                "Currency exchanges",
                "Wire transfers",
                "Check Cashing",
                "Loans or lending",
                "Collections agencies",
                "Money services or transmission",
                "Investment services",
                "Virtual currencies",
                "Digital Wallets",
                "Cryptocurrencies",
                "Other financial institutions",
                "Financial information and research",
            ]

            regulated = [
                "Pharmacies or pharmaceuticals",
                "Tobacco or cigars",
                "Adult content or services",
                "Vapes, e-cigarettes, e-juice or related products",
                "Weapons or munitions",
                "Supplements or nutraceuticals",
                "Marijuana dispensaries",
                "Marijuana-related products",
                "Accessories for tobacco and marijuana",
                "Alcohol",
            ]

            aggregate = {
                "Retail": retail,
                "Digital Products": digital_products,
                "Food and Drink": food_and_drink,
                "Professional Services": professional_services,
                "Membership Organizations": membership_organzations,
                "Personal Services": personal_services,
                "Transportation": transportation,
                "Travel and Lodging": travel_and_lodging,
                "Medical Services": medical_services,
                "Education": education,
                "Entertainment and Recreation": entertainment_and_recreation,
                "Building Services": building_services,
                "Financial Services": financial_services,
                "Regulated": regulated,
            }

            for category, industries in aggregate.items():
                db.session.add_all(
                    list(map(lambda x: Industry(name=x, category=category), industries))
                )
            db.session.commit()
        except Exception:
            db.session.rollback()


class Round(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    def __repr__(self):
        return f"<Round {self.name}>"

    @staticmethod
    def get_all() -> List[Round]:
        try:
            rounds: List[Round] = Round.query.all()
            return rounds
        except NoResultFound:
            return []

    @staticmethod
    def get_by_id(id: int) -> Union[Round, None]:
        try:
            round: Round = Round.query.filter(Round.id == id).first()
            return round
        except NoResultFound:
            return None

    @staticmethod
    def get_by_name(name: str) -> Union[Round, None]:
        try:
            round: Round = Round.query.filter(Round.name == name).first()
            return round
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

    def __repr__(self):
        return f"<Country {self.name}>"

    @staticmethod
    def get_all() -> List[Country]:
        try:
            countries: List[Country] = Country.query.all()
            return countries
        except NoResultFound:
            return []

    @staticmethod
    def get_by_code(code: str) -> Union[Country, None]:
        try:
            country: Country = Country.query.filter(Country.code == code).first()
            return country
        except NoResultFound:
            return None

    @staticmethod
    def get_by_id(id: int) -> Union[Country, None]:
        try:
            country: Country = Country.query.filter(Country.id == id).first()
            return country
        except NoResultFound:
            return None

    @staticmethod
    def populate() -> None:
        try:
            country_list: List[Country] = []
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


class Investor(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[str] = mapped_column(String, nullable=True)
    firm_name: Mapped[str] = mapped_column(String, nullable=True)
    position: Mapped[str] = mapped_column(String, nullable=True)
    website: Mapped[str] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String, nullable=True, unique=True)

    rounds: Mapped[List[Round]] = relationship(secondary=investor_round)
    industries: Mapped[List[Industry]] = relationship(secondary=investor_industry)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f"<Investor {self.first_name} {self.last_name}>"

    @staticmethod
    def get_all() -> List[Investor]:
        try:
            investors: List[Investor] = Investor.query.all()
            return investors
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
                investors = Investor.query.paginate(
                    page=page, per_page=per_page, error_out=error_out
                )
            else:
                investors = Investor.query.filter(
                    Investor.first_name.icontains(query)
                    | Investor.last_name.icontains(query)
                    | Investor.firm_name.icontains(query)
                    | Investor.position.icontains(query)
                    | Investor.website.icontains(query)
                ).paginate(page=page, per_page=per_page, error_out=error_out)

            return investors
        except NoResultFound:
            return []

    @staticmethod
    def get_by_id(id: int) -> Union[Investor, None]:
        try:
            investor = Investor.query.filter(Investor.id == id).one()
            return investor
        except NoResultFound:
            return None

    @staticmethod
    def get_by_email(email: str) -> Union[Investor, None]:
        try:
            investor: Investor = Investor.query.filter(Investor.email == email).first()
            return investor
        except NoResultFound:
            return None

    @staticmethod
    def populate():
        try:
            investor_list = []
            firstnames = get_names(200)
            lastnames = get_last_names(200)
            emails = get_emails(200)
            websites = get_websites(200)
            job_positions = get_job_positions(200)
            companies = get_companies(200)
            for i in range(1, 200):
                investor_list.append(
                    Investor(
                        first_name=f"{firstnames[i]}",
                        last_name=f"{lastnames[i]}",
                        firm_name=f"{companies[i]}",
                        position=f"{job_positions[i]}",
                        website=f"{websites[i]}",
                        email=f"{str(i) + emails[i]}",
                        rounds=[Round.get_by_id(1), Round.get_by_id(2)],
                        industries=[
                            Industry.get_by_id(1),
                            Industry.get_by_id(2),
                            Industry.get_by_id(3),
                        ],
                    )
                )
            db.session.add_all(investor_list)
            db.session.commit()
        except Exception as e:
            print(e)
            db.session.rollback()


@event.listens_for(Country.__table__, "after_create")
def populate_country(*args, **kwargs):
    Country.populate()


@event.listens_for(Round.__table__, "after_create")
def populate_round(*args, **kwargs):
    Round.populate()


@event.listens_for(Industry.__table__, "after_create")
def populate_industry(*args, **kwargs):
    Industry.populate()


@event.listens_for(Investor.__table__, "after_create")
def populate_investor(*args, **kwargs):
    Investor.populate()
