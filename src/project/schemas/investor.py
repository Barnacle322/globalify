from pydantic import BaseModel


class InvestorBookmarkSchema(BaseModel):
    id: int
    name: str
    position: str | None
    firm_name: str | None
    about: str
    twitter: str | None
    slug: str


class InvestmentFirmBookmarkSchema(BaseModel):
    id: int
    name: str
    location: str
    about: str
    slug: str
