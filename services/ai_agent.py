import os
import json
import logging
from groq import Groq
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class LogisticsAIAgent:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "llama-3.3-70b-versatile"

    def analyze(self, text: str, source: str = "VK") -> Optional[Dict]:
        """Анализирует текст и определяет, является ли это лидом"""
        prompt = f"""
Ты профессиональный AI-брокер в логистике.
Проанализируй сообщение из {source}.
Задача: Найти людей, которым нужна доставка груза ИЗ КИТАЯ.

Текст:
"{text[:1500]}"

Критерии:
1. HOT: Срочный запрос, конкретный объем ("нужно 5 тонн", "срочно", "сколько стоит доставка").
2. WARM: Планирует, ищет партнеров, общий вопрос ("кто возит из Китая?", "ищу карго").
3. COLD: Спам, реклама, продажа услуг ("мы доставляем", "аренда склада"), или не про логистику.

Если это HOT или WARM, извлеки:
- contact: телефон или @username автора.
- summary: краткая суть запроса.

ВЕРНИ СТРОГО JSON (без markdown):
{{
  "is_lead": true/false,
  "type": "hot" | "warm" | "cold",
  "score": 0-100,
  "contact": "найденный контакт или null",
  "summary": "суть в 1 предложении"
}}
"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"AI Error: {e}")
            return None