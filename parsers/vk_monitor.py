import os
from parsers.groq_analyzer import GroqAnalyzer

class VKMonitor:
    def __init__(self):
        self.token = os.getenv("VK_TOKEN")
        self.ai = GroqAnalyzer()

    async def monitor_all(self):
        # Заглушка для теста
        return []