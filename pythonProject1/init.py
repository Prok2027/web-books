# init_db.py
from app import get_db

def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_login (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS grade (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            book_id TEXT NOT NULL,
            points INT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS genre (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            genre_name TEXT NOT NULL
        )
    ''')
    conn.execute('''
           CREATE TABLE IF NOT EXISTS book_genre (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               book_id INTEGER,
               genre_id INTEGER
            )
    ''')
    #conn.execute("INSERT INTO genre (genre_name) VALUES ('Фантастика'), ('Детектив'), ('Фэнтези'), ('История')")
    #conn.execute("INSERT INTO genre (genre_name) VALUES ('Роман'), ('Повесть'), ('Учебная'), ('Научная'), ('IT')")
    conn.execute('''
               CREATE TABLE IF NOT EXISTS covers (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   book_id INTEGER,
                   cover TEXT
                )
        ''')
    conn.execute('''
                   CREATE TABLE IF NOT EXISTS best (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       book_id INTEGER,
                       user_id INTEGER
                    )
            ''')
    conn.execute('''
                    CREATE TABLE IF NOT EXISTS review (
                           id INTEGER PRIMARY KEY AUTOINCREMENT,
                           book_id INTEGER,
                           user_id INTEGER,
                           review TEXT
                    )
                ''')
    bk = conn.execute('''SELECT id, title, author FROM books;''').fetchall()
    for book in bk:
        print(f"ID: {book['id']}, Title: {book['title']}, Author: {book['author']}")
    conn.commit()
    conn.close()
    print("База данных инициализирована!")

if __name__ == '__main__':
    init_db()