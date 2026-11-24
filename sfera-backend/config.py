import os
import re

DB_PATH = os.getenv("SFERA_DB", "sfera.db")
RESERVED_USERNAMES = {"asg", "sfera", "suport"}
USERNAME_RE = re.compile(r"^[a-z0-9_]{3,24}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Render автоматически задаёт переменную RENDER_EXTERNAL_URL
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
KEEP_ALIVE_INTERVAL = 600  # 10 минут
