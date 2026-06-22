from __future__ import annotations

import csv
import datetime
import json
import uuid
from ast import literal_eval
from collections.abc import Generator, Sequence
from itertools import islice
from typing import TYPE_CHECKING, Any

from more_itertools import chunked
from slugify import slugify
from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String, exists, func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import (
    Mapped,
    MappedAsDataclass,
    joinedload,
    mapped_column,
    relationship,
    validates,
)
from thefuzz import fuzz

from ..extensions import db
from ..utils.typesense_helpers.typesense_search import (
    SearchBuilder,
    create_schema,
    create_synonym_sets,
    delete_documents,
    delete_schema,
    upsert_documents,
)
from .helpers import Industry, Round

if TYPE_CHECKING:
    from .claim import ClaimRequest, ClaimVerification
    from .user import User


class NotableInvestment(MappedAsDataclass, db.Model, unsafe_hash=True):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    name: Mapped[str] = mapped_column(String, nullable=False)

    def to_dict(self) -> dict[str, str | int | None]:
        return {
            "id": self.id,
            "name": self.name,
        }

    @staticmethod
    def get_all() -> Sequence[NotableInvestment]:
        return db.session.scalars(db.select(NotableInvestment)).all()

    @staticmethod
    def get_by_id(id: int) -> NotableInvestment | None:
        return db.session.scalar(db.select(NotableInvestment).where(NotableInvestment.id == id))

    @staticmethod
    def get_by_name(name: str) -> NotableInvestment | None:
        return db.session.scalar(db.select(NotableInvestment).where(NotableInvestment.name == name))

    @staticmethod
    def get_by_id_list(id_list) -> Sequence[NotableInvestment]:
        if len(id_list) == 0:
            return []
        valid_id_list = [i for i in id_list if isinstance(i, int)]
        stmt = db.select(NotableInvestment).where(NotableInvestment.id.in_(valid_id_list))
        industries = db.session.execute(stmt).scalars().all()
        return industries


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

investor_notable_investment = db.Table(
    "investor_notable_investment",
    Column("investor_id", Integer, ForeignKey("investor.id"), primary_key=True),
    Column("notable_investment_id", Integer, ForeignKey("notable_investment.id"), primary_key=True),
)

investment_firm_notable_investment = db.Table(
    "investment_firm_notable_investment",
    Column("investment_firm_id", Integer, ForeignKey("investment_firm.id"), primary_key=True),
    Column("notable_investment_id", Integer, ForeignKey("notable_investment.id"), primary_key=True),
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


class InvestorBase(db.Model):
    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[str | None] = mapped_column(String, nullable=True)
    slug: Mapped[str] = mapped_column(String, nullable=True, unique=True)
    firm_name: Mapped[str | None] = mapped_column(String, nullable=True)
    about: Mapped[str | None] = mapped_column(String, nullable=True)
    position: Mapped[str | None] = mapped_column(String, nullable=True)
    website: Mapped[str | None] = mapped_column(String, nullable=True)
    linkedin: Mapped[str | None] = mapped_column(String, nullable=True)
    twitter: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True, unique=False)
    phone_number: Mapped[str | None] = mapped_column(String, nullable=True)
    n_investments: Mapped[int | None] = mapped_column(Integer, nullable=True)
    n_exits: Mapped[int] = mapped_column(Integer, nullable=True)
    min_investment: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    max_investment: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    location: Mapped[str | None] = mapped_column(String, nullable=True)


