from __future__ import annotations

import random

from flask_sqlalchemy.pagination import Pagination
from flask_sqlalchemy.query import Query
from geopy.distance import geodesic
from sqlalchemy import Column, ForeignKey, Integer, String, and_, desc, or_
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
from ..utils.suggestion import geocode_location, weights
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
    _coordinates: Mapped[str] = mapped_column(String, nullable=True)
    bias: Mapped[int] = mapped_column(Integer, nullable=True)

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
        self._coordinates = geocode_location(coordinates)  # type: ignore

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
        # company: Company | None = None,
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
    def populate() -> None:
        """
        Populate the database with dummy investor data.

        This method generates random data for 50 investors and adds them to the database.

        """
        try:
            investor_list = []
            firstnames = get_names(300)
            lastnames = get_last_names(300)
            emails = get_emails(300)
            websites = get_websites(300)
            job_positions = get_job_positions(300)
            companies = get_companies(300)
            location = get_countrys(300)
            for i in range(1, 300):
                num_rounds = random.randint(1, 5)
                rounds = [Round.get_by_id(random.randint(1, 5)) for _ in range(num_rounds)]
                num_industries = random.randint(1, 6)
                industries = [Industry.get_by_id(random.randint(1, 92)) for _ in range(num_industries)]
                min_investment = random.randrange(100000, 50000001, 100000)
                max_investment = random.randrange(min_investment, 50000001, 100000)
                n_investments = random.randint(100, 200)
                n_exits = random.randint(0, 100)
                bias = random.randint(0, 100)
                investor_list.append(
                    Investor(
                        first_name=f"{firstnames[i]}",
                        last_name=f"{lastnames[i]}",
                        about=f"{firstnames[i]} is a {job_positions[i]} at {companies[i]}. {get_abouts(1)[0]}",
                        firm_name=f"{companies[i]}",
                        position=f"{job_positions[i]}",
                        website=f"{websites[i]}",
                        email=f"{str(i) + emails[i]}",
                        rounds=list(set(rounds)),
                        industries=list(set(industries)),
                        min_investment=min_investment,
                        max_investment=max_investment,
                        location=location[i],
                        coordinates=location[i],
                        n_investments=n_investments,
                        n_exits=n_exits,
                        bias=bias,
                    )
                )
            db.session.add_all(investor_list)
            db.session.commit()
        except Exception:
            db.session.rollback()

    def calculate_score(self, company):
        try:
            bias_score = (self.bias / 100) if self.bias else 0

            if company.industry in self.industries:
                industry_score = 1 / len(self.industries)
            else:
                industry_score = 0

            if company.coordinates and self.coordinates:
                distance = float(geodesic(company.coordinates, self.coordinates).kilometers)
                location_score = 1 - (distance / 20000) if (distance / 20000) < 1 else 0
                # if distance < 1000:
                #     location_score = 1
                # elif distance < 5000:
                #     location_score = 0.75
                # elif distance < 10000:
                #     location_score = 0.5
                # elif distance < 15000:
                #     location_score = 0.25
                # else:
                #     location_score = 0
            else:
                location_score = 0

            if company.preferred_round in self.rounds:
                round_score = 1 / len(self.rounds)
            else:
                round_score = 0

            if self.n_investments > 0:
                successful_exits = 1 if (self.n_exits / self.n_investments) >= 0.5 else 0
            else:
                successful_exits = 0

            total_score = (
                weights["industry"] * industry_score
                + weights["round"] * round_score
                + weights["bias"] * bias_score
                + weights["location"] * location_score
                + weights["exits"] * successful_exits
            )

        except (AttributeError, TypeError, ZeroDivisionError) as e:
            print(f"An error occurred while calculating the score: {e}")
            total_score = 0

        return total_score


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
