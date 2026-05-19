import pandas as pd
from io import BytesIO

class ExportService:
    def export_to_excel(self, leads: list, user_name: str = "user") -> BytesIO:
        output = BytesIO()
        data = [{"ID": l.id, "Компания": l.company, "Телефон": l.phone, 
                 "Город": l.city, "Тип": l.lead_type} for l in leads]
        df = pd.DataFrame(data)
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Лиды')
        output.seek(0)
        return output