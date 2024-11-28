from pydantic import BaseModel


class RoundSchema(BaseModel):
    id: int
    name: str


class NotableInvestmentSchema(BaseModel):
    id: int
    name: str


class IndustrySchema(BaseModel):
    id: int
    name: str


class InvestorSchema(BaseModel):
    id: int
    name: str | None
    slug: str | None
    firm_name: str | None
    about: str | None
    position: str | None
    website: str | None = None
    linkedin: str | None = None
    twitter: str | None = None
    email: str | None = None
    phone_number: str | None = None
    n_investments: int | None
    n_exits: int | None
    min_max_investment: str | None
    location: str | None
    notable_investments: list[object] | None
    rounds: list[object] | None
    industries: list[object] | None
    user_id: int | None


class MiniInvestorSchema(BaseModel):
    id: int
    name: str | None


class InvestmentFirmSchema(BaseModel):
    id: int
    name: str | None
    slug: str | None
    about: str | None
    website: str | None
    linkedin: str | None
    twitter: str | None
    email: str | None
    phone_number: str | None
    n_investments: int | None
    n_exits: int | None
    n_employees: int | None
    min_max_investment: str | None
    location: str | None
    notable_investments: list[object] | None
    rounds: list[object] | None
    industries: list[object] | None


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
    n_exits: int | None
    min_investment: int | None
    max_investment: int | None
    location: str | None
    notable_investments: list[str] | None
    rounds: list[str] | None
    industries: list[str] | None
