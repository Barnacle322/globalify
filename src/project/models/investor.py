from __future__ import annotations

import csv
import datetime
import json
import random
import uuid
from ast import literal_eval
from collections.abc import Generator, Sequence
from itertools import islice
from typing import Any

from geopy.distance import geodesic
from more_itertools import chunked
from slugify import slugify
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import (
    Mapped,
    MappedAsDataclass,
    backref,
    defer,
    joinedload,
    mapped_column,
    relationship,
    selectinload,
    validates,
)
from thefuzz import fuzz

from ..extensions import db
from ..models.user import Company, User
from ..utils.fake_data import (
    get_abouts,
    get_companies,
    get_countrys,
    get_emails,
    get_job_positions,
    get_last_names,
    get_names,
    get_phone_numbers,
    get_websites,
)
from ..utils.info_lists import notable_investment_list
from ..utils.scraper import populate_blockchain, populate_demo
from ..utils.scraper_helpers.population import (
    get_rounds,
)
from ..utils.suggestion import WEIGHTS, geocode_location
from ..utils.typesense_helpers.typesense_search import (
    SearchBuilder,
    create_schema,
    create_synonyms,
    delete_documents,
    delete_schema,
    upsert_documents,
)
from .helpers import Industry, Round


class SuggestionBuilder:
    def __init__(self, investor_list: list[dict], company: Company | None):
        self.investor_list = investor_list
        self.company = company

    def calculate_all_scores(self):
        for investor in self.investor_list:
            # Calculate bias score
            try:
                bias_score = (investor["bias"] / 100) if investor["bias"] else 0
            except Exception as e:
                print(f"An error occurred while calculating bias score: {e}")
                bias_score = 0

            # Calculate location score
            try:
                if self.company and self.company.coordinates and investor["coordinates"]:
                    distance = float(geodesic(self.company.coordinates, investor["coordinates"]).kilometers)  # type: ignore
                    location_score = 1 - (distance / 20038)
                else:
                    location_score = 0
            except Exception as e:
                print(f"An error occurred while calculating location score: {e}")
                location_score = 0

            # Calculate exits score
            try:
                if investor["n_investments"] and investor["n_exits"]:
                    exits_score = 1 if (investor["n_exits"] / investor["n_investments"]) >= 0.5 else 0
                else:
                    exits_score = 0
            except Exception as e:
                print(f"An error occurred while calculating exits score: {e}")
                exits_score = 0

            # Calculate industry score
            try:
                if self.company.industry.name in investor["industries"] and len(investor["industries"]) == 1:  # type: ignore
                    industry_score = 1
                elif self.company.industry.name in investor["industries"]:  # type: ignore
                    industry_score = 0.8
                else:
                    industry_score = 0
            except Exception as e:
                print(f"An error occurred while calculating industry score: {e}")
                industry_score = 0

            # Calculate round score
            try:
                if self.company.preferred_round.name in investor["rounds"] and len(investor["rounds"]) == 1:  # type: ignore
                    round_score = 1
                elif self.company.preferred_round.name in investor["rounds"]:  # type: ignore
                    round_score = 0.8
                else:
                    round_score = 0
            except Exception as e:
                print(f"An error occurred while calculating round score: {e}")
                round_score = 0

            # Calculate completeness score
            try:
                completeness_score = 1
                for value in investor.values():
                    if not value:
                        completeness_score -= 0.1
                if completeness_score < 0:
                    completeness_score = 0
            except Exception as e:
                print(f"An error occurred while calculating completeness score: {e}")
                completeness_score = 0

            try:
                total_score = (
                    WEIGHTS["bias"] * bias_score
                    + WEIGHTS["location"] * location_score
                    + WEIGHTS["exits"] * exits_score
                    + WEIGHTS["industry"] * industry_score
                    + WEIGHTS["round"] * round_score
                    + WEIGHTS["completeness"] * completeness_score
                )
                investor["total_score"] = total_score
            except Exception as e:
                print(f"An error occurred while calculating total score: {e}")
                investor["total_score"] = 0
        return self

    def sort_by_score(self):
        self.investor_list = sorted(self.investor_list, key=lambda x: x["total_score"], reverse=True)
        return self

    def get_id_list(self, quantity: int):
        return [investor["id"] for investor in self.investor_list[:quantity]]


