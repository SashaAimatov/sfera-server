import secrets
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException

from database import get_db, hash_password, now_iso, verify_password
from models import LoginReq, RegisterReq, UpdateProfileReq
from security import require_user, user_public_dict

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/register")
def register(req: RegisterReq):
    uname = req.username.strip().lstrip("@").lower()
    email = req.email.strip().lower()
    dname = (req.display_name or uname).strip()

    if len(uname) < 3 or len(uname) > 24:
        raise HTTPException(status_code=400, detail="Юзернейм должен быть от 3 до 24 символов")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Пароль должен быть не короче 6 символов")

    conn = get_db()
    if conn.execute("SELECT 1 FROM users WHERE username = ? OR email = ?", (uname, email)).fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Юзернейм или email уже заняты")

    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (username, email, password_hash, display_name, created_at) VALUES (?, ?, ?, ?, ?)",
        (uname, email, hash_password(req.password), dname, now_iso()),
    )
    uid = cur.lastrowid
    token = secrets.token_urlsafe(32)
    cur.execute("INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)", (token, uid, now_iso()))
    conn.commit()
    u = dict(cur.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone())
    pub = user_public_dict(conn, u, uid)
    conn.close()
    return {"token": token, "user": pub}


@router.post("/login")
def login(req: LoginReq):
    ident = req.login.strip().lstrip("@").lower()
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE username = ? OR email = ?", (ident, ident)).fetchone()
    if not row or not verify_password(req.password, row["password_hash"]):
        conn.close()
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")

    token = secrets.token_urlsafe(32)
    conn.execute("INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)", (token, row["id"], now_iso()))
    conn.commit()
    pub = user_public_dict(conn, dict(row), row["id"])
    conn.close()
    return {"token": token, "user": pub}


@router.post("/logout")
def logout(authorization: Optional[str] = Header(default=None)):
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()
        conn = get_db()
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        conn.close()
    return {"status": "ok"}


@router.get("/me")
def get_me(user=Depends(require_user)):
    conn = get_db()
    pub = user_public_dict(conn, user, user["id"])
    conn.close()
    return {"user": pub}


@router.patch("/me")
def update_me(req: UpdateProfileReq, user=Depends(require_user)):
    conn = get_db()
    conn.execute(
        "UPDATE users SET display_name = ?, bio = ?, avatar_color = COALESCE(?, avatar_color), banner_style = COALESCE(?, banner_style) WHERE id = ?",
        (req.display_name.strip()[:50], (req.bio or "").strip()[:200], req.avatar_color, req.banner_style, user["id"]),
    )
    conn.commit()
    updated = dict(conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone())
    pub = user_public_dict(conn, updated, user["id"])
    conn.close()
    return {"user": pub}
