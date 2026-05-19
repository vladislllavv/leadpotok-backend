import time
import requests
import os

# Твой URL
API_URL = "https://leadpotok-api.onrender.com/health"

print(f"🔔 Keep-alive запущен для {API_URL}")
print("Нажми Ctrl+C чтобы остановить")

try:
    while True:
        try:
            response = requests.get(API_URL, timeout=10)
            print(f"✅ {time.strftime('%H:%M:%S')} - Сервер жив (статус: {response.status_code})")
        except Exception as e:
            print(f"⚠️ {time.strftime('%H:%M:%S')} - Ошибка: {e}")
        
        # Пинг каждые 5 минут (меньше 15 минут до сна)
        time.sleep(300)
except KeyboardInterrupt:
    print("\n👋 Keep-alive остановлен")
