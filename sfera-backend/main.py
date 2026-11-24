import asyncio
import urllib.request
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import KEEP_ALIVE_INTERVAL, RENDER_EXTERNAL_URL
from database import init_db
from routes import auth, posts, users


def _ping_self(url: str) -> None:
    try:
        with urllib.request.urlopen(f"{url}/health", timeout=10):
            pass
    except Exception:
        pass


async def keep_alive_loop() -> None:
    while True:
        await asyncio.sleep(KEEP_ALIVE_INTERVAL)
        if RENDER_EXTERNAL_URL:
            await asyncio.to_thread(_ping_self, RENDER_EXTERNAL_URL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task = asyncio.create_task(keep_alive_loop()) if RENDER_EXTERNAL_URL else None
    yield
    if task:
        task.cancel()


app = FastAPI(title="Sfera", version="Alfa 1.2", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(posts.router)


@app.get("/")
@app.get("/health")
def health():
    return {"service": "Sfera", "version": "Alfa 1.2", "status": "ok"}
