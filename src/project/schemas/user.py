from pydantic import BaseModel


class UserSchema(BaseModel):
    id: int
    email: str
    picture_url: str | None


class MemberSchema(BaseModel):
    id: int
    name: str
    picture_url: str | None
    role: str


class CompanyInvitationSchema(MemberSchema):
    company_id: int


class CompanySchema(MemberSchema):
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