class NotableInvestment(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("company.id"), nullable=True)

    company: Mapped[Company | None] = relationship(Company, backref=backref("notable_investment", uselist=False))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<NotableInvestment {self.name}>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "company_id": self.company_id,
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
    def get_by_names(names: list[str]) -> Sequence[NotableInvestment]:
        return db.session.scalars(db.select(NotableInvestment).where(NotableInvestment.name.in_(names))).all()

    @staticmethod
    def get_by_id_list(id_list) -> Sequence[NotableInvestment]:
        if len(id_list) == 0:
            return []
        valid_id_list = [i for i in id_list if isinstance(i, int)]
        stmt = db.select(NotableInvestment).where(NotableInvestment.id.in_(valid_id_list))
        industries = db.session.execute(stmt).scalars().all()
        return industries

    @staticmethod
    def populate() -> None:
        try:
            notable_investments = list(set(notable_investment_list))
            db.session.add_all(list(map(lambda x: NotableInvestment(name=x), notable_investments)))
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
    _coordinates: Mapped[str | None] = mapped_column(String, nullable=True)
    _country: Mapped[str | None] = mapped_column(String, nullable=True)
    bias: Mapped[int | None] = mapped_column(Integer, nullable=True)
    search_index: Mapped[str | None] = mapped_column(String, nullable=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=True)

    user: Mapped[User | None] = relationship(User, backref=backref("investor", uselist=False))
    notable_investments: Mapped[list[NotableInvestment]] = relationship(secondary=investor_notable_investment)
    rounds: Mapped[list[Round]] = relationship(secondary=investor_round)
    industries: Mapped[list[Industry]] = relationship(secondary=investor_industry)

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
        geo_data = geocode_location(location)
        if geo_data is not None:
            self._coordinates = geo_data["coordinates"]  # type: ignore
            self._country = geo_data["country_name"]  # type: ignore

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
        geo_data = geocode_location(value)
        if geo_data is not None:
            self._coordinates = geo_data["coordinates"]  # type: ignore
            self._country = geo_data["country_name"]  # type: ignore
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
    def get_batches(batch_size: int = 100, stmt: Any = False) -> Generator[Sequence[Investor], None, None]:
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

    @staticmethod
    def get_suggestions(company: Company | None, quantity: int) -> Sequence[Investor] | None:
        investor_list = []
        for investor in Investor.get_all():
            investor_info = {
                "id": investor.id,
                "bias": investor.bias,
                "n_investments": investor.n_investments,
                "n_exits": investor.n_exits,
                "coordinates": investor.coordinates,
                "rounds": [round.name for round in investor.rounds],
                "industries": [industry.name for industry in investor.industries],
                "min_investment": investor.min_investment,
                "max_investment": investor.max_investment,
                "about": investor.about,
            }
            investor_list.append(investor_info)
        investor_ids = (
            SuggestionBuilder(investor_list, company).calculate_all_scores().sort_by_score().get_id_list(quantity)
        )
        suggestions = Investor.get_by_id_list(investor_ids)
        suggestions_dict = {suggestion.id: suggestion for suggestion in suggestions}  # type: ignore
        sorted_suggestions = [
            suggestions_dict[investor_id] for investor_id in investor_ids if investor_id in suggestions_dict
        ]
        return sorted_suggestions

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
    ):
        try:
            results = (
                SearchBuilder("investors")
                .query(query_string)
                .query_by(query_by)
                .filter_by_investment_range(min_investment, max_investment)
                .filter_by("rounds", rounds, exclusivity=rounds_exclusive)
                .filter_by("industries", industries, exclusivity=industries_exclusive)
                .filter_by("countries", countries, exclusivity=False)
                .sort_by(sort_by, sort_desc)
                .page(page, per_page)
                .search()
            )

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
                        f"{investor.first_name or ""}-{investor.last_name or ""}-{uuid.uuid4().hex[:6]}"
                    )
                    db.session.commit()

            batch_count += 1

    @staticmethod
    def populate() -> None:
        investor_list = []
        firstnames = get_names(50)
        lastnames = get_last_names(50)
        emails = get_emails(50)
        websites = get_websites(50)
        job_positions = get_job_positions(50)
        locations = get_countrys(50)
        companies = get_companies(50)
        for i in range(1, 10):
            num_rounds = random.randint(1, 5)
            rounds = [Round.get_by_id(random.randint(1, 5)) for _ in range(num_rounds)]
            num_industries = random.randint(1, 6)
            industries = [Industry.get_by_id(random.randint(1, 92)) for _ in range(num_industries)]
            notable_investments = [
                NotableInvestment.get_by_id(random.randint(1, len(NotableInvestment.get_all())))
                for _ in range(random.randint(1, 10))
            ]
            min_investment = random.randrange(100000, 50000001, 100000)
            investor_populate = Investor(
                first_name=f"{firstnames[i]}",
                last_name=f"{lastnames[i]}",
                about=f"{firstnames[i]} is a {job_positions[i]} at {companies[i]}. {get_abouts(1)[0]}",
                firm_name=f"{companies[i]}",
                position=f"{job_positions[i]}",
                website=f"{websites[i]}",
                linkedin=f"https://www.linkedin.com/in/{firstnames[i]}-{lastnames[i]}",
                twitter=f"https://twitter.com/{firstnames[i]}{lastnames[i]}",
                email=f"{str(i) + emails[i]}",
                phone_number=f"+1{random.randrange(1000000000, 9999999999)}",
                n_investments=random.randint(100, 200),
                n_exits=random.randint(1, 100),
                location=locations[i],
                coordinates=locations[i],
                rounds=list(set(rounds)),
                industries=list(set(industries)),
                min_investment=min_investment,
                max_investment=random.randrange(min_investment, 50000001, 100000),
                notable_investments=list(set(notable_investments)),
            )
            investor_populate.full_name = True
            investor_list.append(investor_populate)
        db.session.add_all(investor_list)
        db.session.commit()

    @staticmethod
    def populate_all():
        investors_list = []
        investors_list += populate_demo(NotableInvestment, Industry)
        investors_list += populate_blockchain(NotableInvestment, Industry)
        count = 0
        for investor in investors_list:
            item = Investor(
                first_name=investor.get("first_name"),
                last_name=investor.get("last_name"),
                firm_name=investor.get("firm_name"),
                position=investor.get("position"),
                about=investor.get("about"),
                email=investor.get("email"),
                location=investor.get("location"),
                coordinates=investor.get("location"),
                industries=investor.get("industries"),
                linkedin=investor.get("linkedin"),
                twitter=investor.get("twitter"),
                min_investment=investor.get("min_investment"),
                max_investment=investor.get("max_investment"),
                rounds=investor.get("rounds"),
                notable_investments=investor.get("notable_investments"),
            )
            db.session.add(item)
            count += 1
            print("Added investor:", item)
        print(f"Added {count} investors")
        db.session.commit()

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
                )
                investor.set_slug()
                db.session.add(investor)
                print("Added investor:", investor)
        db.session.commit()

    @staticmethod
    def populate_cli():
        with open("data/mercury_investor.jsonl", encoding="utf-8-sig") as file:
            investors = file.readlines()
            existing_nis = list(NotableInvestment.get_all())
            for investor in investors:
                investor = json.loads(investor)

                industry_list = Industry.get_industry_list()
                cached_results = {}
                industries = []
                for i in investor.get("industries"):
                    if i not in cached_results:
                        result = SearchBuilder("industries").query(i).query_by(["embedding"]).search()

                        hit = result.get("hits", [])[0] if result.get("hits") else None

                        for industry in industry_list:
                            if hit and int(industry.id) == int(hit.get("document").get("db_id")):
                                industries.append(industry)
                                cached_results[i] = industry
                    else:
                        industries.append(cached_results[i])

                nis_to_add = []
                for ni_name_to_add in investor.get("notable_investments"):
                    existing_ni_name_list = map(lambda x: x.name, existing_nis)
                    if ni_name_to_add not in existing_ni_name_list:
                        ni = NotableInvestment(name=ni_name_to_add)
                        db.session.add(ni)
                        existing_nis.append(ni)
                    else:
                        ni = next(filter(lambda x: x.name == ni_name_to_add, existing_nis))

                    nis_to_add.append(ni)

                investor = Investor(
                    first_name=investor.get("first_name"),
                    last_name=investor.get("last_name"),
                    firm_name=investor.get("firm_name"),
                    position=investor.get("position"),
                    about=investor.get("about"),
                    email=investor.get("email"),
                    linkedin=investor.get("linkedin"),
                    twitter=investor.get("twitter"),
                    website=investor.get("website"),
                    location=investor.get("location"),
                    coordinates=investor.get("location"),
                    min_investment=int(investor.get("min_investment") or 0),
                    max_investment=int(investor.get("max_investment") or 0),
                    n_investments=int(investor.get("n_investments") or 0),
                    industries=list(set(industries)),
                    rounds=get_rounds(investor.get("rounds")),
                    notable_investments=nis_to_add,
                )
                db.session.add(investor)
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

    def calculate_bias_score(self):
        try:
            bias_score = (self.bias / 100) if self.bias else 0
        except (AttributeError, TypeError, ZeroDivisionError) as e:
            print(f"An error occurred while calculating the score: {e}")
            bias_score = 0
        return bias_score

    def calculate_location_score(self, company):
        try:
            if company.coordinates and self.coordinates:
                distance = float(geodesic(company.coordinates, self.coordinates).kilometers)
                location_score = 1 - (distance / 20038)
            else:
                location_score = 0
        except (AttributeError, TypeError, ZeroDivisionError) as e:
            print(f"An error occurred while calculating the score: {e}")
            location_score = 0
        return location_score

    def calculate_exits_score(self):
        try:
            if self.n_investments:
                successful_exits = 1 if (self.n_exits / self.n_investments) >= 0.5 else 0
            else:
                successful_exits = 0
        except (AttributeError, TypeError, ZeroDivisionError) as e:
            print(f"An error occurred while calculating the score: {e}")
            successful_exits = 0
        return successful_exits

    def calculate_industry_score(self, company):
        if company.industry in self.industries and len(self.industries) == 1:
            industry_score = 1
        elif company.industry in self.industries:
            industry_score = 0.8
        else:
            industry_score = 0
        return industry_score

    def calculate_round_score(self, company):
        if company.preferred_round in self.rounds and len(self.rounds) == 1:
            round_score = 1
        elif company.preferred_round in self.rounds:
            round_score = 0.8
        else:
            round_score = 0
        return round_score

    def calculate_completeness_score(self):
        attributes_dict = vars(self)
        completeness_score = 1
        for value in attributes_dict.values():
            if not value:
                completeness_score -= 0.1
        if completeness_score < 0:
            completeness_score = 0
        return completeness_score

    @staticmethod
    def generate_index_file():
        investors = Investor.get_all()

        with open("investor_index.jsonl", "w") as file:
            for investor in investors:
                investor_json = {}
                investor_json["db_id"] = investor.id
                investor_json["name"] = investor.full_name
                investor_json["firm_name"] = investor.firm_name
                investor_json["about"] = investor.about
                investor_json["position"] = investor.position
                investor_json["n_investments"] = investor.n_investments
                investor_json["n_exits"] = investor.n_exits
                investor_json["min_investment"] = investor.min_investment
                investor_json["max_investment"] = investor.max_investment
                investor_json["location"] = investor.location
                investor_json["country"] = investor._country
                investor_json["rounds"] = [round_.name for round_ in investor.rounds]
                investor_json["industries"] = [industry.name for industry in investor.industries]
                investor_json["notable_investments"] = [
                    notable_investment.name for notable_investment in investor.notable_investments
                ]

                file.write(json.dumps(investor_json) + "\n")

        return investors

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
            create_synonyms("investors")

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
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    investor_id: Mapped[int] = mapped_column(Integer, ForeignKey("investor.id"), nullable=False)

    user: Mapped[User] = relationship(
        User, backref=backref("investor_bookmarks", passive_deletes=True), lazy=True, init=False
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def get_by_user_id(user_id: int, offset: int = 1, limit: int = 10) -> Sequence[Investor]:
        return (
            db.session.scalars(
                db.select(Investor)
                .join(InvestorBookmark, InvestorBookmark.investor_id == Investor.id)
                .where(InvestorBookmark.user_id == user_id)
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
                .where(InvestorBookmark.user_id == user_id)
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
        geo_data = geocode_location(location)
        if geo_data is not None:
            self._coordinates = geo_data.get("coordinates")
            self._country = geo_data.get("country_name")

    @staticmethod
    def get_batches(batch_size: int = 100, stmt: Any = False) -> Generator[Sequence[InvestmentFirm], None, None]:
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

    @staticmethod
    def get_suggestions(company: Company | None, quantity: int) -> Sequence[InvestmentFirm] | None:
        investment_firm_list = []
        for investment_firm in InvestmentFirm.get_all():
            investment_firm_info = {
                "id": investment_firm.id,
                "bias": investment_firm.bias,
                "n_investments": investment_firm.n_investments,
                "n_exits": investment_firm.n_exits,
                "n_employees": investment_firm.n_employees,
                "coordinates": investment_firm.coordinates,
                "rounds": [round.name for round in investment_firm.rounds],
                "industries": [industry.name for industry in investment_firm.industries],
                "min_investment": investment_firm.min_investment,
                "max_investment": investment_firm.max_investment,
                "about": investment_firm.about,
            }
            investment_firm_list.append(investment_firm_info)
        investment_firm_ids = (
            SuggestionBuilder(investment_firm_list, company)
            .calculate_all_scores()
            .sort_by_score()
            .get_id_list(quantity)
        )
        suggestions = InvestmentFirm.get_by_id_list(investment_firm_ids)
        suggestions_dict = {suggestion.id: suggestion for suggestion in suggestions}  # type: ignore
        sorted_suggestions = [
            suggestions_dict[investment_firm_id]
            for investment_firm_id in investment_firm_ids
            if investment_firm_id in suggestions_dict
        ]
        return sorted_suggestions

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
    ):
        try:
            results = (
                SearchBuilder("investment_firms")
                .query(query_string)
                .query_by(query_by)
                .filter_by_investment_range(min_investment, max_investment)
                .filter_by("rounds", rounds, exclusivity=rounds_exclusive)
                .filter_by("industries", industries, exclusivity=industries_exclusive)
                .filter_by("countries", countries, exclusivity=False)
                .sort_by(sort_by, sort_desc)
                .page(page, per_page)
                .search()
            )

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
    def populate():
        try:
            investment_firms_list = []
            names = get_companies(50)
            abouts = get_abouts(50)
            websites = get_websites(50)
            emails = get_emails(50)
            phone_numbers = get_phone_numbers(50)
            locations = get_countrys(50)
            for i in range(1, 50):
                num_rounds = random.randint(1, 5)
                rounds = [Round.get_by_id(random.randint(1, 5)) for _ in range(num_rounds)]
                num_industries = random.randint(1, 6)
                industries = [Industry.get_by_id(random.randint(1, 92)) for _ in range(num_industries)]
                [
                    NotableInvestment.get_by_id(random.randint(1, len(NotableInvestment.get_all())))
                    for _ in range(random.randint(1, 10))
                ]
                n_investments = random.randint(100, 200)
                n_exits = random.randint(1, 100)
                n_employees = random.randint(1, 300)
                min_investment = random.randrange(100000, 50000001, 100000)
                max_investment = random.randrange(min_investment, 50000001, 100000)
                investment_firm = InvestmentFirm(
                    name=f"{names[i]}",
                    about=f"{abouts[i]}",
                    website=f"{websites[i]}",
                    linkedin=f"https://www.linkedin.com/company/{names[i]}",
                    twitter=f"https://twitter.com/{names[i]}",
                    email=f"{str(i) + emails[i]}",
                    phone_number=f"{phone_numbers[i]}",
                    n_investments=n_investments,
                    n_exits=n_exits,
                    n_employees=n_employees,
                    location=locations[i],
                    # coordinates=locations[i],
                    rounds=list(set(rounds)),
                    industries=list(set(industries)),
                    min_investment=min_investment,
                    max_investment=max_investment,
                    # notable_investments=list(set(notable_investments)),
                )
                investment_firm.set_slug()

                investment_firms_list.append(investment_firm)
            db.session.add_all(investment_firms_list)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return f"An error occurred: {e}"

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

    def calculate_bias_score(self):
        try:
            bias_score = (self.bias / 100) if self.bias else 0
        except (AttributeError, TypeError, ZeroDivisionError) as e:
            print(f"An error occurred while calculating the score: {e}")
            bias_score = 0
        return bias_score

    def calculate_location_score(self, company):
        try:
            if company.coordinates and self.coordinates:
                distance = float(geodesic(company.coordinates, self.coordinates).kilometers)
                location_score = 1 - (distance / 20038)
            else:
                location_score = 0
        except (AttributeError, TypeError, ZeroDivisionError) as e:
            print(f"An error occurred while calculating the score: {e}")
            location_score = 0
        return location_score

    def calculate_exits_score(self):
        try:
            if self.n_investments:
                successful_exits = 1 if (self.n_exits / self.n_investments) >= 0.5 else 0
            else:
                successful_exits = 0
        except (AttributeError, TypeError, ZeroDivisionError) as e:
            print(f"An error occurred while calculating the score: {e}")
            successful_exits = 0
        return successful_exits

    def calculate_industry_score(self, company):
        if company.industry in self.industries and len(self.industries) == 1:
            industry_score = 1
        elif company.industry in self.industries:
            industry_score = 0.8
        else:
            industry_score = 0
        return industry_score

    def calculate_round_score(self, company):
        if company.preferred_round in self.rounds and len(self.rounds) == 1:
            round_score = 1
        elif company.preferred_round in self.rounds:
            round_score = 0.8
        else:
            round_score = 0
        return round_score

    def calculate_completeness_score(self):
        attributes_dict = vars(self)
        completeness_score = 1
        for value in attributes_dict.values():
            if not value:
                completeness_score -= 0.1
        if completeness_score < 0:
            completeness_score = 0
        return completeness_score

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
            create_synonyms("investment_firms")

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
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    investment_firm_id: Mapped[int] = mapped_column(Integer, ForeignKey("investment_firm.id"), nullable=False)

    user: Mapped[User] = relationship(
        User, backref=backref("investment_firm_bookmarks", passive_deletes=True), lazy=True, init=False
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def get_by_user_id(user_id: int, offset: int = 1, limit: int = 10) -> Sequence[InvestmentFirmBookmark]:
        return (
            db.session.scalars(
                db.select(InvestmentFirm)
                .join(InvestmentFirmBookmark, InvestmentFirmBookmark.investment_firm_id == InvestmentFirm.id)
                .where(InvestmentFirmBookmark.user_id == user_id)
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
                .where(InvestmentFirmBookmark.user_id == user_id)
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
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=True)
    investor_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("investor.id"), nullable=False)

    user: Mapped[User | None] = relationship(User, backref=backref("investor_backup", uselist=False))
    investor: Mapped[Investor] = relationship(Investor, backref=backref("backup", uselist=False))
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
    investor_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("investor.id"), nullable=False)
    investor: Mapped[Investor] = relationship(Investor, backref=backref("origin_point", uselist=False))
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
