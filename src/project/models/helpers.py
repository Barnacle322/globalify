from __future__ import annotations

import pycountry
from sqlalchemy import Integer, String, event
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db
from ..utils.info_lists import aggregate as industry_aggregate


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


@event.listens_for(Country.__table__, "after_create")  # type: ignore
def populate_country(*args, **kwargs):
    Country.populate()


@event.listens_for(Round.__table__, "after_create")  # type: ignore
def populate_round(*args, **kwargs):
    Round.populate()


@event.listens_for(Industry.__table__, "after_create")  # type: ignore
def populate_industry(*args, **kwargs):
    Industry.populate()