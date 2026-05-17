import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

load_dotenv()

# Выбираем базу: PostgreSQL для облака, SQLite для локалки
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    engine = create_engine(DATABASE_URL)
else:
    engine = create_engine("sqlite:///leads.db", connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Lead(Base):
    __tablename__ = "leads"
    
    id = Column(Integer, primary_key=True, index=True)
    company = Column(String(255), index=True)
    contact = Column(String(255))
    phone = Column(String(50))
    city = Column(String(100))
    cargo_type = Column(String(100))
    volume = Column(String(100))
    source = Column(String(255))
    reason = Column(Text)
    hot_level = Column(String(20), default='warm')
    created_at = Column(DateTime, default=func.now())

# Создаём таблицы
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def add_lead(db, company: str, contact: str = '', phone: str = '', city: str = '', 
             cargo_type: str = 'любые', volume: str = '', source: str = '', 
             reason: str = '', hot_level: str = 'warm'):
    """Добавляет лид в базу"""
    lead = Lead(
        company=company, contact=contact, phone=phone, city=city,
        cargo_type=cargo_type, volume=volume, source=source,
        reason=reason, hot_level=hot_level
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead

def is_duplicate(db, phone: str, company: str) -> bool:
    """Проверяет дубликаты"""
    clean_company = company.replace(' ', '').lower()[:50]
    exists = db.query(Lead).filter(
        (Lead.phone == phone) | 
        (func.lower(func.replace(Lead.company, ' ', '')).like(f"%{clean_company}%"))
    ).first()
    return exists is not None

def get_leads(db, cargo_type: str = None, city: str = None, limit: int = 100):
    """Получает лиды с фильтрами"""
    query = db.query(Lead)
    if cargo_type and cargo_type != "любые":
        query = query.filter(Lead.cargo_type == cargo_type)
    if city:
        query = query.filter(Lead.city.ilike(f"%{city}%"))
    return query.order_by(Lead.hot_level.desc(), Lead.created_at.desc()).limit(limit).all()

def get_stats(db):
    """Статистика для админки"""
    total = db.query(Lead).count()
    hot = db.query(Lead).filter(Lead.hot_level == 'hot').count()
    today = db.query(Lead).filter(
        func.date(Lead.created_at) == func.date('now')
    ).count()
    return {"total": total, "hot": hot, "today": today}
