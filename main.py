import os
import asyncio
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Импорты из наших модулей
from core.database import get_db, init_db
from api import endpoints
from parsers.vk_monitor import VKMonitor
from services.notification import NotificationService

# === Глобальные переменные для сервисов ===
vk_monitor: VKMonitor = None
notification_service: NotificationService = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup и Shutdown логика приложения"""
    global vk_monitor, notification_service
    
    logger.info("🚀 Запуск LeadPotok Pro...")
    
    # === STARTUP ===
    
    # 1. Инициализация БД
    try:
        init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database init error: {e}")
    
    # 2. Инициализация VK монитора
    if os.getenv("VK_TOKEN") and os.getenv("GROQ_API_KEY"):
        try:
            vk_monitor = VKMonitor()
            # Передаём экземпляр в endpoints через атрибут модуля
            endpoints.vk_monitor_instance = vk_monitor
            logger.info("✅ VK Monitor initialized")
        except Exception as e:
            logger.error(f"❌ VK Monitor init error: {e}")
    
    # 3. Инициализация уведомлений
    if os.getenv("TELEGRAM_BOT_TOKEN"):
        try:
            notification_service = NotificationService(os.getenv("TELEGRAM_BOT_TOKEN"))
            endpoints.notification_service_instance = notification_service
            # Запуск фоновой обработки очередей
            asyncio.create_task(notification_service.process_queues())
            logger.info("✅ Notification service initialized")
        except Exception as e:
            logger.error(f"❌ Notification service init error: {e}")
    
    yield
    
    # === SHUTDOWN ===
    logger.info("🛑 Завершение работы...")
    if notification_service:
        await notification_service.close()

# Создание приложения FastAPI
app = FastAPI(
    title="LeadPotok Pro",
    description="B2B Lead Generation Platform with AI",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware (разрешаем все источники для Telegram Mini App)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем API роуты
app.include_router(endpoints.router, prefix="/api")

# Статические файлы (фронтенд для Mini App)
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "version": "2.0.0",
        "services": {
            "vk_monitor": vk_monitor is not None,
            "notifications": notification_service is not None
        }
    }

# Root endpoint
@app.get("/")
async def root():
    return {"message": "LeadPotok Pro API is running"}

# Запуск через uvicorn (если запускаем напрямую)
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)