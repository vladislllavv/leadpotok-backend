import re

class VKAIFilter:
    """AI-фильтр для отсеивания мусора из VK"""
    
    def __init__(self):
        # Слова-маркеры мусора
        self.spam_words = [
            'раскрутка', 'заработок', 'инвестиции', 'крипта',
            ' MLM ', 'сетевой', 'бизнес молодость'
        ]
        
        # Слова-маркеры релевантности
        self.relevant_words = [
            'доставка', 'карго', 'китай', 'импорт', 'вэд',
            'перевозка', 'логист', 'таможня', '1688', 'alibaba',
            'поставщик', 'товар', 'груз', 'контейнер'
        ]
    
    def is_spam(self, text: str) -> bool:
        """Проверяет на спам"""
        text_lower = text.lower()
        return any(word in text_lower for word in self.spam_words)
    
    def is_relevant(self, text: str) -> bool:
        """Проверяет релевантность"""
        text_lower = text.lower()
        matches = sum(1 for word in self.relevant_words if word in text_lower)
        return matches >= 2  # Хотя бы 2 совпадения
    
    def extract_intent(self, text: str) -> dict:
        """Извлекает намерение из текста"""
        intent = {
            'type': 'unknown',
            'cargo': '',
            'volume': '',
            'city': ''
        }
        
        # Определяем тип заявки
        if 'нужна доставка' in text.lower():
            intent['type'] = 'delivery_request'
        elif 'ищу перевозчика' in text.lower():
            intent['type'] = 'carrier_search'
        elif 'нужен карго' in text.lower():
            intent['type'] = 'cargo_request'
        
        # Ищем город
        cities = ['москва', 'спб', 'питер', 'краснодар', 'новосибирск', 'екатеринбург']
        for city in cities:
            if city in text.lower():
                intent['city'] = city.capitalize()
                break
        
        # Ищем объём
        volume_match = re.search(r'(\d+)\s*(тонн|кг|м3|кубов)', text.lower())
        if volume_match:
            intent['volume'] = f"{volume_match.group(1)} {volume_match.group(2)}"
        
        return intent
    
    def filter_lead(self, lead: dict) -> tuple:
        """
        Фильтрует лид
        Returns: (is_valid: bool, score: int)
        """
        text = lead.get('reason', '') + ' ' + lead.get('company', '')
        
        # Спам — сразу отбрасываем
        if self.is_spam(text):
            return False, 0
        
        # Релевантность
        if not self.is_relevant(text):
            return False, 0
        
        # Считаем score (0-100)
        score = 50  # База
        
        # +20 если есть телефон
        if lead.get('phone'):
            score += 20
        
        # +20 если есть Telegram
        if lead.get('contact'):
            score += 20
        
        # +10 за каждый маркер релевантности
        intent = self.extract_intent(text)
        if intent['type'] != 'unknown':
            score += 10
        if intent['city']:
            score += 10
        
        return True, min(score, 100)
