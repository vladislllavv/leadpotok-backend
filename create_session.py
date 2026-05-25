import os
from telethon import TelegramClient
from dotenv import load_dotenv

load_dotenv()

api_id = int(os.getenv("TELEGRAM_API_ID"))
api_hash = os.getenv("TELEGRAM_API_HASH")
session_name = os.getenv("TELEGRAM_SESSION", "leadpotok")

print(f"🔑 Создаю сессию Telegram...")
print(f"API ID: {api_id}")
print(f"API Hash: {api_hash[:10]}...")

client = TelegramClient(session_name, api_id, api_hash)

async def main():
    await client.start()
    print("✅ Сессия успешно создана!")
    print(f"📁 Файл сессии: {session_name}.session")
    me = await client.get_me()
    print(f"👤 Аккаунт: {me.first_name} @{me.username}")
    await client.disconnect()

with client:
    client.loop.run_until_complete(main())
