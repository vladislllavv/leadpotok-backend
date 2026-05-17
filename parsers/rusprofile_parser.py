import httpx
from bs4 import BeautifulSoup
from datetime import datetime
import time
import random

class RusprofileParser:
    """Парсер для поиска компаний-импортеров на Rusprofile.ru"""
    
    def __init__(self):
        self.base_url = "https://www.rusprofile.ru/search"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            'Referer': 'https://www.rusprofile.ru/'
        }
    
    def safe_sleep(self, min_sec=3, max_sec=6):
        """Важно: Rusprofile защищает от частых запросов"""
        time.sleep(random.uniform(min_sec, max_sec))
    
    async def search(self, query: str) -> list:
        """Ищет компании по ключевому слову"""
        print(f" Rusprofile поиск: '{query}'")
        leads = []
        
        try:
            url = f"{self.base_url}?type=ul&query={query}"
            
            async with httpx.AsyncClient(follow_redirects=True, timeout=30, verify=False) as client:
                resp = await client.get(url, headers=self.headers)
                resp.raise_for_status()
                
                soup = BeautifulSoup(resp.text, 'lxml')
                
                # 🔍 Универсальный селектор: все ссылки вида /id/123456
                links = soup.select('a[href^="/id/"]')
                
                if not links:
                    print(f"⚠️ Ничего не найдено. Статус: {resp.status_code}")
                    # Отладка: покажем фрагмент ответа, чтобы понять структуру
                    print(f"🔍 Фрагмент ответа: {resp.text[:300]}...")
                    return []
                
                seen = set()
                for link in links[:5]:  # Берём первые 5 уникальных
                    href = link['href']
                    if href in seen: 
                        continue
                    seen.add(href)
                    
                    company_name = link.text.strip()
                    if len(company_name) < 4:  # Пропускаем короткие/пустые
                        continue
                    
                    full_url = f"https://www.rusprofile.ru{href}"
                    
                    lead = {
                        'company': company_name,
                        'contact': '',
                        'phone': '',
                        'city': '',
                        'cargo_type': 'import',
                        'volume': '',
                        'source': f'rusprofile:{full_url}',
                        'reason': f'Найдено по запросу "{query}"',
                        'hot_level': 'warm',
                        'created_at': datetime.now().isoformat()
                    }
                    leads.append(lead)
