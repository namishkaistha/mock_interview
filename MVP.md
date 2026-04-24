# AI Mock Interview Tool — Backend MVP
## Claude Code Project Prompt

---

### Project Overview

You are building the Python FastAPI backend for a multi-modal behavioral mock interview tool. The system is stateless (no database) — all session data lives in memory for the duration of a single interview and is discarded afterward.

---

### Tech Stack

| Layer | Tool |
|---|---|
| API framework | FastAPI (Python) |
| Resume parsing | pdfplumber (in memory — never written to disk) |
| LLM | Anthropic Claude API (question gen, interviewer responses, evaluation) |
| Web scraping | Tavily API (company + interviewer context) |
| HTTP client | httpx (async) |
| Config | python-dotenv |

---

### Core Concept

The user provides their resume, target role, company (optional), and interviewer name (optional). The backend uses this to generate a fully personalized 15-minute behavioral interview broken into three stages:

- `intro` **(5 min)** — AI interviewer introduces itself, sets expectations, light warmup questions
- `questions` **(10 min)** — 4–5 STAR-format behavioral questions tailored to the role, company, and resume
- `open_qa` **(5 min)** — User asks the AI interviewer questions; AI responds in character

All session state is stored in a Python dict keyed by a UUID session ID. There is no persistence layer.

---

### Goal #1: Build the Following Endpoints

#### `POST /session/start`

- Accepts multipart form data: `resume` (PDF file upload), `role` (str), `company` (str, optional), `interviewer` (str, optional)
- Parses the resume in memory using pdfplumber (extract raw text, never save to disk)
- Uses Tavily to web scrape:
  - Company culture, values, recent news (if company provided)
  - Interviewer background, LinkedIn-style info (if interviewer provided)
- Sends resume text + scraped context to Claude to generate:
  - A brief AI interviewer persona (name, tone, style — influenced by real interviewer if provided)
  - 4–5 tailored STAR behavioral questions
  - A short intro script for the AI interviewer to open with
- Stores all of this in an in-memory session dict under a new UUID
- Returns: `session_id`, `stage: "intro"`, `interviewer_persona`, `intro_message`

---

#### `POST /session/{session_id}/respond`

- Accepts: `user_input` (str — typed or transcribed from dictation), `stage` (str)
- Looks up the session by ID
- Based on current stage:
  - `intro` — AI responds conversationally, advances to `questions` after 2 exchanges
  - `questions` — AI asks the next prepared question, handles follow-ups contextually, advances to `open_qa` after all questions are done
  - `open_qa` — AI answers user questions in character as the interviewer
- Appends each exchange to the session transcript
- Returns: `ai_message`, `stage` (current or newly transitioned), `question_index` (if in questions stage), `interview_complete` (bool)

---

#### `POST /session/{session_id}/end`

- Accepts: `session_id`
- Takes the full transcript from memory
- Sends to Claude for evaluation using the STAR framework
- Returns a structured JSON feedback report:

```json
{
  "overall_score": 7.5,
  "summary": "...",
  "question_feedback": [
    {
      "question": "...",
      "user_answer": "...",
      "star_score": {
        "situation": 8,
        "task": 7,
        "action": 9,
        "result": 6
      },
      "strengths": "...",
      "improvements": "..."
    }
  ],
  "top_strengths": ["...", "..."],
  "top_improvements": ["...", "..."]
}
```

---

### Project Structure

Scaffold and fully implement every file in this structure:

```
/app
  main.py
  /routers
    session.py
  /services
    llm.py
    scraper.py
    resume_parser.py
  /models
    schemas.py
  session_store.py
requirements.txt
.env.example
```

---

### Additional Requirements

- All Claude calls should use `claude-sonnet-4-5`
- Use `httpx` for all async HTTP calls
- Include a `.env.example` with: `ANTHROPIC_API_KEY`, `TAVILY_API_KEY`
- Include a fully populated `requirements.txt`
- Add docstrings to all functions
- Do **not** add auth, rate limiting, or a database — this is a stateless MVP
- Do **not** leave placeholder comments — write complete, working code for every file

---

### Instructions

Start by scaffolding the full project structure, then implement each file completely from top to bottom. Every file should be production-ready and runnable.

---

> **🗒️ Note for developer (not instructions for Claude Code):** Once the initial wiring is done, revisit the following before moving on:
>
> - **Evaluation rubric** — replace freeform LLM scoring with an explicit rubric-based prompt for each STAR component, with defined criteria per score band. Consider a multi-pass approach: first extract what the user said per STAR component, then score against the rubric in a second pass for consistency.
> - **PDF generation** — convert the JSON feedback report into a formatted 1-page PDF streamed back to the user
> - **Voice integration** — ElevenLabs or OpenAI TTS for the AI interviewer voice output
> - **User accounts + history** — add Supabase for auth, session persistence, and interview history dashboard
