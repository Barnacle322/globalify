from datetime import date

from pydantic import BaseModel


class FundingRoundSchema(BaseModel):
    id: int
    organization_name: str
    round: object
    announced_date: date
