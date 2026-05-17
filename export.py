import pandas as pd
from io import BytesIO
from database import SessionLocal, Lead
from datetime import datetime

def export_leads_to_excel(cargo_type: str = None, city: str = None) -> BytesIO:
    """Генерирует Excel-файл с лидами"""
    db = SessionLocal()
    
    try:
        # Получаем данные
        query = db.query(Lead)
        if cargo_type and cargo_type != "любые":
            query = query.filter(Lead.cargo_type == cargo_type)
        if city:
            query = query.filter(Lead.city.ilike(f"%{city}%"))
        
        leads = query.order_by(Lead.created_at.desc()).all()
        
        print(f"📊 Экспорт: найдено {len(leads)} лидов")
        
        # Преобразуем в DataFrame
        data = []
        for lead in leads:
            data.append({
                'ID': lead.id,
                'Компания': lead.company,
                'Контакт': lead.contact or '',
                'Телефон': lead.phone or '',
                'Город': lead.city or '',
                'Тип груза': lead.cargo_type or '',
                'Объём': lead.volume or '',
                'Источник': lead.source or '',
                'Причина/Описание': lead.reason or '',
                'Статус': '🔥 Горячий' if lead.hot_level == 'hot' else '🌡️ Тёплый',
                'Дата добавления': lead.created_at.strftime('%Y-%m-%d %H:%M') if lead.created_at else ''
            })
        
        df = pd.DataFrame(data)
        
        # Создаём Excel в памяти
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl', options={'remove_timezone': True}) as writer:
            df.to_excel(writer, index=False, sheet_name='Лиды')
            
            # Автоширина колонок
            worksheet = writer.sheets['Лиды']
            for column in worksheet.columns:
                max_length = 0
                column = [cell for cell in column]
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(cell.value)
                    except:
                        pass
                adjusted_width = (max_length + 2)
                worksheet.column_dimensions[column[0].column_letter].width = min(adjusted_width, 50)
        
        output.seek(0)
        print(f"✅ Excel файл создан: {len(leads)} записей")
        
        return output
        
    except Exception as e:
        print(f"❌ Ошибка экспорта: {e}")
        raise e
    finally:
        db.close()
