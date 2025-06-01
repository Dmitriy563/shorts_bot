import asyncio
import aiosqlite
from db import DB_PATH  # путь к базе

async def add_manually_checked_column():
    async with aiosqlite.connect(DB_PATH) as db:
        # Получаем список колонок в таблице videos
        async with db.execute("PRAGMA table_info(videos);") as cursor:
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]

        if "manually_checked" not in column_names:
            print("Добавляем колонку manually_checked...")
            await db.execute("ALTER TABLE videos ADD COLUMN manually_checked INTEGER DEFAULT 0;")
            await db.commit()
            print("Колонка успешно добавлена.")
        else:
            print("Колонка manually_checked уже существует.")

if __name__ == "__main__":
    asyncio.run(add_manually_checked_column())