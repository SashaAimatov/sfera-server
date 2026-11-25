import sqlite3
from fastapi import APIRouter, Header, HTTPException

from config import ADMIN_KEY
from database import get_db
from models import ImportPayload

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/export")
def export_db(x_admin_key: str = Header(default="")):
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Неверный ключ администратора")
    conn = get_db()
    tables = {}
    for table in ["users", "posts", "likes", "comments", "follows", "messages"]:
        rows = conn.execute(f"SELECT * FROM {table}").fetchall()
        tables[table] = [dict(r) for r in rows]
    conn.close()
    return {"status": "ok", "tables": tables}


@router.post("/import")
def import_db(payload: ImportPayload, x_admin_key: str = Header(default="")):
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Неверный ключ администратора")
    conn = get_db()
    cur = conn.cursor()
    restored = {}
    allowed = ("users", "posts", "likes", "comments", "follows", "messages")
    for table, rows in payload.tables.items():
        if table not in allowed or not rows:
            restored[table] = 0
            continue
        count = 0
        for row in rows:
            cols = ", ".join(row.keys())
            placeholders = ", ".join(["?"] * len(row))
            try:
                cur.execute(f"INSERT OR IGNORE INTO {table} ({cols}) VALUES ({placeholders})", list(row.values()))
                count += cur.rowcount
            except sqlite3.Error:
                pass
        restored[table] = count
    conn.commit()
    conn.close()
    return {"status": "ok", "restored": restored}
