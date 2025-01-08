from pydantic import BaseModel


class UserCompany(BaseModel):
    id: int
    name: str
    picture_url: str | None = None
    is_primary: bool


class Investor(BaseModel):
    investor_mode: bool
    name: str | None = None
    twitter: str | None = None
