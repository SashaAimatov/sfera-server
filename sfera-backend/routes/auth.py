import secrets
from typing import Optional

from fastapi import APIRouter, Header, HTTPException

from config import EMAIL_RE, RESERVED_USERNAMES, USERNAME_RE
from database import get_db, now_iso
from schemas import LoginRequest, RegisterRequest
from security import get_current_user, hash_password, verify_password

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/register")
def register(data: RegisterRequest):
    email = data.email.strip().lower()
    username = data.username.strip().lstrip("@").lower()
    display_name = (data.display_name or username).strip()[:50]

    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Некорректный формат почты")
    if not USERNAME_RE.match(username):
        raise HTTPException(
            status_code=400,
            detail="Username: от 3 до 24 символов (латиница, цифры и _)",
        )
    if username in RESERVED_USERNAMES:
        raise HTTPException(status_code=400, detail="Этот @username зарезервирован")
    if len(data.password) < 6:
        raise HTTPException(status_code=400, detail="Пароль должен быть не короче 6 символов")

    conn = get_db()
    cur = conn.cursor()
    exists = cur.execute(
        "SELECT id FROM users WHERE email = ? OR username = ?", (email, username)
    ).fetchone()
    if exists:
        conn.close()
        raise HTTPException(status_code=400, detail="Почта или @username уже заняты")

    token = secrets.token_urlsafe(32)
    created = now_iso()
    cur.execute(
        """
        INSERT INTO users (email, username, display_name, bio, password_hash, token, created_at)
        VALUES (?, ?, ?, '', ?, ?, ?)
        """,
        (email, username, display_name, hash_password(data.password), token, created),
    )
    user_id = cur.lastrowid
    conn.commit()
    conn.close()

    return {
        "status": "ok",
        "token": token,
        "user": {
            "id": user_id,
            "email": email,
            "username": username,
            "display_name": display_name,
            "bio": "",
            "created_at": created,
        },
    }


@router.post("/login")
def login(data: LoginRequest):
    ident = data.login.strip().lstrip("@").lower()
    conn = get_db()
    user = conn.execute(
        """
        SELECT id, email, username, display_name, bio, password_hash, created_at
        FROM users
        WHERE email = ? OR username = ?
        """,
        (ident, ident),
    ).fetchone()

    if not user or not verify_password(data.password, user["password_hash"]):
        conn.close()
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")

    token = secrets.token_urlsafe(32)
    conn.execute("UPDATE users SET token = ? WHERE id = ?", (token, user["id"]))
    conn.commit()
    conn.close()

    return {
        "status": "ok",
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "username": user["username"],
            "display_name": user["display_name"],
            "bio": user["bio"],
            "created_at": user["created_at"],
        },
    }


@router.post("/logout")
def logout(authorization: Optional[str] = Header(default=None)):
    user = get_current_user(authorization)
    conn = get_db()
    conn.execute("UPDATE users SET token = NULL WHERE id = ?", (user["id"],))
    conn.commit()
    conn.close()
    return {"status": "ok"}
