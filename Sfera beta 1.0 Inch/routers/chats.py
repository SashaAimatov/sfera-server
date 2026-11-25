from fastapi import APIRouter, Depends, HTTPException

from database import get_db, now_iso
from models import MessageReq
from security import require_user

router = APIRouter(prefix="/api/chats", tags=["chats"])


@router.get("")
def list_chats(user=Depends(require_user)):
    uid = user["id"]
    conn = get_db()
    rows = conn.execute(
        '''
        SELECT
            CASE WHEN m.sender_id = ? THEN m.receiver_id ELSE m.sender_id END AS peer_id,
            m.content AS last_message,
            m.created_at AS last_time
        FROM messages m
        WHERE m.sender_id = ? OR m.receiver_id = ?
        ORDER BY m.id DESC
        ''',
        (uid, uid, uid),
    ).fetchall()

    seen = set()
    chats = []
    for r in rows:
        pid = r["peer_id"]
        if pid in seen:
            continue
        seen.add(pid)
        peer = conn.execute("SELECT username, display_name, avatar_color FROM users WHERE id = ?", (pid,)).fetchone()
        if peer:
            chats.append(
                {
                    "username": peer["username"],
                    "display_name": peer["display_name"],
                    "avatar_color": peer["avatar_color"] or "#16B8A6",
                    "last_message": r["last_message"],
                    "last_time": r["last_time"],
                }
            )
    conn.close()
    return {"chats": chats}


@router.get("/{username}/messages")
def get_chat_messages(username: str, user=Depends(require_user)):
    uname = username.strip().lstrip("@").lower()
    conn = get_db()
    peer = conn.execute("SELECT id FROM users WHERE username = ?", (uname,)).fetchone()
    if not peer:
        conn.close()
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    rows = conn.execute(
        '''
        SELECT m.id, m.content, m.created_at, u.username AS sender_username
        FROM messages m
        JOIN users u ON u.id = m.sender_id
        WHERE (m.sender_id = ? AND m.receiver_id = ?) OR (m.sender_id = ? AND m.receiver_id = ?)
        ORDER BY m.id ASC
        ''',
        (user["id"], peer["id"], peer["id"], user["id"]),
    ).fetchall()
    conn.close()
    return {"messages": [dict(r) for r in rows]}


@router.post("/{username}/messages")
def send_chat_message(username: str, req: MessageReq, user=Depends(require_user)):
    text = req.content.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Сообщение пустое")
    uname = username.strip().lstrip("@").lower()
    conn = get_db()
    peer = conn.execute("SELECT id FROM users WHERE username = ?", (uname,)).fetchone()
    if not peer:
        conn.close()
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    conn.execute(
        "INSERT INTO messages (sender_id, receiver_id, content, created_at) VALUES (?, ?, ?, ?)",
        (user["id"], peer["id"], text[:1000], now_iso()),
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}
