SITES_TO_PARSE = [
    # Сайты с публичными заявками/контактами
    {
        'name': 'Logist.ru - Контакты компаний',
        'url': 'https://logist.ru/companies',  # ← Проверь актуальный URL
        'parser': 'company',
        'enabled': True
    },
    {
        'name': 'Trans.ru - Партнёры',
        'url': 'https://trans.ru/partners',
        'parser': 'company',
        'enabled': True
    },
    # Добавляй сюда сайты, где есть каталоги компаний
]

# Список компаний для прямого парсинга (ручное добавление)
COMPANY_URLS = [
    'https://example-logistics.ru',
    'https://cargo-company.ru',
    # Добавляй найденные сайты логистических компаний
]

def get_active_sites():
    return [site for site in SITES_TO_PARSE if site.get('enabled', False)]

def get_company_urls():
    return COMPANY_URLS
