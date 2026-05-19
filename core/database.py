import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///leads.db")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String(50), unique=True)
    username = Column(String(100))
    created_at = Column(DateTime, default=func.now())
    daily_limit = Column(Integer, default=100)
    used_today = Column(Integer, default=0)
    leads = relationship("Lead", back_populates="user")

class Lead(Base):
    __tablename__ = "leads"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    company = Column(String(255))
    phone = Column(String(50))
    city = Column(String(100))
    lead_type = Column(String(20), default="warm")
    created_at = Column(DateTime, default=func.now())
    user = relationship("User", back_populates="leads")

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_or_create_user(db, telegram_id: str, username: str = None):
    user = db.query(User).filter(User.telegram_id == str(telegram_id)).first()
    if not user:
        user = User(telegram_id=str(telegram_id), username=username)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user