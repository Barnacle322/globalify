from __future__ import annotations

import csv
import datetime
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
from .entity import NotableInvestment
from .helpers import Industry, Round

if TYPE_CHECKING:
    from .claim import ClaimRequest, ClaimVerification
    from .user import User


# NotableInvestment has been relocated to entity.py (Phase 2d Task 1).
# It is imported above and re-exported here for backward compatibility.
__all__ = ["NotableInvestment"]


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
