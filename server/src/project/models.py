from __future__ import annotations

from typing import List, Set, Union

from flask_login import UserMixin
from sqlalchemy import (
    ForeignKey,
    Integer,
    String,
    Text,
    Boolean,
    Table,
    Column,
    DateTime,
)
from sqlalchemy.orm import Mapped, relationship, mapped_column
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db

import pycountry


def populate_database():
    Country.populate()
    IndustrialGroup.populate()
    Industry.populate()
    Round.populate()


class User(UserMixin, db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=True)
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
            user = User.query.filter(User.id == id).first()
            return user
        except:
            return None
        finally:
            db.session.close()

    @staticmethod
    def get_by_email(email: str) -> Union[User, None]:
        try:
            user = User.query.filter(User.email == email).first()
            return user
        except:
            return None
        finally:
            db.session.close()

    @staticmethod
    def signed_with_oauth(email: str) -> bool:
        """
        Returns False if the user signed up with email and password or doesn't exist.
        """
        try:
            user = User.query.filter(User.email == email).first()
            return True if user.password_hash is None else False
        except:
            return False
        finally:
            db.session.close()


class UserInfo(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    user: Mapped[User] = relationship("User", backref="user_info", lazy=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    linkedin: Mapped[str] = mapped_column(String, nullable=True)
    instagram: Mapped[str] = mapped_column(String, nullable=True)
    bio: Mapped[Text] = mapped_column(Text, nullable=True)

    def __repr__(self):
        return f"<UserInfo {self.username}>"

    @staticmethod
    def get_by_user_id(id: int) -> Union[User, None]:
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
                .filter(UserInfo.user_id == id)
                .join(User)
                .first()
            )
            return full_user
        except:
            return None
        finally:
            db.session.close()

    @staticmethod
    def get_by_username(username: str) -> Union[User, None]:
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
        except:
            return None
        finally:
            db.session.close()


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

    def __repr__(self):
        return f"<Company {self.name}>"

    @staticmethod
    def get_by_id(id: int) -> Union[Company, None]:
        try:
            company = Company.query.filter(Company.id == id).first()
            return company
        except:
            return None
        finally:
            db.session.close()


class IndustrialGroup(db.Model):
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
        except:
            db.session.rollback()
        finally:
            db.session.close()


class Industry(db.Model):
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
        except:
            db.session.rollback()
        finally:
            db.session.close()


class Round(db.Model):
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
        except:
            db.session.rollback()
        finally:
            db.session.close()


class Country(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    code: Mapped[str] = mapped_column(String(2), nullable=False, unique=True)

    def __repr__(self):
        return f"<Country {self.name}>"

    @staticmethod
    def get_by_code(code: str) -> Union[Country, None]:
        try:
            country = Country.query.filter(Country.code == code).first()
            return country
        except:
            return None
        finally:
            db.session.close()

    @staticmethod
    def get_by_id(id: int) -> Union[Country, None]:
        try:
            country = Country.query.filter(Country.id == id).first()
            return country
        except:
            return None
        finally:
            db.session.close()

    @staticmethod
    def populate() -> None:
        try:
            country_list = []
            for country in pycountry.countries:
                country_list.append(Country(name=country.name, code=country.alpha_2))
            db.session.add_all(country_list)
            db.session.commit()
        except:
            db.session.rollback()
        finally:
            db.session.close()


class EmailForNewsletter(db.Model):
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
            email = EmailForNewsletter.query.filter(
                EmailForNewsletter.email == email
            ).first()
            return email
        except:
            return None
        finally:
            db.session.close()

    @staticmethod
    def get_all() -> List[EmailForNewsletter]:
        try:
            email_list = EmailForNewsletter.query.all()
            return email_list
        except:
            return None
        finally:
            db.session.close()
