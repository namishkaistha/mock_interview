# Feature: scraper

## Goal
Fetch web context about the target company and interviewer via Tavily Search API
to personalise interview questions.

## Public API
- `scrape_company(company: str, role: str) -> str`
- `scrape_interviewer(interviewer: str, company: str) -> str`

Both are async (called from async FastAPI endpoints via httpx).

## Query design
- company: `"{role} interviews at {company} - culture values interview process"`
- interviewer: `"{interviewer} {company} interviewer background"` (falls back to
  `"{interviewer} interviewer background"` when company is empty)

`role` is used for company query (what's the culture like for THIS role).
`company` is used for interviewer query (strongest signal to find the right person).

## Boundary value analysis

| Input | Expected |
|-------|----------|
| Valid company + role | Joined content string from Tavily results |
| Valid interviewer + company | Joined content string from Tavily results |
| None/empty company | `""` immediately, no HTTP call |
| None/empty interviewer | `""` immediately, no HTTP call |
| Tavily returns no results | `""` |
| Tavily HTTP error | raises `httpx.HTTPStatusError` |

## Key decisions
- `role` arg on company scrape (not interviewer) — directly relevant to culture query
- `company` arg on interviewer scrape (not role) — best locator for real person
- Tavily results concatenated with `\n\n`
- API key from env: `TAVILY_API_KEY`
