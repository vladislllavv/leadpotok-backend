import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DATABASE_FILE", "leads.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT, contact TEXT, phone TEXT, city TEXT,
            cargo_type TEXT, volume TEXT, source TEXT, reason TEXT,
            hot_level TEXT DEFAULT 'warm',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    if conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0] == 0:
        conn.executemany("""
            INSERT INTO leads (company, contact, phone, city, cargo_type, volume, source, reason, hot_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            ("ООО 'Восток-Текстиль'", "Анна, закупщик", "+74952345678", "Москва", "одежда_текстиль", "3-5 т/мес", "hh.ru", "Ищут логиста для регулярных поставок из Гуанчжоу", "hot"),
            ("ИП Чжан Вэй", "Вячеслав, владелец", "+79268881234", "Москва", "электроника", "1-3 т/мес", "Авито", "Ищет доставку с 1688 на следующую неделю", "hot"),
            ("ТД 'СтанкоИмпорт-Юг'", "Дмитрий, директор", "+78615559012", "Краснодар", "оборудование", "10-20 т/мес", "2ГИС", "Возят станки из Китая, логист на аутсорсе", "warm"),
            ("ООО 'АвтоДеталь-Сибирь'", "Елена, отдел ВЭД", "+73831112233", "Новосибирск", "автозапчасти", "5-10 т/мес", "Telegram", "Текущий логист срывает сроки. Нужна замена", "hot")
        ])
        conn.commit()
    conn.close()

def get_leads(cargo_type: str = None, city: str = None):
    conn = get_db()
    query = "SELECT * FROM leads WHERE 1=1 ORDER BY hot_level DESC, created_at DESC"
    params = []
    if cargo_type and cargo_type != "любые":
        query += " AND cargo_type = ?"
        params.append(cargo_type)
    if city:
        query += " AND city LIKE ?"
        params.append(f"%{city}%")
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def add_lead(company: str, contact: str, phone: str, city: str, 
             cargo_type: str, volume: str, source: str, reason: str, 
             hot_level: str = 'warm', created_at: str = None):
    """Добавляет новый лид в базу (created_at игнорируется, ставится автоматически)"""
    conn = get_db()
    conn.execute("""
        INSERT INTO leads (company, contact, phone, city, cargo_type, volume, source, reason, hot_level)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (company, contact, phone, city, cargo_type, volume, source, reason, hot_level))
    conn.commit()
    conn.close()

def is_duplicate(phone: str, company: str) -> bool:
    """Проверяет, есть ли уже такой лид в базе"""
    conn = get_db()
    clean_company = company.replace(' ', '').lower()[:50]
    row = conn.execute(
        "SELECT id FROM leads WHERE phone = ? OR LOWER(REPLACE(company, ' ', '')) LIKE ?",
        (phone, f"%{clean_company}%")
    ).fetchone()
    conn.close()
    return row is not None
