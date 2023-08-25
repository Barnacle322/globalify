from __future__ import annotations

import enum
import datetime
from typing import List, Union

import pycountry
from flask_login import UserMixin
from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as dbEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


class OauthProvider(enum.Enum):
    GOOGLE = "google"
    LINKEDIN = "linkedin"


class User(UserMixin, db.Model):
    """
    ```python
    def __init__(
        id: int,
        email: str,
        password_hash: str,
        oauth_provider: OauthProvider,
        is_admin: bool,
    ):
    ```
    """

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=True)
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
        except Exception:
            return None
        finally:
            db.session.close()

    @staticmethod
    def get_by_email(email: str) -> Union[User, None]:
        try:
            user: User = User.query.filter(User.email == email).first()
            return user
        except Exception:
            return None
        finally:
            db.session.close()

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
        finally:
            db.session.close()


class UserPayment(db.Model):
    """
    ```python
    def __init__(
        id: int,
        user_id: int,
        user: User,
        customer_id: str,
        subscription_id: str,
        created: datetime,
        expires_at: datetime,
    ):
    ```
    """

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id"), nullable=False, unique=True
    )
    user: Mapped[User] = relationship("User", backref="user_payment", lazy=True)
    customer_id: Mapped[str] = mapped_column(String(255), nullable=False)
    subscription_id: Mapped[str] = mapped_column(String(255), nullable=True)
    created: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)

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
        except Exception:
            return None
        finally:
            db.session.close()

    @staticmethod
    def get_by_user_id(user_id: int) -> Union[UserPayment, None]:
        try:
            user_payment: UserPayment = UserPayment.query.filter(
                UserPayment.user_id == user_id
            ).first()
            return user_payment
        except Exception:
            return None
        finally:
            db.session.close()


