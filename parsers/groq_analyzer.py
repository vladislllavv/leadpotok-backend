import os
import json
from groq import Groq
from typing import Optional, Dict, List

class GroqAnalyzer:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        self.client = Groq(api_key=api_key) if api_key else None

    async def analyze_lead(self, post_text: str, comments: List[str] = None) -> Optional[Dict]:
        if not self.client:
            return None
        prompt = f"Проанализируй заявку: {post_text[:500]}. Верни JSON с lead_type, volume, city, contacts."
        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except:
            return None