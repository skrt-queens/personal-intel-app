import json
import sqlite3
from contextlib import contextmanager
from datetime import date, timedelta
from math import ceil

from app.config import settings


def init_db() -> None:
    with get_db() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS medications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                dosage TEXT,
                frequency TEXT,
                route TEXT,
                duration TEXT,
                instructions TEXT,
                quantity TEXT,
                refills INTEGER DEFAULT 0,
                doses_per_day INTEGER DEFAULT 1,
                start_date TEXT,
                user_id INTEGER
            );
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                medication_id INTEGER NOT NULL,
                remind_at TEXT NOT NULL,
                enabled INTEGER DEFAULT 1
            );
            """
        )
        medication_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(medications)").fetchall()
        }
        if "doses_per_day" not in medication_columns:
            connection.execute(
                "ALTER TABLE medications ADD COLUMN doses_per_day INTEGER DEFAULT 1"
            )


@contextmanager
def get_db():
    connection = sqlite3.connect(settings.database_path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def list_medications() -> list[dict]:
    with get_db() as connection:
        rows = connection.execute("SELECT * FROM medications ORDER BY id DESC").fetchall()
    return [dict(row) for row in rows]


def save_medications(medications: list[dict]) -> list[dict]:
    saved = []
    with get_db() as connection:
        for medication in medications:
            cursor = connection.execute(
                """
                INSERT INTO medications
                (name, dosage, frequency, route, duration, instructions, quantity, refills, doses_per_day, start_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    medication["name"],
                    medication.get("dosage", ""),
                    medication.get("frequency", ""),
                    medication.get("route", ""),
                    medication.get("duration", ""),
                    medication.get("instructions", ""),
                    medication.get("quantity", ""),
                    medication.get("refills", 0),
                    medication.get("doses_per_day", 1),
                    medication.get("start_date", date.today().isoformat()),
                ),
            )
            saved.append({"id": cursor.lastrowid, **medication})
    return saved


def get_medication(medication_id: int) -> dict | None:
    with get_db() as connection:
        row = connection.execute(
            "SELECT * FROM medications WHERE id = ?", (medication_id,)
        ).fetchone()
    return dict(row) if row else None


def calculate_refill_schedule(
    start_date: str | date,
    quantity: int | str,
    doses_per_day: int | str = 1,
    refills: int = 0,
) -> dict:
    start = date.fromisoformat(str(start_date)) if not isinstance(start_date, date) else start_date
    supplied = int(quantity)
    daily = int(doses_per_day)
    if supplied < 0 or daily < 1:
        raise ValueError("Quantity and doses per day must be positive")
    days_supply = max(1, ceil(supplied / daily))
    return {
        "days_supply": days_supply,
        "next_refill_date": (start + timedelta(days=days_supply)).isoformat(),
        "remaining_refills": max(0, refills),
    }


init_db()