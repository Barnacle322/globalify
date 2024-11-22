from datetime import date

from pydantic import BaseModel


class FundingRoundSchema(BaseModel):
    id: int
    company_name: str
    round: object
    announced_date: date


class InvestmentSchema(BaseModel):
    id: int
    name: str | None
    amount: int | None
    round: str | None
    announced_date: str | None
