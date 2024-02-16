from __future__ import annotations

import csv
import json
import random
from collections.abc import Sequence
from itertools import islice

from flask_sqlalchemy.pagination import Pagination
from geopy.distance import geodesic
from sqlalchemy import BigInteger, Column, ForeignKey, Integer, String, and_, desc, or_
from sqlalchemy.orm import Mapped, joinedload, mapped_column, relationship
from sqlalchemy.sql import Select
from thefuzz import fuzz

from ..extensions import db
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
from ..utils.suggestion import geocode_location
from ..utils.typesense_search import SearchBuilder, client, create_schema, delete_schema, upsert_documents
from .helpers import Industry, Round


class QueryBuilder:
    """
    A class that builds and applies filters to a base query.

    This class allows you to dynamically apply search filters, sorting, and various other filters to a base query.

    Attributes:
        base_query (Select): The base query being built.
        cls (type[Investor | InvestmentFirm]): The class type for which the query is built.

    """

    def __init__(self, base_query: Select, cls: type[Investor | InvestmentFirm]):
        self.base_query = base_query
        self.cls = cls

    def apply_search_filters(self, query_string: str, filter_fields: list[str] | None, search_fields: tuple[str, ...]):
        """
        Applies search filters to the query based on the provided parameters.

        Args:
            query_string (str): The search query string.
            filter_fields (list[str] | None): The fields to apply the search filters on.
            search_fields (tuple[str, ...]): The fields to search within.

        Returns:
            QueryBuilder: The QueryBuilder instance with the applied search filters.

        """
        if not query_string:
            return self

        filter_conditions = [
            getattr(self.cls, field).ilike(f"%{query_string}%")
            for field in (filter_fields or search_fields)
            if hasattr(self.cls, field)
        ]

        if filter_conditions:
            self.base_query = self.base_query.where(or_(*filter_conditions))

        return self

    def apply_sorting(self, sort_field: str | None, descending: bool):
        """
        Applies sorting to the query based on the provided parameters.

        Args:
            sort_field (str | None): The field to sort by.
            descending (bool): True if sorting should be done in descending order, False otherwise.

        Returns:
            QueryBuilder: The QueryBuilder instance with the applied sorting.

        """
        if sort_field and hasattr(self.cls, sort_field):
            alias = self.cls
            column = getattr(alias, sort_field)
            self.base_query = self.base_query.order_by(desc(column)) if descending else self.base_query.order_by(column)

        return self

    def filter_by_rounds(self, rounds: list[Round] | None, rounds_exclusive: bool):
        """
        Filters the query based on a list of rounds.

        Args:
            rounds (list[Round] | None): The list of rounds to filter by.
            rounds_exclusive (bool): True if the filter should be exclusive, False otherwise.

        Returns:
            QueryBuilder: The QueryBuilder instance with the applied round filters.

        """
        if rounds:
            round_filters = [self.cls.rounds.any(Round.id == round_obj.id) for round_obj in rounds]
            condition = and_(*round_filters) if rounds_exclusive else or_(*round_filters)
            self.base_query = self.base_query.where(condition)
        return self

    def filter_by_industries(self, industries: list[Industry] | None, industries_exclusive: bool):
        """
        Filters the query based on a list of industries.

        Args:
            industries (list[Industry] | None): The list of industries to filter by.
            industries_exclusive (bool): True if the filter should be exclusive, False otherwise.

        Returns:
            QueryBuilder: The QueryBuilder instance with the applied industry filters.

        """
        if industries:
            industry_filters = [self.cls.industries.any(Industry.id == industry_obj.id) for industry_obj in industries]
            condition = and_(*industry_filters) if industries_exclusive else or_(*industry_filters)
            self.base_query = self.base_query.where(condition)
        return self

    def filter_by_investment_range(self, min_investment: int | None, max_investment: int | None):
        """
        Filters the query based on the investment range.

        Args:
            min_investment (int | None): The minimum investment amount.
            max_investment (int | None): The maximum investment amount.

        Returns:
            QueryBuilder: The QueryBuilder instance with the applied investment range filter.

        """
        if min_investment is not None and max_investment is not None:
            investment_filters = and_(
                self.cls.min_investment >= min_investment, self.cls.max_investment <= max_investment
            )
            self.base_query = self.base_query.where(investment_filters)
        elif min_investment is not None:
            self.base_query = self.base_query.where(self.cls.min_investment >= min_investment)
        elif max_investment is not None:
            self.base_query = self.base_query.where(self.cls.max_investment <= max_investment)
        return self

    def filter_by_countries(self, countries: list[str] | None):
        if countries:
            location_filters = [self.cls._country.ilike(country_obj.name) for country_obj in countries]  # type: ignore
            condition = or_(*location_filters)
            self.base_query = self.base_query.where(condition)
        return self

    def build(self):
        return self.base_query


