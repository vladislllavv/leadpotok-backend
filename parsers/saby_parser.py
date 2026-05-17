import httpx
from bs4 import BeautifulSoup
from datetime import datetime
import time
import random

class SabyParser:
    """Парсер для Saby.ru (СБИС - база компаний)"""
    
    def __init__(self):
        self.base_url = "https://saby.ru"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
    
    def safe_sleep(self, min_sec=3, max_sec=6):
        time.sleep(random.uniform(min_sec, max_sec))
    
    async def search_companies(self, query: str) -> list:
        """Ищет компании в СБИС"""
        print(f"🔍 Saby поиск: '{query}'")
        leads = []
        
        try:
            url = f"{self.base_url}/companies?search={query}"
            
            async with httpx.AsyncClient(follow_redirects=True, timeout=30, verify=False) as client:
                resp = await client.get(url, headers=self.headers)
                resp.raise_for_status()
                
                soup = BeautifulSoup(resp.text, 'lxml')
                
                # Ищем компании
                companies = soup.select('.company-card, .search-item')
                
                for company in companies[:10]:
                    try:
                        name = company.select_one('.name, .title')
                        if not name:
                            continue
                        
                        company_name = name.text.strip()
                        
                        # Ищем телефон
                        phone_elem = company.select_one('.phone, .contact-phone')
                        phone = phone_elem.text.strip() if phone_elem else ''
                        
                        # Ищем город
                        city_elem = company.select_one('.city, .location')
                        city = city_elem.text.strip() if city_elem else ''
                        
                        lead = {
                            'company': company_name,
                            'contact': '',
                            'phone': phone,
                            'city': city,
                            'cargo_type': 'import',
                            'volume': '',
                            'source': f'saby:{self.base_url}',
                            'reason': f'Найдено в СБИС по запросу "{query}"',
                            'hot_level': 'warm',
                            'created_at': datetime.now().isoformat()
                        }
                        leads.append(lead)
                        print(f"✅ Saby: {company_name}")
                        
                    except Exception as e:
                        print(f"⚠️ Ошибка: {e}")
                        continue
                    
                    self.safe_sleep(2, 4)
                    
        except Exception as e:
            print(f"❌ Ошибка Saby: {e}")
            
        return leads
