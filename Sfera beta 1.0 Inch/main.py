from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import UPLOAD_DIR
from database import init_db
from routers import admin, auth, chats, posts, users

init_db()

app = FastAPI(title="Sfera Beta 1.0 Inch")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

app.include_router(auth.router)
app.include_router(posts.router)
app.include_router(users.router)
app.include_router(chats.router)
app.include_router(admin.router)


@app.get("/health")
def health():
    return {"service": "Sfera", "version": "Beta 1.0 Inch", "status": "ok"}
