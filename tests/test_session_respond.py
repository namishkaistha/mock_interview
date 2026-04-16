"""Tests for POST /session/{session_id}/respond endpoint."""
import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.session_store import create_session, clear_all_sessions

client = TestClient(app)

_QUESTIONS = [
    "Tell me about a time you led a project under tight deadlines.",
    "Describe a conflict with a teammate and how you resolved it.",
]


def _make_session(**overrides) -> str:
    """Create a session in the store with sensible defaults and return its ID."""
    data = {
        "stage": "intro",
        "transcript": [],
        "questions": _QUESTIONS,
        "question_index": 0,
        "persona": "Alex, senior engineer at Google.",
        "intro_message": "Hi! I'm Alex.",
        "role": "Software Engineer",
        "company": "Google",
        "interviewer": "Alex",
        "exchanges": 0,
    }
    data.update(overrides)
    return create_session(data)


def _respond(session_id, user_input="I'm doing great.", stage="intro"):
    return client.post(
        f"/session/{session_id}/respond",
        json={"user_input": user_input, "stage": stage},
    )


@pytest.fixture(autouse=True)
def mock_llm(mocker):
    """Patch generate_response so no real Claude calls happen."""
    mocker.patch(
        "app.routers.session.generate_response",
        new=AsyncMock(return_value="Great, let's continue."),
    )


@pytest.fixture(autouse=True)
def clear_store():
    yield
    clear_all_sessions()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_respond_returns_200_with_ai_message():
    """Successful respond returns 200 and an ai_message."""
    session_id = _make_session()
    resp = _respond(session_id)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ai_message"] == "Great, let's continue."


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def test_respond_unknown_session_returns_404():
    """Unknown session_id returns 404."""
    resp = _respond("non-existent-id")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Stage: intro
# ---------------------------------------------------------------------------

def test_respond_intro_stays_in_intro_before_threshold():
    """After the 1st exchange, stage remains 'intro'."""
    session_id = _make_session(stage="intro", exchanges=0)
    resp = _respond(session_id, stage="intro")
    assert resp.json()["stage"] == "intro"


def test_respond_intro_transitions_to_questions_after_2_exchanges():
    """After the 2nd exchange (exchanges reaches 2), stage becomes 'questions'."""
    session_id = _make_session(stage="intro", exchanges=1)
    resp = _respond(session_id, stage="intro")
    assert resp.json()["stage"] == "questions"


# ---------------------------------------------------------------------------
# Stage: questions
# ---------------------------------------------------------------------------

def test_respond_questions_increments_question_index():
    """Each respond in questions stage increments question_index in the response."""
    session_id = _make_session(stage="questions", question_index=0)
    resp = _respond(session_id, stage="questions")
    data = resp.json()
    assert data["stage"] == "questions"
    assert data["question_index"] == 1


def test_respond_questions_transitions_to_open_qa_when_exhausted():
    """After the last question is answered, stage transitions to 'open_qa'."""
    # question_index starts at 1 (last question), answering it should exhaust the list
    session_id = _make_session(stage="questions", question_index=len(_QUESTIONS) - 1)
    resp = _respond(session_id, stage="questions")
    assert resp.json()["stage"] == "open_qa"


# ---------------------------------------------------------------------------
# Stage: open_qa
# ---------------------------------------------------------------------------

def test_respond_open_qa_sets_interview_complete():
    """Any respond during open_qa sets interview_complete=True."""
    session_id = _make_session(stage="open_qa")
    resp = _respond(session_id, stage="open_qa")
    data = resp.json()
    assert data["stage"] == "open_qa"
    assert data["interview_complete"] is True
