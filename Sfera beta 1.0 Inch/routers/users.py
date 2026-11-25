from fastapi import APIRouter, Depends, HTTPException

from database import get_db, now_iso
from security import get_current_user_optional, require_user, user_public_dict

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/{username}")
def get_user_profile(username: str, viewer=Depends(get_current_user_optional)):
    uname = username.strip().lstrip("@").lower()
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (uname,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    pub = user_public_dict(conn, dict(row), viewer["id"] if viewer else None)
    conn.close()
    return {"user": pub}


@router.post("/{username}/follow")
def toggle_follow(username: str, user=Depends(require_user)):
    uname = username.strip().lstrip("@").lower()
    conn = get_db()
    target = conn.execute("SELECT id FROM users WHERE username = ?", (uname,)).fetchone()
    if not target:
        conn.close()
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if target["id"] == user["id"]:
        conn.close()
        raise HTTPException(status_code=400, detail="Нельзя подписаться на себя")

    exists = conn.execute(
        "SELECT 1 FROM follows WHERE follower_id = ? AND following_id = ?",
        (user["id"], target["id"]),
    ).fetchone()
    if exists:
        conn.execute("DELETE FROM follows WHERE follower_id = ? AND following_id = ?", (user["id"], target["id"]))
        following = False
    else:
        conn.execute(
            "INSERT INTO follows (follower_id, following_id, created_at) VALUES (?, ?, ?)",
            (user["id"], target["id"], now_iso()),
        )
        following = True
    conn.commit()
    followers_count = conn.execute("SELECT COUNT(*) FROM follows WHERE following_id = ?", (target["id"],)).fetchone()[0]
    conn.close()
    return {"following": following, "followers_count": followers_count}
