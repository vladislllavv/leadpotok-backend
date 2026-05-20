import os
import logging
from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from core.database import init_db, get_db, Lead, SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Lead Agent", version="4.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ADMIN_KEY = os.getenv("ADMIN_API_KEY", "superadmin")

@app.on_event("startup")
async def startup_event():
    init_db()
    logger.info("✅ Database initialized")

def verify_admin(x_admin_key: str = Header(None)):
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(403, detail="Неверный ключ")

@app.get("/health")
async def health():
    return {"status": "ok", "version": "4.0.0"}

@app.get("/")
async def root():
    try:
        return FileResponse("frontend/index.html")
    except Exception as e:
        logger.error(f"Frontend error: {e}")
        return HTMLResponse(content=f"<h1>❌ Frontend not found: {e}</h1><p>Check logs</p>")

@app.get("/api/stats")
async def get_stats(x_admin_key: str = Header(None)):
    verify_admin(x_admin_key)
    total = SessionLocal().query(func.count(Lead.id)).scalar() or 0
    hot = SessionLocal().query(func.count(Lead.id)).filter(Lead.lead_type == 'hot').scalar() or 0
    return {"total": total, "hot": hot}

@app.get("/api/leads")
async def get_leads(x_admin_key: str = Header(None)):
    verify_admin(x_admin_key)
    db = SessionLocal()
    leads = db.query(Lead).order_by(Lead.created_at.desc()).limit(50).all()
    return {
        "leads": [
            {
                "id": l.id, "source": l.source, "type": l.lead_type, 
                "score": l.score, "contact": l.contact, 
                "content": l.content[:200] + "..." if len(l.content) > 200 else l.content,
                "url": l.source_url,
                "created_at": l.created_at.isoformat()
            } for l in leads
        ]
    }

@app.post("/api/scan/vk")
async def scan_vk(x_admin_key: str = Header(None)):
    verify_admin(x_admin_key)
    try:
        from scanners.vk_scanner import VKScanner
        scanner = VKScanner()
        result = scanner.scan()
        return result
    except Exception as e:
        logger.error(f"Scan error: {e}")
        raise HTTPException(500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 10000)))