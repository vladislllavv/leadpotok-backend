import os
import asyncio
from parsers.groq_analyzer import GroqAnalyzer

async def main():
    # Ключ можно задать здесь или через терминал (export GROQ_API_KEY=...)
    # os.environ["GROQ_API_KEY"] = "gsk_..." 
    
    analyzer = GroqAnalyzer()
    
    if not analyzer.client:
        print("❌ Ошибка: клиент Groq не инициализирован. Проверь ключ!")
        return

    print("⏳ Запрос к Groq AI...")
    
    test_post = "Срочно нужно доставить 20 тонн электроники из Китая в Москву. Ищу надежного перевозчика. Пишите +79990000000 или @manager_logistics"
    
    result = await analyzer.analyze_lead(test_post)
    
    print("\n✅ Результат от Groq:")
    if result:
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("❌ Пустой ответ или ошибка")

if __name__ == "__main__":
    asyncio.run(main())