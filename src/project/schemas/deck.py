from datetime import datetime

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
    clarity_score: int
    grammar_score: int
    design_score: int
    storytelling_score: int
    engagement_score: int
    page_feedback: dict[str, str]
    recommendation: str
    created_at: datetime
