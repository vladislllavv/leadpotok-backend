import os
import json
import logging
from groq import Groq
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class LogisticsAIAgent:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        self.client = Groq(api_key=api_key) if api_key else None
        self.model = "llama-3.3-70b-versatile"

    def analyze(self, text: str, source: str = "Telegram") -> Optional[Dict]:
        if not self.client:
            logger.warning("GROQ_API_KEY not set")
            return {"is_lead": False, "score": 0, "type": "cold"}

        prompt = f"""
Ты AI-агент по поиску клиентов в логистике (Китай → Россия).

Проанализируй сообщение из {source}:
"{text[:1500]}"

Оцени по шкале 1-100:
- 90-100: СРОЧНО! Конкретный запрос, объем, бюджет, сроки ("нужно доставить 10 тонн срочно", "ищу карго на 500к")
- 70-89: Горячий лид! Есть запрос, но нет деталей ("нужна доставка из китая", "ищу поставщика")
- 40-69: Тёплый! Интересуется темой ("сколько стоит доставка", "как заказать из китая")
- 1-39: Холодный/Спам/Не по теме

Верни СТРОГО JSON:
{{
  "is_lead": true/false,
  "score": 0-100,
  "type": "hot" (80+) | "warm" (50-79) | "cold" (<50),
  "contact": "найденный телефон/@username/null",
  "summary": "суть в 1 предложении",
  "urgency": "высокая/средняя/низкая"
}}
"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            
            # Определи is_hot
            result["is_hot"] = result.get("score", 0) >= 80
            
            return result
        except Exception as e:
            logger.error(f"AI Error: {e}")
            return None