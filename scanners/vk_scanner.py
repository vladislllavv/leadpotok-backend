import os
import vk_api
import logging
import time
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
        
        # Ключевые слова для поиска по ВСЕМУ VK (не только в группах)
        self.queries = [
            "ищу доставку из китая",
            "нужно карго",
            "доставка груза китай",
            "ищу перевозчика китай",
            "сколько стоит доставка из китая",
            "нужно привезти из китая",
            "ищу поставщика китай",
            "закупка в китае доставка",
            "карго из китая срочно",
            "доставка 1688",
            "доставка таобао",
            "контейнер из китая",
            "сборный груз китай",
            "логистика китай россия",
            "доставка с китая опт"
        ]
        
        # Группы для мониторинга (ID с минусом для групп)
        # Формат: если vk.com/club123456 → -123456
        # Если vk.com/mygroup → используем как строку
        self.groups = [
            -100656506,        # club100656506
            "kitaidostavka",
            "expresschinakargo",
            301796960,         # id301796960 (профиль, не группа)
            "simple_logistick",
            "kitaicargo",
            "cargo352",
            "cargo.china.russ",
            "chinawaylog",
            "onlinecargo",
            "gomarkt_official",
            "ussuri_cargo",
            "asiaforum",
            "vilspik",
            "wintonasia",
            "chinarynok",
            "zz_biz",
            "chinadeals_gera",
            "sellerwb_ru",
            "udalenka",
            "sellery_marketpleysov",
            "sellercapital",
            "otzyvzatovar",
            "soyuz_sellerov",
            "ozonsellers"
        ]

    def scan(self) -> dict:
        found_count = 0
        processed_posts = set()  # Чтобы не дублировать
        
        with next(get_db()) as db:
            # 1. Поиск по ВСЕЙ ленте VK (все группы и страницы)
            logger.info("🔍 Searching newsfeed across all VK...")
            for q in self.queries:
                try:
                    response = self.api.newsfeed.search(q=q, count=25, start_time=0, end_time=0)
                    items = response.get("items", [])
                    
                    for post in items:
                        post_id = f"{post['owner_id']}_{post['id']}"
                        if post_id in processed_posts:
                            continue
                        processed_posts.add(post_id)
                        
                        if self._process_post(db, post):
                            found_count += 1
                            
                    time.sleep(0.3)  # Пауза чтобы не забанили
                    
                except vk_api.exceptions.ApiError as e:
                    logger.error(f"Newsfeed search error for '{q}': {e}")
                except Exception as e:
                    logger.error(f"Unexpected error for '{q}': {e}")
            
            # 2. Поиск по стенам конкретных групп
            logger.info(f"🔍 Searching {len(self.groups)} specific groups...")
            for group in self.groups:
                try:
                    # Определяем owner_id: для групп с минусом, для профилей без
                    if isinstance(group, int):
                        owner_id = group
                    else:
                        # Если строка (screen name), пробуем как есть
                        owner_id = group
                    
                    wall = self.api.wall.get(owner_id=owner_id, count=30, filter="all")
                    
                    for post in wall.get("items", []):
                        post_id = f"{post['owner_id']}_{post['id']}"
                        if post_id in processed_posts:
                            continue
                        processed_posts.add(post_id)
                        
                        if self._process_post(db, post):
                            found_count += 1
                            
                    time.sleep(0.3)
                    
                except vk_api.exceptions.ApiError as e:
                    logger.warning(f"Cannot access group {group}: {e}")
                except Exception as e:
                    logger.error(f"Group wall error for {group}: {e}")
            
        db.commit()
        logger.info(f"✅ Scan complete. Found {found_count} leads.")
        return {"status": "success", "found": found_count}

    def _process_post(self, db, post) -> bool:
        """Обрабатывает пост: анализирует текст и сохраняет если это лид"""
        text = post.get("text", "")
        if len(text) < 30:  # Пропускаем слишком короткие
            return False

        # AI-анализ поста
        result = self.ai.analyze(text, source="VK")
        if not result:
            return False
            
        if not result.get("is_lead") or result.get("type") == "cold":
            return False

        # Извлекаем контакт (автора)
        author_id = post.get("signer_id") or post.get("from_id") or ""
        
        # Создаём лид
        new_lead = Lead(
            source="VK Post",
            source_url=f"https://vk.com/wall{post['owner_id']}_{post['id']}",
            author=str(author_id),
            contact=result.get("contact", ""),
            content=text[:1000],
            lead_type=result["type"],
            score=result.get("score", 50)
        )
        db.add(new_lead)
        logger.info(f"✅ Found {result['type'].upper()} lead: {result.get('summary', '')[:80]}")
        
        # 3. Сканируем комментарии (если их много)
        comments_count = post.get("comments", {}).get("count", 0)
        if comments_count > 0:
            self._scan_comments(db, post)
        
        return True

    def _scan_comments(self, db, post):
        """Сканирует комментарии к посту в поисках лидов"""
        try:
            comments = self.api.wall.getComments(
                owner_id=post['owner_id'],
                post_id=post['id'],
                count=50,
                need_likes=0
            )
            
            for comment in comments.get("items", []):
                text = comment.get("text", "")
                if len(text) < 20:
                    continue
                
                result = self.ai.analyze(text, source="VK Comment")
                if result and result.get("is_lead") and result.get("type") != "cold":
                    new_lead = Lead(
                        source="VK Comment",
                        source_url=f"https://vk.com/wall{post['owner_id']}_{post['id']}?reply={comment['id']}",
                        author=str(comment.get("from_id", "")),
                        contact=result.get("contact", ""),
                        content=text[:1000],
                        lead_type=result["type"],
                        score=result.get("score", 50)
                    )
                    db.add(new_lead)
                    logger.info(f"✅ Comment lead: {result.get('summary', '')[:60]}")
                    
        except Exception as e:
            logger.debug(f"Comment scan skipped: {e}")