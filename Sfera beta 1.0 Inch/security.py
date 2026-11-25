from typing import Any, Dict, Optional
from fastapi import Depends, Header, HTTPException

from database import get_db


def get_current_user_optional(authorization: Optional[str] = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    conn = get_db()
    row = conn.execute(
        "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token = ?",
        (token,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def require_user(user=Depends(get_current_user_optional)):
    if not user:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    return user


def user_public_dict(conn, u: Dict[str, Any], viewer_id: Optional[int] = None) -> Dict[str, Any]:
    uid = u["id"]
    posts_count = conn.execute("SELECT COUNT(*) FROM posts WHERE user_id = ?", (uid,)).fetchone()[0]
    followers_count = conn.execute("SELECT COUNT(*) FROM follows WHERE following_id = ?", (uid,)).fetchone()[0]
    following_count = conn.execute("SELECT COUNT(*) FROM follows WHERE follower_id = ?", (uid,)).fetchone()[0]
    is_following = False
    if viewer_id and viewer_id != uid:
        is_following = (
            conn.execute(
                "SELECT 1 FROM follows WHERE follower_id = ? AND following_id = ?",
                (viewer_id, uid),
            ).fetchone()
            is not None
        )
    return {
        "id": uid,
        "username": u["username"],
        "display_name": u["display_name"],
        "bio": u["bio"] or "",
        "avatar_color": u["avatar_color"] or "#8294FF",
        "banner_style": u["banner_style"] or "linear-gradient(135deg, #16B8A6 0%, #38BDF8 55%, #8294FF 100%)",
        "posts_count": posts_count,
        "followers_count": followers_count,
        "following_count": following_count,
        "is_following": is_following,
    }
