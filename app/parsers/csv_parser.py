import csv
from datetime import date
from io import StringIO
from typing import Iterable, Mapping


FIELD_ALIASES = {
    "name": ("name", "medication", "drug", "medicine", "drug_name"),
    "dosage": ("dosage", "dose", "strength"),
    "frequency": ("frequency", "frequency_per_day", "schedule", "instructions"),
    "route": ("route", "administration_route"),
    "duration": ("duration", "days", "length"),
}


def _value(row: Mapping[str, object], aliases: Iterable[str]) -> str:
    normalized = {str(key).strip().lower().replace("-", "_"): value for key, value in row.items()}
    for alias in aliases:
        value = normalized.get(alias)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def parse_prescription_csv(
    source: str | bytes,
    *,
    confirmation_date: date | str | None = None,
) -> list[dict[str, str]]:
    """Parse medication rows from prescription CSV text or bytes."""
    if isinstance(source, bytes):
        source = source.decode("utf-8-sig")

    start_date = confirmation_date or date.today()
    if isinstance(start_date, date):
        start_date = start_date.isoformat()

    medications: list[dict[str, str]] = []
    for row in csv.DictReader(StringIO(source)):
        name = _value(row, FIELD_ALIASES["name"])
        if not name:
            continue
        medication = {
            "name": name,
            "dosage": _value(row, FIELD_ALIASES["dosage"]),
            "frequency": _value(row, FIELD_ALIASES["frequency"]),
            "route": _value(row, FIELD_ALIASES["route"]),
            "duration": _value(row, FIELD_ALIASES["duration"]),
            "start_date": str(start_date),
        }
        medications.append(medication)
    return medications


parse_csv = parse_prescription_csv