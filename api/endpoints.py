from fastapi import APIRouter, Depends, Header, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from core.database import get_db, User, Lead, get_or_create_user
from services.export import ExportService
import os
import logging
from datetime import datetime
from sqlalchemy import func

logger = logging.getLogger(__name__)
router = APIRouter()
export_service = ExportService()

def verify_admin(x_admin_key: str = Header(None)) -> bool:
    admin_key = os.getenv("ADMIN_API_KEY", "")
    if not admin_key or x_admin_key != admin_key:
        raise HTTPException(status_code=403, detail="Неверный ключ")
    return True

# === АДМИН ===

@router.get("/api/admin/stats")
async def admin_stats(x_admin_key: str = Header(None), db: Session = Depends(get_db)):
    verify_admin(x_admin_key)
    stats = db.query(
        func.count(Lead.id).label('total'),
        func.sum(func.case((Lead.lead_type == 'hot', 1), else_=0)).label('hot'),
    ).first()
    return {"total": stats.total or 0, "hot": stats.hot or 0, "warm": 0, "today": 0}

@router.get("/api/admin/leads")
async def admin_leads(limit: int = 50, x_admin_key: str = Header(None), db: Session = Depends(get_db)):
    verify_admin(x_admin_key)
    leads = db.query(Lead).order_by(Lead.created_at.desc()).limit(limit).all()
    return {"leads": [{"id": l.id, "company": l.company, "phone": l.phone, "city": l.city, 
                       "lead_type": l.lead_type, "created_at": l.created_at.isoformat() if l.created_at else None} for l in leads]}

@router.post("/api/admin/parse/vk")
async def parse_vk(x_admin_key: str = Header(None)):
    verify_admin(x_admin_key)
    return {"status": "started", "message": "VK парсинг запущен"}

@router.get("/api/admin/export/excel")
async def export_excel(x_admin_key: str = Header(None), db: Session = Depends(get_db)):
    verify_admin(x_admin_key)
    leads = db.query(Lead).all()
    file = export_service.export_to_excel(leads)
    return StreamingResponse(file, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            headers={"Content-Disposition": "attachment; filename=leads.xlsx"})

# === ПУБЛИЧНЫЕ ===

@router.get("/api/leads")
async def get_leads(user_id: int = Query(...), db: Session = Depends(get_db)):
    leads = db.query(Lead).filter(Lead.user_id == user_id).all()
    return {"leads": [{"id": l.id, "company": l.company, "phone": l.phone, "city": l.city, 
                       "lead_type": l.lead_type} for l in leads]}

@router.post("/api/user/init")
async def init_user(telegram_id: str, db: Session = Depends(get_db)):
    user = get_or_create_user(db, telegram_id)
    return {"user_id": user.id}