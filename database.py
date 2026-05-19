import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey, func, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import hashlib

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String(50), unique=True, index=True)
    username = Column(String(100))
    created_at = Column(DateTime, default=func.now())
    is_active = Column(Boolean, default=True)
    
    # Квоты
    daily_limit = Column(Integer, default=100)
    used_today = Column(Integer, default=0)
    
    leads = relationship("Lead", back_populates="user")

class Lead(Base):
    __tablename__ = "leads"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    
    # Данные лида
    company = Column(String(255), index=True)
    inn = Column(String(20), index=True)  # Для дедупликации
    website = Column(String(255))
    phone = Column(String(50), index=True)
    email = Column(String(100))
    telegram = Column(String(100))
    city = Column(String(100))
    region = Column(String(100))
    
    cargo_type = Column(String(100))
    volume = Column(String(100))
    description = Column(Text)
    
    # Источник
    source = Column(String(100))  # rusprofile, vk, etc.
    source_url = Column(String(500))
    raw_data = Column(Text)  # JSON с исходными данными
    
    # Квалификация
    lead_type = Column(String(20), default="warm")  # hot/warm/cold
    ai_score = Column(Integer)  # 0-100
    ai_analysis = Column(Text)
    
    # Мета
    is_processed = Column(Boolean, default=False)
    notified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now(), index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    user = relationship("User", back_populates="leads")
    
    # Индексы для быстрой дедупликации
    __table_args__ = (
        Index('idx_dedup', 'inn', 'phone', 'website'),
        Index('idx_user_source', 'user_id', 'source', 'created_at'),
    )
    
    def normalize_company(self) -> str:
        """Нормализует название компании для сравнения"""
        if not self.company:
            return ""
        return (self.company
                .lower()
                .replace('ооо', '')
                .replace('ип', '')
                .replace(' ', '')
                .strip('""\''))

def get_db():
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///leads.db")
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_or_create_user(db, telegram_id: str, username: str = None):
    """Создаёт или возвращает пользователя"""
    user = db.query(User).filter(User.telegram_id == str(telegram_id)).first()
    if not user:
        user = User(telegram_id=str(telegram_id), username=username)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def is_global_duplicate(db, lead_data: dict) -> bool:
    """Проверяет дубликат ГЛОБАЛЬНО (между всеми пользователями)"""
    # Нормализуем данные
    phone = lead_data.get('phone', '').replace(' ', '').replace('-', '')
    inn = lead_data.get('inn', '').replace(' ', '')
    website = lead_data.get('website', '').lower().strip('/')
    company_norm = lead_data.get('company', '').lower().replace(' ', '').replace('ооо', '').replace('ип', '')
    
    # Проверяем по ключевым полям
    exists = db.query(Lead).filter(
        (Lead.phone == phone) |
        (Lead.inn == inn) |
        (Lead.website == website) |
        (func.lower(func.replace(func.replace(Lead.company, ' ', ''), 'ооо', '')) == company_norm)
    ).first()
    
    return exists is not None

def add_lead_for_user(db, user_id: int, lead_data: dict):
    """Добавляет лид конкретному пользователю"""
    # Глобальная дедупликация
    if is_global_duplicate(db, lead_data):
        return None, "duplicate"
    
    # Проверка квоты
    user = db.query(User).get(user_id)
    if user.used_today >= user.daily_limit:
        return None, "limit_exceeded"
    
    lead = Lead(
        user_id=user_id,
        company=lead_data.get('company', ''),
        inn=lead_data.get('inn'),
        website=lead_data.get('website'),
        phone=lead_data.get('phone'),
        email=lead_data.get('email'),
        telegram=lead_data.get('telegram'),
        city=lead_data.get('city'),
        region=lead_data.get('region'),
        cargo_type=lead_data.get('cargo_type'),
        volume=lead_data.get('volume'),
        description=lead_data.get('description', ''),
        source=lead_data.get('source', ''),
        source_url=lead_data.get('source_url'),
        raw_data=lead_data.get('raw_data', ''),
        lead_type=lead_data.get('lead_type', 'warm'),
        ai_score=lead_data.get('ai_score'),
        ai_analysis=lead_data.get('ai_analysis')
    )
    
    db.add(lead)
    user.used_today += 1
    db.commit()
    db.refresh(lead)
    
    return lead, "created"
