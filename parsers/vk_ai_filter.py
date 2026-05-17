import re

class VKAIFilter:
    """AI-фильтр для VK"""
    
    def __init__(self):
        self.spam_words = ['раскрутка', 'заработок', 'инвестиции', 'крипта', 'mlm', 'сетевой']
        self.relevant_words = ['доставка', 'карго', 'китай', 'импорт', 'вэд', 'перевозка', 'логист', 'таможня', '1688']
    
    def is_spam(self, text: str) -> bool:
        text_lower = text.lower()
        return any(word in text_lower for word in self.spam_words)
    
    def is_relevant(self, text: str) -> bool:
        text_lower = text.lower()
        matches = sum(1 for word in self.relevant_words if word in text_lower)
        return matches >= 2
    
    def filter_lead(self, lead: dict) -> tuple:
        text = lead.get('reason', '') + ' ' + lead.get('company', '')
        
        if self.is_spam(text):
            return False, 0
        
        if not self.is_relevant(text):
            return False, 0
        
        score = 50
        if lead.get('phone'):
            score += 20
        if lead.get('contact'):
            score += 20
        
        return True, min(score, 100)
