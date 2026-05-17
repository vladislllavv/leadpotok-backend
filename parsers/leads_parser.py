import httpx
from bs4 import BeautifulSoup
from datetime import datetime
import time
import random
import re
import warnings
import urllib3

# Отключаем предупреждения о небезопасных соединениях (для тестов)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class LeadsParser:
    """Парсер для поиска лидов на сайтах объявлений"""
    
    def __init__(self):
        self.results = []
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
        }
    
    def safe_sleep(self, min_sec=3, max_sec=7):
        """Пауза между запросами (чтобы не забанили)"""
        time.sleep(random.uniform(min_sec, max_sec))
    
    def clean_text(self, text):
        """Очистка текста"""
        if not text:
            return ""
        return " ".join(str(text).split()).strip()
    
    def extract_phone(self, text: str) -> str:
        """Извлекает телефон из текста"""
        pattern = r'(\+7[\s\-\(\)]?\(?\d{3}\)?[\s\-\(\)]?\d{3}[\s\-\(\)]?\d{2}[\s\-\(\)]?\d{2})'
        match = re.search(pattern, text)
        return match.group(1) if match else ""
    
    def is_hot_lead(self, text: str) -> bool:
        """Проверяет, горячий ли лид"""
        hot_keywords = [
            'китай', 'импорт', 'доставка из китая', 'груз из китая',
            '1688', 'alibaba', 'вэд', 'логист', 'перевозка', 'карго',
            'поставки', 'таможня', 'растаможка', 'контейнер'
        ]
        text_lower = text.lower()
        return any(kw in text_lower for kw in hot_keywords)
    
    async def parse_url(self, url: str, search_terms: list = None) -> list:
        """Парсит одну страницу"""
        print(f"🔍 Парсим: {url}")
        
        try:
            # 🔓 verify=False отключает проверку SSL (для тестов!)
            async with httpx.AsyncClient(follow_redirects=True, timeout=30, verify=False) as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'lxml')
                
                # Ищем заголовки
                titles = soup.find_all(['h1', 'h2', 'h3', 'h4', 'title'])
                
                # Ищем телефоны
                all_text = soup.get_text()
                phone = self.extract_phone(all_text)
                
                leads = []
                for title in titles[:10]:
                    text = self.clean_text(title.get_text())
                    
                    if search_terms:
                        if not any(term.lower() in text.lower() for term in search_terms):
                            continue
                    
                    if len(text) < 10:
                        continue
                    
                    hot_level = 'hot' if self.is_hot_lead(text) else 'warm'
                    
                    lead = {
                        'company': text[:150],
                        'contact': '',
                        'phone': phone,
                        'city': '',
                        'cargo_type': 'любые',
                        'volume': '',
                        'source': f'web:{url[:100]}',
                        'reason': f'Найдено: {text[:80]}...' if len(text) > 80 else f'Найдено: {text}',
                        'hot_level': hot_level,
                        'created_at': datetime.now().isoformat()
                    }
                    leads.append(lead)
                
                self.safe_sleep()
                return leads
                
        except Exception as e:
            print(f"❌ Ошибка при парсинге {url}: {e}")
            return []
    
    async def parse_multiple(self, urls_config: list) -> list:
        """Парсит несколько сайтов"""
        all_leads = []
        
        for config in urls_config:
            url = config.get('url')
            terms = config.get('terms', [])
            
            leads = await self.parse_url(url, terms)
            all_leads.extend(leads)
            print(f"✅ Найдено лидов: {len(leads)}")
        
        return all_leads
