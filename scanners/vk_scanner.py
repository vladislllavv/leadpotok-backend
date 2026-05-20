import os
import vk_api
import logging
from services.ai_agent import LogisticsAIAgent
from core.database import get_db, Lead

logger = logging.getLogger(__name__)

class VKScanner:
    def __init__(self):
        token = os.getenv("VK_TOKEN")
        if not token:
            raise ValueError("VK_TOKEN not set in environment")
        self.vk = vk_api.VkApi(token=token)
        self.api = self.vk.get_api()
        self.ai = LogisticsAIAgent()
        self.queries = ["ищу доставку из китая", "нужно карго", "доставка груза китай", "ищу перевозчика китай"]

    def scan(self) -> dict:
        found_count = 0
        with next(get_db()) as db:
            for q in self.queries:
                try:
                    # Поиск по новостной ленте (публичные посты)
                    response = self.api.newsfeed.search(q=q, count=15, start_time=0, end_time=0)
                    items = response.get("items", [])
                    
                    for post in items:
                        text = post.get("text", "")
                        if len(text) < 30: continue  # Пропускаем слишком короткие

                        # AI-анализ
                        result = self.ai.analyze(text, source="VK")
                        if not result or not result.get("is_lead") or result.get("type") == "cold":
                            continue

                        # Сохранение в БД
                        new_lead = Lead(
                            source="VK",
                            source_url=f"https://vk.com/wall{post['owner_id']}_{post['id']}",
                            author=str(post.get("signer_id", post.get("from_id", ""))),
                            contact=result.get("contact", ""),
                            content=text[:1000],
                            lead_type=result["type"],
                            score=result.get("score", 50)
                        )
                        db.add(new_lead)
                        found_count += 1
                        logger.info(f"✅ Found {result['type']} lead: {result.get('summary')}")
                        
                except vk_api.exceptions.ApiError as e:
                    logger.error(f"VK API Error for '{q}': {e}")
                except Exception as e:
                    logger.error(f"Scan Error for '{q}': {e}")
                
        db.commit()
        return {"status": "success", "found": found_count}