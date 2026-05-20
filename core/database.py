import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///leads.db")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Lead(Base):
    __tablename__ = "leads"
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50))  # VK, Telegram
    source_url = Column(String(500))
    author = Column(String(100)) # Кто написал
    contact = Column(String(100)) # Телефон/ТГ
    content = Column(Text) # Текст сообщения
    lead_type = Column(String(20), default="cold") # hot, warm, cold
    score = Column(Float, default=0.0) # Уверенность AI (0-100)
    created_at = Column(DateTime, default=datetime.utcnow)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String(50), unique=True)
    username = Column(String(100))

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()