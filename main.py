import os
from fastapi import FastAPI, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from database import get_db, add_lead, is_duplicate, get_leads, get_stats, Lead, SessionLocal
from parsers.rusprofile_parser import RusprofileParser
from export import export_leads_to_excel
import asyncio

app = FastAPI()

# 🔥 ВАЖНО: Разрешаем ВСЕ источники для CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешаем все
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔐 Проверка админ-ключа
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")

def verify_admin(x_admin_key: str = Header(None)):
    if not ADMIN_API_KEY:
        raise HTTPException(status_code=500, detail="ADMIN_API_KEY not set")
    if x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Неверный админ-ключ")
    return True

@app.get("/")
async def root():
    return {"status": "ok", "message": "LeadPotok API is running"}

@app.get("/api/leads")
async def get_public_leads(cargo_type: str = Query(None), city: str = Query(None)):
    """Публичный эндпоинт для Mini App"""
    try:
        db = next(get_db())
        leads = get_leads(db, cargo_type, city, limit=50)
        db.close()
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
        return {"error": str(e), "leads": []}

# --- АДМИН ЭНДПОИНТЫ ---

@app.get("/api/admin/stats")
async def admin_stats(x_admin_key: str = Header(None)):
    """Статистика для админки"""
    if not ADMIN_API_KEY or x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Неверный ключ")
    
    try:
        db = next(get_db())
        stats = get_stats(db)
        db.close()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/leads")
async def admin_leads(limit: int = 50, x_admin_key: str = Header(None)):
    """Список лидов для админки"""
    if not ADMIN_API_KEY or x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Неверный ключ")
    
    try:
        db = next(get_db())
        leads = get_leads(db, limit=limit)
        db.close()
        return {
            "leads": [
                {
                    "id": l.id, "company": l.company, "phone": l.phone,
                    "city": l.city, "source": l.source, "hot_level": l.hot_level,
                    "created_at": l.created_at.isoformat() if l.created_at else None
                } for l in leads
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/parse/rusprofile")
async def trigger_rusprofile(query: str = Query(...), x_admin_key: str = Header(None)):
    """Запускает парсинг Rusprofile в фоне"""
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
            print(f"✅ Парсинг '{query}' завершен. Добавлено {count} компаний.")
        except Exception as e:
            print(f"❌ Ошибка парсинга: {e}")

    asyncio.create_task(run_parser())
    return {"status": "started", "message": f"Поиск '{query}' запущен в фоне"}

@app.get("/api/admin/export/excel")
async def export_excel(cargo_type: str = Query(None), city: str = Query(None), x_admin_key: str = Header(None)):
    """Скачивает Excel файл"""
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
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )
