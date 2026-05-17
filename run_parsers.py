import asyncio
import os
from dotenv import load_dotenv
from database import add_lead, is_duplicate
from parsers.leads_parser import LeadsParser
from parsers.selenium_parser import SeleniumParser
from parsers.company_parser import CompanyParser
from parsers.sites_config import get_active_sites, get_company_urls

load_dotenv()

async def main():
    print("🚀 Запуск парсера лидов...")
    print("=" * 50)
    
    sites = get_active_sites()
    company_urls = get_company_urls()
    
    # Разделяем по типам
    httpx_sites = [s for s in sites if s.get('parser') == 'httpx']
    selenium_sites = [s for s in sites if s.get('parser') == 'selenium']
    company_sites = [s for s in sites if s.get('parser') == 'company']
    
    print(f"📋 HTTPX: {len(httpx_sites)} | Selenium: {len(selenium_sites)} | Company: {len(company_sites)}")
    print(f"🏢 Прямые компании: {len(company_urls)}")
    print("=" * 50)
    
    all_leads = []
    
    # HTTPX парсер
    if httpx_sites:
        print("\n🌐 HTTPX парсер...")
        parser = LeadsParser()
        all_leads.extend(await parser.parse_multiple(httpx_sites))
    
    # Selenium парсер
    if selenium_sites:
        print("\n🤖 Selenium парсер...")
        parser = SeleniumParser()
        for site in selenium_sites:
            if 'avito' in site['url'].lower():
                all_leads.extend(parser.parse_avito(site['url']))
            elif 'hh.ru' in site['url'].lower():
                all_leads.extend(parser.parse_hh_ru(site['url']))
        parser.close()
    
    # Company парсер
    if company_sites or company_urls:
        print("\n🏢 Company парсер...")
        parser = CompanyParser()
        
        # Парсим каталоги
        if company_sites:
            for site in company_sites:
                leads = await parser.parse_multiple([site['url']])
                all_leads.extend(leads)
        
        # Парсим прямые ссылки на компании
        if company_urls:
            leads = await parser.parse_multiple(company_urls)
            all_leads.extend(leads)
    
    # Сохранение
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
            print(f"❌ Ошибка: {e}")
    
    print("=" * 50)
    print(f"✨ Готово! Добавлено: {saved} | Дубли: {skipped}")

if __name__ == "__main__":
    asyncio.run(main())
