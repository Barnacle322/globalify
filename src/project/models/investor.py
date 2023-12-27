from __future__ import annotations

import random

from flask_sqlalchemy.pagination import Pagination
from sqlalchemy import Column, ForeignKey, Integer, String, and_, desc, event, or_
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db
from ..utils.fake_data import (
    get_abouts,
    get_companies,
    get_emails,
    get_job_positions,
    get_last_names,
    get_names,
    get_websites,
)
from .helpers import Industry, Round


class QueryBuilder:
    def __init__(self, base_query, cls):
        self.query = base_query
        self.cls = cls

    def apply_search_filters(self, query_string: str, filter_fields: list[str] | None, search_fields: tuple[str, ...]):
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
        if sort_field and hasattr(self.cls, sort_field):
            self.query = self.query.order_by(desc(sort_field)) if descending else self.query.order_by(sort_field)
        return self

    def filter_by_rounds(self, rounds: list[Round] | None, rounds_exclusive: bool):
        if rounds:
            round_filters = [self.cls.rounds.any(Round.id == round_obj.id) for round_obj in rounds]
            condition = and_(*round_filters) if rounds_exclusive else or_(*round_filters)
            self.query = self.query.filter(condition)
        return self

    def filter_by_industries(self, industries: list[Industry] | None, industries_exclusive: bool):
        if industries:
            industry_filters = [self.cls.industries.any(Industry.id == industry_obj.id) for industry_obj in industries]
            condition = and_(*industry_filters) if industries_exclusive else or_(*industry_filters)
            self.query = self.query.filter(condition)
        return self

    def filter_by_investment_range(self, min_investment: int | None, max_investment: int | None):
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

    rounds: Mapped[list[Round]] = relationship(secondary=investor_round)
    industries: Mapped[list[Industry]] = relationship(secondary=investor_industry)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<Investor {self.first_name} {self.last_name}>"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

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
        try:
            investor_list = []
            firstnames = get_names(50)
            lastnames = get_last_names(50)
            emails = get_emails(50)
            websites = get_websites(50)
            job_positions = get_job_positions(50)
            companies = get_companies(50)
            for i in range(1, 50):
                num_rounds = random.randint(1, 5)
                rounds = [Round.get_by_id(random.randint(1, 5)) for _ in range(num_rounds)]
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
                        email=f"{str(i) + emails[i]}",
                        rounds=list(set(rounds)),
                        industries=list(set(industries)),
                        min_investment=min_investment,
                        max_investment=max_investment,
                    )
                )
            db.session.add_all(investor_list)
            db.session.commit()
        except Exception:
            db.session.rollback()


class InvestmentFirm(db.Model):
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


@event.listens_for(Investor.__table__, "after_create")  # type: ignore
def populate_investor(*args, **kwargs):
    Investor.populate()


@event.listens_for(InvestmentFirm.__table__, "after_create")  # type: ignore
def populate_firms(*args, **kwargs):
    InvestmentFirm.populate()
