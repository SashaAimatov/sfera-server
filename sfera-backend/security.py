import hashlib
import secrets
from typing import Optional

from fastapi import HTTPException

from database import get_db


def hash_password(password: str, salt: Optional[str] = None) -> str:
    salt = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"{salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, _ = stored.split("$", 1)
    except ValueError:
        return False
    return secrets.compare_digest(hash_password(password, salt), stored)


def extract_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization.split(" ", 1)[1].strip()


def get_optional_user(authorization: Optional[str]) -> Optional[dict]:
    token = extract_token(authorization)
    if not token:
        return None
    conn = get_db()
    user = conn.execute(
        "SELECT id, email, username, display_name, bio, created_at FROM users WHERE token = ?",
        (token,),
    ).fetchone()
    conn.close()
    return dict(user) if user else None


def get_current_user(authorization: Optional[str]) -> dict:
    user = get_optional_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    return user
