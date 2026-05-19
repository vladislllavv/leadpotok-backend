import os
import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from core.database import get_db
from api import endpoints
from parsers.vk_monitor import VKMonitor
from services.notification import NotificationService

# Инициализация сервисов при старте
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global vk_monitor, endpoints.vk_monitor, endpoints.notification_service
    
    # Инициализация VK монитора
    if os.getenv("VK_TOKEN") and os.getenv("OPENAI_KEY"):
        from ai.analyzer import AIClient  # Твой AI клиент
        ai_client = AIClient(api_key=os.getenv("OPENAI_KEY"))
        vk_monitor = VKMonitor(
            config={
                'groups_file': 'config/vk_groups.yaml',
                'keywords_file': 'config/keywords.json'
            },
            ai_client=ai_client
        )
        endpoints.vk_monitor = vk_monitor
    
    # Инициализация уведомлений
    if os.getenv("TELEGRAM_BOT_TOKEN"):
        notification_service = NotificationService(os.getenv("TELEGRAM_BOT_TOKEN"))
        endpoints.notification_service = notification_service
        # Запуск фоновой обработки очередей
        asyncio.create_task(notification_service.process_queues())
    
    yield
    
    # Shutdown
    if endpoints.notification_service:
        await endpoints.notification_service.close()

app = FastAPI(
    title="LeadPotok Pro",
    description="B2B Lead Generation Platform",
    version="2.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Роуты
app.include_router(endpoints.router, prefix="/api")

# Статика (для Mini App)
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
