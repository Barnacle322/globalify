from datetime import date

from pydantic import BaseModel

from .investor import RoundSchema


class FundingRoundSchema(BaseModel):
    id: int
    company_name: str
    round: RoundSchema | None
    announced_date: date | None

    def model_dump(self, **kwargs):
        data = super().model_dump(**kwargs)
        if self.announced_date:
            data["announced_date"] = self.announced_date.isoformat()
        return data


class FetchFundingRoundSchema(BaseModel):
    id: int
    company_id: int | None
    round_id: int | None
    announced_date: date | None

    def model_dump(self, **kwargs):
        data = super().model_dump(**kwargs)
        if self.announced_date:
            data["announced_date"] = self.announced_date.isoformat()
        return data


class InvestmentSchema(BaseModel):
    id: int
    name: str | None
    amount: int | None
    round: str | None
    announced_date: str | None


class InvestorSchema(BaseModel):
    id: int
    name: str


class FullInvestmentSchema(BaseModel):
    id: int
    funding_round_id: int | None
    investor: InvestorSchema | None
    investment_firm: InvestorSchema | None
    custom_name: str | None
    amount: int | None
    date: date | None
    created_by_admin: bool | None
    is_verified: bool | None

    def model_dump(self, **kwargs):
        data = super().model_dump(**kwargs)
        if self.date:
            data["date"] = self.date.isoformat()
        return data
