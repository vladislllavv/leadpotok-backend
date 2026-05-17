import pandas as pd
from io import BytesIO
from database import SessionLocal, Lead

def export_leads_to_excel(cargo_type: str = None, city: str = None) -> BytesIO:
    """Генерирует Excel-файл с лидами"""
    db = SessionLocal()
    
    # Получаем данные
    query = db.query(Lead)
    if cargo_type and cargo_type != "любые":
        query = query.filter(Lead.cargo_type == cargo_type)
    if city:
        query = query.filter(Lead.city.ilike(f"%{city}%"))
    
    leads = query.order_by(Lead.created_at.desc()).all()
    
    # Преобразуем в DataFrame
    data = []
    for lead in leads:
        data.append({
            'Компания': lead.company,
            'Контакт': lead.contact,
            'Телефон': lead.phone,
            'Город': lead.city,
            'Тип груза': lead.cargo_type,
            'Объём': lead.volume,
            'Источник': lead.source,
            'Причина': lead.reason,
            'Горячий': '🔥' if lead.hot_level == 'hot' else '🌡️',
            'Дата': lead.created_at.strftime('%Y-%m-%d %H:%M') if lead.created_at else ''
        })
    
    df = pd.DataFrame(data)
    
    # Создаём Excel в памяти
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Лиды')
    output.seek(0)
    
    db.close()
    return output
