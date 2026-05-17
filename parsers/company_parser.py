import httpx
from bs4 import BeautifulSoup
from datetime import datetime
import time
import random
import re
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class CompanyParser:
    """Парсер для извлечения контактов логистических компаний"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8',
        }
    
    def safe_sleep(self, min_sec=2, max_sec=5):
        time.sleep(random.uniform(min_sec, max_sec))
    
    def extract_phone(self, text: str) -> str:
        pattern = r'(\+7[\s\-\(\)]?\(?\d{3}\)?[\s\-\(\)]?\d{3}[\s\-\(\)]?\d{2}[\s\-\(\)]?\d{2})'
        match = re.search(pattern, text)
        return match.group(1).replace(' ', '').replace('-', '') if match else ""
    
    def extract_email(self, text: str) -> str:
        pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
        match = re.search(pattern, text)
        return match.group(1) if match else ""
    
    def extract_telegram(self, text: str) -> str:
        pattern = r'(@[a-zA-Z0-9_]{3,}|t\.me/[a-zA-Z0-9_]+)'
        match = re.search(pattern, text)
        return match.group(1) if match else ""
    
    def is_logistics_company(self, text: str) -> bool:
        keywords = [
            'логистика', 'доставка', 'карго', 'перевозка', 'вэд', 'импорт',
            'китай', 'таможня', 'растаможка', 'контейнер', 'фура', 'экспедитор',
            '1688', 'alibaba', 'байер', 'посредник', 'грузоперевозки'
        ]
        text_lower = text.lower()
        return any(kw in text_lower for kw in keywords)
    
    def find_contact_pages(self, base_url: str, soup: BeautifulSoup) -> list:
        """Ищет ссылки на страницы контактов"""
        contact_pages = []
        contact_keywords = ['contact', 'контакты', 'связаться', 'обратная', 'callback', 'request']
        
        for link in soup.find_all('a', href=True):
            href = link['href'].lower()
            text = link.get_text().lower()
            if any(kw in href or kw in text for kw in contact_keywords):
                # Превращаем относительный путь в абсолютный
                if href.startswith('http'):
                    contact_pages.append(href)
                else:
                    contact_pages.append(base_url.rstrip('/') + '/' + href.lstrip('/'))
        
        return list(set(contact_pages))[:3]  # Берём максимум 3 страницы
    
    async def parse_company(self, url: str) -> dict:
        """Парсит одну компанию"""
        print(f"🏢 Парсим: {url}")
        
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=30, verify=False) as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'lxml')
                full_text = soup.get_text()
                
                # Проверяем, логистическая ли это компания
                if not self.is_logistics_company(full_text):
                    print(f"⚠️ Не логистика: {url}")
                    return None
                
                # Извлекаем контакты
                phone = self.extract_phone(full_text)
                email = self.extract_email(full_text)
                telegram = self.extract_telegram(full_text)
                
                # Пытаемся найти название компании
                company = ""
                title = soup.find('title')
                if title:
                    company = title.get_text().strip()[:150]
                else:
                    h1 = soup.find('h1')
                    if h1:
                        company = h1.get_text().strip()[:150]
                
                # Если нет телефона — пропускаем
                if not phone and not email and not telegram:
                    print(f"⚠️ Нет контактов: {url}")
                    return None
                
                # Ищем страницы с доп. контактами
                contact_pages = self.find_contact_pages(url, soup)
                for page in contact_pages:
                    try:
                        resp = await client.get(page, headers=self.headers, timeout=15)
                        if resp.status_code == 200:
                            page_soup = BeautifulSoup(resp.text, 'lxml')
                            page_text = page_soup.get_text()
                            if not phone:
                                phone = self.extract_phone(page_text)
                            if not email:
                                email = self.extract_email(page_text)
                            if not telegram:
                                telegram = self.extract_telegram(page_text)
                        self.safe_sleep(1, 2)
                    except:
                        continue
                
                lead = {
                    'company': company or url[:150],
                    'contact': '',
                    'phone': phone,
                    'city': '',
                    'cargo_type': 'любые',
                    'volume': '',
                    'source': f'company:{url[:100]}',
                    'reason': f'Контакты логистической компании',
                    'hot_level': 'warm',
                    'created_at': datetime.now().isoformat()
                }
                
                print(f"✅ {company[:50]}... | 📞 {phone or '—'} | ✉️ {email or '—'}")
                return lead
                
        except Exception as e:
            print(f"❌ Ошибка: {url} — {e}")
            return None
    
    async def parse_multiple(self, urls: list) -> list:
        """Парсит несколько компаний"""
        leads = []
        for url in urls:
            lead = await self.parse_company(url)
            if lead:
                leads.append(lead)
            self.safe_sleep(2, 4)  # Пауза между сайтами
        return leads
