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
            return {"is_lead": False, "score": 0, "type": "cold", "is_hot": False}

        prompt = f"""
Ты AI-агент по поиску клиентов в логистике (Китай → Россия).

Проанализируй сообщение из {source}:
"{text[:1500]}"

Оцени по шкале 1-100:
- 90-100: СРОЧНО! Конкретный запрос, объем, бюджет
- 70-89: Горячий лид! Есть запрос
- 40-69: Тёплый! Интересуется темой
- 1-39: Холодный/Спам

Верни СТРОГО JSON:
{{
  "is_lead": true/false,
  "score": 0-100,
  "type": "hot" | "warm" | "cold",
  "contact": "найденный контакт или null",
  "summary": "суть в 1 предложении",
  "is_hot": true/false
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
            result["is_hot"] = result.get("score", 0) >= 80
            return result
        except Exception as e:
            logger.error(f"AI Error: {e}")
            return {"is_lead": False, "score": 0, "type": "cold", "is_hot": False}