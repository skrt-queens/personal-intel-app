from datetime import date

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

from app.parsers.doc_parser import parse_prescription_document
from app.parsers.csv_parser import parse_prescription_csv


router = APIRouter(prefix="/prescriptions", tags=["prescriptions"])


class ParsedMedication(BaseModel):
    name: str
    dosage: str = ""
    frequency: str = ""
    route: str = ""
    duration: str = ""
    instructions: str = ""
    start_date: str


class ConfirmRequest(BaseModel):
    medications: list[dict]


@router.post("/parse")
async def parse_prescription(file: UploadFile):
    filename = file.filename or ""
    if not filename.lower().endswith((".csv", ".txt", ".md")):
        raise HTTPException(
            status_code=415,
            detail="Unsupported prescription file type. Upload CSV, TXT, or MD.",
        )
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Prescription file is empty")
    try:
        return parse_prescription_document(content, filename)
    except (UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/confirm")
async def confirm_medications(request: ConfirmRequest):
    """Confirm parsed medications and assign today's date to every medication."""
    confirmed = []
    today = date.today().isoformat()
    for medication in request.medications:
        confirmed.append({**medication, "start_date": today})
    return {"medications": confirmed}