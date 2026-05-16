import asyncio
import json
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

load_dotenv()
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()
WEB_APP_URL = os.getenv("WEB_APP_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇨🇳🔍 Найти клиентов", web_app=WebAppInfo(url=WEB_APP_URL))]
    ])
    await message.answer(
        f"Привет, {message.from_user.first_name}!\n\n"
        "🚛 <b>ЛидПоток: Китай</b>\nНажми кнопку, чтобы начать поиск 👇",
        reply_markup=kb, parse_mode="HTML"
    )

@dp.message()
async def handle_webapp_data(message: types.Message):
    if message.web_app_data:
        try:
            data = json.loads(message.web_app_data.data)
            await bot.send_message(ADMIN_ID, f"📥 Данные:\n<code>{json.dumps(data, indent=2)}</code>", parse_mode="HTML")
            await message.answer("✅ Данные получены.")
        except:
            await message.answer("📦 Получены данные")
    else:
        await message.answer("Напиши /start 🇨🇳🚛")

async def main():
    print("✅ Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
