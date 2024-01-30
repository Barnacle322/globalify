from __future__ import annotations

import pycountry
from sqlalchemy import Integer, String, event
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db
from ..utils.info_lists import aggregate as industry_aggregate


class Industry(db.Model):
    """
    Represents an industry.

    Attributes:
        id (int): The industry ID.
        name (str): The name of the industry.

        class NotableInvestment(db.Model):


        category (str): The category of the industry.

    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    category: Mapped[str] = mapped_column(String, nullable=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<Industry {self.name}>"

    @staticmethod
    def get_all() -> dict[str, list[Industry]] | None:
        """
        Retrieves all industries.

        Returns:
            dict[str, list[Industry]]: A dictionary mapping industry categories to lists of industries.

        """
        try:
            industries: list[Industry] = Industry.query.all()

            industry_dict = {category: [] for category in list(map(lambda x: x.category, industries))}
            for industry in industries:
                industry_dict[industry.category].append(industry)
            return industry_dict
        except NoResultFound:
            return {}

    @staticmethod
    def get_industry_list():
        try:
            industries: list[Industry] = Industry.query.all()
            return industries
        except NoResultFound:
            return []

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
        """
        Populates the industries by adding them to the database.

        Raises:
            Exception: If an exception occurs during the population process, the changes are rolled back.

        """
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
        """
        Populates the investment rounds.

        This method adds a list of predefined investment round names to the database session
        and commits the changes.

        Raises:
            Exception: If an exception occurs during the population process, the changes are rolled back.

        """
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
        """
        Populates the countries.

        This method retrieves country data from the `pycountry` library and creates `Country` objects
        with the specified names and codes. The created objects are then added to the database session and committed.

        Raises:
            Exception: If an exception occurs during the population process, the changes are rolled back.

        """
        try:
            country_list: list[Country] = []
            for country in pycountry.countries:
                country_list.append(Country(name=country.name, code=country.alpha_2))  # type: ignore
            db.session.add_all(country_list)
            db.session.commit()
        except Exception:
            db.session.rollback()


@event.listens_for(Country.__table__, "after_create")  # type: ignore
def populate_country(*args, **kwargs):
    """
    Event listener function for populating countries after the Country table is created.

    This function calls the `populate` method of the `Country` class to populate the countries in the database.

    """
    Country.populate()


@event.listens_for(Round.__table__, "after_create")  # type: ignore
def populate_round(*args, **kwargs):
    """
    Event listener function for populating rounds after the Round table is created.

    This function calls the `populate` method of the `Round` class to populate the rounds in the database.

    """
    Round.populate()


@event.listens_for(Industry.__table__, "after_create")  # type: ignore
def populate_industry(*args, **kwargs):
    """
    Event listener function for populating industries after the Industry table is created.

    This function calls the `populate` method of the `Industry` class to populate the industries in the database.

    """
    Industry.populate()
