"""Tests for the LLM service (Anthropic Claude API calls)."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.llm import generate_session_setup, generate_response, evaluate_interview


_SETUP_JSON = json.dumps({
    "persona": "Alex, a calm senior engineer at Google.",
    "questions": [
        "Tell me about a time you led a project under tight deadlines.",
        "Describe a conflict with a teammate and how you resolved it.",
        "Give an example of a technical decision you made with incomplete info.",
    ],
    "intro_message": "Hi! I'm Alex. Let's start with some quick introductions.",
})

_EVAL_JSON = json.dumps({
    "overall_score": 7.5,
    "summary": "Strong technical answers with room to improve on result articulation.",
    "question_feedback": [
        {
            "question": "Tell me about a time you led a project under tight deadlines.",
            "user_answer": "I once led a migration project...",
            "star_score": {"situation": 8, "task": 7, "action": 9, "result": 6},
            "strengths": "Clear situation and strong action steps.",
            "improvements": "Quantify the results more specifically.",
        }
    ],
    "top_strengths": ["Clear communication", "Strong action orientation"],
    "top_improvements": ["Quantify outcomes", "Address task framing earlier"],
})

_SESSION_DATA = {
    "stage": "questions",
    "transcript": [
        {"role": "ai", "content": "Hi! I'm Alex."},
        {"role": "user", "content": "Thanks, excited to be here."},
    ],
    "questions": [
        "Tell me about a time you led a project under tight deadlines.",
        "Describe a conflict with a teammate.",
    ],
    "question_index": 0,
    "persona": "Alex, a calm senior engineer at Google.",
    "role": "Software Engineer",
    "company": "Google",
}


def _mock_claude(mocker, text):
    """Patch AsyncAnthropic so Claude returns the given text."""
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=text)]
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_msg)
    mocker.patch("app.services.llm.anthropic.AsyncAnthropic", return_value=mock_client)
    return mock_client


# ---------------------------------------------------------------------------
# generate_session_setup
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_session_setup_returns_expected_keys(mocker):
    """Result dict has persona, questions, and intro_message keys."""
    _mock_claude(mocker, _SETUP_JSON)
    result = await generate_session_setup(
        resume_text="Jane Doe, Software Engineer",
        role="Software Engineer",
        company_ctx="Google values collaboration.",
        interviewer_ctx="Alex is a senior engineer.",
        company="Google",
        interviewer="Alex",
    )
    assert "persona" in result
    assert "questions" in result
    assert "intro_message" in result


@pytest.mark.asyncio
async def test_generate_session_setup_questions_is_list(mocker):
    """questions field is a non-empty list of strings."""
    _mock_claude(mocker, _SETUP_JSON)
    result = await generate_session_setup(
        resume_text="Jane Doe",
        role="Software Engineer",
    )
    assert isinstance(result["questions"], list)
    assert len(result["questions"]) > 0
    assert all(isinstance(q, str) for q in result["questions"])


@pytest.mark.asyncio
async def test_generate_session_setup_raises_on_invalid_json(mocker):
    """Raises ValueError when Claude returns unparseable text."""
    _mock_claude(mocker, "Sorry, I cannot help with that.")
    with pytest.raises(ValueError, match="parse"):
        await generate_session_setup(resume_text="Jane Doe", role="Engineer")


# ---------------------------------------------------------------------------
# generate_response
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_response_returns_string(mocker):
    """Returns a plain string AI message."""
    _mock_claude(mocker, "Great, let's move on to the first question.")
    result = await generate_response(_SESSION_DATA, "I'm ready.")
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_generate_response_includes_stage_in_prompt(mocker):
    """The stage from session_data appears in the prompt sent to Claude."""
    mock_client = _mock_claude(mocker, "Next question coming up.")
    await generate_response(_SESSION_DATA, "I'm ready.")
    call_args = mock_client.messages.create.call_args
    messages = call_args.kwargs.get("messages") or call_args.args[0]
    prompt_text = " ".join(m["content"] for m in messages if isinstance(m.get("content"), str))
    assert "questions" in prompt_text


# ---------------------------------------------------------------------------
# evaluate_interview
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_evaluate_interview_returns_valid_structure(mocker):
    """Result dict has all top-level keys with correct types."""
    _mock_claude(mocker, _EVAL_JSON)
    result = await evaluate_interview(_SESSION_DATA)
    assert isinstance(result["overall_score"], float)
    assert isinstance(result["summary"], str)
    assert isinstance(result["question_feedback"], list)
    assert isinstance(result["top_strengths"], list)
    assert isinstance(result["top_improvements"], list)


@pytest.mark.asyncio
async def test_evaluate_interview_question_feedback_has_star_score(mocker):
    """Each question_feedback entry has a star_score with four int components."""
    _mock_claude(mocker, _EVAL_JSON)
    result = await evaluate_interview(_SESSION_DATA)
    fb = result["question_feedback"][0]
    assert "question" in fb
    assert "user_answer" in fb
    assert "strengths" in fb
    assert "improvements" in fb
    star = fb["star_score"]
    for key in ("situation", "task", "action", "result"):
        assert key in star
        assert isinstance(star[key], int)


@pytest.mark.asyncio
async def test_evaluate_interview_raises_on_invalid_json(mocker):
    """Raises ValueError when Claude returns unparseable text."""
    _mock_claude(mocker, "I cannot evaluate this interview.")
    with pytest.raises(ValueError, match="parse"):
        await evaluate_interview(_SESSION_DATA)
