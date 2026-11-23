from datetime import date

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel

from app.auth import get_current_user
from app.db import (
    calculate_refill_schedule,
    get_db,
    get_medication,
    list_medications,
    save_medications,
)
from app.parsers.doc_parser import parse_prescription_document


router = APIRouter(tags=["prescriptions"])


class ConfirmRequest(BaseModel):
    medications: list[dict]


class RefillRequest(BaseModel):
    quantity: int
    doses_per_day: int = 1
    refills: int = 0
    start_date: str | None = None


class ReminderRequest(BaseModel):
    medication_id: int
    remind_at: str
    enabled: bool = True


async def _parse_pdf(file: UploadFile):
    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Only PDF prescription uploads are supported")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Prescription PDF is empty")
    try:
        return parse_prescription_document(content, filename)
    except (UnicodeDecodeError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/upload-pdf/")
async def upload_pdf(file: UploadFile, user=Depends(get_current_user)):
    medications = await _parse_pdf(file)
    return {"medications": medications}


@router.post("/upload-image/")
async def upload_image(file: UploadFile, user=Depends(get_current_user)):
    filename = file.filename or ""
    if not filename.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp")):
        raise HTTPException(status_code=415, detail="Unsupported prescription image type")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Prescription image is empty")
    try:
        medications = parse_prescription_document(content, filename)
    except (UnicodeDecodeError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"medications": medications}


@router.post("/prescriptions/parse")
async def parse_prescription(file: UploadFile, user=Depends(get_current_user)):
    return await upload_pdf(file, user)


@router.post("/medications/confirm/")
async def confirm_medications(request: ConfirmRequest, user=Depends(get_current_user)):
    today = date.today().isoformat()
    confirmed = [{**medication, "start_date": today} for medication in request.medications]
    saved = save_medications(confirmed)
    return {"medications": saved}


@router.post("/prescriptions/confirm")
async def confirm_prescriptions_compat(request: ConfirmRequest, user=Depends(get_current_user)):
    return await confirm_medications(request, user)


@router.get("/medications/")
def medications_list(user=Depends(get_current_user)):
    return {"medications": list_medications()}


@router.get("/prescriptions")
def prescriptions_list(user=Depends(get_current_user)):
    return {"medications": list_medications()}


@router.get("/medications/{medication_id}/refills/")
def medication_refills(medication_id: int, user=Depends(get_current_user)):
    medication = get_medication(medication_id)
    if not medication:
        raise HTTPException(status_code=404, detail="Medication not found")
    try:
        quantity = int(medication.get("quantity") or 0)
        doses_per_day = int(medication.get("doses_per_day") or 1)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Medication refill information is incomplete")
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Medication quantity is required")
    return calculate_refill_schedule(
        medication["start_date"] or date.today().isoformat(),
        quantity,
        doses_per_day,
        medication.get("refills", 0),
    )


@router.post("/medications/refills/calculate/")
def calculate_medication_refills(request: RefillRequest, user=Depends(get_current_user)):
    try:
        return calculate_refill_schedule(
            request.start_date or date.today().isoformat(),
            request.quantity,
            request.doses_per_day,
            request.refills,
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/prescriptions/{prescription_id}/refills")
def prescription_refills(prescription_id: int, user=Depends(get_current_user)):
    return medication_refills(prescription_id, user)


@router.post("/reminders/check/")
def check_reminders(user=Depends(get_current_user)):
    reminders = []
    with get_db() as connection:
        rows = connection.execute(
            """
            SELECT r.id, r.medication_id, r.remind_at, r.enabled,
                   m.name, m.start_date
            FROM reminders r
            JOIN medications m ON m.id = r.medication_id
            WHERE r.enabled = 1
            """
        ).fetchall()
        reminders = [dict(row) for row in rows]
    today = date.today().isoformat()
    due = [reminder for reminder in reminders if reminder["remind_at"] <= today]
    return {"due": due, "reminders": reminders}


@router.post("/reminders/")
def create_reminder(request: ReminderRequest, user=Depends(get_current_user)):
    if not get_medication(request.medication_id):
        raise HTTPException(status_code=404, detail="Medication not found")
    with get_db() as connection:
        cursor = connection.execute(
            "INSERT INTO reminders (medication_id, remind_at, enabled) VALUES (?, ?, ?)",
            (request.medication_id, request.remind_at, int(request.enabled)),
        )
    return {
        "id": cursor.lastrowid,
        "medication_id": request.medication_id,
        "remind_at": request.remind_at,
        "enabled": request.enabled,
    }