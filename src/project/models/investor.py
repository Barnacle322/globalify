from __future__ import annotations

import csv
import random

from flask_sqlalchemy.pagination import Pagination
from flask_sqlalchemy.query import Query
from sqlalchemy import Column, ForeignKey, Integer, String, and_, desc, or_
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Mapped, mapped_column, relationship
from thefuzz import fuzz

from ..extensions import db
from ..utils.fake_data import (
    get_abouts,
    get_companies,
    get_emails,
    get_job_positions,
    get_last_names,
    get_locations,
    get_names,
    get_websites,
)
from .helpers import Industry, Round


class QueryBuilder:
    """
    A class that builds and applies filters to a base query.

    This class allows you to dynamically apply search filters, sorting, and various other filters to a base query.

    Attributes:
        query (Query): The current query being built.
        cls (type[Investor | InvestmentFirm]): The class type for which the query is built.

    """

    def __init__(self, base_query: Query, cls: type[Investor | InvestmentFirm]):
        self.query = base_query
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
            self.query = self.query.filter(or_(*filter_conditions))

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
            self.query = self.query.order_by(desc(sort_field)) if descending else self.query.order_by(sort_field)
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
            self.query = self.query.filter(condition)
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
            self.query = self.query.filter(condition)
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
        if min_investment and max_investment:
            investment_filters = and_(
                self.cls.min_investment >= min_investment, self.cls.max_investment <= max_investment
            )
            self.query = self.query.filter(investment_filters)
        elif min_investment:
            self.query = self.query.filter(self.cls.min_investment >= min_investment)
        elif max_investment:
            self.query = self.query.filter(self.cls.max_investment <= max_investment)
        return self

    def build(self):
        return self.query


