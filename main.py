import os
import logging
from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from core.database import init_db, get_db, Lead, User, SessionLocal
from scanners.vk_scanner import VKScanner

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

def verify_admin(x_admin_key: str = Header(None)):
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(403, detail="Неверный ключ")

@app.get("/health")
async def health():
    return {"status": "ok", "version": "4.0.0"}

@app.get("/")
async def root():
    try:
        with open("frontend/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except:
        return HTMLResponse(content="<h1>Frontend not found</h1>")

# --- API ENDPOINTS ---

@app.get("/api/leads")
async def get_leads(x_admin_key: str = Header(None), db: SessionLocal = Depends(get_db)):
    verify_admin(x_admin_key)
    leads = db.query(Lead).order_by(Lead.created_at.desc()).limit(50).all()
    return {
        "leads": [
            {
                "id": l.id, "source": l.source, "type": l.lead_type, 
                "score": l.score, "contact": l.contact, 
                "content": l.content[:150] + "...", "url": l.source_url,
                "created_at": l.created_at.isoformat()
            } for l in leads
        ]
    }

@app.get("/api/stats")
async def get_stats(x_admin_key: str = Header(None), db: SessionLocal = Depends(get_db)):
    verify_admin(x_admin_key)
    total = db.query(func.count(Lead.id)).scalar()
    hot = db.query(func.count(Lead.id)).filter(Lead.lead_type == 'hot').scalar()
    return {"total": total, "hot": hot}

@app.post("/api/scan/vk")
async def scan_vk(x_admin_key: str = Header(None)):
    verify_admin(x_admin_key)
    try:
        scanner = VKScanner()
        result = scanner.scan()
        return result
    except Exception as e:
        raise HTTPException(500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 10000)))