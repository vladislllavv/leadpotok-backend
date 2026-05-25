import os
import logging
import requests
from bs4 import BeautifulSoup
from services.ai_agent import LogisticsAIAgent
from core.database import SessionLocal, Lead
from datetime import datetime

logger = logging.getLogger(__name__)

class JobBoardScanner:
    def __init__(self):
        self.ai = LogisticsAIAgent()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        # Keywords for searching companies that need logistics/VED
        self.keywords = [
            "ВЭД Китай", "Логистика Китай", "Специалист по закупкам Китай",
            "Менеджер по ВЭД Китай", "Импорт из Китая", "Карго Китай",
            "Доставка из Китая", "Поиск поставщиков Китай"
        ]

    async def scan(self) -> dict:
        found_count = 0
        hot_count = 0
        
        with SessionLocal() as db:
            for keyword in self.keywords:
                try:
                    logger.info(f"Scanning job boards for: {keyword}")
                    # HH.ru search URL
                    url = f"https://hh.ru/search/vacancy?text={keyword}&area=1" # area=1 is Russia
                    
                    response = requests.get(url, headers=self.headers, timeout=15)
                    if response.status_code != 200:
                        logger.warning(f"HH.ru returned {response.status_code}")
                        continue
                        
                    soup = BeautifulSoup(response.text, 'html.parser')
                    # Find vacancy snippets
                    vacancies = soup.find_all('div', {'data-qa-name': 'vacancy-serp__vacancy'})
                    
                    for vac in vacancies:
                        title_elem = vac.find('a', {'data-qa-name': 'serp-item__title'})
                        if not title_elem: continue
                        
                        title = title_elem.text.strip()
                        link = "https://hh.ru" + title_elem['href']
                        
                        # Extract description snippet
                        snippet_elem = vac.find('span', {'data-qa-name': 'serp-item__snippet'})
                        snippet = snippet_elem.text.strip() if snippet_elem else ""
                        
                        text_to_analyze = f"Вакансия: {title}. Описание: {snippet}"
                        
                        # AI Analysis: Does this indicate a company that NEEDS logistics?
                        # We change the prompt slightly in the AI agent or handle it here.
                        result = self.ai.analyze_job_post(text_to_analyze, source="HH.ru")
                        
                        if result and result.get("is_lead"):
                            # Check for duplicates
                            existing = db.query(Lead).filter(Lead.source_url == link).first()
                            if existing: continue
                            
                            lead = Lead(
                                source="HH.ru",
                                source_url=link,
                                author=title, # Company is usually in title or near
                                contact="See vacancy link",
                                content=text_to_analyze,
                                lead_type=result.get("type", "cold"),
                                score=result.get("score", 0),
                                is_hot=result.get("is_hot", False),
                                notification_sent=False
                            )
                            db.add(lead)
                            db.commit()
                            
                            found_count += 1
                            if lead.is_hot:
                                hot_count += 1
                                # Use the notification system from TelegramScanner if possible, 
                                # or implement a shared notification service.
                                # For now, we'll just mark it as hot.
                except Exception as e:
                    logger.error(f"Job scan error for {keyword}: {e}")

        return {"status": "success", "found": found_count, "hot": hot_count}
