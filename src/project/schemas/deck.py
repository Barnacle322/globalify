from pydantic import BaseModel


class DeckSchema(BaseModel):
    id: int
    name: str
    json_feedback: list


class FeedbackSchema(BaseModel):
    id: int
    audience: str
    formality: str
    domain: str
    agent: str
    clarity_score: float
    grammar_score: float
    design_score: float
    storytelling_score: float
    engagement_score: float
    page_feedback: list[dict]  # Изменено на список словарей
    recommendation: str
    created_at: str

    class Config:
        orm_mode = True


class FeedbackHistorySchema(BaseModel):
    id: int
    goals: list
    created_at: str

    class Config:
        orm_mode = True
