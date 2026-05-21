import os
import asyncio
import logging
from datetime import datetime, timedelta
from telethon import TelegramClient
from telethon.tl.types import Message
from services.ai_agent import LogisticsAIAgent
from core.database import get_db, Lead, User
from sqlalchemy import func

logger = logging.getLogger(__name__)

class TelegramScanner:
    def __init__(self):
        api_id = os.getenv("TELEGRAM_API_ID")
        api_hash = os.getenv("TELEGRAM_API_HASH")
        session_name = os.getenv("TELEGRAM_SESSION", "leadpotok")
        
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
        await self.client.start()
        
        with next(get_db()) as db:
            # Поиск по каналам
            for channel in self.channels:
                try:
                    entity = await self.client.get_entity(channel)
                    async for message in self.client.iter_messages(entity, limit=50):
                        if await self._process_message(db, message):
                            found_count += 1
                            if message.text and len(message.text) > 100:
                                result = self.ai.analyze(message.text, "Telegram")
                                if result and result.get("is_hot"):
                                    hot_count += 1
                except Exception as e:
                    logger.debug(f"Channel {channel} error: {e}")
            
            # Глобальный поиск
            for query in self.queries:
                try:
                    async for message in self.client.iter_messages(None, search=query, limit=30):
                        if await self._process_message(db, message):
                            found_count += 1
                except:
                    pass
        
        await self.client.disconnect()
        logger.info(f"✅ Scan: {found_count} leads, {hot_count} hot")
        return {"status": "success", "found": found_count, "hot": hot_count}

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
        
        # Пуш-уведомление для горячих
        if lead.is_hot:
            await self._notify_hot_lead(db, lead)
        
        return True

    async def _notify_hot_lead(self, db, lead: Lead):
        """Отправка пуш-уведомления всем активным пользователям"""
        users = db.query(User).filter(
            User.is_premium == True,
            User.subscription_end > datetime.utcnow()
        ).all()
        
        for user in users:
            try:
                await self.client.send_message(
                    int(user.telegram_id),
                    f"🔥 ГОРЯЧИЙ ЛИД!\n\n"
                    f"Score: {lead.score}/100\n"
                    f"Контакт: {lead.contact or 'Не указан'}\n"
                    f"Суть: {lead.content[:150]}..."
                )
                lead.notification_sent = True
            except Exception as e:
                logger.error(f"Notify error: {e}")