from aiogram import Router, types
from db import DB_PATH
import aiosqlite
import logging

logger = logging.getLogger(__name__)

router = Router()

@router.message(lambda msg: msg.text == "👤Профиль")
async def show_profile(message: types.Message):
    user_id = message.from_user.id
    
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT balance, earnings FROM users WHERE id=?", (user_id,))
            row = await cursor.fetchone()
            
            if row:
                balance, earnings = row
            else:
                # Если пользователь не найден, устанавливаем значения по умолчанию
                balance = 0.0
                earnings = 0.0
                
                # Можно добавить логику для создания нового пользователя
                # await db.execute("INSERT INTO users (id, balance, earnings) VALUES (?, ?, ?)", (user_id, 0.0, 0.0))
                # await db.commit()
                
            await message.answer(
                f"Ваш ID: {user_id}\n"
                f"Баланс: {balance:.2f} ₽\n"
                f"Доход: {earnings:.2f} ₽",
                parse_mode="MarkdownV2"
            )
            
    except Exception as e:
        logger.error(f"Ошибка при получении профиля: {e}")
        await message.answer("Произошла ошибка при получении данных профиля.")