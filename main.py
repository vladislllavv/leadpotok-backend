import os
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from core.database import init_db
from api import endpoints

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting LeadPotok...")
    init_db()
    logger.info("✅ Database initialized")
    yield
    logger.info("🛑 Shutting down...")

app = FastAPI(title="LeadPotok", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем API роуты
app.include_router(endpoints.router)

# Отдаём index.html явно
@app.get("/", response_class=HTMLResponse)
async def root():
    try:
        with open("frontend/index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Frontend not found</h1>"

# Статические файлы (CSS, JS, images)
app.mount("/static", StaticFiles(directory="frontend", html=True), name="static")

@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 10000)))