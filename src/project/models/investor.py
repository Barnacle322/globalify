from __future__ import annotations

import json
import random
from collections.abc import Sequence

from geopy.distance import geodesic
from sqlalchemy import BigInteger, Column, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, joinedload, mapped_column, relationship

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
    get_websites,
)
from ..utils.info_lists import notable_investment_list
from ..utils.scraper import populate_blockchain, populate_demo
from ..utils.suggestion import geocode_location
from ..utils.typesense_helpers.typesense_search import (
    SearchBuilder,
    create_schema,
    create_synonyms,
    delete_schema,
    upsert_documents,
)
from .helpers import Industry, Round


class ScoreBuilder:
    def __init__(self, cls: type[Investor], company: type[Company]):
        self.cls = cls
        self.company = company
        self.scores = {}

    def calculate_bias_score(self):
        try:
            bias_score = (self.cls.bias / 100) if self.cls.bias else 0
        except (AttributeError, TypeError, ZeroDivisionError) as e:
            print(f"An error occurred while calculating bias score: {e}")
            bias_score = 0
        self.scores["bias"] = bias_score
        return self

    def calculate_location_score(self):
        try:
            if self.company.coordinates and self.cls.coordinates:
                distance = float(geodesic(self.company.coordinates, self.cls.coordinates).kilometers)
                location_score = 1 - (distance / 20038)
            else:
                location_score = 0
        except (AttributeError, TypeError, ZeroDivisionError) as e:
            print(f"An error occurred while calculating location score: {e}")
            location_score = 0
        self.scores["location"] = location_score
        return self

    def calculate_exits_score(self):
        try:
            if self.cls.n_investments and self.cls.n_exits:
                successful_exits = 1 if (self.cls.n_exits / self.cls.n_investments) >= 0.5 else 0  # type: ignore
            else:
                successful_exits = 0
        except (AttributeError, TypeError, ZeroDivisionError) as e:
            print(f"An error occurred while calculating exits score: {e}")
            successful_exits = 0
        self.scores["exits"] = successful_exits
        return self

    def calculate_industry_score(self):
        try:
            if self.company.industry in self.cls.industries and len(self.cls.industries) == 1:  # type: ignore
                industry_score = 1
            elif self.company.industry in self.cls.industries:
                industry_score = 0.8
            else:
                industry_score = 0
        except (AttributeError, TypeError) as e:
            print(f"An error occurred while calculating industry score: {e}")
            industry_score = 0
        self.scores["industry"] = industry_score
        return self

    def calculate_round_score(self):
        try:
            if self.company.preferred_round in self.cls.rounds and len(self.cls.rounds) == 1:  # type: ignore
                round_score = 1
            elif self.company.preferred_round in self.cls.rounds:
                round_score = 0.8
            else:
                round_score = 0
        except (AttributeError, TypeError) as e:
            print(f"An error occurred while calculating round score: {e}")
            round_score = 0
        self.scores["round"] = round_score
        return self

    def calculate_completeness_score(self):
        try:
            attributes_dict = vars(self)
            completeness_score = 1
            for value in attributes_dict.values():
                if not value:
                    completeness_score -= 0.1
            if completeness_score < 0:
                completeness_score = 0
        except (AttributeError, TypeError) as e:
            print(f"An error occurred while calculating completeness score: {e}")
            completeness_score = 0
        self.scores["completeness"] = completeness_score
        return self

    def build_scores(self):
        return self.scores


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
    def coordinates(self, coordinates: str) -> None:
        geo_data = geocode_location(coordinates)
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
        return f"{self.min_investment:,} - {self.max_investment:,}"

    @staticmethod
    def get_all() -> Sequence[Investor]:
        return (
            db.session.scalars(
                db.select(Investor).options(joinedload(Investor.rounds), joinedload(Investor.industries))
            )
            .unique()
            .all()
        )

    @classmethod
    def get_search(
        cls,
        rounds: list[str],
        industries: list[str],
        query_string: str,
        query_by: list[str],
        sort_by: str | None = None,
        sort_desc: bool = False,
        rounds_exclusive: bool = False,
        industries_exclusive: bool = False,
        min_investment: int | None = None,
        max_investment: int | None = None,
        countries: list[str] | None = None,
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
            investor_list.append(
                {
                    "id": hit.get("document", {}).get("db_id", 0),
                    "name": hit.get("document", {}).get("name", ""),
                    "firm_name": hit.get("document", {}).get("firm_name", ""),
                    "about": hit.get("document", {}).get("about", ""),
                    "position": hit.get("document", {}).get("position", ""),
                    "n_investments": hit.get("document", {}).get("n_investments", 0),
                    "n_exits": hit.get("document", {}).get("n_exits", 0),
                    "min_investment": hit.get("document", {}).get("min_investment", 0),
                    "max_investment": hit.get("document", {}).get("max_investment", 0),
                    "location": hit.get("document", {}).get("location", ""),
                    "_country": hit.get("document", {}).get("country", ""),
                    "rounds": hit.get("document", {}).get("rounds", []),
                    "industries": hit.get("document", {}).get("industries", []),
                    "notable_investments": hit.get("document", {}).get("notable_investments", []),
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
        investors = Investor.get_all()
        data = []
        for investor in investors:
            investor_object = {}
            if investor.search_index:
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
                                "name",
                                "firm_name",
                                "about",
                                "position",
                                "location",
                                "rounds",
                                "industries",
                                "notable_investments",
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
            create_schema(investor_schema)
        result = upsert_documents("investors", data)
        create_synonyms("investors")

        objects = []
        for line in result.splitlines():
            if line:
                parsed_line = json.loads(line)
                objects.append((parsed_line.get("db_id"), parsed_line.get("id")))

        query = "UPDATE investor SET search_index = CASE id "
        for db_id, search_index in objects:
            query += f"WHEN {db_id} THEN '{search_index}' "
        query += "END WHERE id IN (" + ",".join(str(t[0]) for t in objects) + ")"

        db.session.execute(db.text(query))
        db.session.commit()


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
    _country: Mapped[str] = mapped_column(String, nullable=True)

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

    @staticmethod
    def populate():
        try:
            investment_firms_list = []
            names = get_companies(50)
            abouts = get_abouts(50)
            websites = get_websites(50)
            emails = get_emails(50)
            for i in range(1, 50):
                num_rounds = random.randint(1, 5)
                rounds = [Round.get_by_id(random.randint(1, 5)) for _ in range(num_rounds)]
                num_industries = random.randint(1, 6)
                industries = [Industry.get_by_id(random.randint(1, 92)) for _ in range(num_industries)]
                min_investment = random.randrange(100000, 50000001, 100000)
                max_investment = random.randrange(min_investment, 50000001, 100000)
                investment_firms_list.append(
                    InvestmentFirm(
                        name=f"{names[i]}",
                        about=f"{abouts[i]}",
                        website=f"{websites[i]}",
                        email=f"{str(i) + emails[i]}",
                        rounds=list(set(rounds)),
                        industries=list(set(industries)),
                        min_investment=min_investment,
                        max_investment=max_investment,
                    )
                )
            db.session.add_all(investment_firms_list)
            db.session.commit()
        except Exception:
            db.session.rollback()
