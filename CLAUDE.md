# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

FastAPI Python backend for a multi-modal behavioral mock interview tool.
Stateless — all session data lives in memory. No database.

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then fill in ANTHROPIC_API_KEY and TAVILY_API_KEY
```

## Commands

| Task | Command |
|------|---------|
| Run all tests | `pytest` |
| Run a single test file | `pytest tests/test_session_store.py -v` |
| Run a single test | `pytest tests/test_session_store.py::test_create_session_returns_uuid_string -v` |
| Start dev server | `uvicorn app.main:app --reload` |

## Architecture

```
app/
  main.py              — FastAPI app, router registration
  session_store.py     — in-memory dict keyed by UUID session ID
  models/
    schemas.py         — Pydantic request/response models
  routers/
    session.py         — POST /session/start, /respond, /end
  services/
    resume_parser.py   — pdfplumber PDF text extraction
    scraper.py         — Tavily API company/interviewer context
    llm.py             — Anthropic Claude API calls
```

Data flow: client → router → services (resume_parser, scraper, llm) → session_store → response

## TODOs

- codify interview rating criteria