class NotableInvestment(db.Model):
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
            notable_investment_list = list(
                set(
                    [
                        "Uber",
                        "Airbnb",
                        "Robinhood",
                        "Stripe",
                        "Coinbase",
                        "DoorDash",
                        "Twitch",
                        "Reddit",
                        "TikTok",
                        "Snapchat",
                        "Spotify",
                        "Lyft",
                        "Zoom",
                        "Pinterest",
                        "Dropbox",
                        "Slack",
                        "Tinder",
                        "Instagram",
                        "Facebook",
                        "Twitter",
                        "LinkedIn",
                        "YouTube",
                        "Google",
                        "PayPal",
                        "Tesla",
                        "SpaceX",
                        "Amazon",
                        "Netflix",
                        "Apple",
                        "Microsoft",
                        "Intel",
                        "Cisco",
                        "Oracle",
                        "IBM",
                        "HP",
                        "Dell",
                        "eBay",
                        "Yahoo",
                        "AOL",
                        "Compaq",
                        "Netscape",
                        "Sun Microsystems",
                        "3Com",
                        "Adobe",
                        "AMD",
                        "Xerox",
                        "Sony",
                        "Nintendo",
                        "Sega",
                        "Panasonic",
                        "Samsung",
                        "LG",
                        "Nokia",
                        "Motorola",
                        "Siemens",
                        "Philips",
                        "Vodafone",
                        "Ericsson",
                        "Alcatel",
                        "Sanyo",
                        "Sharp",
                        "NEC",
                        "Palm",
                        "BlackBerry",
                        "HTC",
                        "Qualcomm",
                        "Verizon",
                        "AT&T",
                        "Vodafone",
                        "T-Mobile",
                        "Sprint",
                        "Orange",
                        "Bell",
                        "Telus",
                        "Rogers",
                        "Comcast",
                        "Time Warner",
                        "Cox",
                        "Charter",
                        "CenturyLink",
                        "Viacom",
                        "CBS",
                        "Disney",
                        "News Corp",
                        "Vivendi",
                        "Bertelsmann",
                        "Time Warner",
                        "Sony",
                        "Liberty Media",
                        "Vodafone",
                        "Televisa",
                        "BCE",
                        "Dish",
                        "DirecTV",
                        "Sky",
                        "Telecom Italia",
                        "Telefónica",
                        "NTT",
                        "KDDI",
                        "Softbank",
                        "SK Telecom",
                        "KT",
                        "LG Uplus",
                        "China Mobile",
                        "China Unicom",
                        "China Telecom",
                        "VimpelCom",
                        "MTS",
                        "Megafon",
                        "Telecom Argentina",
                        "Telecom Egypt",
                        "Etisalat",
                        "Ooredoo",
                        "STC",
                        "MTN",
                        "TeliaSonera",
                        "Telenor",
                        "Telstra",
                        "SingTel",
                        "Telkom Indonesia",
                        "Axiata",
                        "Turkcell",
                        "Mobily",
                        "Mobinil",
                        "Zain",
                        "Omantel",
                        "Qtel",
                        "Batelco",
                        "Vivacom",
                        "TDC",
                        "Telenor",
                        "Tele2",
                        "DNA",
                        "Elisa",
                    ]
                )
            )
            db.session.add_all(list(map(lambda x: NotableInvestment(name=x), notable_investment_list)))
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
            # self._coordinates = geo_data["coordinates"]  # type: ignore
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
            search_params = (
                SearchBuilder()
                .query(query_string)
                .query_by(query_by)
                .filter_by_investment_range(min_investment, max_investment)
                .filter_by_rounds(rounds, rounds_exclusive)
                .filter_by_industries(industries, industries_exclusive)
                .filter_by_countries(countries)
                .sort_by(sort_by, sort_desc)
                .page(page, per_page)
                .build()
            )

            results = client.collections["investors"].documents.search(search_params)
        except Exception:
            results = {"found": 0, "page": 1, "per_page": 12, "hits": []}
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

    # @classmethod
    # def get_pagination(
    #     cls,
    #     page: int = 1,
    #     per_page: int = 10,
    #     error_out: bool = False,
    #     search_string: str = "",
    #     filter_fields: list[str] | None = None,
    #     rounds: list[Round] | None = None,
    #     rounds_exclusive: bool = False,
    #     industries: list[Industry] | None = None,
    #     industries_exclusive: bool = False,
    #     countries: list[str] | None = None,
    #     min_investment: int | None = None,
    #     max_investment: int | None = None,
    #     sort_field: str | None = None,
    #     descending: bool = False,
    #     search_fields: tuple[str, ...] = ("first_name", "last_name", "firm_name", "position", "about"),
    #     # company: Company | None = None,
    # ) -> Pagination | list[None]:
    #     """
    #     Get a paginated list of investors based on the provided filters.

    #     Args:
    #         page (int): The page number to retrieve (default: 1).
    #         per_page (int): The number of investors per page (default: 12).
    #         error_out (bool): Whether to raise an error if the requested page is out of range (default: False).
    #         search_string (str): The search string to filter investors by (default: "").
    #         filter_fields (list[str] | None): The fields to filter investors on (default: None).
    #         rounds (list[Round] | None): The rounds to filter investors by (default: None).
    #         rounds_exclusive (bool): Whether the rounds filter should be exclusive or inclusive (default: False).
    #         industries (list[Industry] | None): The industries to filter investors by (default: None).
    #         industries_exclusive (bool): Whether the industries filter should be exclusive or inclusive (default: False).
    #         min_investment (int | None): The minimum investment amount to filter investors by (default: None).
    #         max_investment (int | None): The maximum investment amount to filter investors by (default: None).
    #         sort_field (str | None): The field to sort the investors by (default: None).
    #         descending (bool): Whether to sort the investors in descending order (default: False).
    #         search_fields (tuple[str, ...]): The fields to search for the search string in (default: ("first_name", "last_name", "firm_name", "position", "about")).

    #     Returns:
    #         Pagination | list[None]: The paginated list of investors or an empty list if an exception occurs.

    #     """
    #     try:
    #         combined_query = (
    #             QueryBuilder(
    #                 db.select(Investor).options(joinedload(Investor.rounds), joinedload(Investor.industries)),
    #                 cls,
    #             )
    #             .apply_search_filters(search_string, filter_fields, search_fields)
    #             .apply_sorting(sort_field, descending)
    #             .filter_by_rounds(rounds, rounds_exclusive)
    #             .filter_by_industries(industries, industries_exclusive)
    #             .filter_by_investment_range(min_investment, max_investment)
    #             .filter_by_countries(countries)
    #             .build()
    #         )
    #         investors = db.paginate(combined_query, page=page, per_page=per_page, error_out=error_out)
    #         if investors.pages < page:
    #             investors = db.paginate(combined_query, page=investors.pages, per_page=per_page, error_out=error_out)
    #         return investors
    #     except Exception:
    #         return []

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
    def populate_demo(file_name="investor.csv"):
        with open(file_name, newline="") as file:
            reader = csv.reader(file, delimiter=";")
            for row in islice(reader, 84, None):
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
                    for i in Industry.get_industry_list():
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
                    existing = NotableInvestment.get_by_name(notable_investment)
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
    def populate_blockchain(file_name="globalify - blockchain.csv"):
        with open(file_name, newline="") as file:
            reader = csv.reader(file, delimiter=";")
            existing_notable_investments = NotableInvestment.get_all()
            existing_industry_list = Industry.get_industry_list()
            for row in islice(reader, 1, None):
                first_name = row[0].split(" ")[0]
                if len(row[0].split(" ")) == 1:
                    last_name = None
                else:
                    last_name = row[0].split(" ")[1]
                firm_name = row[1]
                firm_name = firm_name.replace('"', "")

                email = row[4]
                if email == "":
                    email = None

                industries = row[7].split(",")
                industry_list = []
                for industry in industries:
                    if "—" in industry:
                        industry = industry.split(" — ")[1]
                    industry = (
                        industry.replace(")", "")
                        .replace("(", "")
                        .replace(" Commerce", " ")
                        .replace("Smart Tech", " ")
                        .replace("Money Tech", "")
                        .replace("Health Tech", "")
                        .strip()
                    )
                    for i in existing_industry_list:
                        if i and fuzz.ratio(industry, i.name) > 80:
                            industry = i
                            industry_list.append(industry)
                            break

                round_list = []
                for round_ in row[14].split(","):
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
                for notable_investment in row[15].split(","):
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

                check_size_string = row[13]
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
                elif len(range_set) == 1:
                    min_investment = range_set.pop()
                investor = Investor(
                    first_name=first_name,
                    last_name=last_name,
                    firm_name=row[1],
                    position=row[2],
                    about=row[22],
                    email=email,
                    location=row[6],
                    coordinates=row[6],
                    industries=list(set(industry_list)),
                    linkedin=row[9],
                    twitter=row[11],
                    min_investment=min_investment,
                    max_investment=max_investment,
                    rounds=list(set(round_list)),
                    notable_investments=list(set(notable_investment_list)),
                )
                db.session.add(investor)
                print("Added investor:", investor)
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

    @classmethod
    def get_pagination(
        cls,
        page: int = 1,
        per_page: int = 10,
        error_out: bool = False,
        search_string: str = "",
        filter_fields: list[str] | None = None,
        rounds: list[Round] | None = None,
        rounds_exclusive: bool = False,
        industries: list[Industry] | None = None,
        industries_exclusive: bool = False,
        min_investment: int | None = None,
        max_investment: int | None = None,
        sort_field: str | None = None,
        descending: bool = False,
        search_fields: tuple[str, ...] = ("name", "about"),
    ) -> Pagination | list[None]:
        """Get a paginated list of investment firms based on various filters.

        Args:
            page (int, optional): The page number to retrieve. Defaults to 1.
            per_page (int, optional): The number of items per page. Defaults to 10.
            error_out (bool, optional): Whether to raise an error if the page is out of range. Defaults to False.
            search_string (str, optional): The search string to filter investment firms. Defaults to an empty string.
            filter_fields (list[str] | None, optional): The fields to filter on. Defaults to None.
            rounds (list[Round] | None, optional): The rounds to filter on. Defaults to None.
            rounds_exclusive (bool, optional): Whether to exclude the specified rounds. Defaults to False.
            industries (list[Industry] | None, optional): The industries to filter on. Defaults to None.
            industries_exclusive (bool, optional): Whether to exclude the specified industries. Defaults to False.
            min_investment (int | None, optional): The minimum investment amount to filter on. Defaults to None.
            max_investment (int | None, optional): The maximum investment amount to filter on. Defaults to None.
            sort_field (str | None, optional): The field to sort the results by. Defaults to None.
            descending (bool, optional): Whether to sort the results in descending order. Defaults to False.
            search_fields (tuple[str, ...], optional): The fields to search for the search string. Defaults to ("name", "about").

        Returns:
            Pagination | list[None]: A paginated list of investment firms.

        """
        try:
            combined_query = (
                QueryBuilder(
                    db.select(InvestmentFirm).options(
                        joinedload(InvestmentFirm.rounds), joinedload(InvestmentFirm.industries)
                    ),
                    cls,
                )
                .apply_search_filters(search_string, filter_fields, search_fields)
                .apply_sorting(sort_field, descending)
                .filter_by_rounds(rounds, rounds_exclusive)
                .filter_by_industries(industries, industries_exclusive)
                .filter_by_investment_range(min_investment, max_investment)
                .build()
            )
            investment_firms = db.paginate(combined_query, page=page, per_page=per_page, error_out=error_out)
            if investment_firms.pages < page:
                investment_firms = db.paginate(
                    combined_query, page=investment_firms.pages, per_page=per_page, error_out=error_out
                )

            return investment_firms
        except Exception:
            return []

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
