import asyncio
import os
from dotenv import load_dotenv
from database import add_lead
from parsers.leads_parser import LeadsParser
from parsers.sites_config import get_active_sites

load_dotenv()

async def main():
    print("🚀 Запуск парсера лидов...")
    print("=" * 50)
    
    parser = LeadsParser()
    sites = get_active_sites()
    
    if not sites:
        print("⚠️ Нет активных сайтов. Добавь в sites_config.py")
        return
    
    print(f"📋 Активных источников: {len(sites)}")
    print("=" * 50)
    
    all_leads = await parser.parse_multiple(sites)
    
        saved = 0
    skipped = 0
    for lead in all_leads:
        try:
            if is_duplicate(lead['phone'], lead['company']):
                skipped += 1
                continue
            add_lead(**lead)
            saved += 1
            print(f"✅ {lead['company'][:50]}...")
        except Exception as e:
            print(f"❌ Ошибка сохранения: {e}")
    
    print("=" * 50)
    print(f"✨ Готово! Добавлено: {saved} | Пропущено дублей: {skipped}")

if __name__ == "__main__":
    asyncio.run(main())
