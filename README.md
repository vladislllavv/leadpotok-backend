# AI Lead Agent

AI-агент для поиска клиентов в логистике (Китай → Россия) через Telegram и VK.

## Установка

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Создайте файл `.env` с вашими ключами:
```bash
cp .env.example .env
# Отредактируйте .env и добавьте ваши API ключи
```

3. Создайте сессию Telegram (для первого запуска):
```bash
python create_session.py
```

## Запуск

```bash
python main.py
```

Сервер запустится на порту 10000 (или PORT из переменных окружения).

## API Endpoints

- `GET /health` - проверка статуса
- `GET /` - веб-интерфейс
- `POST /api/auth` - аутентификация пользователя
- `GET /api/leads` - получение лидов (требует x-admin-key)
- `POST /api/scan/telegram` - сканирование Telegram (требует x-admin-key)
- `GET /api/scan/telegram/channels` - информация о каналах (требует x-admin-key)
- `GET /api/stats` - статистика (требует x-admin-key)

## Переменные окружения

См. `.env.example` для полного списка переменных.

## Лицензия

MIT
