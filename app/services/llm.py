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

_MODEL = "claude-sonnet-4-5"


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
    interviewer_ctx: str = "",
    company: str = "",
    interviewer: str = "",
) -> dict:
    """Call Claude to produce an interviewer persona, 4-5 behavioral questions,
    and an opening intro message tailored to the candidate's resume and context.

    Args:
        resume_text: Extracted plain text from the candidate's PDF resume.
        role: The role the candidate is interviewing for.
        company_ctx: Web-scraped company culture/values context (may be empty).
        interviewer_ctx: Web-scraped interviewer background context (may be empty).
        company: Company name (may be empty).
        interviewer: Interviewer name (may be empty).

    Returns:
        Dict with keys:
            persona (str): Short description of the AI interviewer character.
            questions (list[str]): 4-5 STAR behavioral questions.
            intro_message (str): Opening script for the AI interviewer.

    Raises:
        ValueError: If Claude's response cannot be parsed as JSON.
    """
    company_section = f"\nCompany context:\n{company_ctx}" if company_ctx else ""
    interviewer_section = f"\nInterviewer context:\n{interviewer_ctx}" if interviewer_ctx else ""
    company_label = company or "the company"
    interviewer_label = f" The real interviewer is {interviewer}." if interviewer else ""

    prompt = f"""You are helping set up a personalized behavioral mock interview.

Candidate resume:
{resume_text}

Role: {role}
Company: {company_label}{interviewer_label}
{company_section}
{interviewer_section}

Generate the following as a single JSON object (no markdown, no extra text):
{{
  "persona": "<2-3 sentence description of the AI interviewer: name, tone, style>",
  "questions": [
    "<STAR behavioral question 1>",
    "<STAR behavioral question 2>",
    "<STAR behavioral question 3>",
    "<STAR behavioral question 4>",
    "<STAR behavioral question 5>"
  ],
  "intro_message": "<Opening 2-3 sentence greeting from the AI interviewer to the candidate>"
}}

Tailor questions to the candidate's background and the role. Keep the persona warm but professional."""

    client = _get_client()
    response = await client.messages.create(
        model=_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return _parse_json(response.content[0].text, "generate_session_setup")


async def generate_response(session_data: dict, user_input: str) -> str:
    """Call Claude for a stage-appropriate AI interviewer reply.

    Args:
        session_data: Current session dict with keys: stage, transcript, questions,
                      question_index, persona, role, company.
        user_input: The candidate's latest message.

    Returns:
        AI message string.
    """
    stage = session_data["stage"]
    persona = session_data.get("persona", "a professional interviewer")
    role = session_data.get("role", "the role")
    company = session_data.get("company", "the company")
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
        current_q = questions[question_index] if question_index < len(questions) else ""
        stage_instructions = (
            f"You are in the QUESTIONS stage. Ask or follow up on behavioral questions. "
            f"Current question ({question_index + 1} of {len(questions)}): {current_q}"
        )
    else:  # open_qa
        stage_instructions = (
            f"You are in the OPEN Q&A stage. Answer the candidate's questions in character "
            f"as the interviewer at {company} for the {role} role."
        )

    prompt = f"""You are roleplaying as: {persona}

You are conducting a behavioral interview for the {role} role at {company}.

Stage instructions: {stage_instructions}

Conversation so far:
{transcript_text}

Candidate just said: {user_input}

Respond as the interviewer. Be concise (2-4 sentences). Do not break character."""

    client = _get_client()
    response = await client.messages.create(
        model=_MODEL,
        max_tokens=512,
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
                    "star_score": {"situation": int, "task": int, "action": int, "result": int},
                    "strengths": str,
                    "improvements": str,
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

    questions_list = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))

    prompt = f"""You evaluated a behavioral mock interview for the {role} role at {company}.

Behavioral questions that were asked:
{questions_list}

Full interview transcript:
{transcript_text}

Evaluate the candidate using the STAR framework (Situation, Task, Action, Result).
Return ONLY a JSON object (no markdown, no extra text) in this exact format:
{{
  "overall_score": <float 0.0-10.0>,
  "summary": "<2-3 sentence overall assessment>",
  "question_feedback": [
    {{
      "question": "<the behavioral question>",
      "user_answer": "<summary of the candidate's answer>",
      "star_score": {{
        "situation": <int 0-10>,
        "task": <int 0-10>,
        "action": <int 0-10>,
        "result": <int 0-10>
      }},
      "strengths": "<what the candidate did well>",
      "improvements": "<what the candidate could improve>"
    }}
  ],
  "top_strengths": ["<strength 1>", "<strength 2>"],
  "top_improvements": ["<improvement 1>", "<improvement 2>"]
}}

Score each STAR component 0-10. Be specific and constructive."""

    client = _get_client()
    response = await client.messages.create(
        model=_MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    return _parse_json(response.content[0].text, "evaluate_interview")
