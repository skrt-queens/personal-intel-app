import asyncio
from datetime import date

from app.parsers.csv_parser import parse_prescription_csv
from app.parsers.doc_parser import parse_prescription_text
from app.routers.upload_routes import ConfirmRequest, confirm_medications


def test_csv_parser_sets_confirmation_date():
    csv_text = "medication,dosage,frequency,route\nMetformin,500 mg,BID,oral\n"

    medications = parse_prescription_csv(
        csv_text,
        confirmation_date=date(2026, 11, 22),
    )

    assert medications == [{
        "name": "Metformin",
        "dosage": "500 mg",
        "frequency": "BID",
        "route": "oral",
        "duration": "",
        "start_date": "2026-11-22",
    }]


def test_text_parser_extracts_medication_and_defaults_to_today():
    medications = parse_prescription_text(
        "Lisinopril 10 mg once daily oral",
        confirmation_date=date(2026, 11, 22),
    )

    assert len(medications) == 1
    assert medications[0]["name"] == "Lisinopril"
    assert medications[0]["dosage"] == "10 mg"
    assert medications[0]["frequency"] == "once daily"
    assert medications[0]["route"] == "oral"
    assert medications[0]["start_date"] == "2026-11-22"


def test_confirmation_overrides_start_date_with_today(monkeypatch):
    monkeypatch.setattr(
        "app.routers.upload_routes.date",
        type(
            "FixedDate",
            (date,),
            {"today": classmethod(lambda cls: cls(2026, 11, 22))},
        ),
    )
    request = ConfirmRequest(medications=[{
        "name": "Metformin",
        "start_date": "2020-01-01",
    }])

    response = asyncio.run(confirm_medications(request))

    assert response["medications"][0]["start_date"] == "2026-11-22"
