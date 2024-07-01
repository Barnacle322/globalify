from pydantic import BaseModel


class InvestorBookmarkSchema(BaseModel):
    id: int
    name: str
    position: str | None
    firm_name: str | None
    about: str | None
    twitter: str | None
    slug: str


class InvestmentFirmBookmarkSchema(BaseModel):
    id: int
    name: str
    about: str | None
    slug: str


class NotableInvestmentSchema(BaseModel):
    title: str


class RoundSchema(BaseModel):
    title: str


class IndustrySchema(BaseModel):
    title: str


class InvestorOriginPointSchema(BaseModel):
    first_name: str
    last_name: str | None
    slug: str | None
    firm_name: str | None
    about: str | None
    position: str | None
    website: str | None
    linkedin: str | None
    twitter: str | None
    email: str | None
    phone_number: str | None
    n_investments: int | None
    n_exits: int
    min_investment: int | None
    max_investment: int | None
    location: str | None
    notable_investments: list[NotableInvestmentSchema]
    rounds: list[RoundSchema]
    industries: list[IndustrySchema]
