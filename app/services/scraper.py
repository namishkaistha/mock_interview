"""Web scraping service using the Tavily Search API.

Fetches context about a target company and/or interviewer to personalise
the AI-generated interview questions.
"""
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

_TAVILY_URL = "https://api.tavily.com/search"


async def scrape_company(company: str, role: str) -> str:
    """Fetch company culture, values, and interview process context via Tavily.

    Args:
        company: Name of the target company.
        role: Role the candidate is interviewing for (used to focus the query).

    Returns:
        Joined content string from Tavily results, or empty string if company
        is None/empty.

    Raises:
        httpx.HTTPStatusError: If the Tavily API returns an error status.
    """
    if not company:
        return ""

    query = f"{role} interviews at {company} - culture values interview process"
    return await _search(query)


async def scrape_interviewer(interviewer: str, company: str) -> str:
    """Fetch background and LinkedIn-style info about the interviewer via Tavily.

    Args:
        interviewer: Full name of the interviewer.
        company: Company the interviewer works at (strongest locator signal).
                 Falls back to name-only query if empty.

    Returns:
        Joined content string from Tavily results, or empty string if interviewer
        is None/empty.

    Raises:
        httpx.HTTPStatusError: If the Tavily API returns an error status.
    """
    if not interviewer:
        return ""

    if company:
        query = f"{interviewer} {company} interviewer background"
    else:
        query = f"{interviewer} interviewer background"

    return await _search(query)


async def _search(query: str) -> str:
    """Execute a Tavily search and return joined content from results.

    Args:
        query: The search query string.

    Returns:
        Content from all results joined by double newlines, or empty string
        if no results are returned.

    Raises:
        httpx.HTTPStatusError: If the Tavily API returns an error status.
    """
    api_key = os.getenv("TAVILY_API_KEY", "")
    payload = {"api_key": api_key, "query": query, "search_depth": "basic"}

    async with httpx.AsyncClient() as client:
        response = await client.post(_TAVILY_URL, json=payload)
        response.raise_for_status()

    results = response.json().get("results", [])
    return "\n\n".join(r["content"] for r in results if r.get("content"))
