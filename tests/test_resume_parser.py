"""Tests for the resume parser service."""
import pytest
from unittest.mock import MagicMock
from app.services.resume_parser import parse_resume


def _make_mock_pdf(mocker, page_texts):
    """Helper: patch pdfplumber.open with pages returning given texts."""
    mock_pages = []
    for text in page_texts:
        page = MagicMock()
        page.extract_text.return_value = text
        mock_pages.append(page)

    mock_pdf = MagicMock()
    mock_pdf.pages = mock_pages
    mock_pdf.__enter__ = lambda s: mock_pdf
    mock_pdf.__exit__ = MagicMock(return_value=False)
    mocker.patch("pdfplumber.open", return_value=mock_pdf)
    return mock_pdf


def test_parse_resume_returns_text_for_single_page(mocker):
    """Single-page PDF returns the extracted text."""
    _make_mock_pdf(mocker, ["Jane Doe\nSoftware Engineer"])
    result = parse_resume(b"%PDF-fake-bytes")
    assert "Jane Doe" in result
    assert "Software Engineer" in result


def test_parse_resume_concatenates_multiple_pages(mocker):
    """Multi-page PDF returns text from all pages joined together."""
    _make_mock_pdf(mocker, ["Page one content", "Page two content"])
    result = parse_resume(b"%PDF-fake-bytes")
    assert "Page one content" in result
    assert "Page two content" in result


def test_parse_resume_raises_on_empty_bytes():
    """Empty bytes raises ValueError before attempting to open."""
    with pytest.raises(ValueError, match="empty"):
        parse_resume(b"")


def test_parse_resume_raises_on_non_pdf_bytes(mocker):
    """Corrupt/non-PDF bytes cause pdfplumber to raise, which is re-raised as ValueError."""
    mocker.patch("pdfplumber.open", side_effect=Exception("not a pdf"))
    with pytest.raises(ValueError, match="Could not parse"):
        parse_resume(b"not a pdf")


def test_parse_resume_raises_when_no_text_extracted(mocker):
    """PDF where all pages return no text raises ValueError."""
    _make_mock_pdf(mocker, [None, None])
    with pytest.raises(ValueError, match="No text"):
        parse_resume(b"%PDF-fake-bytes")
