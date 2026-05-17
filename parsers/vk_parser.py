import httpx
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import random
import re

class VKParser:
    """Парсер для поиска заявок в группах VK"""
    
    def __init__(self):
        # Популярные группы логистики и ВЭД
        self.groups = [
            'logistics_vk',          # Логистика и ВЭД
            'chinatransport',         # Доставка из Китая
            'ved_chat',               # ВЭД чат
            'cargo_china',            # Карго Китай
            'import_export_rf',       # Импорт/Экспорт РФ
            'china_supplier',         # Поставщики Китая
            '1688_taobao',            # 1688 Taobao
            'business_china',         # Бизнес с Китаем
        ]
        
        # Ключевые слова для поиска заявок
        self.keywords = [
            'нужна доставка', 'ищу перевозчика', 'нужен карго',
            'доставка из китая', 'ищу логиста', 'нужна растаможка',
            'помогите доставить', 'ищу поставщика', 'нужен байер',
            'хочу заказать', 'нужно привезти', 'ищу компанию'
        ]
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
    
    def safe_sleep(self, min_sec=3, max_sec=7):
        time.sleep(random.uniform(min_sec, max_sec))
    
    def is_fresh_post(self, post_date: str) -> bool:
        """Проверяет, свежий ли пост (не старше 7 дней)"""
        try:
            # Парсим дату (формат VK может быть разным)
            if 'сегодня' in post_date.lower():
                return True
            elif 'вчера' in post_date.lower():
                return (datetime.now() - timedelta(days=1)).day >= 1
            
            # Пробуем распарсить дату
            post_date = post_date.replace('в ', '')
            date_formats = [
                '%d %b %y', '%d %b %Y', '%d.%m.%Y', '%d.%m.%y'
            ]
            
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(post_date, fmt)
                    days_diff = (datetime.now() - parsed_date).days
                    return days_diff <= 7  # Не старше 7 дней
                except:
                    continue
            
            return False
        except:
            return True  # Если не смогли распарсить — считаем свежим
    
    def extract_phone(self, text: str) -> str:
        """Извлекает телефон из текста"""
        pattern = r'(\+7[\s\-\(\)]?\(?\d{3}\)?[\s\-\(\)]?\d{3}[\s\-\(\)]?\d{2}[\s\-\(\)]?\d{2})'
        match = re.search(pattern, text)
        return match.group(1) if match else ""
    
    def extract_telegram(self, text: str) -> str:
        """Извлекает Telegram из текста"""
        pattern = r'(@[a-zA-Z0-9_]{3,}|t\.me/[a-zA-Z0-9_]+)'
        match = re.search(pattern, text)
        return match.group(1) if match else ""
    
    async def parse_group(self, group_name: str) -> list:
        """Парсит одну группу VK"""
        print(f"🔍 VK группа: {group_name}")
        leads = []
        
        try:
            # Ищем через Google (так как VK требует авторизацию)
            search_query = f"site:vk.com/{group_name} (нужна доставка OR ищу перевозчика OR карго) after:{(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')}"
            
            async with httpx.AsyncClient(follow_redirects=True, timeout=30, verify=False) as client:
                # Поиск через Google
                google_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
                resp = await client.get(google_url, headers=self.headers)
                
                if resp.status_code != 200:
                    print(f"⚠️ Google вернул {resp.status_code}")
                    return []
                
                soup = BeautifulSoup(resp.text, 'lxml')
                
                # Ищем ссылки на посты VK
                links = soup.select('a[href*="vk.com/wall"]')
                
                for link in links[:5]:  # Берём первые 5 результатов
                    try:
                        post_url = link.get('href')
                        
                        # Переходим на пост
                        post_resp = await client.get(post_url, headers=self.headers)
                        post_soup = BeautifulSoup(post_resp.text, 'lxml')
                        
                        # Извлекаем текст поста
                        post_text = post_soup.get_text()
                        
                        # Проверяем на ключевые слова
                        if not any(kw in post_text.lower() for kw in self.keywords):
                            continue
                        
                        # Извлекаем данные
                        phone = self.extract_phone(post_text)
                        telegram = self.extract_telegram(post_text)
                        
                        # Создаём лид
                        lead = {
                            'company': 'VK Заявка',
                            'contact': telegram or '',
                            'phone': phone,
                            'city': '',
                            'cargo_type': 'из VK',
                            'volume': '',
                            'source': f'vk:{post_url}',
                            'reason': post_text[:200] + '...' if len(post_text) > 200 else post_text,
                            'hot_level': 'hot',  # Все заявки из VK — горячие!
                            'created_at': datetime.now().isoformat()
                        }
                        
                        leads.append(lead)
                        print(f"✅ VK заявка найдена!")
                        
                    except Exception as e:
                        print(f"⚠️ Ошибка обработки поста: {e}")
                        continue
                    
                    self.safe_sleep(2, 4)
                    
        except Exception as e:
            print(f"❌ Ошибка парсинга группы {group_name}: {e}")
            
        return leads
    
    async def parse_all_groups(self) -> list:
        """Парсит все группы"""
        all_leads = []
        
        for group in self.groups:
            leads = await self.parse_group(group)
            all_leads.extend(leads)
            self.safe_sleep(5, 10)  # Пауза между группами
        
        return all_leads
