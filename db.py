import aiosqlite
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
DB_PATH = "bot.db"

async def init_db():
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                balance REAL DEFAULT 0,
                earnings REAL DEFAULT 0,
                banned INTEGER DEFAULT 0
            )''')
            
            # Остальные таблицы...
            
            await db.commit()
            logging.info("Все таблицы успешно инициализированы.")
    except Exception as e:
        logging.error(f"Ошибка при инициализации БД: {e}")

async def add_banned_column_if_missing():
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("PRAGMA table_info(users)")
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            if 'banned' not in column_names:
                await db.execute("ALTER TABLE users ADD COLUMN banned INTEGER DEFAULT 0")
                await db.commit()
                logging.info("Колонка 'banned' добавлена.")
            else:
                logging.info("Колонка 'banned' уже существует.")
    except Exception as e:
        logging.error(f"Ошибка при миграции: {e}")

async def main():
    try:
        await init_db()
        await add_banned_column_if_missing()
    except Exception as e:
        logging.critical(f"Критическая ошибка: {e}")

asyncio.run(main())