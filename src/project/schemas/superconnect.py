from pydantic import BaseModel


class Expert(BaseModel):
    id: int
    bio: str
    full_name: str
    picture_url: str | None = None
    current_position_info: str
    industries: list[object] | None