class UserInfo(db.Model):
    """
    ```python
    def __init__(
        id: int,
        user_id: int,
        user: User,
        first_name: str,
        last_name: str,
        username: str,
        bio: str,
        linkedin: str,
        instagram: str,
        twitter: str,
        completed: bool,
    ):
    ```
    """

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id"), nullable=False, unique=True
    )
    user: Mapped[User] = relationship("User", backref="user_info", lazy=True)
    first_name: Mapped[str] = mapped_column(String(50), nullable=True)
    last_name: Mapped[str] = mapped_column(String(50), nullable=True)
    username: Mapped[str] = mapped_column(String(50), nullable=True)
    bio: Mapped[Text] = mapped_column(Text, nullable=True)
    linkedin: Mapped[str] = mapped_column(String, nullable=True)
    instagram: Mapped[str] = mapped_column(String, nullable=True)
    twitter: Mapped[str] = mapped_column(String, nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def __repr__(self):
        return f"<UserInfo {self.username}>"

    @staticmethod
    def get_by_user_id(id: int, close_session: bool = True) -> Union[UserInfo, None]:
        try:
            user_info = (
                db.session.query(UserInfo).filter(UserInfo.user_id == id).first()
            )
            return user_info
        except Exception:
            return None
        finally:
            if close_session:
                db.session.close()

    # TODO: redo
    @staticmethod
    def get_by_username(username: str) -> Union[UserInfo, None]:
        try:
            full_user = (
                db.session.query(
                    UserInfo.id,
                    User.email,
                    UserInfo.username,
                    UserInfo.first_name,
                    UserInfo.last_name,
                    UserInfo.linkedin,
                    UserInfo.instagram,
                    UserInfo.bio,
                    User.is_admin,
                )
                .filter(UserInfo.username == username)
                .join(User)
                .first()
            )
            return full_user
        except Exception:
            return None
        finally:
            db.session.close()

    def sanitize(self) -> dict[str, str]:
        user_info = {
            "user_id": self.user_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "linkedin": self.linkedin,
            "instagram": self.instagram,
            "bio": self.bio,
        }
        return user_info


company_industrial_group = db.Table(
    "company_industrial_group",
    Column("company_id", Integer, ForeignKey("company.id"), primary_key=True),
    Column(
        "industrial_group_id",
        Integer,
        ForeignKey("industrial_group.id"),
        primary_key=True,
    ),
)

company_industry = db.Table(
    "company_industry",
    Column("company_id", Integer, ForeignKey("company.id"), primary_key=True),
    Column("industry_id", Integer, ForeignKey("industry.id"), primary_key=True),
)


class Company(db.Model):
    """
    ```python
    def __init__(

        id: int,
        name: str,
        description: str,
        number_of_employees: int,
        website: str,
        picture: str,
        country_id: int,
        country: Country,
        preferred_round_id: int,
        preferred_round: Round,
        industrial_group: List[IndustrialGroup],
        industry: List[Industry],
    ):
    ```
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    number_of_employees: Mapped[int] = mapped_column(Integer, nullable=True)
    website: Mapped[str] = mapped_column(String, nullable=True)
    picture: Mapped[str] = mapped_column(String, nullable=True)

    country_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("country.id"), nullable=True
    )
    country: Mapped[Country] = relationship()

    preferred_round_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("round.id"), nullable=True
    )
    preferred_round: Mapped[Round] = relationship()

    industrial_group: Mapped[List[IndustrialGroup]] = relationship(
        secondary=company_industrial_group
    )
    industry: Mapped[List[Industry]] = relationship(secondary=company_industry)

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=True)
    user: Mapped[User] = relationship("User", backref="company", lazy=True)

    def __repr__(self):
        return f"<Company {self.name}>"

    @staticmethod
    def get_by_id(id: int) -> Union[Company, None]:
        try:
            company: Company = Company.query.filter(Company.id == id).first()
            return company
        except Exception:
            return None
        finally:
            db.session.close()


class IndustrialGroup(db.Model):
    """
    ```python
    def __init__(
        id: int,
        name: str,
    ):
    ```
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    def __repr__(self):
        return f"<IndustrialGroup {self.name}>"

    @staticmethod
    def populate() -> None:
        try:
            industrial_group_list = [
                "Agriculture",
                "Automotive",
                "Banking",
                "Chemical",
                "Construction",
                "Consumer Goods",
                "Education",
                "Energy",
                "Entertainment",
                "Financial Services",
                "Food & Beverage",
                "Healthcare",
                "Hospitality",
                "Insurance",
                "Manufacturing",
                "Media",
                "Mining",
                "Pharmaceutical",
                "Real Estate",
                "Retail",
                "Telecommunications",
                "Transportation",
                "Utilities",
            ]
            db.session.add_all(
                list(map(lambda x: IndustrialGroup(name=x), industrial_group_list))
            )
            db.session.commit()
        except Exception:
            db.session.rollback()
        finally:
            db.session.close()


class Industry(db.Model):
    """
    ```python
    def __init__(
        id: int,
        name: str
    ):
    ```
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    def __repr__(self):
        return f"<Industry {self.name}>"

    @staticmethod
    def populate() -> None:
        try:
            industry_list = [
                "Manufacturing",
                "Sales",
                "Marketing",
                "Information Technology",
                "Health Care",
                "Human Resources",
                "Accounting",
                "Media & Communications",
                "Administrative",
                "Customer Service",
                "Business",
                "Finance",
                "Engineering",
                "Arts & Design",
                "Education",
                "Legal",
                "Entrepreneurship",
                "Writing",
                "Entertainment",
                "Research",
                "Maintenance & Repair",
                "Community & Social Services",
                "Construction",
                "Installation & Repair",
                "Personal Care & Services",
                "Transportation & Logistics",
                "Social Media",
            ]

            db.session.add_all(list(map(lambda x: Industry(name=x), industry_list)))
            db.session.commit()
        except Exception:
            db.session.rollback()
        finally:
            db.session.close()


class Round(db.Model):
    """
    ```python
    def __init__(
        id: int,
        name: str,
    ):
    ```
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)

    def __repr__(self):
        return f"<Round {self.name}>"

    @staticmethod
    def populate() -> None:
        try:
            round_list = ["Pre-Seed", "Seed", "Series A", "Series B", "Series C"]
            db.session.add_all(list(map(lambda x: Round(name=x), round_list)))
            db.session.commit()
        except Exception:
            db.session.rollback()
        finally:
            db.session.close()


class Country(db.Model):
    """
    ```python
    def __init__(
        id: int,
        name: str,
        code: str,
    ):
    ```
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    code: Mapped[str] = mapped_column(String(2), nullable=False, unique=True)

    def __repr__(self):
        return f"<Country {self.name}>"

    @staticmethod
    def get_by_code(code: str) -> Union[Country, None]:
        try:
            country: Country = Country.query.filter(Country.code == code).first()
            return country
        except Exception:
            return None
        finally:
            db.session.close()

    @staticmethod
    def get_by_id(id: int) -> Union[Country, None]:
        try:
            country: Country = Country.query.filter(Country.id == id).first()
            return country
        except Exception:
            return None
        finally:
            db.session.close()

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
        finally:
            db.session.close()


class EmailForNewsletter(db.Model):
    """
    ```python
    def __init__(
        id: int,
        email: str,
        added_at: datetime,
    ):
    ```
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[int] = mapped_column(String(255), nullable=False, unique=True)
    added_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, default=db.func.now()
    )

    def __repr__(self):
        return f"<EmailForNewsletter {self.email}>"

    @staticmethod
    def get_by_email(email: str) -> Union[EmailForNewsletter, None]:
        try:
            email_obj: EmailForNewsletter = EmailForNewsletter.query.filter(
                EmailForNewsletter.email == email
            ).first()
            return email_obj
        except Exception:
            return None
        finally:
            db.session.close()

    @staticmethod
    def get_all() -> Union[List[EmailForNewsletter], None]:
        try:
            email_list: List[EmailForNewsletter] = EmailForNewsletter.query.all()
            return email_list
        except Exception:
            return None
        finally:
            db.session.close()
