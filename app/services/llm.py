"""LLM service: all Anthropic Claude API calls.

Three public async functions cover the interview lifecycle:
- generate_session_setup: persona, behavioral questions, intro message
- generate_response: stage-aware conversational reply
- evaluate_interview: STAR-scored feedback report
"""
import json
import os
import re
import anthropic
from dotenv import load_dotenv

load_dotenv()

_MODEL_SETUP = "claude-sonnet-4-6"      # used for session setup + evaluation
_MODEL_RESPOND = "claude-haiku-4-5-20251001"  # used for real-time responses (3-5x faster)

# ---------------------------------------------------------------------------
# Interviewer style parameters (1–5 scale)
#
# verbosity        1 = ultra-brief (1 sentence), 5 = elaborate (many sentences)
# warmth           1 = formal/professional,      5 = casual/buddy-like
# behavioral_density  1 = mostly conversation,   5 = strict STAR-only questions
# follow_up_depth  1 = always advance immediately, 5 = probe same topic extensively
# ---------------------------------------------------------------------------
INTERVIEWER_STYLE = {
    "verbosity": 2,           # short responses — acknowledge briefly, then question
    "warmth": 3,              # warm and genuine but not overly casual
    "behavioral_density": 3,  # balanced: brief human moment, then behavioral question
    "follow_up_depth": 2,     # light follow-up; advance to next competency quickly
}


def _style_instructions() -> str:
    """Translate INTERVIEWER_STYLE scale values into prose instructions for the prompt."""
    v = INTERVIEWER_STYLE["verbosity"]
    w = INTERVIEWER_STYLE["warmth"]
    b = INTERVIEWER_STYLE["behavioral_density"]
    f = INTERVIEWER_STYLE["follow_up_depth"]

    length_map = {
        1: "Respond in exactly 1 sentence.",
        2: "Respond in 2-3 sentences max — never more.",
        3: "Respond in 3-4 sentences.",
        4: "You may respond in up to 5-6 sentences.",
        5: "You may respond at length.",
    }
    warmth_map = {
        1: "Be formal and professional in tone.",
        2: "Be professional but approachable.",
        3: "Be warm and genuine — sound like a real person, not a corporate script.",
        4: "Be casual and conversational, like a peer.",
        5: "Be very casual and friendly, like a friend.",
    }
    density_map = {
        1: "Prioritize natural conversation over structured questions. Only ask a behavioral question if it flows naturally.",
        2: "Mix conversation and behavioral questions roughly 60/40.",
        3: "Briefly acknowledge what the candidate said (one clause), then pivot to one behavioral question.",
        4: "Keep conversation brief. Spend most of your response on the behavioral question.",
        5: "Stay strictly on behavioral questions. Skip small talk entirely.",
    }
    follow_up_map = {
        1: "Always move to the next competency area — never re-probe the same topic.",
        2: "Ask a light follow-up only if the candidate was vague; otherwise advance to the next competency.",
        3: "Use one follow-up question when answers are thin, then move on.",
        4: "Probe each answer with 1-2 follow-ups before moving on.",
        5: "Probe deeply on each answer until you're satisfied with the detail.",
    }

    return (
        f"Style rules (follow these strictly):\n"
        f"- Length: {length_map[v]}\n"
        f"- Tone: {warmth_map[w]}\n"
        f"- Question balance: {density_map[b]}\n"
        f"- Follow-up: {follow_up_map[f]}\n"
        f"- Ask ONE question per response — never pile on multiple questions.\n"
        f"- Do NOT use action descriptions or stage directions in asterisks (e.g. *nods*, *pauses*)."
    )


def _get_client() -> anthropic.AsyncAnthropic:
    """Return an AsyncAnthropic client using the env API key."""
    return anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))


def _parse_json(text: str, context: str) -> dict:
    """Strip markdown code fences and parse JSON from Claude's response.

    Args:
        text: Raw text returned by Claude.
        context: Short label for error messages (e.g. "generate_session_setup").

    Returns:
        Parsed dict.

    Raises:
        ValueError: If the text cannot be parsed as JSON.
    """
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Could not parse Claude response in {context}: {exc}") from exc


def _format_transcript(transcript: list[dict]) -> str:
    """Render a transcript list as a readable string for Claude prompts."""
    lines = []
    for turn in transcript:
        role = "Interviewer" if turn["role"] == "ai" else "Candidate"
        lines.append(f"{role}: {turn['content']}")
    return "\n".join(lines)


