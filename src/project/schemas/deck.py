from pydantic import BaseModel


class DeckSchema(BaseModel):
    id: int
    name: str
    json_feedback: dict
