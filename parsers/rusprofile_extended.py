# Расширенный парсер Rusprofile с большим количеством данных
from .rusprofile_parser import RusprofileParser

class RusprofileExtendedParser(RusprofileParser):
    """Расширенный парсер с поиском по ОКВЭД и регионам"""
    
    async def search_by_okved(self, okved_code: str) -> list:
        """Поиск по коду ОКВЭД"""
        print(f"🔍 Поиск по ОКВЭД: {okved_code}")
        return await self.search(f"ОКВЭД {okved_code}")
    
    async def search_by_region(self, region: str, activity: str = "импорт") -> list:
        """Поиск по региону и деятельности"""
        query = f"{activity} {region}"
        return await self.search(query)
