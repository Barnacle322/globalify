from datetime import datetime

from pydantic import BaseModel

from ..utils.enums import SearchHistoryType


class UserSchema(BaseModel):
    id: int
    email: str
    picture_url: str | None


class MemberSchema(BaseModel):
    id: int
    name: str
    picture_url: str | None
    role: str
    position: str


class CompanyInvitationSchema(MemberSchema):
    company_id: int


class CompanySchema(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None
    number_of_employees: int | None
    website: str | None
    linkedin: str | None
    instagram: str | None
    twitter: str | None
    picture_url: str | None
    country: str | None
    preferred_round: object | None
    industry: object | None


class SearchHistorySchema(BaseModel):
    id: int
    query: str
    type: SearchHistoryType | None
    readable_type: str | None = None
    created_at: datetime
    date: datetime | None = None

    def model_dump(self, **kwargs):
        data = super().model_dump(**kwargs)
        if self.type is not None:
            data["type"] = self.type.value.replace("_", "")
            data["readable_type"] = self.type.name.title().replace("_", " ")
        if self.created_at:
            data["created_at"] = self.created_at.strftime("%I:%M %p")
            data["date"] = self.created_at.date().isoformat()
        return data
