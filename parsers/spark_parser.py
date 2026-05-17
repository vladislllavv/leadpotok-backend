import httpx
from bs4 import BeautifulSoup
from datetime import datetime
import time
import random

class SparkParser:
    """Парсер для spark.ru (СПАРК - база компаний)"""
    
    def __init__(self):
        self.base_url = "https://www.spark.ru"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
    
    def safe_sleep(self, min_sec=3, max_sec=6):
        time.sleep(random.uniform(min_sec, max_sec))
    
    async def search_companies(self, query: str) -> list:
        """Ищет компании по ключевым словам"""
        print(f"🔍 Spark поиск: '{query}'")
        leads = []
        
        try:
            # Поиск компаний
            url = f"{self.base_url}/search/Company/Search?searchString={query}"
            
            async with httpx.AsyncClient(follow_redirects=True, timeout=30, verify=False) as client:
                resp = await client.get(url, headers=self.headers)
                resp.raise_for_status()
                
                soup = BeautifulSoup(resp.text, 'lxml')
                
                # Ищем карточки компаний
                companies = soup.select('.company-item, .search-result-item')
                
                for company in companies[:10]:
                    try:
                        name_elem = company.select_one('.company-name, .title a')
                        if not name_elem:
                            continue
                        
                        company_name = name_elem.text.strip()
                        company_link = self.base_url + name_elem.get('href', '')
                        
                        # Ищем ИНН/ОГРН
                        inn_elem = company.select_one('.inn, .ogrn')
                        inn = inn_elem.text.strip() if inn_elem else ''
                        
                        lead = {
                            'company': company_name,
                            'contact': '',
                            'phone': '',
                            'city': '',
                            'cargo_type': 'import',
                            'volume': '',
                            'source': f'spark:{company_link}',
                            'reason': f'Найдено в СПАРК по запросу "{query}" | ИНН: {inn}',
                            'hot_level': 'warm',
                            'created_at': datetime.now().isoformat()
                        }
                        leads.append(lead)
                        print(f"✅ Spark: {company_name}")
                        
                    except Exception as e:
                        print(f"⚠️ Ошибка обработки: {e}")
                        continue
                    
                    self.safe_sleep(2, 4)
                    
        except Exception as e:
            print(f"❌ Ошибка Spark: {e}")
            
        return leads
