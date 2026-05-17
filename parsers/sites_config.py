SITES_TO_PARSE = [
    # Простые сайты (HTTPX)
    {
        'name': 'Logist.ru - Новости',
        'url': 'https://logist.ru/news',
        'terms': ['китай', 'импорт', 'доставка'],
        'enabled': True,
        'parser': 'httpx'  # Простой парсер
    },
    {
        'name': 'Ved.gov.ru - Новости',
        'url': 'https://ved.gov.ru/',
        'terms': ['китай', 'импорт', 'вэд'],
        'enabled': True,
        'parser': 'httpx'
    },
    
    # Сайты с Selenium
    {
        'name': 'Avito.ru - Доставка из Китая',
        'url': 'https://www.avito.ru/all?q=доставка+из+китая',
        'terms': ['китай', 'карго', 'доставка'],
        'enabled': True,
        'parser': 'selenium'  # Требуется Selenium!
    },
    {
        'name': 'HH.ru - Логистические компании',
        'url': 'https://hh.ru/search/vacancy?text=логист+китай+вэд',
        'terms': ['логист', 'вэд', 'импорт', 'китай'],
        'enabled': True,
        'parser': 'selenium'
    }
]

def get_active_sites():
    return [site for site in SITES_TO_PARSE if site.get('enabled', False)]
