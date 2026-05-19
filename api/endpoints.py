import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, Header, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session

from core.database import get_db, get_or_create_user, add_lead_for_user, is_global_duplicate, User, Lead
from parsers.rusprofile_parser import RusprofileParser
from parsers.vk_monitor import VKMonitor
from services.export import ExportService
from services.notification import NotificationService

logger = logging.getLogger(__name__)
router = APIRouter()

# === Глобальные сервисы (инициализируются в main.py при старте) ===
vk_monitor_instance: Optional[VKMonitor] = None
notification_service_instance: Optional[NotificationService] = None
export_service = ExportService()

# --- Вспомогательные функции ---

def verify_admin(x_admin_key: str = Header(None)) -> bool:
    """Проверяет админ-ключ для защищённых эндпоинтов"""
    admin_key = os.getenv("ADMIN_API_KEY", "")
    if not admin_key or x_admin_key != admin_key:
        raise HTTPException(status_code=403, detail="Неверный админ-ключ")
    return True

def get_user_or_404(db: Session, user_id: int) -> User:
    """Возвращает пользователя или ошибку 404"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user

# --- ПУБЛИЧНЫЕ ЭНДПОИНТЫ (для Mini App) ---

@router.post("/api/user/init")
async def init_user(
    telegram_id: str,
    username: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Инициализация пользователя при первом запуске"""
    user = get_or_create_user(db, telegram_id, username)
    return {
        "user_id": user.id,
        "username": user.username,
        "daily_limit": user.daily_limit,
        "used_today": user.used_today,
        "created_at": user.created_at.isoformat() if user.created_at else None
    }

