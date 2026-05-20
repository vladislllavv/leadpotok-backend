import os
import vk_api
import logging
from services.ai_agent import LogisticsAIAgent
from core.database import get_db, Lead

logger = logging.getLogger(__name__)

class VKScanner:
    def __init__(self):
        self.vk = vk_api.VkApi(token=os.getenv("VK_TOKEN"))
        self.api = self.vk.get_api()
        self.ai = LogisticsAIAgent()

    def scan(self):
        """Ищет посты по ключевым словам и анализирует их"""
        queries = ["ищу доставку из китая", "нужно карго", "доставка груза китай", "ищу перевозчика китай"]
        found_count = 0

        with next(get_db()) as db:
            for q in queries:
                try:
                    # Поиск по стенам групп
                    response = self.api.wall.search(q=q, count=20, owners_ids=[-1, -200, -12345]) 
                    # ^ Замени IDs на реальные ID крупных групп, если хочешь точечно, или оставь общий поиск
                    
                    # Для простоты используем newsfeed.search (ищет по всей сети)
                    news = self.api.newsfeed.search(q=q, count=20)
                    
                    for post in news.get('items', []):
                        text = post.get('text', '')
                        if len(text) < 20: continue # Пропуск коротких
                        
                        # Проверка на дубли в БД (упрощенная)
                        # В реальном проекте лучше искать по ID поста
                        
                        result = self.ai.analyze(text, source="VK")
                        
                        if result and result.get('is_lead') and result.get('type') != 'cold':
                            new_lead = Lead(
                                source="VK",
                                source_url=f"https://vk.com/wall{post['owner_id']}_{post['id']}",
                                author=post.get('signer_id', 'Unknown'),
                                contact=result.get('contact', ''),
                                content=text[:1000],
                                lead_type=result['type'],
                                score=result.get('score', 50)
                            )
                            db.add(new_lead)
                            db.commit()
                            found_count += 1
                            logger.info(f"✅ Найден {result['type']} лид: {result.get('summary')}")
                            
                except Exception as e:
                    logger.error(f"VK Search Error for '{q}': {e}")
        
        return {"status": "success", "found": found_count}