class Investor(InvestorBase):
    user: Mapped[User | None] = relationship("User", back_populates="investor", uselist=False)
    notable_investments: Mapped[list[NotableInvestment]] = relationship(secondary=investor_notable_investment)
    rounds: Mapped[list[Round]] = relationship(secondary=investor_round)
    industries: Mapped[list[Industry]] = relationship(secondary=investor_industry)
    claim_verifications: Mapped[list[ClaimVerification]] = relationship(
        "ClaimVerification", back_populates="investor", uselist=True
    )
    claim_requests: Mapped[list[ClaimRequest]] = relationship("ClaimRequest", back_populates="investor", uselist=True)
    investor_backup: Mapped[InvestorBackup | None] = relationship(
        "InvestorBackup", back_populates="investor", uselist=False
    )
    origin_point: Mapped[InvestorOriginPoint | None] = relationship(
        "InvestorOriginPoint", back_populates="investor", uselist=False
    )
    _coordinates: Mapped[str | None] = mapped_column(String, nullable=True)
    _country: Mapped[str | None] = mapped_column(String, nullable=True)
    bias: Mapped[int | None] = mapped_column(Integer, nullable=True)
    search_index: Mapped[str | None] = mapped_column(String, nullable=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    is_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<Investor {self.first_name} {self.last_name}>"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name or ''}"

    @full_name.setter
    def full_name(self, add_slug: bool = True) -> None:
        try:
            self.slug = slugify(f"{self.first_name} {self.last_name}")
        except IntegrityError:
            db.session.rollback()
            self.slug = slugify(f"{self.first_name} {self.last_name} {uuid.uuid4().hex[:4]}")

        db.session.commit()

    @property
    def coordinates(self):
        return self._coordinates

    @coordinates.setter
    def coordinates(self, location: str) -> None:
        # TODO(phase-3): geocode via Geography table
        pass

    @property
    def country(self):
        return self._country

    @property
    def min_max_investment(self):
        min_investment, max_investment = None, None
        if self.min_investment is not None and self.min_investment != 0:
            min_investment = f"${self.min_investment:,}"

        if self.max_investment is not None and self.max_investment != 0:
            max_investment = f"${self.max_investment:,}"

        if min_investment and max_investment:
            return f"{min_investment} - {max_investment}"
        elif min_investment:
            return f"{min_investment}+"
        elif max_investment:
            return f"Up to {max_investment}"

    @validates("location")
    def on_location_change(self, key, value):
        # TODO(phase-3): geocode via Geography table
        return value

    @staticmethod
    def get_all() -> Sequence[Investor]:
        return (
            db.session.scalars(
                db.select(Investor).options(joinedload(Investor.rounds), joinedload(Investor.industries))
            )
            .unique()
            .all()
        )

    @staticmethod
    def get_by_slug(slug: str) -> Investor | None:
        return db.session.scalar(db.select(Investor).where(Investor.slug == slug))

    @staticmethod
    def get_by_slug_without_contacts(slug: str) -> Investor | None:
        result = db.session.scalar(db.select(Investor).where(Investor.slug == slug))

        if result:
            result.website = None
            result.linkedin = None
            result.twitter = None
            result.email = None
            result.phone_number = None

            return result

        return None

    @staticmethod
    def get_by_user_id(user_id: int) -> Investor | None:
        return db.session.scalar(db.select(Investor).where(Investor.user_id == user_id))

    @staticmethod
    def get_batches(batch_size: int = 100, stmt: Any = False) -> Generator[Sequence[Investor]]:
        stmt = db.select(Investor.id) if isinstance(stmt, bool) else stmt

        ids_query = db.session.scalars(stmt).all()

        for ids in chunked(ids_query, batch_size):
            investors = (
                db.session.scalars(
                    db.select(Investor)
                    .options(joinedload(Investor.rounds), joinedload(Investor.industries))
                    .where(Investor.id.in_(ids))
                )
                .unique()
                .all()
            )
            yield investors

    @classmethod
    def get_search(
        cls,
        query_string: str,
        query_by: list[str],
        sort_by: str | None = None,
        sort_desc: bool = False,
        rounds_exclusive: bool = False,
        industries_exclusive: bool = False,
        min_investment: int | None = None,
        max_investment: int | None = None,
        countries: list[str] | None = None,
        rounds: list[str] | None = None,
        industries: list[str] | None = None,
        per_page: int = 12,
        page: int = 1,
        is_public: bool | None = None,
        is_approved: bool | None = None,
    ):
        try:
            search_builder = (
                SearchBuilder("investors")
                .query(query_string)
                .query_by(query_by)
                .filter_by_investment_range(min_investment, max_investment)
                .filter_by("rounds", rounds, exclusivity=rounds_exclusive)
                .filter_by("industries", industries, exclusivity=industries_exclusive)
                .filter_by("countries", countries, exclusivity=False)
            )

            if is_approved is not None:
                search_builder = search_builder.filter_by_boolean("is_approved", is_approved)

            if is_public is not None:
                search_builder = search_builder.filter_by_boolean("is_public", is_public)

            search_builder = search_builder.sort_by(sort_by, sort_desc).page(page, per_page)
            results = search_builder.search()

        except Exception:
            results = {"found": 0, "page": page, "per_page": per_page, "hits": []}
            return results

        found = results.get("found", 0)
        page = results.get("page", 1)

        pages = found // per_page
        if found % per_page > 0:
            pages += 1

        investor_list = []
        for hit in results.get("hits", []):
            hit = hit.get("document", {})
            investor_list.append(
                {
                    "id": hit.get("db_id", 0),
                    "name": hit.get("name", ""),
                    "slug": hit.get("slug", ""),
                    "firm_name": hit.get("firm_name", ""),
                    "about": hit.get("about", ""),
                    "position": hit.get("position", ""),
                    "n_investments": hit.get("n_investments", 0),
                    "n_exits": hit.get("n_exits", 0),
                    "min_investment": hit.get("min_investment", 0),
                    "max_investment": hit.get("max_investment", 0),
                    "location": hit.get("location", ""),
                    "_country": hit.get("country", ""),
                    "rounds": hit.get("rounds", []),
                    "industries": hit.get("industries", []),
                    "notable_investments": hit.get("notable_investments", []),
                }
            )
        return {"investors": investor_list, "found": found, "pages": pages, "page": page}

    @staticmethod
    def get_by_id(id: int) -> Investor | None:
        return db.session.scalar(db.select(Investor).where(Investor.id == id))

    @staticmethod
    def get_by_id_with_investments(id: int) -> Investor | None:
        return db.session.scalar(
            db.select(Investor).options(joinedload(Investor.notable_investments)).where(Investor.id == id)
        )

    @staticmethod
    def get_by_user_id_with_investments(user_id: int) -> Investor | None:
        return db.session.scalar(
            db.select(Investor).options(joinedload(Investor.notable_investments)).where(Investor.user_id == user_id)
        )

    @staticmethod
    def get_by_id_list(ids: list[int]) -> Sequence[Investor] | None:
        return (
            db.session.scalars(
                db.select(Investor)
                .options(joinedload(Investor.rounds), joinedload(Investor.industries))
                .where(Investor.id.in_(ids))
            )
            .unique()
            .all()
        )

    @staticmethod
    def get_by_email(email: str) -> Investor | None:
        return db.session.scalar(db.select(Investor).where(Investor.email == email))

    def set_slug(self):
        base_slug = slugify(f"{self.first_name} {self.last_name}")

        existing_slug = db.session.scalar(db.select(Investor).where(Investor.slug == base_slug))

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
    def slugify_existing():
        batch_count = 1
        stmt = db.select(Investor.id).where(Investor.slug.is_(None))
        for investors in Investor.get_batches(batch_size=100, stmt=stmt):
            print(f"Processing batch {batch_count}")
            for investor in investors:
                try:
                    investor.slug = slugify(f"{investor.first_name} {investor.last_name}")
                    db.session.commit()
                except Exception:
                    db.session.rollback()
                    investor.slug = slugify(
                        f"{investor.first_name or ''}-{investor.last_name or ''}-{uuid.uuid4().hex[:6]}"
                    )
                    db.session.commit()

            batch_count += 1

    @staticmethod
    def populate_demo(file_name="data/investor.csv"):
        with open(file_name, newline="") as file:
            existing_notable_investments = NotableInvestment.get_all()
            existing_industry_list = Industry.get_industry_list()
            reader = csv.reader(file, delimiter=";")
            # for row in islice(reader, 84, None):

            for i, row in enumerate(reader):
                check_size_string = row[8]
                range_set = set()
                for range_ in check_size_string.split(","):
                    sanitized_range = (
                        range_.replace("$", "")
                        .replace(",", " ")
                        .replace(" ", "")
                        .replace("K", "000")
                        .replace("M", "000000")
                        .replace("B", "000000000")
                        .replace("+", "")
                    )
                    if "-" in sanitized_range:
                        min_investment, max_investment = sanitized_range.split("-")
                        range_set.add(int(min_investment))
                        range_set.add(int(max_investment))
                    else:
                        if sanitized_range in ["", " "]:
                            continue
                        range_set.add(int(sanitized_range))
                min_investment, max_investment = None, None
                if len(range_set) > 1:
                    min_investment, max_investment = min(range_set), max(range_set)

                industry_list = []
                for industry in row[5].split(","):
                    for i in existing_industry_list:
                        if i and fuzz.ratio(industry, i.name) > 80:
                            industry = i
                            industry_list.append(industry)
                            break

                round_list = []
                for round_ in row[9].split(","):
                    for r in Round.get_all():
                        if round_ == "Series B+":
                            round_list.append(Round.get_by_name("Series B"))
                            round_list.append(Round.get_by_name("Series C"))
                            break
                        if r and fuzz.ratio(round_.lower(), r.name.lower()) > 90:
                            round_ = r
                            round_list.append(round_)
                            break

                notable_investment_list = []
                for notable_investment in row[10].split(","):
                    existing = None
                    for eni in existing_notable_investments:
                        if fuzz.ratio(notable_investment, eni.name) > 90:
                            existing = eni
                            break
                    if existing:
                        notable_investment_list.append(existing)
                    else:
                        ni = NotableInvestment(name=notable_investment)
                        db.session.add(ni)
                        notable_investment_list.append(ni)

                investor = Investor(
                    first_name=row[0].split(" ")[0],
                    last_name=row[0].split(" ")[1],
                    firm_name=row[1],
                    position=row[2],
                    email=row[3],
                    location=row[4],
                    coordinates=row[4],
                    industries=list(set(industry_list)),
                    linkedin=row[6],
                    twitter=row[7],
                    min_investment=min_investment,
                    max_investment=max_investment,
                    rounds=list(set(round_list)),
                    notable_investments=notable_investment_list,
                    is_public=True,
                    is_approved=True,
                )
                investor.set_slug()
                db.session.add(investor)
                print("Added investor:", investor)
        db.session.commit()

    @staticmethod
    def populate_vcsheet(file_name="data/investors_vc.csv"):
        with open(file_name, newline="", encoding="utf-8") as file:
            reader = csv.reader(file, delimiter=",", quotechar='"')
            existing_notable_investments = NotableInvestment.get_all()
            existing_industry_list = Industry.get_industry_list()
            existing_round_list = Round.get_all()
            for row in islice(reader, 1, None):
                first_name = row[0]
                last_name = row[1]
                firm_name = row[2]
                position = row[3]
                about = row[4]
                email = row[5]
                website = row[6]
                linkedin = row[7]
                twitter = row[8]
                # crunchbase = row[9]
                n_exits = row[10] if row[10] else None
                min_investment = int(row[11]) if row[11] else None
                max_investment = int(row[12]) if row[12] else None
                location = row[13]
                # invests_in_location = row[14]

                industries = row[16]

                if email == "":
                    email = None

                industries = literal_eval(row[16])
                industry_list = []
                for industry in industries:
                    for i in existing_industry_list:
                        if i and fuzz.ratio(industry, i.name) > 80:
                            industry = i
                            industry_list.append(industry)
                            break

                rounds = literal_eval(row[15])
                round_list = []
                for round_ in rounds:
                    for r in existing_round_list:
                        if round_ == "Series B+":
                            round_list.append(Round.get_by_name("Series B"))
                            round_list.append(Round.get_by_name("Series C"))
                            break
                        if r and fuzz.ratio(round_.lower(), r.name.lower()) > 90:
                            round_ = r
                            round_list.append(round_)
                            break

                notable_investments = literal_eval(row[17])
                notable_investment_list = []
                for notable_investment in notable_investments:
                    existing = None
                    for eni in existing_notable_investments:
                        if fuzz.ratio(notable_investment, eni.name) > 90:
                            existing = eni
                            break
                    if existing:
                        notable_investment_list.append(existing)
                    else:
                        ni = NotableInvestment(name=notable_investment)
                        db.session.add(ni)
                        notable_investment_list.append(ni)

                investor = Investor(
                    first_name=first_name,
                    last_name=last_name,
                    firm_name=firm_name,
                    position=position,
                    about=about,
                    email=email,
                    location=location,
                    coordinates=location,
                    industries=list(set(industry_list)),
                    rounds=list(set(round_list)),
                    notable_investments=list(set(notable_investment_list)),
                    website=website,
                    linkedin=linkedin,
                    twitter=twitter,
                    min_investment=min_investment,
                    max_investment=max_investment,
                    n_exits=n_exits,
                )
                db.session.add(investor)
        db.session.commit()

    def upsert_data(self):
        investor_object = {}
        if self.search_index:
            investor_object["id"] = self.search_index
        investor_object["db_id"] = self.id
        if self.full_name:
            investor_object["name"] = self.full_name
        if self.slug:
            investor_object["slug"] = self.slug
        if self.firm_name:
            investor_object["firm_name"] = self.firm_name
        if self.about:
            investor_object["about"] = self.about
        if self.position:
            investor_object["position"] = self.position
        if self.n_investments:
            investor_object["n_investments"] = self.n_investments
        if self.n_exits:
            investor_object["n_exits"] = self.n_exits
        if self.min_investment:
            investor_object["min_investment"] = self.min_investment
        if self.max_investment:
            investor_object["max_investment"] = self.max_investment
        if self.location:
            investor_object["location"] = self.location
        if self._country:
            investor_object["country"] = self._country
        if self.rounds:
            investor_object["rounds"] = [round_.name for round_ in self.rounds]
        if self.industries:
            investor_object["industries"] = [industry.name for industry in self.industries]
        else:
            investor_object["industries"] = []
        if self.notable_investments:
            investor_object["notable_investments"] = [
                notable_investment.name for notable_investment in self.notable_investments
            ]
        if self.is_public:
            investor_object["is_public"] = self.is_public
        if self.is_approved:
            investor_object["is_approved"] = self.is_approved

        data = [investor_object]

        if self.search_index:
            data[0]["id"] = self.search_index

        result = upsert_documents("investors", data)

        if json.loads(result[0].get("document", "{}")).get("id"):
            search_index = json.loads(result[0].get("document", "{}")).get("id")
        elif result[0].get("id"):
            search_index = result[0].get("id")

        if not search_index:
            raise Exception("Search index not found")

        self.search_index = search_index
        db.session.commit()

    def delete_data(self):
        delete_documents("investors", str(self.id))

    @staticmethod
    def sync_search_index(recreate: bool = False):
        if recreate:
            investor_schema = {
                "name": "investors",
                "fields": [
                    {"name": "name", "type": "string"},
                    {
                        "name": "db_id",
                        "type": "int32",
                        "facet": True,
                    },
                    {"name": "slug", "type": "string", "optional": True},
                    {"name": "firm_name", "type": "string", "optional": True},
                    {"name": "about", "type": "string", "optional": True},
                    {"name": "position", "type": "string", "facet": True, "optional": True},
                    {"name": "n_investments", "type": "int32", "optional": True, "sort": True},
                    {"name": "n_exits", "type": "int32", "optional": True, "sort": True},
                    {"name": "min_investment", "type": "int32", "optional": True, "sort": True},
                    {"name": "max_investment", "type": "int32", "optional": True, "sort": True},
                    {"name": "location", "type": "string", "facet": True, "optional": True},
                    {"name": "country", "type": "string", "facet": True, "optional": True},
                    {"name": "rounds", "type": "string[]", "facet": True, "optional": True},
                    {"name": "industries", "type": "string[]", "facet": True, "optional": True},
                    {"name": "notable_investments", "type": "string[]", "optional": True},
                    {"name": "is_public", "type": "bool", "optional": True},
                    {"name": "is_approved", "type": "bool", "optional": True},
                    {
                        "name": "embedding",
                        "type": "float[]",
                        "embed": {
                            "from": [
                                "about",
                                "position",
                                "location",
                                "industries",
                            ],
                            "model_config": {"model_name": "ts/all-MiniLM-L12-v2"},
                        },
                    },
                ],
                "primary_key": "db_id",
            }
            try:
                delete_schema("investors")
            except Exception:
                print("Schema does not exist")
            print("Creating schema")
            create_schema(investor_schema)
            create_synonym_sets()

        batch_count = 1
        for investors in Investor.get_batches(batch_size=100):
            print(f"Processing batch {batch_count} of investors...")
            data = []
            for investor in investors:
                investor_object = {}
                if investor.search_index and not recreate:
                    investor_object["id"] = investor.search_index
                investor_object["db_id"] = investor.id
                if investor.full_name:
                    investor_object["name"] = investor.full_name
                if investor.slug:
                    investor_object["slug"] = investor.slug
                if investor.firm_name:
                    investor_object["firm_name"] = investor.firm_name
                if investor.about:
                    investor_object["about"] = investor.about
                if investor.position:
                    investor_object["position"] = investor.position
                if investor.n_investments:
                    investor_object["n_investments"] = investor.n_investments
                if investor.n_exits:
                    investor_object["n_exits"] = investor.n_exits
                if investor.min_investment:
                    investor_object["min_investment"] = investor.min_investment
                if investor.max_investment:
                    investor_object["max_investment"] = investor.max_investment
                if investor.location:
                    investor_object["location"] = investor.location
                if investor._country:
                    investor_object["country"] = investor._country
                if investor.rounds:
                    investor_object["rounds"] = [round_.name for round_ in investor.rounds]
                if investor.industries:
                    investor_object["industries"] = [industry.name for industry in investor.industries]
                if investor.notable_investments:
                    investor_object["notable_investments"] = [
                        notable_investment.name for notable_investment in investor.notable_investments
                    ]
                if investor.is_public is not None:
                    investor_object["is_public"] = investor.is_public
                if investor.is_approved is not None:
                    investor_object["is_approved"] = investor.is_approved
                data.append(investor_object)

            result = upsert_documents("investors", data)

            objects = []
            for index, obj in enumerate(result):
                if json.loads(obj.get("document", "{}")).get("id"):
                    objects.append((investors[index].id, json.loads(obj.get("document", "{}")).get("id")))
                elif obj.get("id"):
                    objects.append((investors[index].id, obj.get("id")))
                else:
                    continue

            query = "UPDATE investor SET search_index = CASE id "
            for db_id, search_index in objects:
                query += f"WHEN {db_id} THEN '{search_index}' "
            query += "END WHERE id IN (" + ",".join(str(t[0]) for t in objects) + ")"

            db.session.execute(db.text(query))
            db.session.commit()
            batch_count += 1


class InvestorBookmark(MappedAsDataclass, db.Model, unsafe_hash=True):
    user: Mapped[User] = relationship("User", back_populates="investor_bookmarks", passive_deletes=True, init=False)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    investor_id: Mapped[int] = mapped_column(Integer, ForeignKey("investor.id"), nullable=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def get_by_user_id(user_id: int, offset: int = 1, limit: int = 10) -> Sequence[Investor]:
        return (
            db.session.scalars(
                db.select(Investor)
                .join(InvestorBookmark, InvestorBookmark.investor_id == Investor.id)
                .where(InvestorBookmark.user_id == user_id, Investor.is_public.is_(True))
                .options(joinedload(Investor.rounds), joinedload(Investor.industries))
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
                db.select(Investor.id)
                .join(InvestorBookmark, InvestorBookmark.investor_id == Investor.id)
                .where(InvestorBookmark.user_id == user_id, Investor.is_public.is_(True))
            )
            .scalars()
            .all()
        )

    @staticmethod
    def get_by_id(investor_id: int, user_id: int) -> InvestorBookmark | None:
        return db.session.scalars(
            db.select(InvestorBookmark).where(
                InvestorBookmark.investor_id == investor_id, InvestorBookmark.user_id == user_id
            )
        ).first()

    @staticmethod
    def exists(investor_id: int, user_id: int) -> bool:
        return db.session.scalar(
            db.select(exists().where(InvestorBookmark.investor_id == investor_id, InvestorBookmark.user_id == user_id))
        )


class InvestmentFirm(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=True)
    slug: Mapped[str] = mapped_column(String, nullable=True, unique=True)
    about: Mapped[str | None] = mapped_column(String, nullable=True)
    website: Mapped[str | None] = mapped_column(String, nullable=True)
    linkedin: Mapped[str | None] = mapped_column(String, nullable=True)
    twitter: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    phone_number: Mapped[str | None] = mapped_column(String, nullable=True)
    n_investments: Mapped[int | None] = mapped_column(Integer, nullable=True)
    n_exits: Mapped[int] = mapped_column(Integer, nullable=True)
    n_employees: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_investment: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_investment: Mapped[int | None] = mapped_column(Integer, nullable=True)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    _coordinates: Mapped[str | None] = mapped_column(String, nullable=True)
    _country: Mapped[str | None] = mapped_column(String, nullable=True)
    bias: Mapped[int | None] = mapped_column(Integer, nullable=True)
    search_index: Mapped[str | None] = mapped_column(String, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    notable_investments: Mapped[list[NotableInvestment]] = relationship(secondary=investment_firm_notable_investment)
    rounds: Mapped[list[Round]] = relationship(secondary=investment_firm_round)
    industries: Mapped[list[Industry]] = relationship(secondary=investment_firm_industry)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<InvestmentFirm {self.name}>"

    @staticmethod
    def get_all() -> Sequence[InvestmentFirm]:
        return (
            db.session.scalars(
                db.select(InvestmentFirm).options(
                    joinedload(InvestmentFirm.rounds), joinedload(InvestmentFirm.industries)
                )
            )
            .unique()
            .all()
        )

    @staticmethod
    def get_by_slug(slug: str) -> InvestmentFirm | None:
        return db.session.scalar(db.select(InvestmentFirm).where(InvestmentFirm.slug == slug))

    @staticmethod
    def get_by_id(id: int) -> InvestmentFirm | None:
        return db.session.scalar(db.select(InvestmentFirm).where(InvestmentFirm.id == id))

    @staticmethod
    def get_by_id_with_investments(id: int) -> InvestmentFirm | None:
        return db.session.scalar(
            db.select(InvestmentFirm)
            .options(joinedload(InvestmentFirm.notable_investments))
            .where(InvestmentFirm.id == id)
        )

    @staticmethod
    def get_by_email(email: str) -> InvestmentFirm | None:
        return db.session.scalar(db.select(InvestmentFirm).where(InvestmentFirm.email == email))

    def set_slug(self):
        base_slug = slugify(f"{self.name}")

        existing_slug = db.session.scalar(db.select(InvestmentFirm).where(InvestmentFirm.slug == base_slug))

        if existing_slug:
            base_slug = f"{base_slug}-{uuid.uuid4().hex[:4]}"

        self.slug = base_slug

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            self.slug = f"{base_slug}-{uuid.uuid4().hex[:4]}"
            db.session.commit()

    @property
    def coordinates(self):
        return self._coordinates

    @property
    def min_max_investment(self):
        if self.min_investment is None or self.max_investment is None:
            return None
        return f"${self.min_investment:,} - ${self.max_investment:,}"

    @coordinates.setter
    def coordinates(self, location: str) -> None:
        # TODO(phase-3): geocode via Geography table
        pass

    @staticmethod
    def get_batches(batch_size: int = 100, stmt: Any = False) -> Generator[Sequence[InvestmentFirm]]:
        stmt = db.select(InvestmentFirm.id) if isinstance(stmt, bool) else stmt
        ids_query = db.session.scalars(stmt).all()

        for ids in chunked(ids_query, batch_size):
            investment_firm = (
                db.session.scalars(
                    db.select(InvestmentFirm)
                    .options(joinedload(InvestmentFirm.rounds), joinedload(InvestmentFirm.industries))
                    .where(InvestmentFirm.id.in_(ids))
                )
                .unique()
                .all()
            )
            yield investment_firm

    @staticmethod
    def get_by_id_list(ids: list[int]) -> Sequence[InvestmentFirm] | None:
        return (
            db.session.scalars(
                db.select(InvestmentFirm)
                .options(joinedload(InvestmentFirm.rounds), joinedload(InvestmentFirm.industries))
                .where(InvestmentFirm.id.in_(ids))
            )
            .unique()
            .all()
        )

    @classmethod
    def get_search(
        cls,
        query_string: str,
        query_by: list[str],
        sort_by: str | None = None,
        sort_desc: bool = False,
        rounds_exclusive: bool = False,
        industries_exclusive: bool = False,
        min_investment: int | None = None,
        max_investment: int | None = None,
        countries: list[str] | None = None,
        rounds: list[str] | None = None,
        industries: list[str] | None = None,
        per_page: int = 12,
        page: int = 1,
        is_public: bool | None = None,
    ):
        try:
            search_builder = (
                SearchBuilder("investment_firms")
                .query(query_string)
                .query_by(query_by)
                .filter_by_investment_range(min_investment, max_investment)
                .filter_by("rounds", rounds, exclusivity=rounds_exclusive)
                .filter_by("industries", industries, exclusivity=industries_exclusive)
                .filter_by("countries", countries, exclusivity=False)
            )

            if is_public is not None:
                search_builder = search_builder.filter_by_boolean("is_public", is_public)

            search_builder = search_builder.sort_by(sort_by, sort_desc).page(page, per_page)
            results = search_builder.search()

        except Exception as e:
            print("An error occurred while searching for investment firms. Error:", e)
            results = {"found": 0, "page": page, "per_page": per_page, "hits": []}
            return results

        found = results.get("found", 0)
        page = results.get("page", 1)

        pages = found // per_page
        if found % per_page > 0:
            pages += 1

        investment_firm_list = []
        for hit in results.get("hits", []):
            hit = hit.get("document", {})
            investment_firm_list.append(
                {
                    "id": hit.get("db_id", 0),
                    "name": hit.get("name", ""),
                    "slug": hit.get("slug", ""),
                    "about": hit.get("about", ""),
                    "n_investments": hit.get("n_investments", 0),
                    "n_exits": hit.get("n_exits", 0),
                    "n_employees": hit.get("n_employees", 0),
                    "min_investment": hit.get("min_investment", 0),
                    "max_investment": hit.get("max_investment", 0),
                    "location": hit.get("location", ""),
                    "_country": hit.get("country", ""),
                    "rounds": hit.get("rounds", []),
                    "industries": hit.get("industries", []),
                    "notable_investments": hit.get("notable_investments", []),
                }
            )
        return {"investment_firms": investment_firm_list, "found": found, "pages": pages, "page": page}

    @staticmethod
    def slugify_existing():
        batch_count = 1
        stmt = db.select(InvestmentFirm.id).where(InvestmentFirm.slug.is_(None))
        for investment_firms in InvestmentFirm.get_batches(batch_size=100, stmt=stmt):
            for investment_firm in investment_firms:
                investment_firm.set_slug()
            batch_count += 1

    @staticmethod
    def populate_vcsheet(file_name="data/funds_vc.csv"):
        with open(file_name, newline="", encoding="utf-8") as file:
            reader = csv.reader(file, delimiter=",", quotechar='"')
            existing_notable_investments = NotableInvestment.get_all()
            existing_industry_list = Industry.get_industry_list()
            existing_round_list = Round.get_all()
            for row in islice(reader, 1, None):
                name = row[0]
                about = row[1]
                website = row[2]
                email = row[3]
                location = row[7]
                n_exits = row[9] if row[9] else None
                min_investment = int(row[10]) if row[10] else None
                max_investment = int(row[11]) if row[11] else None

                industries = row[13]

                if email == "":
                    email = None

                industries = literal_eval(row[13])
                industry_list = []
                for industry in industries:
                    for i in existing_industry_list:
                        if i and fuzz.ratio(industry, i.name) > 80:
                            industry = i
                            industry_list.append(industry)
                            break

                rounds = literal_eval(row[12])
                round_list = []
                for round_ in rounds:
                    for r in existing_round_list:
                        if round_ == "Series B+":
                            round_list.append(Round.get_by_name("Series B"))
                            round_list.append(Round.get_by_name("Series C"))
                            break
                        if r and fuzz.ratio(round_.lower(), r.name.lower()) > 90:
                            round_ = r
                            round_list.append(round_)
                            break

                notable_investments = literal_eval(row[14])
                notable_investment_list = []
                for notable_investment in notable_investments:
                    existing = None
                    for eni in existing_notable_investments:
                        if fuzz.ratio(notable_investment, eni.name) > 90:
                            existing = eni
                            break
                    if existing:
                        notable_investment_list.append(existing)
                    else:
                        ni = NotableInvestment(name=notable_investment)
                        db.session.add(ni)
                        notable_investment_list.append(ni)

                investment_firm = InvestmentFirm(
                    name=name,
                    about=about,
                    email=email,
                    location=location,
                    coordinates=location,
                    industries=list(set(industry_list)),
                    rounds=list(set(round_list)),
                    notable_investments=list(set(notable_investment_list)),
                    website=website,
                    min_investment=min_investment,
                    max_investment=max_investment,
                    n_exits=n_exits,
                )
                db.session.add(investment_firm)
                print(name)
        db.session.commit()

    def upsert_data(self):
        investment_firm_object = {}

        if self.search_index:
            investment_firm_object["id"] = self.search_index
        investment_firm_object["db_id"] = self.id
        if self.name:
            investment_firm_object["name"] = self.name
        if self.slug:
            investment_firm_object["slug"] = self.slug
        if self.about:
            investment_firm_object["about"] = self.about
        if self.n_investments:
            investment_firm_object["n_investments"] = self.n_investments
        if self.n_exits:
            investment_firm_object["n_exits"] = self.n_exits
        if self.n_employees:
            investment_firm_object["n_employees"] = self.n_employees
        if self.min_investment:
            investment_firm_object["min_investment"] = self.min_investment
        if self.max_investment:
            investment_firm_object["max_investment"] = self.max_investment
        if self.location:
            investment_firm_object["location"] = self.location
        if self._country:
            investment_firm_object["country"] = self._country
        if self.rounds:
            investment_firm_object["rounds"] = [round_.name for round_ in self.rounds]
        if self.industries:
            investment_firm_object["industries"] = [industry.name for industry in self.industries]
        else:
            investment_firm_object["industries"] = []
        if self.notable_investments:
            investment_firm_object["notable_investments"] = [
                notable_investment.name for notable_investment in self.notable_investments
            ]
        if self.is_public:
            investment_firm_object["is_public"] = self.is_public

        data = [investment_firm_object]

        if self.search_index:
            data[0]["id"] = self.search_index

        result = upsert_documents("investment_firms", data)

        if result[0].get("id"):
            search_index = result[0].get("id")

        if not search_index:
            raise Exception("Search index not found")

        self.search_index = search_index
        db.session.commit()

    def delete_data(self):
        delete_documents("investment_firms", str(self.id))

    @staticmethod
    def sync_search_index(recreate: bool = False):
        if recreate:
            investment_firm_schema = {
                "name": "investment_firms",
                "fields": [
                    {"name": "name", "type": "string"},
                    {
                        "name": "db_id",
                        "type": "int32",
                        "facet": True,
                    },
                    {"name": "slug", "type": "string", "optional": True},
                    {"name": "about", "type": "string", "optional": True},
                    {"name": "n_investments", "type": "int32", "optional": True, "sort": True},
                    {"name": "n_exits", "type": "int32", "optional": True, "sort": True},
                    {"name": "n_employees", "type": "int32", "optional": True, "sort": True},
                    {"name": "min_investment", "type": "int32", "optional": True, "sort": True},
                    {"name": "max_investment", "type": "int32", "optional": True, "sort": True},
                    {"name": "location", "type": "string", "facet": True, "optional": True},
                    {"name": "country", "type": "string", "facet": True, "optional": True},
                    {"name": "rounds", "type": "string[]", "facet": True, "optional": True},
                    {"name": "industries", "type": "string[]", "facet": True, "optional": True},
                    {"name": "notable_investments", "type": "string[]", "optional": True},
                    {"name": "is_public", "type": "bool", "optional": True},
                    {
                        "name": "embedding",
                        "type": "float[]",
                        "embed": {
                            "from": [
                                "about",
                                "location",
                                "industries",
                            ],
                            "model_config": {"model_name": "ts/all-MiniLM-L12-v2"},
                        },
                    },
                ],
                "primary_key": "db_id",
            }
            try:
                delete_schema("investment_firms")
            except Exception:
                print("Schema does not exist")
            print("Creating schema")
            create_schema(investment_firm_schema)
            create_synonym_sets()

        batch_count = 1
        for investment_firms in InvestmentFirm.get_batches(batch_size=100):
            print(f"Processing batch {batch_count} of investment firms...")
            data = []
            for investment_firm in investment_firms:
                investment_firm_object = {}
                if investment_firm.search_index and not recreate:
                    investment_firm_object["id"] = investment_firm.search_index
                investment_firm_object["db_id"] = investment_firm.id
                investment_firm_object["name"] = investment_firm.name
                investment_firm_object["slug"] = investment_firm.slug
                investment_firm_object["about"] = investment_firm.about
                investment_firm_object["n_investments"] = investment_firm.n_investments
                investment_firm_object["n_exits"] = investment_firm.n_exits
                investment_firm_object["n_employees"] = investment_firm.n_employees
                investment_firm_object["min_investment"] = investment_firm.min_investment
                investment_firm_object["min_investment"] = investment_firm.min_investment
                investment_firm_object["location"] = investment_firm.location
                investment_firm_object["country"] = investment_firm._country
                investment_firm_object["rounds"] = [round_.name for round_ in investment_firm.rounds]
                investment_firm_object["industries"] = [industry.name for industry in investment_firm.industries]
                investment_firm_object["notable_investments"] = [
                    notable_investment.name for notable_investment in investment_firm.notable_investments
                ]
                investment_firm_object["is_public"] = investment_firm.is_public
                data.append(investment_firm_object)

            print("Upserting documents")
            result = upsert_documents("investment_firms", data)

            objects = []
            for index, obj in enumerate(result):
                if obj.get("id"):
                    objects.append((investment_firms[index].id, obj.get("id", 0)))
                else:
                    continue

            query = "UPDATE investment_firm SET search_index = CASE id "
            for db_id, search_index in objects:
                query += f"WHEN {db_id} THEN '{search_index}' "
            query += "END WHERE id IN (" + ",".join(str(t[0]) for t in objects) + ")"

            db.session.execute(db.text(query))
            db.session.commit()
            batch_count += 1


class InvestmentFirmBookmark(MappedAsDataclass, db.Model, unsafe_hash=True):
    user: Mapped[User] = relationship(
        "User", back_populates="investment_firm_bookmarks", passive_deletes=True, init=False
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    investment_firm_id: Mapped[int] = mapped_column(Integer, ForeignKey("investment_firm.id"), nullable=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def get_by_user_id(user_id: int, offset: int = 1, limit: int = 10) -> Sequence[InvestmentFirmBookmark]:
        return (
            db.session.scalars(
                db.select(InvestmentFirm)
                .join(InvestmentFirmBookmark, InvestmentFirmBookmark.investment_firm_id == InvestmentFirm.id)
                .where(InvestmentFirmBookmark.user_id == user_id, InvestmentFirm.is_public.is_(True))
                .options(joinedload(InvestmentFirm.rounds), joinedload(InvestmentFirm.industries))
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
                db.select(InvestmentFirm.id)
                .join(InvestmentFirmBookmark, InvestmentFirmBookmark.investment_firm_id == InvestmentFirm.id)
                .where(InvestmentFirmBookmark.user_id == user_id, InvestmentFirm.is_public.is_(True))
            )
            .scalars()
            .all()
        )

    @staticmethod
    def get_by_id(investment_firm_id: int, user_id: int) -> InvestmentFirmBookmark | None:
        return db.session.scalars(
            db.select(InvestmentFirmBookmark).where(
                InvestmentFirmBookmark.investment_firm_id == investment_firm_id,
                InvestmentFirmBookmark.user_id == user_id,
            )
        ).first()

    @staticmethod
    def exists(investment_firm_id: int, user_id: int) -> bool:
        return db.session.scalar(
            db.select(
                exists().where(
                    InvestmentFirmBookmark.investment_firm_id == investment_firm_id,
                    InvestmentFirmBookmark.user_id == user_id,
                )
            )
        )


investor_backup_round = db.Table(
    "investor_backup_round",
    Column("investor_backup_id", Integer, ForeignKey("investor_backup.id"), primary_key=True),
    Column("round_id", Integer, ForeignKey("round.id"), primary_key=True),
)

investor_backup_industry = db.Table(
    "investor_backup_industry",
    Column("investor_backup_id", Integer, ForeignKey("investor_backup.id"), primary_key=True),
    Column("industry_id", Integer, ForeignKey("industry.id"), primary_key=True),
)

investor_backup_notable_investment = db.Table(
    "investor_backup_notable_investment",
    Column("investor_backup_id", Integer, ForeignKey("investor_backup.id"), primary_key=True),
    Column("notable_investment_id", Integer, ForeignKey("notable_investment.id"), primary_key=True),
)

investor_origin_point_round = db.Table(
    "investor_origin_point_round",
    Column("investor_origin_point_id", Integer, ForeignKey("investor_origin_point.id"), primary_key=True),
    Column("round_id", Integer, ForeignKey("round.id"), primary_key=True),
)

investor_origin_point_industry = db.Table(
    "investor_origin_point_industry",
    Column("investor_origin_point_id", Integer, ForeignKey("investor_origin_point.id"), primary_key=True),
    Column("industry_id", Integer, ForeignKey("industry.id"), primary_key=True),
)

investor_origin_point_notable_investment = db.Table(
    "investor_origin_point_notable_investment",
    Column("investor_origin_point_id", Integer, ForeignKey("investor_origin_point.id"), primary_key=True),
    Column("notable_investment_id", Integer, ForeignKey("notable_investment.id"), primary_key=True),
)


class InvestorBackup(InvestorBase):
    user: Mapped[User | None] = relationship("User", back_populates="investor_backup", uselist=False)
    investor: Mapped[Investor] = relationship(Investor, back_populates="investor_backup", uselist=False)

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=True)
    investor_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("investor.id"), nullable=False)
    notable_investments: Mapped[list[NotableInvestment]] = relationship(secondary=investor_backup_notable_investment)
    rounds: Mapped[list[Round]] = relationship(secondary=investor_backup_round)
    industries: Mapped[list[Industry]] = relationship(secondary=investor_backup_industry)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<InvestorBackup {self.first_name} {self.last_name}>"

    @staticmethod
    def get_by_id(id: int) -> InvestorBackup | None:
        return db.session.scalar(db.select(InvestorBackup).where(InvestorBackup.id == id))

    @staticmethod
    def get_by_investor_id(investor_id: int) -> InvestorBackup | None:
        return db.session.scalar(db.select(InvestorBackup).where(InvestorBackup.investor_id == investor_id))

    @staticmethod
    def get_all() -> Sequence[InvestorBackup]:
        return (
            db.session.scalars(
                db.select(InvestorBackup).options(
                    joinedload(InvestorBackup.rounds), joinedload(InvestorBackup.industries)
                )
            )
            .unique()
            .all()
        )


class InvestorOriginPoint(InvestorBase):
    investor: Mapped[Investor] = relationship(Investor, back_populates="origin_point", uselist=False)

    investor_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("investor.id"), nullable=False)
    notable_investments: Mapped[list[NotableInvestment]] = relationship(
        secondary=investor_origin_point_notable_investment
    )
    rounds: Mapped[list[Round]] = relationship(secondary=investor_origin_point_round)
    industries: Mapped[list[Industry]] = relationship(secondary=investor_origin_point_industry)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<InvestorOriginPoint {self.first_name} {self.last_name}>"

    @staticmethod
    def get_by_id(id: int) -> InvestorOriginPoint | None:
        return db.session.scalar(db.select(InvestorOriginPoint).where(InvestorOriginPoint.id == id))

    @staticmethod
    def get_by_investor_id(investor_id: int) -> InvestorOriginPoint | None:
        return db.session.scalar(db.select(InvestorOriginPoint).where(InvestorOriginPoint.investor_id == investor_id))

    @staticmethod
    def exists(investor_id: int) -> bool:
        return db.session.scalar(db.select(exists().where(InvestorOriginPoint.investor_id == investor_id)))

    @staticmethod
    def get_all() -> Sequence[InvestorOriginPoint]:
        return (
            db.session.scalars(
                db.select(InvestorOriginPoint).options(
                    joinedload(InvestorOriginPoint.rounds), joinedload(InvestorOriginPoint.industries)
                )
            )
            .unique()
            .all()
        )
