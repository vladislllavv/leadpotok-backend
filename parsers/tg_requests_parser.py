import asyncio
from telethon import TelegramClient
from datetime import datetime
import re

class TGRequestsParser:
    """Ищет заявки в Telegram-чатах"""
    
    def __init__(self, api_id, api_hash):
        self.api_id = api_id
        self.api_hash = api_hash
        # Список чатов, где ищут перевозчиков
        self.chats = [
            'logistics_chat', # Замени на реальные названия чатов
            'cargo_china',
            'ved_chat',
            'biznes_s_kitaem'
        ]
        # Ключевые слова заявки
        self.keywords = ['ищу перевозчика', 'нужна доставка', 'карго', 'доставка из китая', 'везу груз', 'нужен логист']

    async def run(self):
        client = TelegramClient('session_parser', self.api_id, self.api_hash)
        await client.start()
        
        leads = []
        
        for chat_name in self.chats:
            try:
                print(f"🔍 Сканируем чат: {chat_name}")
                # Берем последние 50 сообщений
                async for message in client.iter_messages(chat_name, limit=50):
                    if not message.text:
                        continue
                    
                    text = message.text.lower()
                    # Если есть ключевое слово заявки
                    if any(kw in text for kw in self.keywords):
                        
                        # Ищем контакт в тексте (@username или телефон)
                        contact = ""
                        tg_match = re.search(r'@\w+', message.text)
                        phone_match = re.search(r'(\+7\d{10})', message.text.replace(' ', '').replace('-', ''))
                        
                        if tg_match: contact = tg_match.group(0)
                        elif phone_match: contact = phone_match.group(0)
                        
                        # Имя автора
                        sender = message.sender.first_name if message.sender else "Аноним"
                        
                        lead = {
                            'company': f"Заявка от {sender}",
                            'contact': contact,
                            'phone': contact if contact.startswith('+') else '',
                            'city': '',
                            'cargo_type': 'любые',
                            'volume': '',
                            'source': f'tg_req:{chat_name}',
                            'reason': f'Заявка: {message.text[:50]}...',
                            'hot_level': 'hot',
                            'created_at': datetime.now().isoformat()
                        }
                        leads.append(lead)
                        print(f"✅ Заявка найдена: {sender} | {contact}")
                        
            except Exception as e:
                print(f"⚠️ Ошибка в чате {chat_name}: {e}")
                
        await client.disconnect()
        return leads
