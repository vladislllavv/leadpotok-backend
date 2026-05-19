from fastapi import APIRouter, Depends, Header, HTTPException, Query, BackgroundTasks
from core.database import get_db, get_or_create_user, add_lead_for_user
from parsers.vk_monitor import VKMonitor
from services.notification import NotificationService
from services.export import ExportService
from fastapi.responses import StreamingResponse
import asyncio
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Глобальные сервисы (инициализируются при старте)
vk_monitor: VKMonitor = None
notification_service: NotificationService = None
export_service = ExportService()

@router.post("/api/user/init")
async def init_user(
    telegram_id: str,
    username: str = None,
    db = Depends(get_db)
):
    """Инициализация пользователя при первом запуске"""
    user = get_or_create_user(db, telegram_id, username)
    return {
        "user_id": user.id,
        "daily_limit": user.daily_limit,
        "used_today": user.used_today
    }

@router.get("/api/leads")
async def get_leads(
    user_id: int,
    cargo_type: str = Query(None),
    city: str = Query(None),
    lead_type: str = Query(None),  # hot/warm/cold
    limit: int = Query(50, le=200),
    db = Depends(get_db)
):
    """Получение лидов пользователя с фильтрами"""
    from core.database import Lead
    from sqlalchemy import and_
    
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

@router.post("/api/parse/rusprofile")
async def trigger_rusprofile(
    user_id: int,
    query: str,
    background_tasks: BackgroundTasks,
    db = Depends(get_db),
    x_admin_key: str = Header(None)
):
    """Запуск парсинга Rusprofile для пользователя"""
    # Проверка прав (упрощённо)
    if x_admin_key and x_admin_key != "your_admin_key":
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    from parsers.rusprofile import RusprofileParser
    
    async def run_parser():
        parser = RusprofileParser({'name': 'Rusprofile', 'rate_limit': 5})
        raw_leads = await parser.search(query)
        
        for raw in raw_leads:
            normalized = parser.normalize_lead(raw)
            result, status = add_lead_for_user(db, user_id, normalized)
            
            # Уведомление если горячий
            if status == "created" and result and result.lead_type == "hot":
                # Отправка уведомления (если настроен bot)
                pass
    
    background_tasks.add_task(run_parser)
    return {"status": "started", "message": "Парсинг запущен в фоне"}

@router.post("/api/parse/vk")
async def trigger_vk_monitoring(
    user_id: int,
    background_tasks: BackgroundTasks,
    db = Depends(get_db)
):
    """Запуск VK-мониторинга"""
    async def run_vk_monitor():
        if not vk_monitor:
            logger.error("VK monitor not initialized")
            return
        
        leads = await vk_monitor.monitor_all()
        
        for lead in leads:
            result, status = add_lead_for_user(db, user_id, lead)
            
            if status == "created" and result:
                # Мгновенное уведомление для горячих
                if result.lead_type == "hot" and notification_service:
                    user = db.query(User).get(user_id)
                    await notification_service.send_hot_lead(
                        int(user.telegram_id), 
                        lead
                    )
    
    background_tasks.add_task(run_vk_monitor)
    return {"status": "started", "message": "VK мониторинг запущен"}

@router.get("/api/export/excel")
async def export_excel(
    user_id: int,
    cargo_type: str = Query(None),
    lead_type: str = Query(None),
    db = Depends(get_db)
):
    """Экспорт лидов пользователя в Excel"""
    from core.database import Lead
    
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
        headers={"Content-Disposition": f"attachment; filename=leadpotok_{user_id}_{datetime.now().strftime('%Y%m%d')}.xlsx"}
    )

@router.get("/api/stats")
async def get_user_stats(user_id: int, db = Depends(get_db)):
    """Статистика пользователя"""
    from core.database import Lead
    from sqlalchemy import func
    
    stats = db.query(
        func.count(Lead.id).label('total'),
        func.sum(func.case((Lead.lead_type == 'hot', 1), else_=0)).label('hot'),
        func.sum(func.case((Lead.lead_type == 'warm', 1), else_=0)).label('warm'),
    ).filter(Lead.user_id == user_id).first()
    
    return {
        "total": stats.total or 0,
        "hot": stats.hot or 0,
        "warm": stats.warm or 0,
        "cold": (stats.total or 0) - (stats.hot or 0) - (stats.warm or 0)
    }
