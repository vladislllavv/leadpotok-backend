# core/database.py
import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey, func, Index, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)
Base = declarative_base()

# URL базы данных из переменных окружения
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///leads.db")

def create_engine_with_retries(db_url: str, max_retries: int = 3):
    """Создаёт движок БД с повторными попытками (для облака)"""
    for attempt in range(max_retries):
        try:
            engine = create_engine(
                db_url,
                pool_pre_ping=True,  # Проверка соединения перед использованием
                pool_recycle=3600,   # Переподключение каждые 1 час
                echo=False           # Отключить логирование SQL в продакшене
            )
            # Тестовое подключение
            with engine.connect() as conn:
                conn.execute(func.now())
            logger.info(f"✅ Database connected: {db_url[:30]}...")
            return engine
        except Exception as e:
            logger.warning(f"⚠️ DB connection attempt {attempt+1} failed: {e}")
            if attempt == max_retries - 1:
                raise
            import time
            time.sleep(2 ** attempt)  # Exponential backoff

# Создаём движок
engine = create_engine_with_retries(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# === МОДЕЛИ ===

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String(50), unique=True, index=True, nullable=False)
    username = Column(String(100))
    created_at = Column(DateTime, default=func.now())
    is_active = Column(Boolean, default=True)
    
    # Квоты
    daily_limit = Column(Integer, default=100)
    used_today = Column(Integer, default=0)
    last_reset = Column(DateTime, default=func.now())
    
    leads = relationship("Lead", back_populates="user", cascade="all, delete-orphan")

class Lead(Base):
    __tablename__ = "leads"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)  # nullable для системных лидов
    
    # Данные лида
    company = Column(String(255), index=True)
    inn = Column(String(20), index=True)
    website = Column(String(255))
    phone = Column(String(50), index=True)
    email = Column(String(100))
    telegram = Column(String(100))
    city = Column(String(100))
    region = Column(String(100))
    
    cargo_type = Column(String(100), default="любые")
    volume = Column(String(100))
    description = Column(Text)
    
    # Источник
    source = Column(String(100), index=True)
    source_url = Column(String(500))
    raw_data = Column(Text)
    
    # Квалификация
    lead_type = Column(String(20), default="warm")  # hot/warm/cold
    ai_score = Column(Integer, default=50)
    ai_analysis = Column(Text)
    
    # Мета
    is_processed = Column(Boolean, default=False)
    notified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now(), index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    user = relationship("User", back_populates="leads")
    
    # Индексы для дедупликации
    __table_args__ = (
        Index('idx_dedup_global', 'inn', 'phone', 'website', 'company'),
        Index('idx_user_source', 'user_id', 'source', 'created_at'),
    )

# === ФУНКЦИИ ===

def init_db():
    """Инициализирует БД: создаёт таблицы, если их нет"""
    logger.info("🗄️ Initializing database...")
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Tables created/verified")

