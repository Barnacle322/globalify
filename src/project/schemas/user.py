from pydantic import BaseModel


class UserSchema(BaseModel):
    id: int
    email: str
    picture_url: str | None
