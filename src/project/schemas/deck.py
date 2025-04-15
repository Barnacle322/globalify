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
    formated_created_at: str
    agent: str | None

    class Config:
        orm_mode = True


class PageFeedback(BaseModel):
    page_number: int
    feedback: str
    clarity: int
    grammar: int
    design: int
    storytelling: int
    engagement: int


class DeckAnalysisResponse(BaseModel):
    deck_name: str
    recommendation: str
    investment_readiness: int
    feedback: dict[str, int]
    page_feedback: list[PageFeedback]


class OverallFeedbackScores(BaseModel):
    clarity: int
    grammar: int
    design: int
    storytelling: int
    engagement: int


class GeminiFeedback(BaseModel):
    deck_name: str
    recommendation: str
    feedback: OverallFeedbackScores
    page_feedback: list[PageFeedback]
