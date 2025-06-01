from aiogram import Router, types
from db import DB_PATH
import aiosqlite

router = Router()

@router.message(lambda msg: msg.text == "👤Профиль")
async def show_profile(message: types.Message):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT balance, earnings FROM users WHERE id=?", (user_id,))
        row = await cursor.fetchone()
        balance, earnings = row if row else (0, 0)

        await message.answer(
            f"Ваш ID: {user_id}\n"
            f"Баланс: {balance:.2f} ₽\n"
            f"Доход: {earnings:.2f} ₽"
        )