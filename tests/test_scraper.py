"""Tests for the Tavily web scraper service."""
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock
from app.services.scraper import scrape_company, scrape_interviewer


def _mock_tavily(mocker, results):
    """Patch httpx.AsyncClient.post to return a fake Tavily response."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"results": results}
    mocker.patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_response))
    return mock_response


# ---------------------------------------------------------------------------
# scrape_company
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scrape_company_returns_context_string(mocker):
    """Returns joined content from Tavily results."""
    _mock_tavily(mocker, [{"content": "Google values innovation."}, {"content": "Great culture."}])
    result = await scrape_company("Google", "Software Engineer")
    assert "Google values innovation." in result
    assert "Great culture." in result


@pytest.mark.asyncio
async def test_scrape_company_includes_role_in_query(mocker):
    """The Tavily query includes the role string."""
    mock_post = _mock_tavily(mocker, [{"content": "info"}])
    await scrape_company("Google", "Software Engineer")
    call_kwargs = mock_post.json.call_args  # we check the POST body instead
    posted = httpx.AsyncClient.post.call_args
    body = posted.kwargs.get("json") or posted.args[1] if posted.args else posted.kwargs["json"]
    assert "Software Engineer" in body["query"]
    assert "Google" in body["query"]


@pytest.mark.asyncio
async def test_scrape_company_returns_empty_for_none_input(mocker):
    """Returns empty string without making an HTTP call when company is None."""
    mock_post = mocker.patch("httpx.AsyncClient.post", new=AsyncMock())
    result = await scrape_company(None, "Software Engineer")
    assert result == ""
    mock_post.assert_not_called()


@pytest.mark.asyncio
async def test_scrape_company_returns_empty_for_empty_string(mocker):
    """Returns empty string without making an HTTP call when company is empty."""
    mock_post = mocker.patch("httpx.AsyncClient.post", new=AsyncMock())
    result = await scrape_company("", "Software Engineer")
    assert result == ""
    mock_post.assert_not_called()


@pytest.mark.asyncio
async def test_scrape_company_returns_empty_when_no_results(mocker):
    """Returns empty string when Tavily returns an empty results list."""
    _mock_tavily(mocker, [])
    result = await scrape_company("Google", "Software Engineer")
    assert result == ""


@pytest.mark.asyncio
async def test_scrape_company_raises_on_http_error(mocker):
    """Propagates httpx.HTTPStatusError when Tavily returns an error status."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "error", request=MagicMock(), response=MagicMock()
    )
    mocker.patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_response))
    with pytest.raises(httpx.HTTPStatusError):
        await scrape_company("Google", "Software Engineer")


# ---------------------------------------------------------------------------
# scrape_interviewer
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scrape_interviewer_returns_context_string(mocker):
    """Returns joined content from Tavily results for interviewer lookup."""
    _mock_tavily(mocker, [{"content": "Sarah Chen is a senior engineer at Google."}])
    result = await scrape_interviewer("Sarah Chen", "Google")
    assert "Sarah Chen is a senior engineer" in result


@pytest.mark.asyncio
async def test_scrape_interviewer_returns_empty_for_none_input(mocker):
    """Returns empty string without HTTP call when interviewer is None."""
    mock_post = mocker.patch("httpx.AsyncClient.post", new=AsyncMock())
    result = await scrape_interviewer(None, "Google")
    assert result == ""
    mock_post.assert_not_called()
