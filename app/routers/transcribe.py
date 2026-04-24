"""Transcribe router: POST /transcribe — sends audio to OpenAI Whisper."""
import os
import httpx
from fastapi import APIRouter, File, HTTPException, UploadFile
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

_WHISPER_URL = "https://api.openai.com/v1/audio/transcriptions"


@router.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    """Transcribe uploaded audio using OpenAI Whisper.

    Args:
        audio: Audio file (webm, mp4, wav, etc.).

    Returns:
        Dict with key "text" containing the transcription.

    Raises:
        HTTPException 422: If no audio file or empty bytes provided.
        HTTPException 502: If Whisper API returns an error.
    """
    file_bytes = await audio.read()
    if not file_bytes:
        raise HTTPException(status_code=422, detail="audio file is required")

    api_key = os.getenv("OPENAI_API_KEY", "")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            _WHISPER_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            files={
                "file": (
                    audio.filename or "audio.webm",
                    file_bytes,
                    audio.content_type or "audio/webm",
                )
            },
            data={"model": "whisper-1"},
        )

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Transcription service error")

    result = response.json()
    return {"text": result.get("text", "")}
