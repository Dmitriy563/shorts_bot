import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from config import BOT_TOKEN
if not BOT_TOKEN:
    print("Токен бота не найден! Проверьте файл .env")
    exit(1)
from db import init_db
from utils import ensure_dir
from handlers import start, video, profile, withdraw, my_video
from handlers.admin_kb import router as admin_kb_router
from handlers.admin import router as admin_router
from aiogram.utils.callback_answer import CallbackAnswerMiddleware
import os 
if not os.path.exists('.env'):
    print("Файл .env не найден!")
    exit(1)

# Улучшенное логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    try:
        # Создание необходимых директорий
        ensure_dir()

        # Проверка конфигурации
        if not BOT_TOKEN:
            raise ValueError("BOT_TOKEN не установлен")

        # Инициализация базы данных
        await init_db()

        # Создание бота и диспетчера с FSM-хранилищем
        bot = Bot(BOT_TOKEN)
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)

        # Middleware для корректных ответов на inline-кнопки
        dp.message.middleware(CallbackAnswerMiddleware())
        dp.callback_query.middleware(CallbackAnswerMiddleware())

        # Подключение всех роутеров
        dp.include_routers(
            start.router,
            video.router,
            profile.router,
            withdraw.router,
            my_video.router,
            admin_kb_router,
            admin_router,
        )

        # Запуск бота
        logger.info("Бот запущен")
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.critical(f"Ошибка при запуске бота: {e}")