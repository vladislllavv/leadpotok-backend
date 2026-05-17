import asyncio
import os
from dotenv import load_dotenv
from database import add_lead, is_duplicate
from parsers.leads_parser import LeadsParser
from parsers.selenium_parser import SeleniumParser
from parsers.rusprofile_parser import RusprofileParser # <--- Добавили импорт
from parsers.sites_config import get_active_sites

load_dotenv()

async def main():
    print("🚀 Запуск парсера лидов...")
    print("=" * 50)
    
    sites = get_active_sites()
    
    # Разделяем сайты по типу
    httpx_sites = [s for s in sites if s.get('parser') == 'httpx']
    selenium_sites = [s for s in sites if s.get('parser') == 'selenium']
    
    print(f" HTTPX сайтов: {len(httpx_sites)}")
    print(f"🤖 Selenium сайтов: {len(selenium_sites)}")
    print("=" * 50)
    
    all_leads = []
    
    # 1. HTTPX (обычные сайты)
    if httpx_sites:
        print("\n🌐 Запуск HTTPX парсера...")
        parser = LeadsParser()
        httpx_leads = await parser.parse_multiple(httpx_sites)
        all_leads.extend(httpx_leads)
    
    # 2. Selenium (Avito, HH)
    if selenium_sites:
        print("\n🤖 Запуск Selenium парсера...")
        parser = SeleniumParser()
        for site in selenium_sites:
            if 'avito' in site['url'].lower():
                leads = parser.parse_avito(site['url'])
                all_leads.extend(leads)
            elif 'hh.ru' in site['url'].lower():
                leads = parser.parse_hh_ru(site['url'])
                all_leads.extend(leads)
        parser.close()

    # 3. Rusprofile (Новый!)
    print("\n🏢 Запуск поиска компаний (Rusprofile)...")
    rp_parser = RusprofileParser()
    
    # Ключевые слова для поиска импортеров
    search_queries = ['Импорт', 'Торговля с Китаем', 'ВЭД', 'Оптовая торговля']
    
    for query in search_queries:
        leads = await rp_parser.search(query)
        all_leads.extend(leads)
        rp_parser.safe_sleep(5, 10) # Длинная пауза между запросами к Rusprofile
    
    # 4. Сохранение в базу
    print("\n💾 Сохранение в базу...")
    saved = 0
    skipped = 0
    
    for lead in all_leads:
        try:
            # Проверяем дубли (по названию компании)
            if is_duplicate('', lead.get('company', '')):
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
