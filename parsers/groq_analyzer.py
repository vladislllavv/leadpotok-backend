# -*- coding: utf-8 -*-
import os
import json
import logging
from groq import Groq
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

class GroqAnalyzer:
    """Анализатор постов через Groq API (Llama-3.3)"""

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.warning("⚠️ GROQ_API_KEY не найден!")
            self.client = None
        else:
            self.client = Groq(api_key=api_key)
            print("✅ Groq клиент инициализирован")

    async def analyze_lead(self, post_text: str, comments: List[str] = None) -> Optional[Dict]:
        """Анализирует текст и возвращает JSON с данными лида"""
        if not self.client:
            return None

        comments_text = "\n".join([c.get('text', '') for c in (comments or [])[:5]])
        
        # Формируем промпт
        prompt = (
            "Ты AI-ассистент, ищущий заявки на доставку грузов из Китая.\n"
            "Проанализируй пост ВКонтакте и комментарии.\n\n"
            f"ПОСТ:\n{post_text[:2000]}\n\n"
            f"КОММЕНТАРИИ:\n{comments_text[:500]}\n\n"
            "Задача:\n"
            "1. Определи тип запроса (hot - срочно, warm - планирует, cold - спам/не то).\n"
            "2. Извлеки контакты (телефон, телеграм).\n"
            "3. Укажи объем груза и город.\n"
            "4. Напиши краткий анализ.\n\n"
            "ВЕРНИ ТОЛЬКО JSON (без markdown форматирования):\n"
            '{\n'
            '  "lead_type": "hot" | "warm" | "cold",\n'
            '  "volume": "объем (например 5 тонн) или пусто",\n'
            '  "city": "город доставки или пусто",\n'
            '  "contacts": { "phone": "номер", "telegram": "@username" },\n'
            '  "company": "название компании или пусто",\n'
            '  "analysis": "кратко суть (1 предложение)",\n'
            '  "quote": "цитата из поста подтверждающая заявку"\n'
            '}'
        )

        try:
            # Кодируем промпт в UTF-8 для гарантии
            prompt_safe = prompt.encode('utf-8').decode('utf-8')

            response = self.client.chat.completions.create(
                # ✅ АКТУАЛЬНАЯ МОДЕЛЬ (обновлено)
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "Ты полезный ассистент. Отвечай СТРОГО в формате JSON."},
                    {"role": "user", "content": prompt_safe}
                ],
                temperature=0.2,
                max_tokens=500
            )

            raw_text = response.choices[0].message.content.strip()
            # Чистим от markdown, если модель его добавила
            clean_text = raw_text.replace("```json", "").replace("```", "").strip()
            
            result = json.loads(clean_text)
            return result

        except json.JSONDecodeError as e:
            print(f"❌ Ошибка парсинга JSON: {e}")
            print(f"📄 Raw response: {raw_text[:200]}")
            return None
        except Exception as e:
            print(f"❌ Ошибка Groq: {e}")
            return None