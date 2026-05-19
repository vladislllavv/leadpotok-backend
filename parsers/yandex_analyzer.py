import httpx
import json
import logging
import os
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

class YandexGPTAnalyzer:
    """Анализатор постов через YandexGPT API (Исправленная версия)"""
    
    def __init__(self, api_key: str = None, folder_id: str = None):
        # Берем ключ и ID, убирая лишние пробелы (strip)
        self.api_key = (api_key or os.getenv("YANDEX_API_KEY", "")).strip()
        self.folder_id = (folder_id or os.getenv("YANDEX_FOLDER_ID", "")).strip()
        
        if not self.api_key:
            logger.warning("⚠️ YANDEX_API_KEY not found!")
        if not self.folder_id:
            logger.warning("⚠️ YANDEX_FOLDER_ID not found!")
            
        # Формируем URI модели
        # ВАЖНО: Замени b1g... на свой реальный Folder ID, если не используешь переменную окружения
        # Но лучше пропиши Folder ID в Render/Env как YANDEX_FOLDER_ID
        fallback_folder = "b1geb8n3it1p5ifr9gld/dashboard?spm=a2ty_o01.29997173.0.0.3ccd55fbmOKR33&utm_referrer=about%3Ablank" # Твой ID из консоли (пример)
        active_folder = self.folder_id if self.folder_id else fallback_folder
        
        self.model_uri = f"gpt://{active_folder}/yandexgpt/latest"
        self.api_url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        
        print(f"🤖 YandexGPT Initialized. Folder: {active_folder}")

    async def analyze_lead(self, post_text: str, comments: List[str] = None) -> Optional[Dict]:
        """Отправляет пост в YandexGPT"""
        if not self.api_key:
            logger.error("❌ API Key is empty")
            return None

        comments_text = ""
        if comments:
            comments_text = "\n".join([c.get('text', '') for c in comments[:5]])
        
        prompt = f"""
Проанализируй пост. Найди заявку на логистику из Китая.
Пост: {post_text[:2000]}
Комментарии: {comments_text[:500]}
Верни JSON: {{ "lead_type": "hot/warm/cold", "volume": "...", "city": "...", "contacts": {{"phone": "..."}}, "analysis": "..." }}
"""

        payload = {
            "modelUri": self.model_uri,
            "completionOptions": {
                "stream": False,
                "temperature": 0.2,
                "maxTokens": "1000"
            },
            "messages": [
                {"role": "system", "text": "Ты ассистент. Отвечай ТОЛЬКО JSON."},
                {"role": "user", "text": prompt}
            ]
        }

        # Явно указываем заголовки
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Api-Key {self.api_key}",
            "x-folder-id": self.folder_id if self.folder_id else self.model_uri.split('/')[1]
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                print(f"📡 Отправка запроса в Yandex...")
                response = await client.post(self.api_url, json=payload, headers=headers)
                response.raise_for_status()
                
                result_data = response.json()
                text_response = result_data['result']['alternatives'][0]['message']['text']
                
                # Чистим ответ от markdown
                clean_text = text_response.strip().replace("```json", "").replace("```", "")
                
                return json.loads(clean_text)

        except httpx.HTTPStatusError as e:
            print(f"❌ HTTP Error: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            print(f"❌ General Error: {e}")
            return None