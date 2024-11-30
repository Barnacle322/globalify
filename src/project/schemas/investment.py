from datetime import date

from pydantic import BaseModel


class FundingRoundSchema(BaseModel):
    id: int
    company_name: str
    round: object | None
    announced_date: date | None


class InvestmentSchema(BaseModel):
    id: int
    name: str | None
    amount: int | None
    round: str | None
    announced_date: str | None


class FullInvestmentSchema(BaseModel):
    id: int
    funding_round_id: int | None
    investor_id: int | None
    investment_firm_id: int | None
    amount: int | None
    created_by_admin: bool | None
    is_verified: bool | None
