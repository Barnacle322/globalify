from datetime import date

from pydantic import BaseModel


class QualificationSchema(BaseModel):
    id: int
    type: str
    title: str
    description: str | None
    company_id: int | None
    company_name: str | None
    company_description: str | None
    company_url: str | None
    start_date: date | None
    end_date: date | None


class ExpertSchema(BaseModel):
    id: int
    user_id: int | None
    name: str
    bio: str | None
    description: str | None
    picture_url: str | None
    position: str | None
    linkedin: str | None
    twitter: str | None
    email: str | None
    phone_number: str | None
    location: str | None
    price: float | None
    qualifications: list[QualificationSchema]


class SessionSchema(BaseModel):
    id: int
    expert_name: str
    expert_email: str | None
    user_name: str
    user_email: str
    notes: str | None
    picture_url: str | None
    type: str
    status: str
    created_at: date
