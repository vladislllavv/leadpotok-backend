import os
import asyncio
from fastapi import FastAPI, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Импорты из наших модулей
from database import get_db, add_lead, is_duplicate, get_leads, get_stats, Lead, SessionLocal
from parsers.rusprofile_parser import RusprofileParser
from parsers.vk_parser import VKParser
from parsers.vk_ai_filter import VKAIFilter
from export import export_leads_to_excel

# Инициализация FastAPI (ОБЯЗАТЕЛЬНО в начале!)
app = FastAPI()

# Настройка CORS (чтобы сайт работал из Telegram)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Загрузка ключа администратора
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")

def verify_admin(x_admin_key: str = Header(None)):
    """Проверяет админ-ключ"""
    if not ADMIN_API_KEY or x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Неверный админ-ключ")
    return True

# --- ПУБЛИЧНЫЕ ЭНДПОИНТЫ ---

@app.get("/api/leads")
async def get_public_leads(cargo_type: str = Query(None), city: str = Query(None)):
    """Получение списка лидов для Mini App"""
    db = next(get_db())
    try:
        leads = get_leads(db, cargo_type, city, limit=50)
        return {
            "leads": [
                {
                    "id": l.id, "company": l.company, "phone": l.phone,
                    "city": l.city, "source": l.source, "hot_level": l.hot_level,
                    "reason": l.reason, "cargo_type": l.cargo_type
                } for l in leads
            ]
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        db.close()

@app.get("/")
async def root():
    return {"status": "ok", "message": "LeadPotok API is running"}

# --- АДМИН ЭНДПОИНТЫ ---

@app.get("/api/admin/stats")
async def admin_stats(x_admin_key: str = Header(None)):
    """Статистика (Всего лидов, горячих и т.д.)"""
    if not ADMIN_API_KEY or x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Неверный ключ")
    
    db = next(get_db())
    try:
        stats = get_stats(db)
        return stats
    finally:
        db.close()

@app.get("/api/admin/leads")
async def admin_leads(limit: int = 50, x_admin_key: str = Header(None)):
    """Список последних лидов для админки"""
    if not ADMIN_API_KEY or x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Неверный ключ")
    
    db = next(get_db())
    try:
        leads = get_leads(db, limit=limit)
        return {
            "leads": [
                {
                    "id": l.id, "company": l.company, "phone": l.phone,
                    "city": l.city, "source": l.source, "hot_level": l.hot_level,
                    "created_at": l.created_at.isoformat() if l.created_at else None
                } for l in leads
            ]
        }
    finally:
        db.close()

@app.post("/api/admin/parse/rusprofile")
async def trigger_rusprofile_parse(query: str = Query(...), x_admin_key: str = Header(None)):
    """Запуск парсера Rusprofile"""
    if not ADMIN_API_KEY or x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Неверный ключ")
    
    async def run_parser():
        try:
            parser = RusprofileParser()
            leads = await parser.search(query)
            db = next(get_db())
            count = 0
            for lead in leads:
                if not is_duplicate(db, lead.get('phone', ''), lead.get('company', '')):
                    add_lead(db, **lead)
                    count += 1
            db.close()
            print(f"✅ Rusprofile '{query}' завершен. Добавлено {count} компаний.")
        except Exception as e:
            print(f"❌ Ошибка парсинга Rusprofile: {e}")

    asyncio.create_task(run_parser())
    return {"status": "started", "message": "Поиск запущен в фоне"}

@app.post("/api/admin/parse/vk")
async def trigger_vk_parse(x_admin_key: str = Header(None)):
    """Запуск парсера VK Групп"""
    if not ADMIN_API_KEY or x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Неверный ключ")
    
    async def run_vk_parser():
        try:
            parser = VKParser()
            ai_filter = VKAIFilter()
            
            leads = await parser.parse_all_groups()
            
            db = next(get_db())
            new_count = 0
            
            for lead in leads:
                is_valid, score = ai_filter.filter_lead(lead)
                
                if is_valid and score >= 60:
                    if not is_duplicate(db, lead.get('phone', ''), lead.get('company', '')):
                        lead['reason'] = f"[Score: {score}] {lead['reason']}"
                        lead['hot_level'] = 'hot' if score >= 80 else 'warm'
                        add_lead(db, **lead)
                        new_count += 1
                        
                        # Отправка уведомления в Telegram если очень горячий лид
                        if score >= 80:
                            await send_telegram_notification(lead, score)
            
            db.close()
            print(f"✅ VK парсинг завершен. Добавлено {new_count} заявок.")
        except Exception as e:
            print(f"❌ Ошибка парсинга VK: {e}")

    asyncio.create_task(run_vk_parser())
    return {"status": "started", "message": "Парсинг VK запущен"}

@app.get("/api/admin/export/excel")
async def export_excel(cargo_type: str = Query(None), city: str = Query(None), x_admin_key: str = Header(None)):
    """Скачивание Excel файла"""
    if not ADMIN_API_KEY or x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Неверный ключ")
    
    try:
        file = export_leads_to_excel(cargo_type, city)
        return StreamingResponse(
            file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=leadpotok_leads.xlsx"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

async def send_telegram_notification(lead: dict, score: int):
    """Отправляет сообщение в Telegram боту"""
    try:
        from aiogram import Bot
        token = os.getenv("BOT_TOKEN")
        admin_id = os.getenv("ADMIN_ID")
        
        if not token or not admin_id:
            return
            
        bot = Bot(token=token)
        
        text = f"""
 <b>Новая заявка из VK!</b> (Score: {score})

<b>Текст:</b>
{lead['reason'][:250]}...

<b>Контакты:</b>
{lead.get('phone', 'Нет телефона')}
{lead.get('contact', 'Нет Telegram')}
        """
        
        await bot.send_message(chat_id=admin_id, text=text, parse_mode='HTML')
        await bot.session.close()
    except Exception as e:
        print(f"❌ Ошибка отправки уведомления: {e}")
