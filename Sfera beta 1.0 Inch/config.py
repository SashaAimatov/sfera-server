import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "sfera.db"))
UPLOAD_DIR = BASE_DIR / "uploads"
BACKUP_FILE = BASE_DIR / "posts_backup.json"
ADMIN_KEY = os.getenv("ADMIN_KEY", "sfera-inch-admin-2026")
MAX_UPLOAD_MB = 25

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
