import httpx
import time
import random
from abc import ABC, abstractmethod
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

class BaseParser(ABC):
    """Абстрактный базовый парсер с общими функциями"""
    
    def __init__(self, config: dict):
        self.config = config
        self.base_url = config.get('base_url', '')
        self.rate_limit = config.get('rate_limit', 3)
        self.max_retries = 3
        self.headers = {
            'User-Agent': self._rotate_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
        }
        self._last_request_time = 0
    
    def _rotate_user_agent(self) -> str:
        """Ротирует User-Agent для обхода базовых блокировок"""
        agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        ]
        return random.choice(agents)
    
    def _respect_rate_limit(self):
        """Соблюдает rate limiting"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self._last_request_time = time.time()
    
    async def _request_with_retry(self, url: str, **kwargs) -> Optional[httpx.Response]:
        """Запрос с автоматическими повторами"""
        for attempt in range(self.max_retries):
            try:
                self._respect_rate_limit()
                
                async with httpx.AsyncClient(
                    follow_redirects=True, 
                    timeout=30,
                    verify=False,  # Для тестов; в проде использовать valid certs
                    headers={**self.headers, **kwargs.get('headers', {})}
                ) as client:
                    response = await client.get(url, **kwargs)
                    response.raise_for_status()
                    return response
                    
            except httpx.HTTPStatusError as e:
                if e.response.status_code in [429, 503]:  # Rate limited / Service unavailable
                    wait_time = (attempt + 1) * 10
                    logger.warning(f"Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                logger.error(f"HTTP error: {e}")
                break
                
            except Exception as e:
                logger.error(f"Request error (attempt {attempt+1}): {e}")
                if attempt == self.max_retries - 1:
                    break
                time.sleep(2 ** attempt)  # Exponential backoff
        
        return None
    
    @abstractmethod
    async def search(self, query: str) -> List[dict]:
        """Поиск по ключевому слову - реализовать в наследнике"""
        pass
    
    def normalize_lead(self, raw: dict) -> dict:
        """Нормализует данные лида к единому формату"""
        return {
            'company': raw.get('company', '')[:255],
            'inn': raw.get('inn', ''),
            'website': raw.get('website', ''),
            'phone': self._clean_phone(raw.get('phone', '')),
            'email': raw.get('email', ''),
            'telegram': raw.get('telegram', ''),
            'city': raw.get('city', ''),
            'region': raw.get('region', ''),
            'cargo_type': raw.get('cargo_type', 'любые'),
            'volume': raw.get('volume', ''),
            'description': raw.get('description', '')[:1000],
            'source': self.config.get('name', 'unknown'),
            'source_url': raw.get('source_url', ''),
            'raw_data': raw.get('raw_data', ''),
        }
    
    def _clean_phone(self, phone: str) -> str:
        """Очищает телефон от лишних символов"""
        if not phone:
            return ""
        return ''.join(c for c in phone if c.isdigit() or c == '+')[:20]
