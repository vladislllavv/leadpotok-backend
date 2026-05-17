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
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
    
    def safe_sleep(self, min_sec=3, max_sec=6):
        """Важно: Rusprofile защищает от частых запросов"""
        time.sleep(random.uniform(min_sec, max_sec))
    
    async def search(self, query: str) -> list:
        """Ищет компании по ключевому слову"""
        print(f"🏢 Rusprofile поиск: '{query}'")
        leads = []
        
        try:
            # Тип ul (юридические лица), ищем по названию/ОКВЭД
            url = f"{self.base_url}?type=ul&query={query}"
            
            async with httpx.AsyncClient(follow_redirects=True, timeout=30, verify=False) as client:
                resp = await client.get(url, headers=self.headers)
                resp.raise_for_status()
                
                soup = BeautifulSoup(resp.text, 'lxml')
                
                # Находим карточки компаний
                # На Rusprofile это обычно ссылки внутри div.card
                cards = soup.select('a.text-truncate.d-block')
                
                if not cards:
                    print(f"⚠️ Ничего не найдено по запросу '{query}'")
                    return []
                
                for card in cards[:5]:  # Берем первые 5 компаний за раз (чтобы не забанили)
                    try:
                        company_name = card.text.strip()
                        company_link = card['href']
                        
                        # Формируем полную ссылку
                        if company_link.startswith('/'):
                            company_link = "https://www.rusprofile.ru" + company_link
                        
                        lead = {
                            'company': company_name,
                            'contact': '',
                            'phone': '', # Телефон часто скрыт, будем искать отдельно или вручную
                            'city': '',
                            'cargo_type': 'import',
                            'volume': '',
                            'source': f'rusprofile:{company_link}',
                            'reason': f'Активный импортер (найдено по запросу "{query}")',
                            'hot_level': 'warm',
                            'created_at': datetime.now().isoformat()
                        }
                        leads.append(lead)
                        print(f"✅ Найдена компания: {company_name}")
                        
                    except Exception as e:
                        print(f"️ Ошибка обработки карточки: {e}")
                        continue
                    
                    # Пауза между компаниями
                    self.safe_sleep(2, 4)
                    
        except Exception as e:
            print(f"❌ Ошибка Rusprofile: {e}")
            
        return leads
