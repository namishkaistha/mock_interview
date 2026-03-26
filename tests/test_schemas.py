"""Tests for Pydantic request/response schemas."""
import pytest
from pydantic import ValidationError
from app.models.schemas import (
    RespondRequest,
    RespondResponse,
    SessionStartResponse,
    SessionEndResponse,
    STARScore,
    QuestionFeedback,
)


class TestRespondRequest:
    def test_valid_with_required_fields(self):
        req = RespondRequest(user_input="I led a team project.", stage="intro")
        assert req.user_input == "I led a team project."
        assert req.stage == "intro"

    def test_valid_stages(self):
        for stage in ("intro", "questions", "open_qa"):
            req = RespondRequest(user_input="hello", stage=stage)
            assert req.stage == stage

    def test_invalid_stage_raises(self):
        with pytest.raises(ValidationError):
            RespondRequest(user_input="hello", stage="invalid_stage")

    def test_missing_user_input_raises(self):
        with pytest.raises(ValidationError):
            RespondRequest(stage="intro")

    def test_missing_stage_raises(self):
        with pytest.raises(ValidationError):
            RespondRequest(user_input="hello")


class TestSessionStartResponse:
    def test_valid_response(self):
        resp = SessionStartResponse(
            session_id="abc-123",
            stage="intro",
            interviewer_persona="Friendly interviewer",
            intro_message="Welcome!",
        )
        assert resp.session_id == "abc-123"
        assert resp.stage == "intro"

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            SessionStartResponse(stage="intro", interviewer_persona="x", intro_message="y")


class TestRespondResponse:
    def test_valid_with_defaults(self):
        resp = RespondResponse(ai_message="Great answer!", stage="intro")
        assert resp.interview_complete is False
        assert resp.question_index is None

    def test_with_question_index(self):
        resp = RespondResponse(ai_message="Next question", stage="questions", question_index=2)
        assert resp.question_index == 2

    def test_interview_complete_true(self):
        resp = RespondResponse(ai_message="Done!", stage="open_qa", interview_complete=True)
        assert resp.interview_complete is True


class TestSTARScore:
    def test_valid_star_score(self):
        score = STARScore(situation=8, task=7, action=9, result=6)
        assert score.situation == 8
        assert score.result == 6


class TestQuestionFeedback:
    def test_valid_question_feedback(self):
        feedback = QuestionFeedback(
            question="Tell me about a challenge.",
            user_answer="I faced a tough deadline...",
            star_score=STARScore(situation=8, task=7, action=9, result=6),
            strengths="Clear structure",
            improvements="Add more metrics",
        )
        assert feedback.star_score.action == 9


class TestSessionEndResponse:
    def test_valid_full_response(self):
        resp = SessionEndResponse(
            overall_score=7.5,
            summary="Good performance overall.",
            question_feedback=[
                QuestionFeedback(
                    question="Q1",
                    user_answer="A1",
                    star_score=STARScore(situation=7, task=8, action=9, result=6),
                    strengths="Strong",
                    improvements="More detail",
                )
            ],
            top_strengths=["Communication", "Structure"],
            top_improvements=["Add metrics"],
        )
        assert resp.overall_score == 7.5
        assert len(resp.question_feedback) == 1
        assert resp.top_strengths[0] == "Communication"
