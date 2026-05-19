import os
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="LeadPotok", version="2.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ADMIN_KEY = os.getenv("ADMIN_API_KEY", "test_key_123")

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "2.1.0", "env_admin_key": bool(os.getenv("ADMIN_API_KEY"))}

@app.get("/")
async def serve_frontend():
    try:
        with open("frontend/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except Exception as e:
        return HTMLResponse(content=f"<h1>Ошибка: {e}</h1>")

@app.get("/api/admin/stats")
async def get_stats(x_admin_key: str = Header(None)):
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(403, detail="Неверный ключ")
    return {"total": 12, "hot": 4, "warm": 3, "today": 5}

@app.get("/api/admin/leads")
async def get_leads(x_admin_key: str = Header(None)):
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(403, detail="Неверный ключ")
    return {
        "leads": [
            {"id": 1, "company": "ООО Восток-Трейдинг", "phone": "+79991234567", "city": "Москва", "lead_type": "hot", "created_at": "2024-05-19T10:00:00"},
            {"id": 2, "company": "ИП Сидоров", "phone": "+79160000000", "city": "Казань", "lead_type": "warm", "created_at": "2024-05-18T15:30:00"}
        ]
    }

@app.post("/api/admin/parse/vk")
async def parse_vk(x_admin_key: str = Header(None)):
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(403, detail="Неверный ключ")
    return {"status": "started", "message": "✅ Парсинг VK запущен (тестовый режим)"}

@app.get("/api/admin/export/excel")
async def export_excel(x_admin_key: str = Header(None)):
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(403, detail="Неверный ключ")
    return HTMLResponse(content="MOCK_EXCEL_FILE", media_type="application/vnd.ms-excel")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
