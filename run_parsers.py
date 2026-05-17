import asyncio
import os
from dotenv import load_dotenv
from database import add_lead, is_duplicate, SessionLocal
from parsers.leads_parser import LeadsParser
from parsers.selenium_parser import SeleniumParser
from parsers.rusprofile_parser import RusprofileParser
from parsers.spark_parser import SparkParser
from parsers.saby_parser import SabyParser
from export import export_leads_to_excel

load_dotenv()

async def main():
    print("🚀 Запуск парсера лидов...")
    print("=" * 50)
    
    db = SessionLocal()
    
    # Источники для парсинга
    sources = {
        'rusprofile': ['Импорт', 'ВЭД', 'Торговля с Китаем', 'Оптовая торговля'],
        'spark': ['импорт', 'внешнеэкономическая деятельность', 'китай'],
        'saby': ['логистика', 'импорт', 'вэд']
    }
    
    all_leads = []
    
    # 1. Rusprofile
    print("\n🏢 Rusprofile...")
    rp_parser = RusprofileParser()
    for query in sources['rusprofile']:
        leads = await rp_parser.search(query)
        all_leads.extend(leads)
        await asyncio.sleep(5)
    
    # 2. Spark
    print("\n💎 Spark...")
    spark_parser = SparkParser()
    for query in sources['spark']:
        leads = await spark_parser.search_companies(query)
        all_leads.extend(leads)
        await asyncio.sleep(5)
    
    # 3. Saby
    print("\n📋 Saby...")
    saby_parser = SabyParser()
    for query in sources['saby']:
        leads = await saby_parser.search_companies(query)
        all_leads.extend(leads)
        await asyncio.sleep(5)
    
    # Сохранение
    print(f"\n💾 Сохранение {len(all_leads)} лидов...")
    saved = 0
    skipped = 0
    
    for lead in all_leads:
        try:
            if is_duplicate(db, lead.get('phone', ''), lead.get('company', '')):
                skipped += 1
                continue
            add_lead(db, **lead)
            saved += 1
        except Exception as e:
            print(f"❌ Ошибка: {e}")
    
    db.close()
    
    print("=" * 50)
    print(f"✨ Готово! Добавлено: {saved} | Пропущено: {skipped}")

if __name__ == "__main__":
    asyncio.run(main())
