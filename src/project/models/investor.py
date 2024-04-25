from __future__ import annotations

import csv
import json
import random
from ast import literal_eval
from collections.abc import Generator, Sequence
from itertools import islice

from geopy.distance import geodesic
from more_itertools import chunked
from sqlalchemy import BigInteger, Column, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, joinedload, mapped_column, relationship
from thefuzz import fuzz

from ..extensions import db
from ..models.user import Company
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
    get_industries,
    get_min_max_investment,
    get_notable_investments,
    get_rounds,
)
from ..utils.suggestion import WEIGHTS, geocode_location
from ..utils.typesense_helpers.typesense_search import (
    SearchBuilder,
    create_schema,
    create_synonyms,
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
                if self.company.coordinates and investor["coordinates"]:  # type: ignore
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
    """
    Represents a notable investment of an investor or investment firm.

    Attributes:
        id (int): The unique identifier for the notable investment (primary key).
        name (str): The name of the notable investment (not nullable).
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<NotableInvestment {self.name}>"

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
    def populate() -> None:
        """
        Populates the notable investments.

        This method adds a list of predefined notable investment names to the database session
        and commits the changes.

        Raises:
            Exception: If an exception occurs during the population process, the changes are rolled back.

        """
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


class Investor(db.Model):
    """
    Class representing an investor in the database.

    Attributes:
        id (int): The unique identifier for the investor (primary key).
        first_name (str): The first name of the investor (not nullable).
        last_name (str): The last name of the investor.
        firm_name (str): The name of the investor's firm.
        about (str): A brief description or information about the investor.
        position (str): The position or role of the investor.
        website (str): The website URL of the investor.
        linkedin (str): The LinkedIn profile of the investor.
        twitter (str): The Twitter handle of the investor.
        email (str): The email address of the investor (unique).
        phone_number (str): The phone number of the investor.
        n_investments (int): The number of investments made by the investor.
        n_exits (int): The number of exits achieved by the investor.
        min_investment (int): The minimum investment amount accepted by the investor.
        max_investment (int): The maximum investment amount accepted by the investor.
        location (str): The location or address of the investor.
        rounds (List[Round]): List of Round objects associated with the investor.
        industries (List[Industry]): List of Industry objects associated with the investor.
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[str] = mapped_column(String, nullable=True)
    firm_name: Mapped[str] = mapped_column(String, nullable=True)
    about: Mapped[str] = mapped_column(String, nullable=True)
    position: Mapped[str] = mapped_column(String, nullable=True)
    website: Mapped[str] = mapped_column(String, nullable=True)
    linkedin: Mapped[str] = mapped_column(String, nullable=True)
    twitter: Mapped[str] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String, nullable=True, unique=False)
    phone_number: Mapped[str] = mapped_column(String, nullable=True)
    n_investments: Mapped[int] = mapped_column(Integer, nullable=True)
    n_exits: Mapped[int] = mapped_column(Integer, nullable=True)
    min_investment: Mapped[int] = mapped_column(BigInteger, nullable=True)
    max_investment: Mapped[int] = mapped_column(BigInteger, nullable=True)
    location: Mapped[str] = mapped_column(String, nullable=True)
    _coordinates: Mapped[str] = mapped_column(String, nullable=True)
    _country: Mapped[str] = mapped_column(String, nullable=True)
    bias: Mapped[int] = mapped_column(Integer, nullable=True)
    search_index: Mapped[str] = mapped_column(String, nullable=True)

    notable_investments: Mapped[list[NotableInvestment]] = relationship(secondary=investor_notable_investment)
    rounds: Mapped[list[Round]] = relationship(secondary=investor_round)
    industries: Mapped[list[Industry]] = relationship(secondary=investor_industry)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<Investor {self.first_name} {self.last_name}>"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

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
        if self.min_investment is None or self.max_investment is None:
            return None
        return f"${self.min_investment:,} - ${self.max_investment:,}"

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
    def get_batches(batch_size: int = 100) -> Generator[Sequence[Investor], None, None]:
        ids_query = db.session.execute(db.select(Investor.id)).scalars().all()

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
                .filter_by_rounds(rounds, rounds_exclusive)
                .filter_by_industries(industries, industries_exclusive)
                .filter_by_countries(countries)
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
            investor_list.append(
                Investor(
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
            )
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
    def populate_demo(file_name="investor.csv"):
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
                db.session.add(investor)
                print("Added investor:", investor)
        db.session.commit()

    @staticmethod
    def populate_cli():
        notable_investment_list = NotableInvestment.get_all()
        industry_list = Industry.get_industry_list()
        with open("investor_list.json", encoding="utf-8-sig") as file:
            investors = json.load(file)
            for investor in investors:
                industries = get_industries(investor.get("industry"), industry_list)
                min_investment, max_investment = get_min_max_investment(investor.get("investment_range"))
                rounds = get_rounds(investor.get("rounds"))
                notable_investments = get_notable_investments(
                    investor.get("notable_investments"), notable_investment_list, NotableInvestment
                )
                investor = Investor(
                    first_name=investor.get("first_name"),
                    last_name=investor.get("last_name"),
                    firm_name=investor.get("firm_name"),
                    position=investor.get("position"),
                    about=investor.get("about"),
                    email=investor.get("email"),
                    linkedin=investor.get("linkedin"),
                    twitter=investor.get("twitter"),
                    location=investor.get("location"),
                    coordinates=investor.get("location"),
                    min_investment=min_investment,
                    max_investment=max_investment,
                    industries=industries,
                    rounds=rounds,
                    notable_investments=notable_investments,
                )
                db.session.add(investor)
            db.session.commit()

    @staticmethod
    def populate_vcsheet(file_name="investors_vc.csv"):
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
                investor_object["name"] = investor.full_name
                investor_object["firm_name"] = investor.firm_name
                investor_object["about"] = investor.about
                investor_object["position"] = investor.position
                investor_object["n_investments"] = investor.n_investments
                investor_object["n_exits"] = investor.n_exits
                investor_object["min_investment"] = investor.min_investment
                investor_object["max_investment"] = investor.max_investment
                investor_object["location"] = investor.location
                investor_object["country"] = investor._country
                investor_object["rounds"] = [round_.name for round_ in investor.rounds]
                investor_object["industries"] = [industry.name for industry in investor.industries]
                investor_object["notable_investments"] = [
                    notable_investment.name for notable_investment in investor.notable_investments
                ]
                data.append(investor_object)

            print("Upserting documents")
            result = upsert_documents("investors", data)

            objects = []
            for index, obj in enumerate(result):
                if obj.get("id"):
                    objects.append((investors[index].id, obj.get("id", 0)))
                else:
                    continue

            query = "UPDATE investor SET search_index = CASE id "
            for db_id, search_index in objects:
                query += f"WHEN {db_id} THEN '{search_index}' "
            query += "END WHERE id IN (" + ",".join(str(t[0]) for t in objects) + ")"

            db.session.execute(db.text(query))
            db.session.commit()
            batch_count += 1


class InvestmentFirm(db.Model):
    """
    Represents an investment firm.

    Attributes:
        id (int): The ID of the investment firm.
        name (str): The name of the investment firm.
        about (str): A description of the investment firm.
        website (str): The website of the investment firm.
        email (str): The email of the investment firm.
        phone_number (str): The phone number of the investment firm.
        n_investments (int): The number of investments made by the investment firm.
        n_exits (int): The number of exits made by the investment firm.
        n_employees (int): The number of employees in the investment firm.
        min_investment (int): The minimum investment amount for the investment firm.
        max_investment (int): The maximum investment amount for the investment firm.
        rounds (list[Round]): The rounds associated with the investment firm.
        industries (list[Industry]): The industries associated with the investment firm.
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=True)
    about: Mapped[str] = mapped_column(String, nullable=True)
    website: Mapped[str] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String, nullable=True, unique=True)
    phone_number: Mapped[str] = mapped_column(String, nullable=True)
    n_investments: Mapped[int] = mapped_column(Integer, nullable=True)
    n_exits: Mapped[int] = mapped_column(Integer, nullable=True)
    n_employees: Mapped[int] = mapped_column(Integer, nullable=True)
    min_investment: Mapped[int] = mapped_column(Integer, nullable=True)
    max_investment: Mapped[int] = mapped_column(Integer, nullable=True)
    location: Mapped[str] = mapped_column(String, nullable=True)
    _coordinates: Mapped[str] = mapped_column(String, nullable=True)
    _country: Mapped[str] = mapped_column(String, nullable=True)
    bias: Mapped[int] = mapped_column(Integer, nullable=True)
    search_index: Mapped[str] = mapped_column(String, nullable=True)

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
    def get_by_id(id: int) -> InvestmentFirm | None:
        return db.session.scalar(db.select(InvestmentFirm).where(InvestmentFirm.id == id))

    @staticmethod
    def get_by_email(email: str) -> InvestmentFirm | None:
        return db.session.scalar(db.select(InvestmentFirm).where(InvestmentFirm.email == email))

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
            self._coordinates = geo_data["coordinates"]  # type: ignore
            self._country = geo_data["country_name"]  # type: ignore

    @staticmethod
    def get_batches(batch_size: int = 100) -> Generator[Sequence[InvestmentFirm], None, None]:
        ids_query = db.session.execute(db.select(InvestmentFirm.id)).scalars().all()

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
                .filter_by_rounds(rounds, rounds_exclusive)
                .filter_by_industries(industries, industries_exclusive)
                .filter_by_countries(countries)
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
                investment_firms_list.append(
                    InvestmentFirm(
                        name=f"{names[i]}",
                        about=f"{abouts[i]}",
                        website=f"{websites[i]}",
                        email=f"{str(i) + emails[i]}",
                        phone_number=f"{phone_numbers[i]}",
                        n_investments=n_investments,
                        n_exits=n_exits,
                        n_employees=n_employees,
                        location=locations[i],
                        coordinates=locations[i],
                        rounds=list(set(rounds)),
                        industries=list(set(industries)),
                        min_investment=min_investment,
                        max_investment=max_investment,
                        # notable_investments=list(set(notable_investments)),
                    )
                )
            db.session.add_all(investment_firms_list)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return f"An error occurred: {e}"

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
