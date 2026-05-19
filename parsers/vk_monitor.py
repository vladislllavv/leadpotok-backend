import httpx
import os
import json
import re
import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime

# Импорт твоего Yandex анализатора
from parsers.yandex_analyzer import YandexGPTAnalyzer

logger = logging.getLogger(__name__)

class VKMonitor:
    """
    Мониторинг VK групп с использованием YandexGPT для анализа
    """

    def __init__(self):
        self.token = os.getenv("VK_TOKEN")
        # Инициализируем Yandex AI
        self.ai_analyzer = YandexGPTAnalyzer()

        # Список групп для мониторинга (ID групп, а не адреса!)
        # Чтобы узнать ID, зайди в группу -> Кликни на аватарку -> Посмотри в адресную строку
        # Обычно это число после "club" или "public" (например club12345 -> ID: 12345)
        self.groups = [
            {"id": "166383671", "name": "Карго из Китая"}, # Пример ID
            {"id": "142692422", "name": "Доставка грузов из Китая"}, # Пример ID
            {"id": "654321", "name": "Бизнес с Китаем"}, # Замени на реальные ID!
        ]

    async def monitor_all(self) -> List[Dict]:
        """Запускает мониторинг всех групп"""
        if not self.token:
            logger.error("❌ VK_TOKEN not found in environment. Cannot monitor VK.")
            return []

        print("🚀 Запуск VK мониторинга...")
        all_leads = []

        for group in self.groups:
            print(f"🔍 Сканируем группу: {group['name']} (ID: {group['id']})")
            try:
                # 1. Получаем посты
                posts = await self.get_recent_posts(group["id"])
                
                # 2. Обрабатываем посты через AI
                leads_from_group = await self.process_posts(posts, group["name"])
                all_leads.extend(leads_from_group)
                
                # Пауза между группами, чтобы VK не забанил
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"⚠️ Ошибка сканирования группы {group['name']}: {e}")

        print(f"✅ VK Мониторинг завершен. Найдено лидов: {len(all_leads)}")
        return all_leads

    async def get_recent_posts(self, group_id: str) -> List[Dict]:
        """Получает последние посты через VK API (wall.get)"""
        url = f"https://api.vk.com/method/wall.get"
        params = {
            "owner_id": f"-{group_id}", # Отрицательный ID для групп
            "count": 10,                # Берем последние 10 постов
            "filter": "all",
            "access_token": self.token,
            "v": "5.131"                # Версия API
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            data = response.json()

            # Проверка на ошибку VK
            if "error" in data:
                raise Exception(f"VK API Error: {data['error']}")

            if "response" not in data or "items" not in data["response"]:
                return []

            return data["response"]["items"]

    async def process_posts(self, posts: List[Dict], source_group: str) -> List[Dict]:
        """Фильтрует посты и отправляет релевантные в AI"""
        leads = []

        for post in posts:
            text = post.get("text", "")
            
            # Пропускаем пустые или слишком короткие
            if not text or len(text) < 20:
                continue

            # 1. Быстрая фильтрация (чтобы не тратить токены Яндекса на спам/рекламу)
            if not self.is_relevant_fast(text):
                continue

            print(f"  📝 Найден потенциальный лид, отправляю в Yandex AI...")

            # 2. AI Анализ через Yandex
            # Мы не передаем комментарии для скорости, только текст поста
            ai_result = await self.ai_analyzer.analyze_lead(text)

            # 3. Если AI решил, что это лид (hot или warm)
            if ai_result and ai_result.get("lead_type") in ["hot", "warm"]:
                lead_data = self.format_lead(ai_result, post, source_group)
                leads.append(lead_data)
                print(f"    ✅ Лид найден: {lead_data['company']} ({ai_result['lead_type']})")
            
            # Пауза между запросами к AI
            await asyncio.sleep(1) 

        return leads

    def is_relevant_fast(self, text: str) -> bool:
        """Быстрая проверка по ключевым словам (регулярка)"""
        # Ищем слова, связанные с логистикой и поиском
        keywords = [
            r"ищу\s", r"нужен\s", r"нужна\s", r"доставка", r"китай", 
            r"карго", r"перевозка", r"выкуп", r"байер", r"срочно", r"логист"
        ]
        text_lower = text.lower()
        return any(re.search(kw, text_lower) for kw in keywords)

    def format_lead(self, ai_data: Dict, post: Dict, source: str) -> Dict:
        """Форматирует ответ AI в формат Лида для базы данных"""
        contacts = ai_data.get("contacts", {})
        
        # Формирование ссылки на пост
        # owner_id из API обычно отрицательный (например -12345), ID поста (id)
        owner_id = post.get("owner_id", "")
        post_id = post.get("id", "")
        post_url = f"https://vk.com/wall{owner_id}_{post_id}"
            
        return {
            "company": ai_data.get("company", "Частное лицо"),
            "contact_person": ai_data.get("contact_person", ""),
            "phone": contacts.get("phone", ""),
            "telegram": contacts.get("telegram", ""),
            "email": "",
            "city": ai_data.get("city", ""),
            "volume": ai_data.get("volume", ""),
            "description": post.get("text", "")[:300],
            "source": "vk",
            "source_url": post_url,
            "lead_type": ai_data.get("lead_type", "warm"),
            "ai_score": 90 if ai_data.get("lead_type") == "hot" else 70,
            "ai_analysis": ai_data.get("analysis", ""),
            "raw_data": json.dumps(post, ensure_ascii=False),
        }