async def generate_session_setup(
    resume_text: str,
    role: str,
    company_ctx: str = "",
    company: str = "",
) -> dict:
    """Call Claude to produce an interviewer persona, 4-5 behavioral competency
    themes, and an opening intro message tailored to the candidate's resume and context.

    Args:
        resume_text: Extracted plain text from the candidate's PDF resume.
        role: The role the candidate is interviewing for.
        company_ctx: Web-scraped company culture/values context (may be empty).
        company: Company name (may be empty).

    Returns:
        Dict with keys:
            persona (str): Short description of the AI interviewer character.
            questions (list[str]): 4-5 behavioral competency theme labels.
            intro_message (str): Opening script for the AI interviewer.

    Raises:
        ValueError: If Claude's response cannot be parsed as JSON.
    """
    company_section = f"\nCompany context:\n{company_ctx}" if company_ctx else ""
    company_label = company or "the company"

    prompt = f"""You are helping set up a personalized behavioral mock interview.

Candidate resume:
{resume_text}

Role: {role}
Company: {company_label}
{company_section}

Generate the following as a single JSON object (no markdown, no extra text):
{{
  "persona": "<Invent a realistic interviewer. Write their full name followed by 2-3 sentences on their background and interviewing style. Keep it warm but professional.>",
  "questions": [
    "<behavioral competency theme 1 — 5-10 words, e.g. 'cross-functional influence under ambiguity'>",
    "<behavioral competency theme 2>",
    "<behavioral competency theme 3>",
    "<behavioral competency theme 4>",
    "<behavioral competency theme 5>"
  ],
  "intro_message": "<Opening 1-2 sentence greeting from the interviewer introducing themselves by name. Be brief and natural.>"
}}

The competency themes should be grounded in THIS candidate's background and THIS role at THIS company — not generic. Think about what behavioral signals actually matter for this specific role and what gaps or strengths in this candidate's resume are worth probing."""

    client = _get_client()
    response = await client.messages.create(
        model=_MODEL_SETUP,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return _parse_json(response.content[0].text, "generate_session_setup")


def _build_questions_stage_instructions(
    questions: list,
    question_index: int,
    company: str,
    company_ctx: str,
    resume_text: str,
) -> str:
    """Build the questions-stage instruction block for the LLM prompt."""
    remaining_themes = questions[question_index:] if question_index < len(questions) else []
    explored_count = question_index
    total = len(questions)
    themes_str = "\n".join(f"- {t}" for t in remaining_themes)
    company_ctx_snippet = company_ctx[:600] if company_ctx else ""
    resume_snippet = resume_text[:800] if resume_text else ""

    return (
        f"You are in the QUESTIONS stage ({explored_count + 1} of {total}).\n\n"
        f"Remaining behavioral competency areas to explore:\n{themes_str}\n\n"
        + (f"Company context:\n{company_ctx_snippet}\n\n" if company_ctx_snippet else "")
        + (f"Candidate resume highlights:\n{resume_snippet}\n\n" if resume_snippet else "")
        + "Craft the next behavioral question. It MUST:\n"
        "- Naturally acknowledge or build on something specific the candidate just said\n"
        "- Reference the company's known culture, products, or values using the company context above\n"
        "- Name a specific project, skill, or role from the candidate's resume\n"
        "- Cover the first unexplored competency area listed above\n"
        "Keep it to 1-2 sentences. Sound natural and tailored, not scripted."
    )


async def generate_response_stream(session_data: dict, user_input: str):
    """Streaming version of generate_response — yields text chunks as they arrive.

    Args:
        session_data: Current session dict.
        user_input: The candidate's latest message.

    Yields:
        str: Text chunks from the model stream.
    """
    stage = session_data["stage"]
    persona = session_data.get("persona", "a professional interviewer")
    role = session_data.get("role", "the role")
    company = session_data.get("company", "the company")
    company_ctx = session_data.get("company_ctx", "")
    resume_text = session_data.get("resume_text", "")
    transcript = session_data.get("transcript", [])
    questions = session_data.get("questions", [])
    question_index = session_data.get("question_index", 0)

    transcript_text = _format_transcript(transcript)

    if stage == "intro":
        stage_instructions = (
            "You are in the INTRO stage. Engage warmly and conversationally. "
            "Do not ask behavioral questions yet — focus on making the candidate comfortable."
        )
    elif stage == "questions":
        stage_instructions = _build_questions_stage_instructions(
            questions, question_index, company, company_ctx, resume_text
        )
    else:
        stage_instructions = (
            f"You are in the OPEN Q&A stage. Answer the candidate's questions in character "
            f"as the interviewer at {company} for the {role} role."
        )

    prompt = f"""You are roleplaying as: {persona}
You are conducting a behavioral interview for the {role} role at {company}.

{_style_instructions()}

Stage instructions: {stage_instructions}

Conversation so far:
{transcript_text}

Candidate just said: {user_input}

Respond as the interviewer. Do not summarize or repeat what the candidate said. Do not break character."""

    client = _get_client()
    async with client.messages.stream(
        model=_MODEL_RESPOND,
        max_tokens=180,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        async for text in stream.text_stream:
            yield text


async def generate_response(session_data: dict, user_input: str) -> str:
    """Call Claude for a stage-appropriate AI interviewer reply.

    Args:
        session_data: Current session dict with keys: stage, transcript, questions,
                      question_index, persona, role, company, company_ctx, resume_text.
        user_input: The candidate's latest message.

    Returns:
        AI message string.
    """
    stage = session_data["stage"]
    persona = session_data.get("persona", "a professional interviewer")
    role = session_data.get("role", "the role")
    company = session_data.get("company", "the company")
    company_ctx = session_data.get("company_ctx", "")
    resume_text = session_data.get("resume_text", "")
    transcript = session_data.get("transcript", [])
    questions = session_data.get("questions", [])
    question_index = session_data.get("question_index", 0)

    transcript_text = _format_transcript(transcript)

    if stage == "intro":
        stage_instructions = (
            "You are in the INTRO stage. Engage warmly and conversationally. "
            "Do not ask behavioral questions yet — focus on making the candidate comfortable."
        )
    elif stage == "questions":
        stage_instructions = _build_questions_stage_instructions(
            questions, question_index, company, company_ctx, resume_text
        )
    else:  # open_qa
        stage_instructions = (
            f"You are in the OPEN Q&A stage. Answer the candidate's questions in character "
            f"as the interviewer at {company} for the {role} role."
        )

    prompt = f"""You are roleplaying as: {persona}
You are conducting a behavioral interview for the {role} role at {company}.

{_style_instructions()}

Stage instructions: {stage_instructions}

Conversation so far:
{transcript_text}

Candidate just said: {user_input}

Respond as the interviewer. Do not summarize or repeat what the candidate said. Do not break character."""

    client = _get_client()
    response = await client.messages.create(
        model=_MODEL_RESPOND,
        max_tokens=180,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


async def evaluate_interview(session_data: dict) -> dict:
    """Call Claude to produce STAR-scored feedback over the full interview transcript.

    Args:
        session_data: Session dict with keys: transcript, questions, role, company.

    Returns:
        Dict matching SessionEndResponse schema:
        {
            "overall_score": float,
            "summary": str,
            "question_feedback": [
                {
                    "question": str,
                    "user_answer": str,
                    "star_scores": {"situation": int, "task": int, "action": int, "result": int},
                    "strengths": [str, ...],
                    "improvements": [str, ...],
                }
            ],
            "top_strengths": [str, ...],
            "top_improvements": [str, ...],
        }

    Raises:
        ValueError: If Claude's response cannot be parsed as JSON.
    """
    transcript_text = _format_transcript(session_data.get("transcript", []))
    questions = session_data.get("questions", [])
    role = session_data.get("role", "the role")
    company = session_data.get("company", "the company")

    themes_list = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))

    prompt = f"""You evaluated a behavioral mock interview for the {role} role at {company}.

Behavioral competency areas that were explored:
{themes_list}

Full interview transcript:
{transcript_text}

Note: The actual questions asked are embedded in the transcript as Interviewer turns. Identify each behavioral question from the transcript, then evaluate the candidate's response.

Evaluate the candidate using the STAR framework (Situation, Task, Action, Result).
Return ONLY a JSON object (no markdown, no extra text) in this exact format:
{{
  "overall_score": <float 0.0-10.0>,
  "summary": "<2-3 sentence overall assessment>",
  "question_feedback": [
    {{
      "question": "<the behavioral question>",
      "user_answer": "<summary of the candidate's answer>",
      "star_scores": {{
        "situation": <int 0-10>,
        "task": <int 0-10>,
        "action": <int 0-10>,
        "result": <int 0-10>
      }},
      "strengths": ["<strength 1>", "<strength 2>"],
      "improvements": ["<improvement 1>", "<improvement 2>"]
    }}
  ],
  "top_strengths": ["<strength 1>", "<strength 2>"],
  "top_improvements": ["<improvement 1>", "<improvement 2>"]
}}

Score each STAR component 0-10. Be specific and constructive."""

    client = _get_client()
    response = await client.messages.create(
        model=_MODEL_SETUP,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    return _parse_json(response.content[0].text, "evaluate_interview")
