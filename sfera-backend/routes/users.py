from typing import Optional

from fastapi import APIRouter, Header, HTTPException

from database import get_db
from schemas import ProfileUpdateRequest
from security import get_current_user

router = APIRouter(prefix="/api", tags=["users"])


@router.get("/me")
def me(authorization: Optional[str] = Header(default=None)):
    return {"user": get_current_user(authorization)}


@router.patch("/me")
def update_me(data: ProfileUpdateRequest, authorization: Optional[str] = Header(default=None)):
    user = get_current_user(authorization)
    display_name = (
        data.display_name.strip() if data.display_name is not None else user["display_name"]
    )
    bio = data.bio.strip() if data.bio is not None else user["bio"]

    if not display_name:
        raise HTTPException(status_code=400, detail="Имя не может быть пустым")

    conn = get_db()
    conn.execute(
        "UPDATE users SET display_name = ?, bio = ? WHERE id = ?",
        (display_name, bio, user["id"]),
    )
    conn.commit()
    conn.close()

    user["display_name"] = display_name
    user["bio"] = bio
    return {"status": "ok", "user": user}


@router.get("/users/{username}")
def get_user_profile(username: str):
    clean = username.strip().lstrip("@").lower()
    conn = get_db()
    user = conn.execute(
        "SELECT id, username, display_name, bio, created_at FROM users WHERE username = ?",
        (clean,),
    ).fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    posts_count = conn.execute(
        "SELECT COUNT(*) FROM posts WHERE user_id = ?", (user["id"],)
    ).fetchone()[0]
    conn.close()

    profile = dict(user)
    profile["posts_count"] = posts_count
    return {"user": profile}
