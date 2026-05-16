from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from security import validate_telegram_data
from database import init_db, get_leads

load_dotenv()
app = FastAPI(title="ЛидПоток API")

CORS_ORIGIN = os.getenv("CORS_ORIGIN", "https://t.me")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[CORS_ORIGIN],
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["*"],
)

class LeadRequest(BaseModel):
    init_data: str
    cargo_type: str = None
    region: str = None

init_db()

@app.post("/api/leads")
async def get_leads_api(request: LeadRequest):
    user = validate_telegram_data(request.init_data, os.getenv("BOT_TOKEN"))
    if not user:
        raise HTTPException(status_code=403, detail="Невалидные данные Telegram")
    leads = get_leads(cargo_type=request.cargo_type, city=request.region)
    return {"status": "ok", "user_id": user.get("id"), "leads": leads}

@app.get("/health")
def health():
    return {"status": "running"}
