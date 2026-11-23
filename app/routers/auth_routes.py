from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.auth import hash_password, verify_password
from app.db import get_db


router = APIRouter(prefix="/auth", tags=["authentication"])


class Credentials(BaseModel):
    username: str
    password: str


@router.post("/register")
def register(credentials: Credentials):
    with get_db() as connection:
        try:
            connection.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (credentials.username, hash_password(credentials.password)),
            )
        except Exception as exc:
            raise HTTPException(status_code=409, detail="Username already exists") from exc
    return {"username": credentials.username}


@router.post("/login")
def login(credentials: Credentials):
    with get_db() as connection:
        row = connection.execute(
            "SELECT password_hash FROM users WHERE username = ?",
            (credentials.username,),
        ).fetchone()
    if not row or not verify_password(credentials.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"authenticated": True, "username": credentials.username}