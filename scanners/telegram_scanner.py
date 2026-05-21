import os
import asyncio
import logging
from datetime import datetime
from telethon import TelegramClient
from telethon.tl.types import Message
from services.ai_agent import LogisticsAIAgent
from core.database import get_db, Lead
from sqlalchemy import func

logger = logging.getLogger(__name__)

class TelegramScanner:
    def __init__(self):
        api_id = os.getenv("TELEGRAM_API_ID")
        api_hash = os.getenv("TELEGRAM_API_HASH")
        session_name = os.getenv("TELEGRAM_SESSION", "leadpotok")
        
        logger.info(f"🔑 Initializing Telegram scanner...")
        logger.info(f"API ID: {api_id}")
        logger.info(f"API Hash: {api_hash[:10] if api_hash else None}...")
        logger.info(f"Session: {session_name}")
        
        if not api_id or not api_hash:
            raise ValueError("TELEGRAM credentials not set")
        
        self.client = TelegramClient(session_name, int(api_id), api_hash)
        self.ai = LogisticsAIAgent()
        
        self.queries = [
            "ищу доставку из китая", "нужно карго", "доставка груза китай",
            "ищу перевозчика китай", "сколько стоит доставка из китая",
            "нужно привезти из китая", "ищу поставщика китай",
            "закупка в китае доставка", "карго из китая срочно",
            "доставка 1688", "доставка таобао", "контейнер из китая",
            "сборный груз китай", "логистика китай россия"
        ]
        
        self.channels = [
            "kitaidostavka", "expresschinakargo", "simple_logistick",
            "kitaicargo", "cargo352", "cargo.china.russ", "chinawaylog",
            "onlinecargo", "gomarkt_official", "ussuri_cargo", "asiaforum",
            "vilspik", "wintonasia", "chinarynok", "zz_biz",
            "chinadeals_gera", "sellerwb_ru", "udalenka",
            "sellery_marketpleysov", "sellercapital", "otzyvzatovar",
            "soyuz_sellerov", "ozonsellers"
        ]

    async def scan(self) -> dict:
        found_count = 0
        hot_count = 0
        errors = 0
        
        try:
            await self.client.start()
            logger.info("✅ Telegram client started")
            
            with next(get_db()) as db:
                # Поиск по каналам
                for channel in self.channels[:5]:  # Первые 5 для теста
                    try:
                        logger.info(f"🔍 Scanning channel: {channel}")
                        entity = await self.client.get_entity(channel)
                        logger.info(f"✓ Found: {entity.title}")
                        
                        async for message in self.client.iter_messages(entity, limit=20):
                            if await self._process_message(db, message):
                                found_count += 1
                                result = self.ai.analyze(message.text or "", "Telegram")
                                if result and result.get("is_hot"):
                                    hot_count += 1
                                    
                    except Exception as e:
                        logger.warning(f"❌ Channel {channel} error: {e}")
                        errors += 1
                
                logger.info(f"✅ Scan complete: {found_count} leads, {hot_count} hot")
                
        except Exception as e:
            logger.error(f"❌ Scan error: {e}")
            raise
        finally:
            await self.client.disconnect()
        
        return {"status": "success", "found": found_count, "hot": hot_count, "errors": errors}

    async def _process_message(self, db, message: Message) -> bool:
        text = message.text
        if not text or len(text) < 30:
            return False

        result = self.ai.analyze(text, source="Telegram")
        if not result or not result.get("is_lead"):
            return False

        sender = await message.get_sender()
        contact = sender.username if sender and hasattr(sender, 'username') else None
        
        lead = Lead(
            source="Telegram",
            source_url=f"https://t.me/c/{message.chat_id}/{message.id}" if message.chat_id else "",
            author=contact or str(message.sender_id),
            contact=f"@{contact}" if contact else "",
            content=text[:1000],
            lead_type=result.get("type", "cold"),
            score=result.get("score", 0),
            is_hot=result.get("is_hot", False)
        )
        db.add(lead)
        db.commit()
        
        logger.info(f"✅ New lead: score={lead.score}, type={lead.lead_type}")
        return True