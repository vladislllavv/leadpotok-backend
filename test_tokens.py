import os
import httpx

# Проверка VK
async def test_vk():
    token = os.getenv("VK_TOKEN")
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"https://api.vk.com/method/groups.get?access_token={token}&v=5.131")
        print(f"VK Token: {'✅ OK' if resp.status_code == 200 else '❌ Error'}")

# Проверка OpenAI
async def test_openai():
    key = os.getenv("OPENAI_KEY")
    headers = {"Authorization": f"Bearer {key}"}
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://api.openai.com/v1/models", headers=headers)
        print(f"OpenAI Key: {'✅ OK' if resp.status_code == 200 else '❌ Error'}")

# Запуск
import asyncio
asyncio.run(test_vk())
asyncio.run(test_openai())
