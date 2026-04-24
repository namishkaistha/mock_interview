"""TTS router: POST /tts — proxies text to OpenAI TTS API."""
import os
import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

_OPENAI_TTS_URL = "https://api.openai.com/v1/audio/speech"


class TTSRequest(BaseModel):
    text: str


@router.post("/tts")
async def text_to_speech(body: TTSRequest):
    """Convert text to speech using OpenAI TTS API and stream audio back.

    Args:
        body: TTSRequest with text field.

    Returns:
        StreamingResponse of audio/mpeg bytes.

    Raises:
        HTTPException 422: If text is empty.
        HTTPException 502: If OpenAI TTS returns an error.
    """
    if not body.text or not body.text.strip():
        raise HTTPException(status_code=422, detail="text is required")

    api_key = os.getenv("OPENAI_API_KEY", "")

    payload = {
        "model": "tts-1",
        "input": body.text,
        "voice": "nova",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            _OPENAI_TTS_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="TTS service error")

    return StreamingResponse(
        iter([response.content]),
        media_type="audio/mpeg",
    )