@router.get("/api/leads")
async def get_leads(
    user_id: int,
    cargo_type: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    lead_type: Optional[str] = Query(None),  # hot/warm/cold
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Получение лидов пользователя с фильтрами"""
    query = db.query(Lead).filter(Lead.user_id == user_id)
    
    if cargo_type and cargo_type != "любые":
        query = query.filter(Lead.cargo_type == cargo_type)
    if city:
        query = query.filter(Lead.city.ilike(f"%{city}%"))
    if lead_type:
        query = query.filter(Lead.lead_type == lead_type)
    
    leads = query.order_by(
        Lead.lead_type.desc(),  # hot first
        Lead.created_at.desc()
    ).limit(limit).all()
    
    return {
        "leads": [
            {
                "id": l.id,
                "company": l.company,
                "phone": l.phone,
                "city": l.city,
                "lead_type": l.lead_type,
                "ai_score": l.ai_score,
                "source": l.source,
                "created_at": l.created_at.isoformat() if l.created_at else None
            } for l in leads
        ],
        "total": query.count()
    }

@router.get("/api/stats")
async def get_user_stats(user_id: int, db: Session = Depends(get_db)):
    """Статистика пользователя"""
    from sqlalchemy import func
    
    stats = db.query(
        func.count(Lead.id).label('total'),
        func.sum(func.case((Lead.lead_type == 'hot', 1), else_=0)).label('hot'),
        func.sum(func.case((Lead.lead_type == 'warm', 1), else_=0)).label('warm'),
    ).filter(Lead.user_id == user_id).first()
    
    total = stats.total or 0
    hot = stats.hot or 0
    warm = stats.warm or 0
    
    return {
        "total": total,
        "hot": hot,
        "warm": warm,
        "cold": total - hot - warm
    }

# --- АДМИН ЭНДПОИНТЫ (защищённые) ---

@router.get("/api/admin/stats")
async def admin_stats(
    x_admin_key: str = Header(None),
    db: Session = Depends(get_db)
):
    """Глобальная статистика для админки"""
    verify_admin(x_admin_key)
    
    from sqlalchemy import func
    stats = db.query(
        func.count(Lead.id).label('total'),
        func.sum(func.case((Lead.lead_type == 'hot', 1), else_=0)).label('hot'),
        func.count(func.distinct(Lead.user_id)).label('users'),
    ).first()
    
    # Лиды за сегодня
    today = datetime.now().date()
    today_count = db.query(Lead).filter(
        func.date(Lead.created_at) == today
    ).count()
    
    return {
        "total": stats.total or 0,
        "hot": stats.hot or 0,
        "users": stats.users or 0,
        "today": today_count
    }

@router.get("/api/admin/leads")
async def admin_leads(
    limit: int = Query(50, ge=1, le=200),
    x_admin_key: str = Header(None),
    db: Session = Depends(get_db)
):
    """Список последних лидов для админки (все пользователи)"""
    verify_admin(x_admin_key)
    
    leads = db.query(Lead).order_by(
        Lead.lead_type.desc(),
        Lead.created_at.desc()
    ).limit(limit).all()
    
    return {
        "leads": [
            {
                "id": l.id,
                "company": l.company,
                "phone": l.phone,
                "city": l.city,
                "source": l.source,
                "lead_type": l.lead_type,
                "ai_score": l.ai_score,
                "created_at": l.created_at.isoformat() if l.created_at else None
            } for l in leads
        ]
    }

@router.post("/api/admin/parse/rusprofile")
async def trigger_rusprofile_parse(
    query: str = Query(...),
    background_tasks: BackgroundTasks = None,
    x_admin_key: str = Header(None),
    db: Session = Depends(get_db)
):
    """Запуск парсинга Rusprofile (глобальный)"""
    verify_admin(x_admin_key)
    
    async def run_parser():
        try:
            parser = RusprofileParser({'name': 'Rusprofile', 'rate_limit': 5})
            raw_leads = await parser.search(query)
            
            added = 0
            for raw in raw_leads:
                normalized = parser.normalize_lead(raw)
                # Добавляем как глобальный лид (user_id=None для системных)
                if not is_global_duplicate(db, normalized):
                    lead = Lead(
                        company=normalized.get('company', ''),
                        inn=normalized.get('inn'),
                        website=normalized.get('website'),
                        phone=normalized.get('phone'),
                        city=normalized.get('city'),
                        cargo_type=normalized.get('cargo_type', 'любые'),
                        volume=normalized.get('volume', ''),
                        description=normalized.get('description', ''),
                        source=normalized.get('source', ''),
                        source_url=normalized.get('source_url', ''),
                        lead_type='warm',
                        ai_score=50
                    )
                    db.add(lead)
                    added += 1
            
            db.commit()
            logger.info(f"✅ Rusprofile '{query}' завершён. Добавлено: {added}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга Rusprofile: {e}")
            db.rollback()
    
    if background_tasks:
        background_tasks.add_task(run_parser)
    else:
        asyncio.create_task(run_parser())
    
    return {"status": "started", "message": f"Поиск '{query}' запущен в фоне"}

@router.post("/api/admin/parse/vk")
async def trigger_vk_monitoring(
    background_tasks: BackgroundTasks = None,
    x_admin_key: str = Header(None),
    db: Session = Depends(get_db)
):
    """Запуск глобального мониторинга VK"""
    verify_admin(x_admin_key)
    
    if not vk_monitor_instance:
        raise HTTPException(status_code=503, detail="VK Monitor not initialized")
    
    async def run_vk_monitor():
        try:
            leads = await vk_monitor_instance.monitor_all()
            
            added = 0
            for lead in leads:
                if not is_global_duplicate(db, lead):
                    # Создаём лид
                    new_lead = Lead(
                        company=lead.get('company', ''),
                        phone=lead.get('phone'),
                        telegram=lead.get('telegram'),
                        city=lead.get('city'),
                        volume=lead.get('volume'),
                        description=lead.get('description', ''),
                        source=lead.get('source', ''),
                        source_url=lead.get('source_url', ''),
                        lead_type=lead.get('lead_type', 'warm'),
                        ai_score=lead.get('ai_score', 50),
                        ai_analysis=lead.get('ai_analysis', '')
                    )
                    db.add(new_lead)
                    added += 1
                    
                    # Мгновенное уведомление для горячих лидов
                    if lead.get('lead_type') == 'hot' and notification_service_instance:
                        # Отправляем уведомление всем активным админам (упрощённо)
                        admin_id = os.getenv("ADMIN_ID")
                        if admin_id:
                            try:
                                await notification_service_instance.send_hot_lead(
                                    int(admin_id), 
                                    lead
                                )
                            except Exception as e:
                                logger.error(f"❌ Ошибка отправки уведомления: {e}")
            
            db.commit()
            logger.info(f"✅ VK мониторинг завершён. Добавлено: {added}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка VK мониторинга: {e}")
            db.rollback()
    
    if background_tasks:
        background_tasks.add_task(run_vk_monitor)
    else:
        asyncio.create_task(run_vk_monitor())
    
    return {"status": "started", "message": "VK мониторинг запущен"}

@router.get("/api/admin/export/excel")
async def export_excel(
    cargo_type: Optional[str] = Query(None),
    lead_type: Optional[str] = Query(None),
    x_admin_key: str = Header(None),
    db: Session = Depends(get_db)
):
    """Экспорт всех лидов в Excel (админ)"""
    verify_admin(x_admin_key)
    
    query = db.query(Lead)
    if cargo_type:
        query = query.filter(Lead.cargo_type == cargo_type)
    if lead_type:
        query = query.filter(Lead.lead_type == lead_type)
    
    leads = query.order_by(Lead.created_at.desc()).all()
    
    file = export_service.export_to_excel(leads, user_name="admin")
    
    return StreamingResponse(
        file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=leadpotok_admin_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        }
    )

@router.get("/api/export/excel")
async def export_user_excel(
    user_id: int,
    cargo_type: Optional[str] = Query(None),
    lead_type: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Экспорт лидов конкретного пользователя в Excel"""
    query = db.query(Lead).filter(Lead.user_id == user_id)
    if cargo_type:
        query = query.filter(Lead.cargo_type == cargo_type)
    if lead_type:
        query = query.filter(Lead.lead_type == lead_type)
    
    leads = query.order_by(Lead.created_at.desc()).all()
    
    file = export_service.export_to_excel(leads)
    
    return StreamingResponse(
        file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=leadpotok_user{user_id}_{datetime.now().strftime('%Y%m%d')}.xlsx"
        }
    )

# --- УТИЛИТЫ ---

@router.get("/api/admin/reset-quotas")
async def reset_daily_quotas(
    x_admin_key: str = Header(None),
    db: Session = Depends(get_db)
):
    """Сброс дневных квот пользователей (для тестов)"""
    verify_admin(x_admin_key)
    
    db.query(User).update({User.used_today: 0})
    db.commit()
    
    return {"status": "ok", "message": "Quotas reset"}

@router.delete("/api/admin/lead/{lead_id}")
async def delete_lead(
    lead_id: int,
    x_admin_key: str = Header(None),
    db: Session = Depends(get_db)
):
    """Удаление лида (админ)"""
    verify_admin(x_admin_key)
    
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Лид не найден")
    
    db.delete(lead)
    db.commit()
    
    return {"status": "ok", "message": "Лид удалён"}