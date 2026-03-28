"""Resume parsing service.

Extracts plain text from a PDF supplied as raw bytes.
The bytes are never written to disk.
"""
import io
import pdfplumber


def parse_resume(file_bytes: bytes) -> str:
    """Extract plain text from PDF bytes using pdfplumber.

    Args:
        file_bytes: Raw bytes of the uploaded PDF file.

    Returns:
        Extracted text with pages joined by double newlines.

    Raises:
        ValueError: If bytes are empty, the file cannot be parsed,
                    or no text can be extracted.
    """
    if not file_bytes:
        raise ValueError("Cannot parse empty bytes")

    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            page_texts = [page.extract_text() for page in pdf.pages]
    except Exception as exc:
        raise ValueError(f"Could not parse PDF: {exc}") from exc

    text = "\n\n".join(t for t in page_texts if t)
    if not text.strip():
        raise ValueError("No text could be extracted from the PDF")

    return text
