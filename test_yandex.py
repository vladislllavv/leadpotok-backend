import os
import asyncio
from parsers.yandex_analyzer import YandexGPTAnalyzer

async def main():
    # Убедись, что переменная задана в терминале
    os.environ["YANDEX_API_KEY"] = "твой_ключ_сюда" 
    
    analyzer = YandexGPTAnalyzer()
    print("⏳ Запрос к Яндекс AI...")
    
    result = await analyzer.analyze_lead("Срочно нужно доставить 20 тонн кирпича из Китая в Москву. Ищу надежного перевозчика.")
    
    print("✅ Результат:")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
