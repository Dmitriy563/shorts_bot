import asyncio
import aiosqlite
from db import DB_PATH  # путь к базе
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def add_manually_checked_column():
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Получаем список колонок в таблице videos
            async with db.execute("PRAGMA table_info(videos);") as cursor:
                columns = await cursor.fetchall()
                column_names = [col[1] for col in columns]

            if "manually_checked" not in column_names:
                logger.info("Добавляем колонку manually_checked...")
                await db.execute("ALTER TABLE videos ADD COLUMN manually_checked INTEGER DEFAULT 0;")
                await db.commit()
                logger.info("Колонка успешно добавлена.")
            else:
                logger.info("Колонка manually_checked уже существует.")
    except Exception as e:
        logger.error(f"Ошибка при миграции: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(add_manually_checked_column())
    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}")