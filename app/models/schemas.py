"""Pydantic schemas for request and response validation."""
from typing import List, Literal, Optional
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class RespondRequest(BaseModel):
    """Body for POST /session/{session_id}/respond."""

    user_input: str
    stage: Literal["intro", "questions", "open_qa"]


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class SessionStartResponse(BaseModel):
    """Response from POST /session/start."""

    session_id: str
    stage: Literal["intro"]
    interviewer_persona: str
    intro_message: str


class RespondResponse(BaseModel):
    """Response from POST /session/{session_id}/respond."""

    ai_message: str
    stage: Literal["intro", "questions", "open_qa"]
    question_index: Optional[int] = None
    interview_complete: bool = False


class STARScore(BaseModel):
    """Per-component STAR scores (0–10)."""

    situation: int
    task: int
    action: int
    result: int


class QuestionFeedback(BaseModel):
    """Feedback for a single behavioral question."""

    question: str
    user_answer: str
    star_scores: STARScore
    strengths: List[str]
    improvements: List[str]


class SessionEndResponse(BaseModel):
    """Response from POST /session/{session_id}/end."""

    overall_score: float
    summary: str
    question_feedback: list[QuestionFeedback]
    top_strengths: list[str]
    top_improvements: list[str]
