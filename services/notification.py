import asyncio
import logging
from datetime import datetime
from typing import Optional
from aiogram import Bot, types

logger = logging.getLogger(__name__)

class NotificationService:
    """Умная система уведомлений"""
    
    def __init__(self, bot_token: str):
        self.bot = Bot(token=bot_token)
        self.hot_queue = asyncio.Queue()  # Мгновенные
        self.warm_queue = asyncio.Queue()  # Раз в 4 часа
        self.cold_queue = asyncio.Queue()  # Ежедневный дайджест
        
        # Кэш отправленных уведомлений (чтобы не спамить)
        self.sent_cache = set()
    
    async def send_hot_lead(self, chat_id: int, lead: dict):
        """Мгновенное уведомление для горячего лида"""
        cache_key = f"hot_{lead.get('source_url')}_{lead.get('phone')}"
        if cache_key in self.sent_cache:
            return
        
        message = self._format_hot_message(lead)
        
        # Кнопки для быстрого действия
        keyboard = types.InlineKeyboardMarkup()
        if lead.get('phone'):
            keyboard.add(types.InlineKeyboardButton(
                f"📞 {lead['phone']}", 
                url=f"tel:{lead['phone'].replace(' ', '')}"
            ))
        if lead.get('telegram'):
            keyboard.add(types.InlineKeyboardButton(
                "✈️ Telegram", 
                url=f"https://t.me/{lead['telegram'].lstrip('@')}"
            ))
        if lead.get('source_url'):
            keyboard.add(types.InlineKeyboardButton(
                "🔗 Открыть источник", 
                url=lead['source_url']
            ))
        
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            self.sent_cache.add(cache_key)
            logger.info(f"Hot notification sent to {chat_id}")
        except Exception as e:
            logger.error(f"Failed to send hot notification: {e}")
    
    def _format_hot_message(self, lead: dict) -> str:
        """Форматирует сообщение для горячего лида"""
        emoji = "🔥"
        company = lead.get('company') or "Частное лицо"
        contacts = lead.get('phone') or lead.get('telegram') or "Контакты не найдены"
        
        return f"""
{emoji} <b>ГОРЯЧИЙ ЛИД</b>

<b>{company}</b>
📍 {lead.get('city', 'Город не указан')} | 📦 {lead.get('volume', 'Объём не указан')}
📱 {contacts}

<b>Анализ:</b>
{lead.get('ai_analysis', lead.get('description', '')[:200])}

💬 <b>Цитата:</b>
"{lead.get('description', '')[:150]}..."

🔗 Источник: <a href="{lead.get('source_url', '#')}">VK Пост</a>
🕐 {datetime.now().strftime('%H:%M')}
        """.strip()
    
    async def process_queues(self):
        """Фоновая обработка очередей (запустить как задачу Celery)"""
        while True:
            # Горячие - мгновенно
            while not self.hot_queue.empty():
                chat_id, lead = await self.hot_queue.get()
                await self.send_hot_lead(chat_id, lead)
                self.hot_queue.task_done()
            
            # Тёплые - раз в 4 часа (упрощённо)
            # Холодные - дайджест раз в сутки
            
            await asyncio.sleep(60)  # Проверка каждую минуту
    
    async def close(self):
        await self.bot.session.close()
