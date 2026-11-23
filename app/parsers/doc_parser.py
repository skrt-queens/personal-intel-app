import json
import re
import tempfile
from datetime import date
from io import BytesIO
from pathlib import Path

from app.config import settings


MEDICATION_LINE = re.compile(
    r"^\s*(?:[-*]\s*)?"
    r"(?P<name>[A-Za-z][A-Za-z0-9 .'-]{1,80}?)"
    r"\s+(?P<dosage>\d+(?:\.\d+)?(?:\s*(?:mg|mcg|g|ml|units?)))"
    r"(?:\s+(?P<rest>.+))?$",
    re.IGNORECASE,
)
FREQUENCY_PATTERN = re.compile(
    r"\b(?:twice daily|three times daily|once daily|once|twice|daily|"
    r"every \d+(?:-\d+)? hours?|q\d+h|bid|tid|qid|prn)\b",
    re.IGNORECASE,
)
ROUTE_PATTERN = re.compile(r"\b(?:oral|po|iv|im|subcutaneous|topical|inhaled)\b", re.IGNORECASE)


def parse_prescription_text(
    text: str,
    *,
    confirmation_date: date | str | None = None,
) -> list[dict]:
    start_date = (
        confirmation_date.isoformat()
        if isinstance(confirmation_date, date)
        else str(confirmation_date or date.today())
    )
    medications = []
    for raw_line in text.splitlines():
        match = MEDICATION_LINE.match(raw_line.strip())
        if not match:
            continue
        rest = (match.group("rest") or "").strip()
        frequency = FREQUENCY_PATTERN.search(rest)
        route = ROUTE_PATTERN.search(rest)
        medications.append({
            "name": match.group("name").strip(),
            "dosage": match.group("dosage").strip(),
            "frequency": frequency.group(0).strip() if frequency else "",
            "route": route.group(0).strip() if route else "",
            "duration": "",
            "instructions": rest,
            "start_date": start_date,
        })
    return medications


def extract_embedded_pdf_text(content: bytes) -> str:
    """Extract native embedded PDF text with pymupdf4llm. No OCR or image transmission."""
    try:
        import pymupdf4llm
    except ImportError as exc:
        raise RuntimeError("pymupdf4llm is required for PDF prescription parsing") from exc

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temporary:
        temporary.write(content)
        temporary_path = Path(temporary.name)
    try:
        markdown = pymupdf4llm.to_markdown(str(temporary_path))
    except Exception as exc:
        raise RuntimeError("Could not read the prescription PDF") from exc
    finally:
        temporary_path.unlink(missing_ok=True)
    return markdown.strip()


def extract_prescription_pdf_text(content: bytes) -> str:
    return extract_embedded_pdf_text(content)


def ocr_prescription_image(content: bytes) -> str:
    try:
        from PIL import Image
        import pytesseract
    except ImportError as exc:
        raise RuntimeError("Pillow and pytesseract are required for image OCR") from exc
    try:
        return pytesseract.image_to_string(Image.open(BytesIO(content)))
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError("Tesseract OCR executable was not found") from exc
    except Exception as exc:
        raise RuntimeError("Could not read the prescription image") from exc


def extract_medications_with_ollama(text: str) -> list[dict]:
    if len(text.strip()) < 20:
        raise ValueError("Prescription text contains fewer than 20 characters")
    try:
        import httpx
    except ImportError as exc:
        raise RuntimeError("httpx is required for Ollama extraction") from exc

    prompt = (
        "Extract every medication from this prescription. Return only a JSON array. "
        "Each object must contain name, dosage, frequency, route, duration, instructions, "
        "quantity, and refills as strings or numbers; use empty strings or 0 when unknown.\n\n"
        + text
    )
    try:
        response = httpx.post(
            f"{settings.ollama_base_url.rstrip('/')}/api/generate",
            json={
                "model": settings.ollama_model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
            },
            timeout=settings.ollama_timeout,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Could not reach Ollama at {settings.ollama_base_url}: {exc}") from exc

    raw = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        str(response.json().get("response", "")).strip(),
        flags=re.IGNORECASE,
    )
    try:
        items = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Ollama returned invalid medication JSON") from exc
    if not isinstance(items, list):
        raise RuntimeError("Ollama returned an unexpected medication response")
    return [item for item in items if isinstance(item, dict) and str(item.get("name", "")).strip()]


def parse_prescription_document(
    content: bytes,
    filename: str,
    *,
    confirmation_date: date | str | None = None,
) -> list[dict]:
    name = filename.lower()
    if name.endswith(".pdf"):
        text = extract_prescription_pdf_text(content)
    elif name.endswith((".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp")):
        text = ocr_prescription_image(content)
    else:
        raise ValueError("Only PDF and prescription image uploads are supported")

    if len(text.strip()) < 20:
        raise ValueError("Prescription text contains fewer than 20 characters")

    start_date = (
        confirmation_date.isoformat()
        if isinstance(confirmation_date, date)
        else str(confirmation_date or date.today())
    )
    return [
        {**item, "start_date": start_date}
        for item in extract_medications_with_ollama(text)
    ]


parse_pdf = parse_prescription_document


parse_document = parse_prescription_document
parse_doc = parse_prescription_document