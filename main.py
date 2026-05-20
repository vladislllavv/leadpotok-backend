import os, logging
from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from core.database import init_db, get_db, Lead

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="AI Lead Agent", version="4.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
ADMIN_KEY = os.getenv("ADMIN_API_KEY", "superadmin")

@app.on_event("startup")
async def startup(): init_db()

def check_key(x_admin_key: str = Header(None)):
    if x_admin_key != ADMIN_KEY: raise HTTPException(403, detail="Неверный ключ")

@app.get("/health")
async def health(): return {"status": "ok", "version": "4.0.0"}

@app.get("/")
async def root(): return FileResponse("frontend/index.html")

@app.get("/api/stats")
async def stats(x_admin_key: str = Header(None), db = Depends(get_db)):
    check_key(x_admin_key)
    return {"total": db.query(func.count(Lead.id)).scalar() or 0, "hot": db.query(func.count(Lead.id)).filter(Lead.lead_type == 'hot').scalar() or 0}

@app.get("/api/leads")
async def get_leads(x_admin_key: str = Header(None), db = Depends(get_db)):
    check_key(x_admin_key)
    items = db.query(Lead).order_by(Lead.created_at.desc()).limit(50).all()
    return {"leads": [{"id": i.id, "source": i.source, "type": i.lead_type, "contact": i.contact, "content": i.content[:200], "url": i.source_url, "created_at": i.created_at.isoformat()} for i in items]}

@app.post("/api/scan/vk")
async def scan_vk(x_admin_key: str = Header(None)):
    check_key(x_admin_key)
    try:
        from scanners.vk_scanner import VKScanner
        return VKScanner().scan()
    except Exception as e:
        raise HTTPException(500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
