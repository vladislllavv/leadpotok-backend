import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///leads.db")
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String(50), unique=True, index=True)
    username = Column(String(100))
    first_name = Column(String(100))
    is_premium = Column(Boolean, default=False)
    subscription_end = Column(DateTime, nullable=True)
    leads_received = Column(Integer, default=0)
    week_start = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    leads = relationship("Lead", back_populates="assigned_user")

class Lead(Base):
    __tablename__ = "leads"
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50), default="Telegram")
    source_url = Column(String(500))
    author = Column(String(100))
    contact = Column(String(100))
    content = Column(Text)
    lead_type = Column(String(20), default="cold")
    score = Column(Integer, default=0)
    is_hot = Column(Boolean, default=False)
    notification_sent = Column(Boolean, default=False)
    assigned_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    assigned_user = relationship("User", back_populates="leads")

class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    plan = Column(String(20))
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime)
    is_active = Column(Boolean, default=True)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()