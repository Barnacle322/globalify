from pydantic import BaseModel


class DeckSchema(BaseModel):
    id: int
    name: str
    json_feedback: list


class SummarySchema(BaseModel):
    id: int
    clarity: int
    grammary: int
    storytelling: int
    completeness: int
    engagement: int
    overall_score: float
    recommandation: str
