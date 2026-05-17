import asyncio
import os
from dotenv import load_dotenv
from database import add_lead, is_duplicate
from parsers.leads_parser import LeadsParser
from parsers.selenium_parser import SeleniumParser
from parsers.sites_config import get_active_sites

load_dotenv()

async def main():
    print("🚀 Запуск парсера лидов...")
    print("=" * 50)
    
    sites = get_active_sites()
    
    if not sites:
        print("⚠️ Нет активных сайтов. Добавь в sites_config.py")
        return
    
    # Разделяем сайты по типу парсера
    httpx_sites = [s for s in sites if s.get('parser') == 'httpx']
    selenium_sites = [s for s in sites if s.get('parser') == 'selenium']
    
    print(f"📋 HTTPX сайтов: {len(httpx_sites)}")
    print(f"🤖 Selenium сайтов: {len(selenium_sites)}")
    print("=" * 50)
    
    all_leads = []
    
    # Парсим через HTTPX
    if httpx_sites:
        print("\n🌐 Запуск HTTPX парсера...")
        httpx_parser = LeadsParser()
        httpx_leads = await httpx_parser.parse_multiple(httpx_sites)
        all_leads.extend(httpx_leads)
    
    # Парсим через Selenium
    if selenium_sites:
        print("\n🤖 Запуск Selenium парсера...")
        selenium_parser = SeleniumParser()
        
        for site in selenium_sites:
            if 'avito' in site['url'].lower():
                leads = selenium_parser.parse_avito(site['url'])
                all_leads.extend(leads)
            elif 'hh.ru' in site['url'].lower():
                leads = selenium_parser.parse_hh_ru(site['url'])
                all_leads.extend(leads)
        
        selenium_parser.close()
    
    # Сохраняем в базу
    print("\n💾 Сохранение в базу...")
    saved = 0
    skipped = 0
    
    for lead in all_leads:
        try:
            if is_duplicate(lead.get('phone', ''), lead.get('company', '')):
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
