# Feature: project-setup-and-schemas

## Goal
Scaffold the full project structure, install dependencies, and implement:
- Pydantic schemas (request/response models)
- In-memory session store (dict + helper functions)

## Key decisions
- Session store is a module-level dict keyed by UUID string
- Missing session raises KeyError → routers will catch and return 404
- Schemas use Optional fields for company/interviewer (not required)
- Stage is a Literal type: "intro" | "questions" | "open_qa"

## Test coverage targets
- session_store: create, get, delete, clear; KeyError on missing
- schemas: field validation, optional fields, stage literals
