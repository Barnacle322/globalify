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


class CompanyInvitationSchema(BaseModel):
    id: int
    name: str
    picture_url: str | None
    role: str
    company_id: int
