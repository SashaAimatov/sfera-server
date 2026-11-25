import secrets
from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from config import MAX_UPLOAD_MB, UPLOAD_DIR
from database import get_db, now_iso
from models import CommentReq, CreatePostReq
from security import get_current_user_optional, require_user

router = APIRouter(prefix="/api", tags=["posts"])


@router.post("/upload")
async def upload_media(file: UploadFile = File(...), user=Depends(require_user)):
    ctype = (file.content_type or "").lower()
    if not (ctype.startswith("image/") or ctype.startswith("video/")):
        raise HTTPException(status_code=400, detail="Разрешены только фото и видео")

    data = await file.read()
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"Файл больше {MAX_UPLOAD_MB} МБ")

    ext = Path(file.filename or "file.bin").suffix.lower() or (".mp4" if ctype.startswith("video/") else ".png")
    fname = f"{secrets.token_hex(12)}{ext}"
    (UPLOAD_DIR / fname).write_bytes(data)

    return {
        "url": f"/uploads/{fname}",
        "media_type": "video" if ctype.startswith("video/") else "image",
    }


@router.get("/posts")
def list_posts(viewer=Depends(get_current_user_optional)):
    viewer_id = viewer["id"] if viewer else None
    conn = get_db()
    rows = conn.execute(
        "SELECT p.*, u.username, u.display_name, u.avatar_color FROM posts p JOIN users u ON u.id = p.user_id ORDER BY p.id DESC"
    ).fetchall()

    posts = []
    for r in rows:
        pid = r["id"]
        likes_count = conn.execute("SELECT COUNT(*) FROM likes WHERE post_id = ?", (pid,)).fetchone()[0]
        comments_count = conn.execute("SELECT COUNT(*) FROM comments WHERE post_id = ?", (pid,)).fetchone()[0]
        liked_by_me = False
        author_followed = False
        if viewer_id:
            liked_by_me = conn.execute("SELECT 1 FROM likes WHERE user_id = ? AND post_id = ?", (viewer_id, pid)).fetchone() is not None
            author_followed = conn.execute("SELECT 1 FROM follows WHERE follower_id = ? AND following_id = ?", (viewer_id, r["user_id"])).fetchone() is not None

        posts.append(
            {
                "id": pid,
                "content": r["content"],
                "media_url": r["media_url"],
                "media_type": r["media_type"],
                "created_at": r["created_at"],
                "username": r["username"],
                "display_name": r["display_name"],
                "avatar_color": r["avatar_color"] or "#16B8A6",
                "likes_count": likes_count,
                "liked_by_me": liked_by_me,
                "comments_count": comments_count,
                "author_followed": author_followed,
            }
        )
    conn.close()
    return {"posts": posts}


@router.post("/posts")
def create_post(req: CreatePostReq, user=Depends(require_user)):
    text = (req.content or "").strip()
    if not text and not req.media_url:
        raise HTTPException(status_code=400, detail="Пост не может быть пустым")

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO posts (user_id, content, media_url, media_type, created_at) VALUES (?, ?, ?, ?, ?)",
        (user["id"], text, req.media_url, req.media_type, now_iso()),
    )
    pid = cur.lastrowid
    conn.commit()
    conn.close()
    return {"status": "ok", "id": pid}


@router.delete("/posts/{post_id}")
def delete_post(post_id: int, user=Depends(require_user)):
    conn = get_db()
    row = conn.execute("SELECT user_id FROM posts WHERE id = ?", (post_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Пост не найден")
    if row["user_id"] != user["id"]:
        conn.close()
        raise HTTPException(status_code=403, detail="Нельзя удалить чужой пост")
    conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}


@router.post("/posts/{post_id}/like")
def toggle_like(post_id: int, user=Depends(require_user)):
    conn = get_db()
    exists = conn.execute("SELECT 1 FROM likes WHERE user_id = ? AND post_id = ?", (user["id"], post_id)).fetchone()
    if exists:
        conn.execute("DELETE FROM likes WHERE user_id = ? AND post_id = ?", (user["id"], post_id))
        liked = False
    else:
        conn.execute("INSERT OR IGNORE INTO likes (user_id, post_id) VALUES (?, ?)", (user["id"], post_id))
        liked = True
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM likes WHERE post_id = ?", (post_id,)).fetchone()[0]
    conn.close()
    return {"liked": liked, "likes_count": count}


@router.get("/posts/{post_id}/comments")
def list_comments(post_id: int):
    conn = get_db()
    rows = conn.execute(
        "SELECT c.id, c.content, c.created_at, u.username, u.display_name FROM comments c JOIN users u ON u.id = c.user_id WHERE c.post_id = ? ORDER BY c.id ASC",
        (post_id,),
    ).fetchall()
    conn.close()
    return {"comments": [dict(r) for r in rows]}


@router.post("/posts/{post_id}/comments")
def add_comment(post_id: int, req: CommentReq, user=Depends(require_user)):
    text = req.content.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Комментарий пуст")
    conn = get_db()
    if not conn.execute("SELECT 1 FROM posts WHERE id = ?", (post_id,)).fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Пост не найден")
    conn.execute(
        "INSERT INTO comments (post_id, user_id, content, created_at) VALUES (?, ?, ?, ?)",
        (post_id, user["id"], text[:500], now_iso()),
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}
