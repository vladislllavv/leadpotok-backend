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

    def analyze(self, text: str, source: str = "VK") -> Optional[Dict]:
        if not self.client:
            logger.warning("GROQ_API_KEY not set. Skipping AI analysis.")
            return {"is_lead": True, "type": "warm", "score": 50, "contact": None, "summary": "AI disabled"}

        prompt = f"""
Ты AI-брокер в логистике. Проанализируй сообщение из {source}.
Задача: Найти людей, которым нужна доставка груза ИЗ КИТАЯ.

Текст:
"{text[:1200]}"

Критерии:
- HOT: Срочный запрос, конкретный объем, бюджет ("нужно 5 тонн срочно", "сколько стоит доставка 20фут").
- WARM: Планирует, ищет партнеров, общий вопрос ("кто возит из китая?", "ищу карго надежно").
- COLD: Спам, реклама, продажа услуг ("мы доставляем"), или не про логистику.

Верни СТРОГО JSON (без markdown и пояснений):
{{
  "is_lead": true/false,
  "type": "hot" | "warm" | "cold",
  "score": 0-100,
  "contact": "найденный телефон или @username или null",
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
            logger.error(f"AI Analysis Error: {e}")
            return None