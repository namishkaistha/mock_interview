"""TTS router: POST /tts — proxies text to ElevenLabs streaming API."""
import os
import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

_ELEVENLABS_BASE = "https://api.elevenlabs.io/v1/text-to-speech"


class TTSRequest(BaseModel):
    text: str


@router.post("/tts")
async def text_to_speech(body: TTSRequest):
    """Convert text to speech using ElevenLabs API and stream audio back.

    Args:
        body: TTSRequest with text field.

    Returns:
        StreamingResponse of audio/mpeg bytes.

    Raises:
        HTTPException 422: If text is empty.
        HTTPException 502: If ElevenLabs returns an error.
    """
    if not body.text or not body.text.strip():
        raise HTTPException(status_code=422, detail="text is required")

    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    api_key = os.getenv("ELEVENLABS_API_KEY", "")
    url = f"{_ELEVENLABS_BASE}/{voice_id}/stream"

    payload = {
        "text": body.text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            headers={"xi-api-key": api_key, "Content-Type": "application/json"},
            json=payload,
        )

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="TTS service error")

    return StreamingResponse(
        iter([response.content]),
        media_type="audio/mpeg",
    )
