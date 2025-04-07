from pydantic import BaseModel


class DeckSchema(BaseModel):
    id: int
    name: str
    json_feedback: list


class SummarySchema(BaseModel):
    id: int
    agent: str
    clarity_score: float
    grammar_score: float
    design_score: float
    storytelling_score: float
    engagement_score: float
    recommendation: str

    class Config:
        orm_mode = True


class FeedbackHistorySchema(BaseModel):
    id: int
    goals: list
    created_at: str

    class Config:
        orm_mode = True
