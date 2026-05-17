import httpx
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import random
import re

class VKParser:
    """Парсер для поиска заявок в группах VK"""
    
    def __init__(self):
        self.groups = [
            'logistics_vk',
            'chinatransport',
            'ved_chat',
            'cargo_china',
            'import_export_rf',
            'china_supplier',
            '1688_taobao',
            'business_china',
        ]
        
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
    
    def extract_phone(self, text: str) -> str:
        pattern = r'(\+7[\s\-\(\)]?\(?\d{3}\)?[\s\-\(\)]?\d{3}[\s\-\(\)]?\d{2}[\s\-\(\)]?\d{2})'
        match = re.search(pattern, text)
        return match.group(1) if match else ""
    
    def extract_telegram(self, text: str) -> str:
        pattern = r'(@[a-zA-Z0-9_]{3,}|t\.me/[a-zA-Z0-9_]+)'
        match = re.search(pattern, text)
        return match.group(1) if match else ""
    
    async def parse_group(self, group_name: str) -> list:
        print(f"🔍 VK группа: {group_name}")
        leads = []
        
        try:
            search_query = f"site:vk.com/{group_name} (нужна доставка OR ищу перевозчика OR карго)"
            
            async with httpx.AsyncClient(follow_redirects=True, timeout=30, verify=False) as client:
                google_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
                resp = await client.get(google_url, headers=self.headers)
                
                if resp.status_code != 200:
                    return []
                
                soup = BeautifulSoup(resp.text, 'lxml')
                links = soup.select('a[href*="vk.com/wall"]')
                
                for link in links[:5]:
                    try:
                        post_url = link.get('href')
                        post_resp = await client.get(post_url, headers=self.headers)
                        post_soup = BeautifulSoup(post_resp.text, 'lxml')
                        post_text = post_soup.get_text()
                        
                        if not any(kw in post_text.lower() for kw in self.keywords):
                            continue
                        
                        phone = self.extract_phone(post_text)
                        telegram = self.extract_telegram(post_text)
                        
                        lead = {
                            'company': 'VK Заявка',
                            'contact': telegram or '',
                            'phone': phone,
                            'city': '',
                            'cargo_type': 'из VK',
                            'volume': '',
                            'source': f'vk:{post_url}',
                            'reason': post_text[:200] + '...' if len(post_text) > 200 else post_text,
                            'hot_level': 'hot',
                            'created_at': datetime.now().isoformat()
                        }
                        
                        leads.append(lead)
                        print(f"✅ VK заявка найдена!")
                        
                    except Exception as e:
                        print(f"⚠️ Ошибка: {e}")
                        continue
                    
                    self.safe_sleep(2, 4)
                    
        except Exception as e:
            print(f"❌ Ошибка парсинга группы {group_name}: {e}")
            
        return leads
    
    async def parse_all_groups(self) -> list:
        all_leads = []
        
        for group in self.groups:
            leads = await self.parse_group(group)
            all_leads.extend(leads)
            self.safe_sleep(5, 10)
        
        return all_leads
