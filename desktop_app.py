import asyncio
import customtkinter as ctk
import threading
import os
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.types import Message
from groq import Groq
import json
import re

# Загрузка настроек
load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
PHONE = os.getenv("TELEGRAM_PHONE")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

class LeadScannerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("LeadPotok Scanner")
        self.geometry("600x500")
        
        # Настройка темы
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        # Переменные
        self.client = None
        self.is_running = False
        self.keywords = []
        self.groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

        # UI Элементы
        self.create_widgets()

    def create_widgets(self):
        # Заголовок
        self.lbl_title = ctk.CTkLabel(self, text="🔍 LeadPotok Scanner", font=ctk.CTkFont(size=24, weight="bold"))
        self.lbl_title.pack(pady=20)

        # Поле ввода ключевых слов
        self.lbl_keywords = ctk.CTkLabel(self, text="Ключевые слова (через запятую):")
        self.lbl_keywords.pack(pady=(10, 0))
        
        self.entry_keywords = ctk.CTkEntry(self, width=400, placeholder_text="ремонт, строительство, дизайн")
        self.entry_keywords.pack(pady=10)
        self.entry_keywords.insert(0, "ремонт, строительство, дизайн, квартира")

        # Статус
        self.lbl_status = ctk.CTkLabel(self, text="Статус: Остановлено", text_color="gray")
        self.lbl_status.pack(pady=10)

        # Лог событий
        self.txt_log = ctk.CTkTextbox(self, width=500, height=200)
        self.txt_log.pack(pady=10)
        self.log_message("Приложение готово к запуску.")

        # Кнопки
        self.btn_start = ctk.CTkButton(self, text="Запустить сканер", command=self.toggle_scanner, fg_color="green")
        self.btn_start.pack(pady=20)

        self.btn_test = ctk.CTkButton(self, text="Тест уведомления", command=self.send_test_notification)
        self.btn_test.pack(pady=5)

    def log_message(self, message):
        self.txt_log.insert("end", f"{message}\n")
        self.txt_log.see("end")

    def toggle_scanner(self):
        if not self.is_running:
            keywords_str = self.entry_keywords.get()
            if not keywords_str:
                self.log_message("Ошибка: Введите ключевые слова!")
                return
            
            self.keywords = [k.strip().lower() for k in keywords_str.split(',')]
            self.is_running = True
            self.btn_start.configure(text="Остановить сканер", fg_color="red")
            self.lbl_status.configure(text="Статус: Сканирование...", text_color="green")
            self.log_message(f"Запуск сканера. Ключевые слова: {', '.join(self.keywords)}")
            
            # Запуск в отдельном потоке
            thread = threading.Thread(target=self.run_scanner_loop, daemon=True)
            thread.start()
        else:
            self.is_running = False
            self.btn_start.configure(text="Запустить сканер", fg_color="green")
            self.lbl_status.configure(text="Статус: Остановлено", text_color="gray")
            self.log_message("Сканер остановлен пользователем.")
            if self.client:
                asyncio.run(self.stop_client())

    async def stop_client(self):
        if self.client:
            await self.client.disconnect()

    def run_scanner_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.start_telegram_client())

    async def start_telegram_client(self):
        if not API_ID or not API_HASH or not PHONE:
            self.log_message("Ошибка: Проверьте .env файл (API_ID, API_HASH, PHONE)")
            return

        self.client = TelegramClient('scanner_session', API_ID, API_HASH)
        await self.client.start(phone=PHONE)
        self.log_message("Подключено к Telegram!")

        @self.client.on(events.NewMessage)
        async def my_event_handler(event):
            if not self.is_running:
                return
                
            message_text = event.message.text
            if not message_text:
                return

            # Проверка на ключевые слова
            found_keyword = None
            for kw in self.keywords:
                if kw in message_text.lower():
                    found_keyword = kw
                    break
            
            if found_keyword:
                self.log_message(f"Найдено упоминание: '{found_keyword}'")
                await self.process_lead(event.message, found_keyword)

        await self.client.run_until_disconnected()

    async def process_lead(self, message: Message, keyword):
        # Анализ через AI
        is_lead = False
        analysis = "Не удалось проанализировать"
        
        if self.groq_client:
            try:
                chat_completion = self.groq_client.chat.completions.create(
                    messages=[{
                        "role": "system",
                        "content": "Ты ассистент по поиску лидов. Определи, является ли сообщение реальным запросом на услугу или просто разговором. Ответь только JSON: {'is_lead': true/false, 'reason': 'краткая причина'}"
                    }, {
                        "role": "user",
                        "content": f"Сообщение: {message.text[:500]}"
                    }],
                    model="llama3-8b-8192",
                    temperature=0.5,
                    max_tokens=100
                )
                response = chat_completion.choices[0].message.content
                data = json.loads(response)
                is_lead = data.get('is_lead', False)
                analysis = data.get('reason', '')
            except Exception as e:
                self.log_message(f"Ошибка AI: {e}")
                is_lead = True # Если AI упал, считаем лидом по ключевому слову

        if is_lead:
            self.log_message(f"✅ ЛИД НАЙДЕН! Причина: {analysis}")
            await self.send_notification(message, keyword, analysis)
        else:
            self.log_message(f"❌ Пропущено (не лид): {analysis}")

    async def send_notification(self, message: Message, keyword, analysis):
        text = (
            f"🔥 **НОВЫЙ ЛИД**\n\n"
            f"🔑 Ключевое слово: `{keyword}`\n"
            f"🤖 Анализ: {analysis}\n"
            f"📝 Текст: {message.text[:200]}...\n"
            f"🔗 Ссылка: https://t.me/c/{message.chat_id}/{message.id}"
        )
        
        # Отправка в Telegram ботом
        if BOT_TOKEN and ADMIN_CHAT_ID:
            try:
                import aiohttp
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                data = {"chat_id": ADMIN_CHAT_ID, "text": text, "parse_mode": "Markdown"}
                async with aiohttp.ClientSession() as session:
                    await session.post(url, json=data)
                self.log_message("Уведомление отправлено в Telegram")
            except Exception as e:
                self.log_message(f"Ошибка отправки в TG: {e}")
        
        # Здесь можно добавить логику SMS (через сторонний API, например Twilio/SMS.ru)
        # self.send_sms_api(...)

    def send_test_notification(self):
        if BOT_TOKEN and ADMIN_CHAT_ID:
            import requests
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            data = {"chat_id": ADMIN_CHAT_ID, "text": "✅ Тестовое уведомление от LeadPotok работает!"}
            try:
                requests.post(url, json=data)
                self.log_message("Тестовое уведомление отправлено!")
            except Exception as e:
                self.log_message(f"Ошибка теста: {e}")
        else:
            self.log_message("Ошибка: Не настроен BOT_TOKEN или ADMIN_CHAT_ID")

if __name__ == "__main__":
    app = LeadScannerApp()
    app.mainloop()
