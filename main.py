import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from datetime import datetime
from core.database import Base, engine, User, Lead, SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ADMIN_KEY = os.getenv("ADMIN_API_KEY", "superadmin")
logger.info(f"ADMIN_KEY: {ADMIN_KEY}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database ready")
    yield

app = FastAPI(title="AI Lead Agent", version="5.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def verify_admin(x_admin_key: str = Header(None)):
    if not x_admin_key or x_admin_key.strip() != ADMIN_KEY.strip():
        raise HTTPException(403, detail="Invalid API key")

@app.get("/health")
async def health():
    return {"status": "ok", "version": "5.0.0"}

@app.get("/")
async def root():
    try:
        return FileResponse("frontend/index.html")
    except Exception as e:
        logger.error(f"Frontend error: {e}")
        return HTMLResponse(content=f"<h1>Error: {e}</h1>")

@app.post("/api/auth")
async def auth_user(telegram_id: str = Header(), username: str = Header(None), first_name: str = Header(None)):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            user = User(telegram_id=telegram_id, username=username, first_name=first_name)
            db.add(user)
            db.commit()
            db.refresh(user)
        
        is_premium = user.is_premium and user.subscription_end and user.subscription_end > datetime.utcnow()
        week_start = user.week_start or user.created_at
        leads_this_week = db.query(Lead).filter(
            Lead.assigned_user_id == user.id,
            Lead.created_at >= week_start
        ).count()
        
        return {
            "user_id": user.id,
            "is_premium": is_premium,
            "leads_received": leads_this_week,
            "can_receive": is_premium or leads_this_week < 5
        }
    finally:
        db.close()

@app.get("/api/leads")
async def get_leads(x_admin_key: str = Header(None), user_id: int = Header(None)):
    verify_admin(x_admin_key)
    db = SessionLocal()
    try:
        query = db.query(Lead)
        if user_id:
            query = query.filter(Lead.assigned_user_id == user_id)
        leads = query.order_by(Lead.created_at.desc()).limit(50).all()
        return {"leads": [
            {
                "id": l.id, "source": l.source, "type": l.lead_type,
                "score": l.score, "is_hot": l.is_hot, "contact": l.contact,
                "content": l.content[:250], "url": l.source_url,
                "created_at": l.created_at.isoformat()
            } for l in leads
        ]}
    finally:
        db.close()

@app.post("/api/scan/telegram")
async def scan_telegram(x_admin_key: str = Header(None)):
    verify_admin(x_admin_key)
    try:
        from scanners.telegram_scanner import TelegramScanner
        import asyncio
        scanner = TelegramScanner()
        result = asyncio.run(scanner.scan())
        return result
    except Exception as e:
        logger.error(f"Scan error: {e}")
        raise HTTPException(500, detail=str(e))

@app.get("/api/stats")
async def get_stats(x_admin_key: str = Header(None)):
    verify_admin(x_admin_key)
    db = SessionLocal()
    try:
        total = db.query(func.count(Lead.id)).scalar() or 0
        hot = db.query(func.count(Lead.id)).filter(Lead.is_hot == True).scalar() or 0
        return {"total": total, "hot": hot}
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 10000)))