class NotableInvestment(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<NotableInvestment {self.name}>"

    @staticmethod
    def get_all() -> list[NotableInvestment]:
        try:
            notable_investments: list[NotableInvestment] = NotableInvestment.query.all()
            return notable_investments
        except NoResultFound:
            return []

    @staticmethod
    def get_by_id(id: int) -> NotableInvestment | None:
        try:
            notable_investment = NotableInvestment.query.filter(NotableInvestment.id == id).first()
            return notable_investment
        except NoResultFound:
            return None

    @staticmethod
    def get_by_name(name: str) -> NotableInvestment | None:
        try:
            notable_investment = NotableInvestment.query.filter(NotableInvestment.name == name).first()
            return notable_investment
        except NoResultFound:
            return None

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
    email: Mapped[str] = mapped_column(String, nullable=True, unique=True)
    phone_number: Mapped[str] = mapped_column(String, nullable=True)
    n_investments: Mapped[int] = mapped_column(Integer, nullable=True)
    n_exits: Mapped[int] = mapped_column(Integer, nullable=True)
    min_investment: Mapped[int] = mapped_column(Integer, nullable=True)
    max_investment: Mapped[int] = mapped_column(Integer, nullable=True)
    location: Mapped[str] = mapped_column(String, nullable=True)

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
    def min_max_investment(self):
        if self.min_investment is None or self.max_investment is None:
            return None
        return f"{self.min_investment:,} - {self.max_investment:,}"

    @staticmethod
    def get_all() -> list[Investor]:
        try:
            investors: list[Investor] = Investor.query.all()
            return investors
        except NoResultFound:
            return []

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
        search_fields: tuple[str, ...] = ("first_name", "last_name", "firm_name", "position", "about"),
    ) -> Pagination | list[None]:
        """
        Get a paginated list of investors based on the provided filters.

        Args:
            page (int): The page number to retrieve (default: 1).
            per_page (int): The number of investors per page (default: 10).
            error_out (bool): Whether to raise an error if the requested page is out of range (default: False).
            search_string (str): The search string to filter investors by (default: "").
            filter_fields (list[str] | None): The fields to filter investors on (default: None).
            rounds (list[Round] | None): The rounds to filter investors by (default: None).
            rounds_exclusive (bool): Whether the rounds filter should be exclusive or inclusive (default: False).
            industries (list[Industry] | None): The industries to filter investors by (default: None).
            industries_exclusive (bool): Whether the industries filter should be exclusive or inclusive (default: False).
            min_investment (int | None): The minimum investment amount to filter investors by (default: None).
            max_investment (int | None): The maximum investment amount to filter investors by (default: None).
            sort_field (str | None): The field to sort the investors by (default: None).
            descending (bool): Whether to sort the investors in descending order (default: False).
            search_fields (tuple[str, ...]): The fields to search for the search string in (default: ("first_name", "last_name", "firm_name", "position", "about")).

        Returns:
            Pagination | list[None]: The paginated list of investors or an empty list if an exception occurs.

        """
        try:
            combined_query = (
                QueryBuilder(Investor.query, cls)
                .apply_search_filters(search_string, filter_fields, search_fields)
                .apply_sorting(sort_field, descending)
                .filter_by_rounds(rounds, rounds_exclusive)
                .filter_by_industries(industries, industries_exclusive)
                .filter_by_investment_range(min_investment, max_investment)
                .build()
            )
            investors = combined_query.paginate(page=page, per_page=per_page, error_out=error_out)
            if investors.pages < page:
                investors = combined_query.paginate(page=investors.pages, per_page=per_page, error_out=error_out)

            return investors
        except Exception:
            return []

    @staticmethod
    def get_by_id(id: int) -> Investor | None:
        try:
            investor = Investor.query.filter(Investor.id == id).one()
            return investor
        except NoResultFound:
            return None

    @staticmethod
    def get_by_email(email: str) -> Investor | None:
        try:
            investor = Investor.query.filter(Investor.email == email).first()
            return investor
        except NoResultFound:
            return None

    @staticmethod
    def populate():
        """
        Populate the database with dummy investor data.

        This method generates random data for 50 investors and adds them to the database.

        """
        # try:
        investor_list = []
        firstnames = get_names(50)
        lastnames = get_last_names(50)
        emails = get_emails(50)
        websites = get_websites(50)
        job_positions = get_job_positions(50)
        locations = get_locations(50)
        companies = get_companies(50)
        for i in range(1, 50):
            num_rounds = random.randint(1, 5)
            rounds = [Round.get_by_id(random.randint(1, 5)) for _ in range(num_rounds)]
            notable_investments = [
                NotableInvestment.get_by_id(random.randint(1, len(NotableInvestment.get_all())))
                for _ in range(random.randint(1, 10))
            ]
            num_industries = random.randint(1, 6)
            industries = [Industry.get_by_id(random.randint(1, 92)) for _ in range(num_industries)]
            min_investment = random.randrange(100000, 50000001, 100000)
            max_investment = random.randrange(min_investment, 50000001, 100000)
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
                    n_investments=random.randint(1, 100),
                    n_exits=random.randint(1, 100),
                    location=f"{locations[i]}",
                    rounds=list(set(rounds)),
                    industries=list(set(industries)),
                    min_investment=min_investment,
                    max_investment=max_investment,
                    notable_investments=list(set(notable_investments)),
                )
            )
        db.session.add_all(investor_list)
        db.session.commit()
        # except Exception:
        #     db.session.rollback()

    @staticmethod
    def populate_demo(file_name="investor.csv"):
        with open(file_name, newline="") as file:
            reader = csv.reader(file, delimiter=";")
            for row in reader:
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
                    # print(min_investment, max_investment)

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
                        db.session.commit()
                        notable_investment_list.append(ni)

                investor = Investor(
                    first_name=row[0].split(" ")[0],
                    last_name=row[0].split(" ")[1],
                    firm_name=row[1],
                    position=row[2],
                    email=row[3],
                    location=row[4],
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

    rounds: Mapped[list[Round]] = relationship(secondary=investment_firm_round)
    industries: Mapped[list[Industry]] = relationship(secondary=investment_firm_industry)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<InvestmentFirm {self.name}>"

    @staticmethod
    def get_all() -> list[InvestmentFirm]:
        try:
            firms: list[InvestmentFirm] = InvestmentFirm.query.all()
            return firms
        except NoResultFound:
            return []

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
                QueryBuilder(InvestmentFirm.query, cls)
                .apply_search_filters(search_string, filter_fields, search_fields)
                .apply_sorting(sort_field, descending)
                .filter_by_rounds(rounds, rounds_exclusive)
                .filter_by_industries(industries, industries_exclusive)
                .filter_by_investment_range(min_investment, max_investment)
                .build()
            )
            investment_firms = combined_query.paginate(page=page, per_page=per_page, error_out=error_out)
            if investment_firms.pages < page:
                investment_firms = combined_query.paginate(
                    page=investment_firms.pages, per_page=per_page, error_out=error_out
                )

            return investment_firms
        except Exception:
            return []

    @staticmethod
    def get_by_id(id: int) -> InvestmentFirm | None:
        try:
            firm = InvestmentFirm.query.filter(InvestmentFirm.id == id).one()
            return firm
        except NoResultFound:
            return None

    @staticmethod
    def get_by_email(email: str) -> InvestmentFirm | None:
        try:
            firm = InvestmentFirm.query.filter(InvestmentFirm.email == email).first()
            return firm
        except NoResultFound:
            return None

    @staticmethod
    def populate():
        """Populate the database with dummy investment firm data.

        This method generates random data for 50 investment firms and adds them to the database.

        """
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


# @event.listens_for(Investor.__table__, "after_create")  # type: ignore
# def populate_investor(*args, **kwargs):
#     """
#     Event listener function that populates the investor table with random data after it is created.

#     Args:
#         *args: Variable length argument list.
#         **kwargs: Arbitrary keyword arguments.

#     """
#     Investor.populate()


# @event.listens_for(InvestmentFirm.__table__, "after_create")  # type: ignore
# def populate_firms(*args, **kwargs):
#     """
#     Event listener function that populates the investment firms table with random data after it is created.

#     Args:
#         *args: Variable length argument list.
#         **kwargs: Arbitrary keyword arguments.

#     """
#     InvestmentFirm.populate()
