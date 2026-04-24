"""Tests for POST /session/start endpoint."""
import io
import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.session_store import clear_all_sessions, get_session

client = TestClient(app)

_FAKE_SETUP = {
    "persona": "Alex, a calm senior engineer at Google.",
    "questions": [
        "Tell me about a time you led a project under tight deadlines.",
        "Describe a conflict with a teammate and how you resolved it.",
    ],
    "intro_message": "Hi! I'm Alex. Let's start with a quick intro.",
}


@pytest.fixture(autouse=True)
def mock_services(mocker):
    """Patch all service calls so no real IO happens."""
    mocker.patch("app.routers.session.parse_resume", return_value="Jane Doe resume text")
    mocker.patch("app.routers.session.scrape_company", new=AsyncMock(return_value="Google info"))
    mocker.patch(
        "app.routers.session.generate_session_setup", new=AsyncMock(return_value=_FAKE_SETUP)
    )


@pytest.fixture(autouse=True)
def clear_store():
    """Ensure a clean session store for every test."""
    yield
    clear_all_sessions()


def _post_start(**extra_form):
    """Helper: POST /session/start with a fake PDF and sensible defaults."""
    form = {
        "role": (None, "Software Engineer"),
        "resume": ("resume.pdf", io.BytesIO(b"%PDF-fake"), "application/pdf"),
    }
    form.update(extra_form)
    return client.post("/session/start", files=form)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_session_start_returns_200_and_session_id():
    """Successful request returns 200 and a non-empty session_id."""
    resp = _post_start()
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert len(data["session_id"]) > 0


def test_session_start_response_stage_is_intro():
    """Response stage is always 'intro' on session creation."""
    resp = _post_start()
    assert resp.json()["stage"] == "intro"


def test_session_start_response_has_persona_and_intro_message():
    """interviewer_persona and intro_message are non-empty strings."""
    resp = _post_start()
    data = resp.json()
    assert isinstance(data["interviewer_persona"], str) and data["interviewer_persona"]
    assert isinstance(data["intro_message"], str) and data["intro_message"]


def test_session_start_session_stored_in_session_store():
    """The returned session_id is actually stored in the session store."""
    resp = _post_start()
    session_id = resp.json()["session_id"]
    session = get_session(session_id)
    assert session["stage"] == "intro"
    assert session["role"] == "Software Engineer"
    assert session["questions"] == _FAKE_SETUP["questions"]


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------

def test_session_start_missing_role_returns_422():
    """Omitting the required role field returns 422."""
    resp = client.post(
        "/session/start",
        files={"resume": ("resume.pdf", io.BytesIO(b"%PDF-fake"), "application/pdf")},
    )
    assert resp.status_code == 422


def test_session_start_missing_resume_returns_422():
    """Omitting the required resume file returns 422."""
    resp = client.post("/session/start", data={"role": "Software Engineer"})
    assert resp.status_code == 422


def test_session_start_invalid_resume_returns_422(mocker):
    """parse_resume raising ValueError results in a 422 response."""
    mocker.patch(
        "app.routers.session.parse_resume",
        side_effect=ValueError("Cannot parse empty bytes"),
    )
    resp = _post_start()
    assert resp.status_code == 422
