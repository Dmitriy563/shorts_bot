from aiogram import Router, types
from aiogram.filters import CommandStart
from db import DB_PATH
import aiosqlite
import logging

logger = logging.getLogger(__name__)

router = Router()

@router.message(CommandStart())
async def on_start(message: types.Message):
    user_id = message.from_user.id
    
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))
            await db.commit()
            
            # Проверяем, новый ли это пользователь
            cursor = await db.execute("SELECT id FROM users WHERE id=?", (user_id,))
            existing_user = await cursor.fetchone()
            
            if existing_user:
                welcome_text = "Добро пожаловать обратно! 🎯"
            else:
                welcome_text = "Добро пожаловать в наш бот! 🎉"
                
    except Exception as e:
        logger.error(f"Ошибка при регистрации пользователя: {e}")
        welcome_text = "Добро пожаловать! Произошла небольшая ошибка при регистрации."
        
    kb = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Старт")],
            [types.KeyboardButton(text="📥Загрузить видео")],
            [types.KeyboardButton(text="📊Мои видео")],
            [types.KeyboardButton(text="👤Профиль")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        f"{welcome_text}\n\nНажмите кнопку Старт для начала работы с ботом.",
        reply_markup=kb
    )

@router.message(lambda message: message.text == "Старт")
async def on_start_button(message: types.Message):
    await message.answer(
        "Вы нажали кнопку Старт!\n\n"
        "Здесь вы можете:\n"
        "- Загрузить новое видео\n"
        "- Просмотреть свои видео\n"
        "- Узнать информацию о профиле\n"
        "\n"
        "Выберите нужную опцию ниже 👇"
    )