import aiosqlite
import asyncio

DB_PATH = "bot.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0,
            earnings REAL DEFAULT 0,
            banned INTEGER DEFAULT 0
        )''')

        await db.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            video_id TEXT NOT NULL,
            link TEXT,
            status TEXT,
            earnings REAL DEFAULT 0,
            cpm REAL,
            platform TEXT,
            added_at TEXT,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )''')

        await db.execute('''
        CREATE TABLE IF NOT EXISTS payouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            method TEXT NOT NULL,
            details TEXT,
            created_at TEXT,
            status TEXT,
            admin_comment TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )''')

        await db.execute('''
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )''')

        await db.execute('''
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT UNIQUE NOT NULL
        )''')

        await db.commit()
        print("Все таблицы успешно инициализированы.")

# Миграция (добавляет колонку 'banned', если её нет)
async def add_banned_column_if_missing():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("PRAGMA table_info(users)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]

        if 'banned' not in column_names:
            await db.execute("ALTER TABLE users ADD COLUMN banned INTEGER DEFAULT 0")
            await db.commit()
            print("Колонка 'banned' добавлена.")
        else:
            print("Колонка 'banned' уже существует.")

# Запуск
async def main():
    await init_db()
    await add_banned_column_if_missing()

asyncio.run(main())