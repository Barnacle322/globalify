from pydantic import BaseModel
from typing import Optional

from ..schemas.user import CompanySchema


class CompanyBookmarkSchema(BaseModel):
    id: int
    name: str
    about: str | None = None


class UserCompanySchema(BaseModel):
    id: int
    role: str
    position: Optional[str]
    is_primary: bool
    is_public: bool
    company_id: int
