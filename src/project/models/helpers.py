from __future__ import annotations

from collections.abc import Sequence

import pycountry
from sqlalchemy import Integer, String, event
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db
from ..utils.info_lists import aggregate as industry_aggregate


class Industry(db.Model):
    """
    Represents an industry.

    Attributes:
        id (int): The industry ID.
        name (str): The name of the industry.
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
        industries = Industry.get_industry_list()

        industry_dict = {category: [] for category in list(map(lambda x: x.category, industries))}
        for industry in industries:
            industry_dict[industry.category].append(industry)
        return industry_dict

    @staticmethod
    def get_industry_list():
        return db.session.scalars(db.select(Industry)).all()

    @staticmethod
    def get_by_id(id: int) -> Industry | None:
        return db.session.scalar(db.select(Industry).filter(Industry.id == id))

    @staticmethod
    def get_by_name(name: str) -> Industry | None:
        return db.session.scalar(db.select(Industry).filter(Industry.name == name))

    @staticmethod
    def populate() -> None:
        try:
            for category, industries in industry_aggregate.items():
                db.session.add_all(list(map(lambda x: Industry(name=x, category=category), industries)))
            db.session.commit()
        except Exception:
            db.session.rollback()

    @staticmethod
    def populate_if_not_exists() -> None:
        try:
            for category, industries in industry_aggregate.items():
                for industry in industries:
                    if not Industry.get_by_name(industry):
                        db.session.add(Industry(name=industry, category=category))
            db.session.commit()
        except Exception:
            db.session.rollback()


class Round(db.Model):
    """
    Represents a funding round.

    Attributes:
        id (int): The round ID.
        name (str): The name of the round.
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<Round {self.name}>"

    @staticmethod
    def get_all() -> Sequence[Round]:
        return db.session.scalars(db.select(Round)).all()

    @staticmethod
    def get_by_id(id: int) -> Round | None:
        return db.session.scalar(db.select(Round).filter(Round.id == id))

    @staticmethod
    def get_by_name(name: str) -> Round | None:
        return db.session.scalar(db.select(Round).filter(Round.name == name))

    @staticmethod
    def populate() -> None:
        try:
            round_list = ["Pre-Seed", "Seed", "Series A", "Series B", "Series C"]
            db.session.add_all(list(map(lambda x: Round(name=x), round_list)))
            db.session.commit()
        except Exception:
            db.session.rollback()


class Country(db.Model):
    """
    Represents a country.

    Attributes:
        id (int): The country ID.
        name (str): The name of the country.
        code (str): The code of the country.
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    code: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<Country {self.name}>"

    @staticmethod
    def get_all() -> Sequence[Country]:
        return db.session.scalars(db.select(Country)).all()

    @staticmethod
    def get_by_code(code: str) -> Country | None:
        return db.session.scalar(db.select(Country).filter(Country.code == code))

    @staticmethod
    def get_by_id(id: int) -> Country | None:
        return db.session.scalar(db.select(Country).filter(Country.id == id))

    @staticmethod
    def get_by_name(name: str) -> Country | None:
        return db.session.scalar(db.select(Country).filter(Country.name == name))

    @staticmethod
    def populate() -> None:
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
    Country.populate()


@event.listens_for(Round.__table__, "after_create")  # type: ignore
def populate_round(*args, **kwargs):
    Round.populate()


@event.listens_for(Industry.__table__, "after_create")  # type: ignore
def populate_industry(*args, **kwargs):
    Industry.populate()
