"""Tests for POST /tts endpoint."""
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _mock_openai_tts(mocker, status_code=200, content=b"fake-audio-bytes"):
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.content = content
    mocker.patch("app.routers.tts.httpx.AsyncClient.post", new=AsyncMock(return_value=mock_response))
    return mock_response


def test_tts_returns_audio_stream(mocker):
    """Successful request returns 200 with audio/mpeg content type."""
    _mock_openai_tts(mocker, status_code=200, content=b"fake-mp3-bytes")
    resp = client.post("/tts", json={"text": "Hello, let's begin the interview."})
    assert resp.status_code == 200
    assert "audio" in resp.headers.get("content-type", "")


def test_tts_empty_text_returns_422(mocker):
    """Empty text returns 422 without calling OpenAI."""
    mock_post = mocker.patch("app.routers.tts.httpx.AsyncClient.post", new=AsyncMock())
    resp = client.post("/tts", json={"text": ""})
    assert resp.status_code == 422
    mock_post.assert_not_called()


def test_tts_openai_error_returns_502(mocker):
    """OpenAI TTS returning non-200 results in 502."""
    _mock_openai_tts(mocker, status_code=401)
    resp = client.post("/tts", json={"text": "Hello there."})
    assert resp.status_code == 502
