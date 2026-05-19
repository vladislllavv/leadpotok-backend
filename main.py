import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

app = FastAPI(
    title="LeadPotok Pro",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роуты (уже с префиксом /api внутри router)
app.include_router(endpoints.router)

# Статика
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 10000)))