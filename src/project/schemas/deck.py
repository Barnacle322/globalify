from pydantic import BaseModel


class DeckSchema(BaseModel):
    id: int
    name: str
    json_feedback: list


class SummarySchema(BaseModel):
    id: int
    clarity_score: int
    grammar_score: int
    design_score: int
    storytelling_score: int
    engagement_score: int
    overall_score: float
    recommendation: str

    class Config:
        orm_mode = True


class FeedbackHistorySchema(BaseModel):
    id: int
    goals: list
    created_at: str

    class Config:
        orm_mode = True
