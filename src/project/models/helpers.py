from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

import pycountry
from sqlalchemy import Integer, String, event
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db
from ..utils.info_lists import aggregate as industry_aggregate
from ..utils.typesense_helpers.typesense_search import (
    create_schema,
    create_synonyms,
    delete_schema,
    upsert_documents,
)

if TYPE_CHECKING:
    from ..models import FundingRound


class Industry(db.Model):
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
        return db.session.scalar(db.select(Industry).where(Industry.id == id))

    @staticmethod
    def get_by_name(name: str) -> Industry | None:
        return db.session.scalar(db.select(Industry).where(Industry.name == name))

    @staticmethod
    def populate() -> None:
        try:
            for category, industries in industry_aggregate.items():
                db.session.add_all(list(map(lambda x: Industry(name=x, category=category), industries)))
            db.session.commit()
        except Exception:
            db.session.rollback()

    @staticmethod
    def get_by_id_list(id_list) -> Sequence[Industry]:
        if len(id_list) == 0:
            return []
        valid_id_list = [i for i in id_list if isinstance(i, int)]
        industries = db.session.execute(db.select(Industry).where(Industry.id.in_(valid_id_list))).scalars().all()
        return industries

    @staticmethod
    def populate_if_not_exists() -> None:
        try:
            print(Industry.get_industry_list(), "Here")
            for category, industries in industry_aggregate.items():
                for industry in industries:
                    if not Industry.get_by_name(industry):
                        db.session.add(Industry(name=industry, category=category))
            db.session.commit()

        except Exception:
            db.session.rollback()

    @staticmethod
    def sync_typesense(recreate: bool = False):
        if recreate:
            industry_schema = {
                "name": "industries",
                "fields": [
                    {
                        "name": "db_id",
                        "type": "int32",
                        "facet": True,
                    },
                    {"name": "name", "type": "string"},
                    {
                        "name": "embedding",
                        "type": "float[]",
                        "embed": {
                            "from": ["name"],
                            "model_config": {"model_name": "ts/all-MiniLM-L12-v2"},
                        },
                    },
                ],
                "primary_key": "db_id",
            }
            try:
                delete_schema("industries")
            except Exception:
                print("Schema does not exist")
            create_schema(industry_schema)
            create_synonyms("industries")
        data = []
        for industry in Industry.get_industry_list():
            industry_object = {}

            industry_object["db_id"] = industry.id
            industry_object["name"] = industry.name

            data.append(industry_object)

        print("Upserting documents")
        upsert_documents("industries", data)


class Round(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    funding_rounds: Mapped[list[FundingRound]] = relationship("FundingRound", back_populates="round", uselist=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<Round {self.name}>"

    @staticmethod
    def get_all() -> Sequence[Round]:
        return db.session.scalars(db.select(Round)).all()

    @staticmethod
    def get_by_id(id: int) -> Round | None:
        return db.session.scalar(db.select(Round).where(Round.id == id))

    @staticmethod
    def get_by_name(name: str) -> Round | None:
        return db.session.scalar(db.select(Round).where(Round.name == name))

    @staticmethod
    def get_by_id_list(id_list) -> Sequence[Round]:
        if len(id_list) == 0:
            return []
        valid_id_list = [i for i in id_list if isinstance(i, int)]
        rounds = db.session.execute(db.select(Round).where(Round.id.in_(valid_id_list))).scalars().all()
        return rounds

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
    def get_all() -> Sequence[Country]:
        return db.session.scalars(db.select(Country)).all()

    @staticmethod
    def get_by_code(code: str) -> Country | None:
        return db.session.scalar(db.select(Country).where(Country.code == code))

    @staticmethod
    def get_by_id(id: int) -> Country | None:
        return db.session.scalar(db.select(Country).where(Country.id == id))

    @staticmethod
    def get_by_name(name: str) -> Country | None:
        return db.session.scalar(db.select(Country).where(Country.name == name))

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
