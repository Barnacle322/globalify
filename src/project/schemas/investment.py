from datetime import date

from pydantic import BaseModel


class FundingRoundSchema(BaseModel):
    id: int
    company_name: str
    round: object
    announced_date: date


class InvestmentFundingRoundSchema(BaseModel):
    id: int
    company_name: str
    round: str
    announced_date: str


class InvestmentSchema(BaseModel):
    id: int
    funding_round: InvestmentFundingRoundSchema
