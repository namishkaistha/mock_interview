"""Tests for POST /session/{session_id}/end endpoint."""
import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.session_store import create_session, get_session, clear_all_sessions

client = TestClient(app)

_FAKE_FEEDBACK = {
    "overall_score": 7.5,
    "summary": "Strong technical answers with room to improve result articulation.",
    "question_feedback": [
        {
            "question": "Tell me about a time you led a project under tight deadlines.",
            "user_answer": "I led a database migration project...",
            "star_score": {"situation": 8, "task": 7, "action": 9, "result": 6},
            "strengths": "Clear action steps and strong ownership.",
            "improvements": "Quantify the business impact of results.",
        }
    ],
    "top_strengths": ["Communication", "Technical depth"],
    "top_improvements": ["Quantify outcomes", "Address task framing earlier"],
}


def _make_session() -> str:
    return create_session({
        "stage": "open_qa",
        "transcript": [
            {"role": "ai", "content": "Hi! I'm Alex."},
            {"role": "user", "content": "I once led a migration project..."},
        ],
        "questions": ["Tell me about a time you led a project under tight deadlines."],
        "question_index": 1,
        "persona": "Alex, senior engineer at Google.",
        "role": "Software Engineer",
        "company": "Google",
        "interviewer": "Alex",
        "exchanges": 2,
    })


@pytest.fixture(autouse=True)
def mock_llm(mocker):
    """Patch evaluate_interview so no real Claude calls happen."""
    mocker.patch(
        "app.routers.session.evaluate_interview",
        new=AsyncMock(return_value=_FAKE_FEEDBACK),
    )


@pytest.fixture(autouse=True)
def clear_store():
    yield
    clear_all_sessions()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_session_end_returns_200_with_feedback():
    """Successful end returns 200 and all top-level feedback keys."""
    session_id = _make_session()
    resp = client.post(f"/session/{session_id}/end")
    assert resp.status_code == 200
    data = resp.json()
    assert "overall_score" in data
    assert "summary" in data
    assert "question_feedback" in data
    assert "top_strengths" in data
    assert "top_improvements" in data


def test_session_end_feedback_has_correct_types():
    """overall_score is float, question_feedback/top_strengths/top_improvements are lists."""
    session_id = _make_session()
    data = client.post(f"/session/{session_id}/end").json()
    assert isinstance(data["overall_score"], float)
    assert isinstance(data["question_feedback"], list)
    assert isinstance(data["top_strengths"], list)
    assert isinstance(data["top_improvements"], list)


def test_session_end_question_feedback_has_star_score():
    """Each question_feedback entry contains a valid nested star_score."""
    session_id = _make_session()
    data = client.post(f"/session/{session_id}/end").json()
    fb = data["question_feedback"][0]
    star = fb["star_score"]
    for key in ("situation", "task", "action", "result"):
        assert key in star
        assert isinstance(star[key], int)


def test_session_end_deletes_session_from_store():
    """Session is removed from the store after a successful end call."""
    session_id = _make_session()
    client.post(f"/session/{session_id}/end")
    with pytest.raises(KeyError):
        get_session(session_id)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def test_session_end_unknown_session_returns_404():
    """Unknown session_id returns 404."""
    resp = client.post("/session/non-existent-id/end")
    assert resp.status_code == 404
