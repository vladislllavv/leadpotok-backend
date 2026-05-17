SITES_TO_PARSE = [
    {
        'name': 'Logist.ru - Новости/Объявления',
        'url': 'https://www.logist.ru/news',
        'terms': ['китай', 'импорт', 'доставка', 'вэд', 'контейнер'],
        'enabled': True
    },
    {
        'name': 'Transp.ru - Грузоперевозки',
        'url': 'https://transp.ru/news',
        'terms': ['китай', 'карго', 'логистика', 'таможня'],
        'enabled': True
    },
    {
        'name': 'Cargo.ru - Доска заявок',
        'url': 'https://cargo.ru/loads',
        'terms': ['из китая', 'импорт', 'китай', '1688'],
        'enabled': True
    },
    # ⚠️ ДОБАВЛЯЙ САЙТЫ ПО ОДНОМУ. Если сайт выдаёт 0 лидов или ошибку 403/429:
    # 1. Проверь robots.txt (например: https://site.ru/robots.txt)
    # 2. Попробуй URL поиска: https://site.ru/search?q=доставка+из+китая
    # 3. Поставь 'enabled': False для проблемных
]

def get_active_sites():
    return [site for site in SITES_TO_PARSE if site.get('enabled', False)]
