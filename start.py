from aiogram import Router, types
from aiogram.filters import CommandStart
from db import DB_PATH
import aiosqlite

router = Router()

@router.message(CommandStart())
async def on_start(message: types.Message):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (message.from_user.id,))
        await db.commit()

    kb = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Старт")],
            [types.KeyboardButton(text="📥Загрузить видео")],
            [types.KeyboardButton(text="📊Мои видео")],
            [types.KeyboardButton(text="👤Профиль")]
        ],
        resize_keyboard=True
    )

    await message.answer("Добро пожаловать! Нажмите кнопку Старт для начала.", reply_markup=kb)

@router.message(lambda message: message.text == "Старт")
async def on_start_button(message: types.Message):
    await message.answer("Вы нажали кнопку Старт! Здесь можно запускать основное меню или действия.")