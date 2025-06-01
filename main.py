import asyncio
from db import init_db
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from utils import ensure_dir
from handlers import start, video, profile, withdraw, my_video, admin, admin_kb
from handlers.admin_kb import router as admin_router  # <-- импорт админ-роутера

async def main():
    # Создание необходимых директорий
    ensure_dir()

    # Инициализация базы данных
    await init_db()

    # Создание бота и диспетчера с FSM-хранилищем
    bot = Bot(BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Подключение всех роутеров, включая админский
    dp.include_router(start.router)
    dp.include_router(video.router)
    dp.include_router(profile.router)
    dp.include_router(withdraw.router)
    dp.include_router(my_video.router)
    dp.include_router(admin.router)  # <-- добавляем сюда админский роутер

    # Запуск бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())