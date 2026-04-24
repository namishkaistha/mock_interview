"""Session router: POST /session/start, /respond, /respond/stream, /end."""
import json
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse as FastAPIStreamingResponse

from app.models.schemas import RespondRequest, RespondResponse, SessionEndResponse, SessionStartResponse
from app.services.resume_parser import parse_resume
from app.services.scraper import scrape_company
from app.services.llm import generate_session_setup, generate_response, generate_response_stream, evaluate_interview
from app.session_store import create_session, get_session, update_session, delete_session

router = APIRouter()


@router.post("/start", response_model=SessionStartResponse)
async def session_start(
    resume: UploadFile = File(...),
    role: str = Form(...),
    company: str = Form(""),
):
    """Start a new mock interview session.

    Parses the uploaded PDF resume, fetches web context for the company,
    asks Claude to generate a persona and behavioral competency themes,
    then stores everything in the in-memory session store.

    Args:
        resume: Uploaded PDF file.
        role: Job role the candidate is interviewing for.
        company: Target company name (optional).

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

    company_ctx = await scrape_company(company, role)

    setup = await generate_session_setup(
        resume_text=resume_text,
        role=role,
        company_ctx=company_ctx,
        company=company,
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
        "company_ctx": company_ctx,
        "resume_text": resume_text,
        "exchanges": 0,
    })

    return SessionStartResponse(
        session_id=session_id,
        stage="intro",
        interviewer_persona=setup["persona"],
        intro_message=setup["intro_message"],
    )


@router.post("/{session_id}/respond", response_model=RespondResponse)
async def session_respond(session_id: str, body: RespondRequest):
    """Handle one exchange in an ongoing interview session.

    Generates a stage-appropriate AI reply, appends both turns to the
    transcript, and advances the stage machine when thresholds are met:
    - intro → questions after 2 exchanges
    - questions → open_qa after all prepared questions are answered
    - open_qa marks interview_complete=True

    Args:
        session_id: UUID of the session returned by /start.
        body: RespondRequest with user_input and current stage.

    Returns:
        RespondResponse with ai_message, updated stage, question_index,
        and interview_complete flag.

    Raises:
        HTTPException 404: If the session does not exist.
    """
    try:
        session = get_session(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found")

    ai_message = await generate_response(session, body.user_input)

    session["transcript"].append({"role": "user", "content": body.user_input})
    session["transcript"].append({"role": "ai", "content": ai_message})

    current_stage = session["stage"]
    new_stage = current_stage
    interview_complete = False

    if current_stage == "intro":
        session["exchanges"] += 1
        if session["exchanges"] >= 2:
            new_stage = "questions"
    elif current_stage == "questions":
        session["question_index"] += 1
        if session["question_index"] >= len(session["questions"]):
            new_stage = "open_qa"
    elif current_stage == "open_qa":
        interview_complete = True

    update_session(session_id, {"stage": new_stage})

    question_index = session["question_index"] if new_stage == "questions" else None

    return RespondResponse(
        ai_message=ai_message,
        stage=new_stage,
        question_index=question_index,
        interview_complete=interview_complete,
    )


@router.post("/{session_id}/respond/stream")
async def session_respond_stream(session_id: str, body: RespondRequest):
    """Streaming version of /respond — sends tokens via SSE as they arrive.

    Emits two event types:
      {"type": "token", "text": "<chunk>"}  — streamed text fragments
      {"type": "done", "stage": "...", "interview_complete": false}  — final metadata

    The transcript and stage are updated after the full message is assembled.
    """
    try:
        session = get_session(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found")

    # Compute stage transition upfront so it's included in the done event
    current_stage = session["stage"]
    new_stage = current_stage
    interview_complete = False

    if current_stage == "intro":
        session["exchanges"] += 1
        if session["exchanges"] >= 2:
            new_stage = "questions"
    elif current_stage == "questions":
        session["question_index"] += 1
        if session["question_index"] >= len(session["questions"]):
            new_stage = "open_qa"
    elif current_stage == "open_qa":
        interview_complete = True

    async def event_generator():
        full_message = ""
        async for chunk in generate_response_stream(session, body.user_input):
            full_message += chunk
            yield f"data: {json.dumps({'type': 'token', 'text': chunk})}\n\n"

        # Persist transcript + stage after streaming completes
        session["transcript"].append({"role": "user", "content": body.user_input})
        session["transcript"].append({"role": "ai", "content": full_message})
        update_session(session_id, {"stage": new_stage})

        done_payload = {"type": "done", "stage": new_stage, "interview_complete": interview_complete}
        yield f"data: {json.dumps(done_payload)}\n\n"

    return FastAPIStreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{session_id}/end", response_model=SessionEndResponse)
async def session_end(session_id: str):
    """Evaluate the completed interview and return STAR-scored feedback.

    Sends the full session transcript to Claude for evaluation, returns
    structured feedback, then removes the session from memory.

    Args:
        session_id: UUID of the session returned by /start.

    Returns:
        SessionEndResponse with overall_score, summary, per-question STAR
        feedback, top_strengths, and top_improvements.

    Raises:
        HTTPException 404: If the session does not exist.
    """
    try:
        session = get_session(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found")

    feedback = await evaluate_interview(session)
    delete_session(session_id)

    return SessionEndResponse(**feedback)
