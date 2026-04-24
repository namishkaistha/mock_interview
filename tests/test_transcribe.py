"""Tests for POST /transcribe endpoint."""
import io
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _mock_whisper(mocker, status_code=200, text="Hello, I am ready for the interview."):
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json.return_value = {"text": text}
    mocker.patch(
        "app.routers.transcribe.httpx.AsyncClient.post",
        new=AsyncMock(return_value=mock_response),
    )
    return mock_response


def test_transcribe_returns_text(mocker):
    """Successful transcription returns {"text": "..."}."""
    _mock_whisper(mocker, text="I led a team of five engineers.")
    resp = client.post(
        "/transcribe",
        files={"audio": ("audio.webm", io.BytesIO(b"fake-audio-data"), "audio/webm")},
    )
    assert resp.status_code == 200
    assert resp.json()["text"] == "I led a team of five engineers."


def test_transcribe_no_file_returns_422():
    """Missing audio file returns 422."""
    resp = client.post("/transcribe")
    assert resp.status_code == 422


def test_transcribe_whisper_error_returns_502(mocker):
    """Whisper API returning non-200 results in 502."""
    _mock_whisper(mocker, status_code=500)
    resp = client.post(
        "/transcribe",
        files={"audio": ("audio.webm", io.BytesIO(b"fake-audio-data"), "audio/webm")},
    )
    assert resp.status_code == 502
