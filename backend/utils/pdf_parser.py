# ============================================================
# utils/pdf_parser.py — PDF Text Extraction Utility (Phase-3)
# Downloads file from a URL and extracts text using PyPDF2
# ============================================================

import io
import requests


def extract_text(file_url):
    """
    Download a file from a URL and extract text content.
    
    Supports:
      - PDF files (via PyPDF2)
      - Plain text files (returned as-is)
    
    Args:
        file_url (str): Public URL of the file (from Supabase Storage).
    
    Returns:
        str: Extracted plain text.
    
    Raises:
        ValueError: If the URL is empty or the file cannot be downloaded.
    """
    if not file_url or not file_url.strip():
        raise ValueError("No file URL provided.")

    # Download the file
    try:
        resp = requests.get(file_url, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise ValueError(f"Failed to download file: {e}")

    content = resp.content
    content_type = resp.headers.get("Content-Type", "").lower()

    # Determine file type
    is_pdf = (
        "application/pdf" in content_type
        or file_url.lower().endswith(".pdf")
        or content[:5] == b"%PDF-"
    )

    if is_pdf:
        return _extract_from_pdf(content)
    else:
        # Treat as plain text
        try:
            return content.decode("utf-8", errors="replace")
        except Exception:
            return content.decode("latin-1", errors="replace")


def _extract_from_pdf(pdf_bytes):
    """Extract text from PDF bytes using PyPDF2."""
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        raise ImportError(
            "PyPDF2 is required for PDF text extraction. "
            "Install it with: pip install PyPDF2"
        )

    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages_text = []

    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text()
        if text and text.strip():
            pages_text.append(text.strip())

    if not pages_text:
        raise ValueError(
            "Could not extract any text from the PDF. "
            "The file may be scanned/image-based or empty."
        )

    return "\n\n".join(pages_text)
