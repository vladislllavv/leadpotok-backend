from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from security import validate_telegram_data
from database import init_db, get_leads

load_dotenv()
app = FastAPI(title="ЛидПоток API")

CORS_ORIGIN = os.getenv("CORS_ORIGIN", "https://t.me")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[CORS_ORIGIN],
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["*"],
)

class LeadRequest(BaseModel):
    init_data: str
    cargo_type: str = None
    region: str = None

init_db()

@app.post("/api/leads")
async def get_leads_api(request: LeadRequest):
    user = validate_telegram_data(request.init_data, os.getenv("BOT_TOKEN"))
    if not user:
        raise HTTPException(status_code=403, detail="Невалидные данные Telegram")
    leads = get_leads(cargo_type=request.cargo_type, city=request.region)
    return {"status": "ok", "user_id": user.get("id"), "leads": leads}

@app.get("/health")
def health():
    return {"status": "running"}
import os
from fastapi import Header, HTTPException

# Простой ключ для защиты (смени на случайную строку!)
PARSE_API_KEY = os.getenv("PARSE_API_KEY", "change-me-to-random-string-123")

@app.post("/api/parse")
async def trigger_parse(x_api_key: str = Header(None)):
    """Запускает парсинг только при правильном ключе"""
    if x_api_key != PARSE_API_KEY:
        raise HTTPException(status_code=403, detail="Неверный ключ доступа")
    
    # Запускаем в фоне, чтобы не блокировать ответ
    import asyncio
    from run_parsers import main as run_parser_main
    asyncio.create_task(run_parser_main())
    
    return {"status": "started", "message": "Парсинг запущен в фоне. Проверь базу через 2-3 минуты."}
