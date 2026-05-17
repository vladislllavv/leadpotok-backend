import os
from fastapi import FastAPI, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from database import get_db, add_lead, is_duplicate, get_leads, get_stats, Lead, SessionLocal
from parsers.rusprofile_parser import RusprofileParser
from export import export_leads_to_excel
import asyncio

app = FastAPI()

# Разрешаем CORS для GitHub Pages
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔐 Проверка админ-ключа
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")

def verify_admin(x_admin_key: str = Header(None)):
    if not ADMIN_API_KEY or x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Неверный админ-ключ")
    return True

@app.get("/api/leads")
async def get_public_leads(cargo_type: str = Query(None), city: str = Query(None)):
    """Публичный эндпоинт для Mini App"""
    db = next(get_db())
    leads = get_leads(db, cargo_type, city, limit=50)
    db.close()
    return {
        "leads": [
            {
                "id": l.id, "company": l.company, "phone": l.phone,
                "city": l.city, "source": l.source, "hot_level": l.hot_level,
                "reason": l.reason
            } for l in leads
        ]
    }

# --- АДМИН ЭНДПОИНТЫ ---

@app.get("/api/admin/stats")
async def admin_stats(_=Depends(verify_admin)):
    """Статистика для админки"""
    db = next(get_db())
    stats = get_stats(db)
    db.close()
    return stats

@app.get("/api/admin/leads")
async def admin_leads(limit: int = 50, _=Depends(verify_admin)):
    """Список лидов для админки"""
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

@app.post("/api/admin/parse/rusprofile")
async def trigger_rusprofile(query: str = Query(...), _=Depends(verify_admin)):
    """Запускает парсинг Rusprofile в фоне"""
    async def run_parser():
        parser = RusprofileParser()
        leads = await parser.search(query)
        db = next(get_db())
        for lead in leads:
            if not is_duplicate(db, lead.get('phone', ''), lead.get('company', '')):
                add_lead(db, **lead)
        db.close()
        print(f"✅ Парсинг '{query}' завершен. Добавлено {len(leads)} компаний.")

    asyncio.create_task(run_parser())
    return {"status": "started", "message": f"Поиск '{query}' запущен в фоне"}

@app.get("/api/admin/export/excel")
async def export_excel(cargo_type: str = Query(None), city: str = Query(None), _=Depends(verify_admin)):
    """Скачивает Excel файл"""
    file = export_leads_to_excel(cargo_type, city)
    return StreamingResponse(
        file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=leadpotok_leads.xlsx"}
    )
