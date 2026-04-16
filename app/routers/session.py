"""Session router: POST /session/start, /respond, /end."""
import asyncio
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.models.schemas import SessionStartResponse
from app.services.resume_parser import parse_resume
from app.services.scraper import scrape_company, scrape_interviewer
from app.services.llm import generate_session_setup
from app.session_store import create_session

router = APIRouter()


@router.post("/start", response_model=SessionStartResponse)
async def session_start(
    resume: UploadFile = File(...),
    role: str = Form(...),
    company: str = Form(""),
    interviewer: str = Form(""),
):
    """Start a new mock interview session.

    Parses the uploaded PDF resume, fetches web context for the company
    and interviewer (in parallel), asks Claude to generate a persona and
    behavioral questions, then stores everything in the in-memory session
    store.

    Args:
        resume: Uploaded PDF file.
        role: Job role the candidate is interviewing for.
        company: Target company name (optional).
        interviewer: Interviewer's name (optional).

    Returns:
        SessionStartResponse with session_id, stage, interviewer_persona,
        and intro_message.

    Raises:
        HTTPException 422: If the resume cannot be parsed.
    """
    file_bytes = await resume.read()
    try:
        resume_text = parse_resume(file_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    company_ctx, interviewer_ctx = await asyncio.gather(
        scrape_company(company, role),
        scrape_interviewer(interviewer, company),
    )

    setup = await generate_session_setup(
        resume_text=resume_text,
        role=role,
        company_ctx=company_ctx,
        interviewer_ctx=interviewer_ctx,
        company=company,
        interviewer=interviewer,
    )

    session_id = create_session({
        "stage": "intro",
        "transcript": [],
        "questions": setup["questions"],
        "question_index": 0,
        "persona": setup["persona"],
        "intro_message": setup["intro_message"],
        "role": role,
        "company": company,
        "interviewer": interviewer,
        "exchanges": 0,
    })

    return SessionStartResponse(
        session_id=session_id,
        stage="intro",
        interviewer_persona=setup["persona"],
        intro_message=setup["intro_message"],
    )
