import hashlib
import json
import secrets
import sqlite3
from datetime import datetime, timezone

from config import BACKUP_FILE, DB_PATH


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return f"{salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, hex_hash = stored.split("$", 1)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
        return secrets.compare_digest(dk.hex(), hex_hash)
    except Exception:
        return False


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.executescript(
        '''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            display_name TEXT NOT NULL,
            bio TEXT DEFAULT '',
            avatar_color TEXT DEFAULT '#8294FF',
            banner_style TEXT DEFAULT 'linear-gradient(135deg, #16B8A6 0%, #38BDF8 55%, #8294FF 100%)',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            content TEXT DEFAULT '',
            media_url TEXT,
            media_type TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS likes (
            user_id INTEGER NOT NULL,
            post_id INTEGER NOT NULL,
            PRIMARY KEY (user_id, post_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS follows (
            follower_id INTEGER NOT NULL,
            following_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (follower_id, following_id),
            FOREIGN KEY (follower_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (following_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE
        );
        '''
    )

    post_count = cur.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    if post_count == 0 and BACKUP_FILE.exists():
        try:
            raw = json.loads(BACKUP_FILE.read_text(encoding="utf-8"))
            posts_data = raw.get("posts", raw) if isinstance(raw, dict) else raw
            if isinstance(posts_data, list):
                default_pw = hash_password("sfera12345")
                for item in reversed(posts_data):
                    uname = str(item.get("username", "")).strip().lower()
                    if not uname:
                        continue
                    dname = str(item.get("display_name") or uname).strip()
                    row = cur.execute("SELECT id FROM users WHERE username = ?", (uname,)).fetchone()
                    if not row:
                        cur.execute(
                            "INSERT INTO users (username, email, password_hash, display_name, created_at) VALUES (?, ?, ?, ?, ?)",
                            (uname, f"{uname}@sfera.local", default_pw, dname, now_iso()),
                        )
                        uid = cur.lastrowid
                    else:
                        uid = row["id"]

                    cur.execute(
                        "INSERT INTO posts (user_id, content, media_url, media_type, created_at) VALUES (?, ?, ?, ?, ?)",
                        (
                            uid,
                            str(item.get("content", "")),
                            item.get("media_url"),
                            item.get("media_type"),
                            str(item.get("created_at") or now_iso()),
                        ),
                    )
        except Exception as exc:
            print(f"[Sfera] Ошибка импорта posts_backup.json: {exc}")

    conn.commit()
    conn.close()
