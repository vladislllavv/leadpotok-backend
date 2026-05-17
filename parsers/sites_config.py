SITES_TO_PARSE = [
    {
        'name': 'Logist.ru - Новости',
        'url': 'https://www.logist.ru/news',
        'terms': ['китай', 'импорт', 'доставка', 'вэд', 'контейнер'],
        'enabled': True
    },
    {
        'name': 'Transp.ru - Новости',
        'url': 'https://transp.ru/news',
        'terms': ['китай', 'карго', 'логистика', 'таможня'],
        'enabled': True
    },
    {
        'name': 'Cargo.ru - Заявки',
        'url': 'https://cargo.ru/loads',
        'terms': ['из китая', 'импорт', 'китай', '1688'],
        'enabled': True
    }
]

def get_active_sites():
    return [site for site in SITES_TO_PARSE if site.get('enabled', False)]
