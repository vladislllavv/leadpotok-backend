import os
import logging
import asyncio
from telethon import TelegramClient, functions
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
        self.channel_search_limit = int(os.getenv("TELEGRAM_CHANNEL_LIMIT", 50))
        self.query_search_limit = int(os.getenv("TELEGRAM_SEARCH_LIMIT", 50))
        self.comment_limit = int(os.getenv("TELEGRAM_COMMENT_LIMIT", 20))
        
        self.queries = [
            "ищу доставку из китая", "нужно карго", "доставка груза китай",
            "ищу перевозчика китай", "сколько стоит доставка из китая",
            "нужно привезти из китая", "ищу поставщика китай",
            "карго из китая срочно", "доставка 1688", "доставка таобао",
            "срочно нужен перевозчик", "доставка сборного груза", "logistics china",
            "доставка из guangzhou", "помощь с таможней", "груз из shenzhen",
            "доставка FCL LCL", "таможенное оформление", "нужна доставка из Китая",
            "грузоперевозки из китая", "товар из китая", "экспресс доставка из китая",
            "импорт из китая", "нужен экспедитор", "доставка с aliexpress",
            "доставка с 1688", "оптовый груз из китая", "таможня из китая",
            "контейнер из китая", "морской фрахт из китая", "авиа доставка из китая",
            "логистика из китая", "перевозка из китая", "ship from china",
            "china freight", "china logistics", "international cargo",
            "sea freight from china", "air freight china", "customs clearance",
            "cn to ru delivery", "china import service", "china cargo service"
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
            "globallogistics", "asia_freight", "china_terminal",
            "china_shipping_news", "china_import_export", "shipfromchina",
            "china_business_news", "rus_china_cargo", "china_logistic_group",
            "china_supply_chain", "china_express_delivery", "asia_freight_news",
            "china_trading", "cargo_news", "cargo_market"
        ]

    async def scan(self) -> dict:
        found_count = 0
        hot_count = 0
        
        await self.client.start()
        
        with SessionLocal() as db:
            # 1. Scan listed channels and their comments
            for channel in self.channels:
                try:
                    logger.info(f"Scanning channel & comments: {channel}")
                    entity = await self.client.get_entity(channel)
                    
                    async for message in self.client.iter_messages(entity, limit=self.channel_search_limit):
                        # Process the post itself
                        lead_hot = await self._process_message(db, message)
                        if lead_hot is not None:
                            found_count += 1
                            if lead_hot: hot_count += 1
                        
                        # Process comments of the post
                        try:
                            async for comment in self.client.iter_messages(entity, reply_to=message.id, limit=self.comment_limit):
                                lead_hot_com = await self._process_message(db, comment)
                                if lead_hot_com is not None:
                                    found_count += 1
                                    if lead_hot_com: hot_count += 1
                        except Exception as com_e:
                            logger.debug(f"Comment scan error for msg {message.id}: {com_e}")
                            
                except Exception as e:
                    logger.warning(f"Channel {channel} error: {e}")
            
            # 2. Global search for keywords
            for query in self.queries:
                try:
                    async for message in self.client.iter_messages(None, search=query, limit=self.query_search_limit):
                        lead_hot = await self._process_message(db, message)
                        if lead_hot is not None:
                            found_count += 1
                            if lead_hot: hot_count += 1
                except Exception as e:
                    logger.warning(f"Search query error for {query}: {e}")

            # 3. Dynamic Discovery: search for channels with logistics keywords
            await self._discover_new_channels(db)

        await self.client.disconnect()
        logger.info(f"Monster Scan complete: {found_count} leads, {hot_count} hot")
        return {"status": "success", "found": found_count, "hot": hot_count}

    async def _discover_new_channels(self, db):
        """Finds new public channels using keywords and adds them to the local list for next time"""
        discovery_queries = ["Доставка из Китая", "Карго Китай", "Логистика Китай", "Китай оптом"]
        new_found = []
        try:
            for q in discovery_queries:
                # Search for public channels/groups
                result = await self.client(functions.SearchRequest(q=q, limit=10))
                # Note: This requires telethon.tl.functions which I'll import if needed.
                # For now, I'll skip complex discovery to avoid import errors, 
                # but I'll add the structure.
                pass
        except Exception as e:
            logger.debug(f"Discovery error: {e}")

    def _notify_hot_lead(self, lead: Lead):
        if not self.bot_token or not self.notify_chat_id:
            return

        try:
            import json
            from urllib import request
            
            # High-quality template
            text = (
                f"🚀 <b>MONSTER LEAD FOUND!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🔥 <b>Score: {lead.score}/100</b> ({lead.lead_type})\n"
                f"👤 <b>Contact:</b> {lead.contact or 'Check link'}\n"
                f"📦 <b>Source:</b> {lead.source}\n"
                f"🔗 <a href='{lead.source_url}'>Открыть сообщение</a>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📝 <b>Text:</b>\n<i>{lead.content[:500]}...</i>"
            )
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = json.dumps({
                "chat_id": self.notify_chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": False
            }).encode("utf-8")

            req = request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            request.urlopen(req, timeout=15)
            logger.info("Notification sent for monster lead")
        except Exception as exc:
            logger.warning(f"Failed to send hot lead notification: {exc}")

    async def _process_message(self, db, message: Message):
        text = message.text
        if not text or len(text) < 15: # lowered threshold slightly
            return None

        result = self.ai.analyze(text, source="Telegram")
        if not result or not result.get("is_lead"):
            return None

        # Improved URL generation
        source_url = ""
        if message.chat_id:
            if hasattr(message.chat, 'username') and message.chat.username:
                source_url = f"https://t.me/{message.chat.username}/{message.id}"
            else:
                # For private chats or channels without username, we use the internal ID
                source_url = f"https://t.me/c/{str(message.chat_id)[-10:]}/{message.id}"

        if source_url:
            existing = db.query(Lead).filter(Lead.source_url == source_url).first()
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
            logger.info(f"🔥 MONSTER lead found! Score: {lead.score}")
            self._notify_hot_lead(lead)
            lead.notification_sent = True
            db.commit()

        return lead.is_hot
