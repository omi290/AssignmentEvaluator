# ============================================================
# utils/pdf_parser.py — Text Extraction Utility (Phase-6 OCR)
# Downloads file from a URL and extracts text.
# Pipeline:
#   1. PyPDF2 digital text extraction (fast)
#   2. OCR fallback via pytesseract + pdf2image (for scans)
#   3. Direct image OCR for .jpg/.png uploads
# ============================================================

import io
import os
import requests


def _sanitize_text(text):
    """Remove NUL (0x00) characters that break PostgreSQL string literals."""
    if not text:
        return text
    return text.replace("\x00", "")


# ── OCR availability check ──────────────────────────────────

_OCR_AVAILABLE = False
try:
    import pytesseract
    from PIL import Image
    _OCR_AVAILABLE = True
except ImportError:
    pass

_PDF2IMAGE_AVAILABLE = False
try:
    from pdf2image import convert_from_bytes
    _PDF2IMAGE_AVAILABLE = True
except ImportError:
    pass


# ── Public API ──────────────────────────────────────────────

def extract_text(file_url):
    """
    Download a file from a URL and extract text content.

    Supports:
      - PDF files (digital text via PyPDF2, scanned via OCR)
      - Image files (.jpg, .jpeg, .png) via OCR
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
    url_lower = file_url.lower().split("?")[0]  # strip query params

    # ── Route 1: Image files → direct OCR ──
    is_image = (
        "image/" in content_type
        or url_lower.endswith((".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"))
    )
    if is_image:
        return _sanitize_text(_extract_from_image(content))

    # ── Route 2: PDF files → PyPDF2 then OCR fallback ──
    is_pdf = (
        "application/pdf" in content_type
        or url_lower.endswith(".pdf")
        or content[:5] == b"%PDF-"
    )
    if is_pdf:
        return _sanitize_text(_extract_from_pdf(content))

    # ── Route 3: Plain text ──
    try:
        return _sanitize_text(content.decode("utf-8", errors="replace"))
    except Exception:
        return _sanitize_text(content.decode("latin-1", errors="replace"))


# ── PDF extraction (digital + OCR fallback) ─────────────────

def _extract_from_pdf(pdf_bytes):
    """
    Extract text from PDF bytes.
    Step 1: Try PyPDF2 for digitally-created PDFs.
    Step 2: If very little text found, try OCR on each page image.
    """
    # Step 1: PyPDF2
    digital_text = _pyppdf2_extract(pdf_bytes)

    # If we got a reasonable amount of text, return it
    if digital_text and len(digital_text.split()) >= 20:
        return digital_text

    # Step 2: OCR fallback (for scanned / image-based PDFs)
    ocr_text = _ocr_pdf_extract(pdf_bytes)

    if ocr_text and ocr_text.strip():
        return ocr_text

    # If OCR also failed but we had some digital text, return what we have
    if digital_text and digital_text.strip():
        return digital_text

    raise ValueError(
        "Could not extract any text from the PDF. "
        "The file may be empty or in an unsupported format. "
        + ("" if _OCR_AVAILABLE else "(OCR libraries not installed — install pytesseract and pdf2image for scanned PDF support.)")
    )


def _pyppdf2_extract(pdf_bytes):
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

    for page in reader.pages:
        text = page.extract_text()
        if text and text.strip():
            pages_text.append(text.strip())

    return "\n\n".join(pages_text) if pages_text else ""


def _ocr_pdf_extract(pdf_bytes):
    """
    Convert each PDF page to an image and run OCR.
    Requires: pytesseract, pdf2image, and system Tesseract binary.
    """
    if not _OCR_AVAILABLE or not _PDF2IMAGE_AVAILABLE:
        print("[pdf_parser.py] OCR libraries not available — skipping OCR fallback.")
        return ""

    try:
        # Convert PDF pages to images (300 DPI for decent OCR quality)
        images = convert_from_bytes(pdf_bytes, dpi=200, fmt="png")
    except Exception as e:
        print(f"[pdf_parser.py] pdf2image conversion failed: {e}")
        return ""

    pages_text = []
    for i, img in enumerate(images):
        try:
            text = pytesseract.image_to_string(img, lang="eng")
            if text and text.strip():
                pages_text.append(text.strip())
        except Exception as e:
            print(f"[pdf_parser.py] OCR failed on page {i + 1}: {e}")
            continue

    return "\n\n".join(pages_text) if pages_text else ""


# ── Image extraction (direct OCR) ──────────────────────────

def _extract_from_image(image_bytes):
    """
    Extract text from an image file using OCR.
    Supports: JPG, PNG, BMP, TIFF, WebP.
    """
    if not _OCR_AVAILABLE:
        raise ValueError(
            "Cannot extract text from images — pytesseract is not installed. "
            "Install it with: pip install pytesseract Pillow"
        )

    try:
        img = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(img, lang="eng")
    except Exception as e:
        raise ValueError(f"OCR failed on image: {e}")

    if not text or not text.strip():
        raise ValueError(
            "OCR could not extract any text from the image. "
            "The image may be too blurry, empty, or not contain readable text."
        )

    return text.strip()
