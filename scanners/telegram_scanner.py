import os
import logging
from telethon import TelegramClient
from telethon.tl.types import Message
from services.ai_agent import LogisticsAIAgent
from core.database import SessionLocal, Lead

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
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.notify_chat_id = os.getenv("TELEGRAM_NOTIFY_CHAT_ID")
        self.hot_score_threshold = int(os.getenv("HOT_LEAD_SCORE_THRESHOLD", 80))
        self.channel_search_limit = int(os.getenv("TELEGRAM_CHANNEL_LIMIT", 30))
        self.query_search_limit = int(os.getenv("TELEGRAM_SEARCH_LIMIT", 20))
        
        self.queries = [
            "ищу доставку из китая", "нужно карго", "доставка груза китай",
            "ищу перевозчика китай", "сколько стоит доставка из китая",
            "нужно привезти из китая", "ищу поставщика китай",
            "карго из китая срочно", "доставка 1688", "доставка таобао",
            "срочно нужен перевозчик", "доставка сборного груза", "logistics china",
            "доставка из guangzhou", "помощь с таможней", "груз из shenzhen",
            "доставка FCL LCL", "таможенное оформление", "нужна доставка из Китая",
            "грузоперевозки из китая", "товар из китая", "экспресс доставка из китая"
        ]
        
        self.channels = [
            "kitaidostavka", "expresschinakargo", "simple_logistick",
            "kitaicargo", "cargo352", "cargo.china.russ", "chinawaylog",
            "onlinecargo", "gomarkt_official", "ussuri_cargo", "asiaforum",
            "vilspik", "wintonasia", "chinarynok", "zz_biz",
            "chinadeals_gera", "sellerwb_ru", "udalenka",
            "sellery_marketpleysov", "sellercapital", "otzyvzatovar",
            "soyuz_sellerov", "ozonsellers", "china_logistics",
            "china_cargo", "logistics_news", "cargo_china",
            "china_express", "china_import", "china_export",
            "china_trade", "china_business", "asia_shipping",
            "cargo_for_business", "freight_china", "china_supply",
            "china_carrier", "china_freight", "cargoru",
            "china_trade_info", "china_delivery", "china_port",
            "cargo_world", "shipping_china", "china_ecommerce",
            "globallogistics", "asia_freight", "china_terminal"
        ]

    async def scan(self) -> dict:
        found_count = 0
        hot_count = 0
        
        await self.client.start()
        
        with SessionLocal() as db:
            for channel in self.channels:
                try:
                    logger.info(f"Scanning: {channel}")
                    entity = await self.client.get_entity(channel)
                    
                    async for message in self.client.iter_messages(entity, limit=self.channel_search_limit):
                        lead_hot = await self._process_message(db, message)
                        if lead_hot is not None:
                            found_count += 1
                            if lead_hot:
                                hot_count += 1
                            if message and message.text:
                                logger.debug(f"Lead message id={message.id} added")
                except Exception as e:
                    logger.warning(f"Channel {channel} error: {e}")
            
            for query in self.queries:
                try:
                    async for message in self.client.iter_messages(None, search=query, limit=self.query_search_limit):
                        lead_hot = await self._process_message(db, message)
                        if lead_hot is not None:
                            found_count += 1
                            if lead_hot:
                                hot_count += 1
                except Exception as e:
                    logger.warning(f"Search query error: {e}")

        await self.client.disconnect()
        logger.info(f"Scan complete: {found_count} leads, {hot_count} hot")
        return {"status": "success", "found": found_count, "hot": hot_count}

    def _notify_hot_lead(self, lead: Lead):
        if not self.bot_token or not self.notify_chat_id:
            return

        try:
            import json
            from urllib import request, parse

            text = (
                f"🔥 Горячий лид\n"
                f"Источник: {lead.source}\n"
                f"Скор: {lead.score}/100\n"
                f"Тип: {lead.lead_type}\n"
                f"Контакт: {lead.contact or 'Нет контакта'}\n"
                f"Ссылка: {lead.source_url}\n"
                f"Текст: {lead.content[:300]}"
            )
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = json.dumps({
                "chat_id": self.notify_chat_id,
                "text": text,
                "parse_mode": "HTML"
            }).encode("utf-8")

            req = request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            request.urlopen(req, timeout=15)
            logger.info("Notification sent for hot lead")
        except Exception as exc:
            logger.warning(f"Failed to send hot lead notification: {exc}")

    async def _process_message(self, db, message: Message):
        text = message.text
        if not text or len(text) < 30:
            return None

        result = self.ai.analyze(text, source="Telegram")
        if not result or not result.get("is_lead"):
            return None

        source_url = f"https://t.me/c/{message.chat_id}/{message.id}" if message.chat_id else ""
        if source_url:
            existing = db.query(Lead).filter(Lead.source == "Telegram", Lead.source_url == source_url).first()
            if existing:
                return None

        sender = await message.get_sender()
        contact = sender.username if sender and hasattr(sender, 'username') else None
        
        lead = Lead(
            source="Telegram",
            source_url=source_url,
            author=contact or str(message.sender_id),
            contact=f"@{contact}" if contact else "",
            content=text[:1000],
            lead_type=result.get("type", "cold"),
            score=result.get("score", 0),
            is_hot=result.get("is_hot", False),
            notification_sent=False
        )
        db.add(lead)
        db.commit()

        if lead.is_hot:
            logger.info(f"🔥 HOT lead found! Score: {lead.score}")
            self._notify_hot_lead(lead)
            lead.notification_sent = True
            db.commit()

        return lead.is_hot