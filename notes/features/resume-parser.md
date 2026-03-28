# Feature: resume-parser

## Goal
Extract plain text from a PDF resume uploaded as bytes.
pdfplumber is used in-memory — bytes are never written to disk.

## Public API
`parse_resume(file_bytes: bytes) -> str`

## Boundary value analysis

| Input | Expected |
|-------|----------|
| Valid single-page PDF | Extracted text string |
| Valid multi-page PDF | Pages concatenated with newline |
| `b""` (empty) | raises `ValueError` |
| Non-PDF bytes | raises `ValueError` (pdfplumber raises on open) |
| PDF with no extractable text | raises `ValueError` |

## Key decisions
- Raise `ValueError` (not HTTP exceptions) — the router will catch and return 400
- Pages joined with `\n\n` for readability
- pdfplumber.open patched in tests — no real PDF files needed
