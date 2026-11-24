from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query

from database import get_db, now_iso
from schemas import PostRequest
from security import get_current_user, get_optional_user

router = APIRouter(prefix="/api/posts", tags=["posts"])


@router.get("")
def get_posts(
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    authorization: Optional[str] = Header(default=None),
):
    current_user = get_optional_user(authorization)
    current_uid = current_user["id"] if current_user else -1

    conn = get_db()
    rows = conn.execute(
        """
        SELECT
            p.id,
            p.content,
            p.created_at,
            u.username,
            u.display_name,
            (SELECT COUNT(*) FROM post_likes pl WHERE pl.post_id = p.id) AS likes_count,
            EXISTS(
                SELECT 1 FROM post_likes pl
                WHERE pl.post_id = p.id AND pl.user_id = ?
            ) AS liked_by_me
        FROM posts p
        JOIN users u ON u.id = p.user_id
        ORDER BY p.id DESC
        LIMIT ? OFFSET ?
        """,
        (current_uid, limit, offset),
    ).fetchall()
    conn.close()

    posts = []
    for r in rows:
        item = dict(r)
        item["liked_by_me"] = bool(item["liked_by_me"])
        posts.append(item)
    return {"posts": posts}


@router.post("")
def create_post(data: PostRequest, authorization: Optional[str] = Header(default=None)):
    user = get_current_user(authorization)
    content = data.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Пост не может быть пустым")

    created = now_iso()
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO posts (user_id, content, created_at) VALUES (?, ?, ?)",
        (user["id"], content, created),
    )
    post_id = cur.lastrowid
    conn.commit()
    conn.close()

    return {
        "status": "ok",
        "post": {
            "id": post_id,
            "username": user["username"],
            "display_name": user["display_name"],
            "content": content,
            "created_at": created,
            "likes_count": 0,
            "liked_by_me": False,
        },
    }


@router.delete("/{post_id}")
def delete_post(post_id: int, authorization: Optional[str] = Header(default=None)):
    user = get_current_user(authorization)
    conn = get_db()
    post = conn.execute("SELECT user_id FROM posts WHERE id = ?", (post_id,)).fetchone()
    if not post:
        conn.close()
        raise HTTPException(status_code=404, detail="Пост не найден")
    if post["user_id"] != user["id"]:
        conn.close()
        raise HTTPException(status_code=403, detail="Можно удалять только свои посты")

    conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}


@router.post("/{post_id}/like")
def toggle_like(post_id: int, authorization: Optional[str] = Header(default=None)):
    user = get_current_user(authorization)
    conn = get_db()
    post = conn.execute("SELECT id FROM posts WHERE id = ?", (post_id,)).fetchone()
    if not post:
        conn.close()
        raise HTTPException(status_code=404, detail="Пост не найден")

    existing = conn.execute(
        "SELECT 1 FROM post_likes WHERE user_id = ? AND post_id = ?",
        (user["id"], post_id),
    ).fetchone()

    if existing:
        conn.execute(
            "DELETE FROM post_likes WHERE user_id = ? AND post_id = ?",
            (user["id"], post_id),
        )
        liked = False
    else:
        conn.execute(
            "INSERT INTO post_likes (user_id, post_id, created_at) VALUES (?, ?, ?)",
            (user["id"], post_id, now_iso()),
        )
        liked = True

    likes_count = conn.execute(
        "SELECT COUNT(*) FROM post_likes WHERE post_id = ?", (post_id,)
    ).fetchone()[0]
    conn.commit()
    conn.close()

    return {"status": "ok", "liked": liked, "likes_count": likes_count}
