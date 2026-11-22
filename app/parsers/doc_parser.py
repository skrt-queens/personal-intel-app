import re
from datetime import date


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
) -> list[dict[str, str]]:
    """Extract likely medication entries from prescription text."""
    if not text:
        return []

    start_date = confirmation_date or date.today()
    if isinstance(start_date, date):
        start_date = start_date.isoformat()

    medications: list[dict[str, str]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = MEDICATION_LINE.match(line)
        if not match:
            continue

        name = match.group("name").strip()
        dosage = match.group("dosage").strip()
        rest = (match.group("rest") or "").strip()
        frequency_match = FREQUENCY_PATTERN.search(rest)
        route_match = ROUTE_PATTERN.search(rest)
        medications.append({
            "name": name,
            "dosage": dosage,
            "frequency": frequency_match.group(0).strip() if frequency_match else "",
            "route": route_match.group(0).strip() if route_match else "",
            "duration": "",
            "instructions": rest,
            "start_date": str(start_date),
        })
    return medications


def parse_prescription_document(
    content: bytes,
    filename: str,
    *,
    confirmation_date: date | str | None = None,
) -> list[dict[str, str]]:
    """Parse text-based prescription files; document binary formats require prior OCR/text extraction."""
    name = filename.lower()
    if name.endswith(".csv"):
        from .csv_parser import parse_prescription_csv
        return parse_prescription_csv(content, confirmation_date=confirmation_date)
    if name.endswith(".txt") or name.endswith(".md"):
        return parse_prescription_text(
            content.decode("utf-8-sig"),
            confirmation_date=confirmation_date,
        )
    raise ValueError("Unsupported prescription file type")


parse_document = parse_prescription_document
parse_doc = parse_prescription_document