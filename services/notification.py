class NotificationService:
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
    
    async def send_hot_lead(self, chat_id: int, lead: dict):
        # Заглушка для теста
        pass
    
    async def process_queues(self):
        pass
    
    async def close(self):
        pass