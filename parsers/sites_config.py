SITES_TO_PARSE = [
    {
        'name': 'Тестовая проверка (не меняй пока)',
        'url': 'https://httpbin.org/html',
        'terms': [],
        'enabled': True
    },
    # Пример реального сайта (раскомментируй и заполни позже):
    # {
    #     'name': 'Логистический форум',
    #     'url': 'https://example.com/logistics',
    #     'terms': ['китай', 'доставка', 'импорт'],
    #     'enabled': False
    # }
]

def get_active_sites():
    return [site for site in SITES_TO_PARSE if site.get('enabled', False)]