def get_db():
    """Зависимость для получения сессии БД в FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_or_create_user(db, telegram_id: str, username: str = None):
    """Создаёт или возвращает пользователя по Telegram ID"""
    user = db.query(User).filter(User.telegram_id == str(telegram_id)).first()
    if not user:
        logger.info(f"🆕 Creating new user: {telegram_id}")
        user = User(telegram_id=str(telegram_id), username=username)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def reset_daily_quota_if_needed(db, user: User):
    """Сбрасывает квоту, если прошёл день"""
    now = datetime.now()
    if user.last_reset:
        days_passed = (now - user.last_reset).days
        if days_passed >= 1:
            user.used_today = 0
            user.last_reset = now
            logger.info(f"🔄 Reset quota for user {user.id}")

def is_global_duplicate(db, lead_data: dict) -> bool:
    """Проверяет дубликат ГЛОБАЛЬНО (между всеми пользователями)"""
    phone = lead_data.get('phone', '').replace(' ', '').replace('-', '')
    inn = lead_data.get('inn', '').replace(' ', '')
    website = lead_data.get('website', '').lower().strip('/')
    company_norm = lead_data.get('company', '').lower().replace(' ', '').replace('ооо', '').replace('ип', '').strip('""\'')
    
    # Проверка по ключевым полям
    query = db.query(Lead)
    if phone:
        query = query.filter(Lead.phone == phone)
    if inn:
        query = query.filter(Lead.inn == inn)
    if website:
        query = query.filter(Lead.website == website)
    
    # Проверка по нормализованному названию компании
    existing = query.first()
    if existing:
        return True
    
    # Дополнительная проверка по названию (менее строгая)
    if company_norm and len(company_norm) > 5:
        similar = db.query(Lead).filter(
            func.lower(func.replace(func.replace(Lead.company, ' ', ''), 'ооо', '')) == company_norm
        ).first()
        if similar:
            return True
    
    return False

def add_lead_for_user(db, user_id: int, lead_data: dict):
    """Добавляет лид конкретному пользователю с проверкой квот и дублей"""
    # Глобальная дедупликация
    if is_global_duplicate(db, lead_data):
        return None, "duplicate"
    
    # Проверка пользователя
    user = db.query(User).get(user_id)
    if not user:
        return None, "user_not_found"
    
    # Сброс квоты если нужно
    reset_daily_quota_if_needed(db, user)
    
    # Проверка лимита
    if user.used_today >= user.daily_limit:
        return None, "limit_exceeded"
    
    # Создание лида
    lead = Lead(
        user_id=user_id,
        company=lead_data.get('company', '')[:255],
        inn=lead_data.get('inn'),
        website=lead_data.get('website'),
        phone=lead_data.get('phone'),
        email=lead_data.get('email'),
        telegram=lead_data.get('telegram'),
        city=lead_data.get('city'),
        region=lead_data.get('region'),
        cargo_type=lead_data.get('cargo_type', 'любые'),
        volume=lead_data.get('volume'),
        description=lead_data.get('description', '')[:2000],
        source=lead_data.get('source', ''),
        source_url=lead_data.get('source_url', ''),
        raw_data=lead_data.get('raw_data', ''),
        lead_type=lead_data.get('lead_type', 'warm'),
        ai_score=lead_data.get('ai_score', 50),
        ai_analysis=lead_data.get('ai_analysis', '')
    )
    
    db.add(lead)
    user.used_today += 1
    db.commit()
    db.refresh(lead)
    
    return lead, "created"

def get_leads(db, user_id: int = None, cargo_type: str = None, city: str = None, 
              lead_type: str = None, limit: int = 50, global_scope: bool = False):
    """Получает лиды с фильтрами"""
    query = db.query(Lead)
    
    if not global_scope and user_id:
        query = query.filter(Lead.user_id == user_id)
    
    if cargo_type and cargo_type != "любые":
        query = query.filter(Lead.cargo_type == cargo_type)
    if city:
        query = query.filter(Lead.city.ilike(f"%{city}%"))
    if lead_type:
        query = query.filter(Lead.lead_type == lead_type)
    
    return query.order_by(
        Lead.lead_type.desc(),
        Lead.created_at.desc()
    ).limit(limit).all()

def get_stats(db, user_id: int = None):
    """Возвращает статистику"""
    from sqlalchemy import func
    
    query = db.query(
        func.count(Lead.id).label('total'),
        func.sum(func.case((Lead.lead_type == 'hot', 1), else_=0)).label('hot'),
        func.sum(func.case((Lead.lead_type == 'warm', 1), else_=0)).label('warm'),
    )
    
    if user_id:
        query = query.filter(Lead.user_id == user_id)
    
    stats = query.first()
    total = stats.total or 0
    hot = stats.hot or 0
    warm = stats.warm or 0
    
    return {
        "total": total,
        "hot": hot,
        "warm": warm,
        "cold": total - hot - warm
    }