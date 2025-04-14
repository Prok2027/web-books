# init_db.py
from app import get_db

def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS logins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
    print("База данных инициализирована!")

if __name__ == '__main__':
    init_db()