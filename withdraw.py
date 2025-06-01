from aiogram import Router, types
from db import DB_PATH
import aiosqlite, datetime

router = Router()

@router.message(lambda msg: msg.text == "Вывести")
async def withdraw_menu(message: types.Message):
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="💸 USDT", callback_data="withdraw_usdt")],
        [types.InlineKeyboardButton(text="🔵 TON", callback_data="withdraw_ton")],
        [types.InlineKeyboardButton(text="🏦 Карта", callback_data="withdraw_card")]
    ])
    await message.answer("Выберите способ вывода:", reply_markup=kb)

@router.callback_query(lambda c: c.data.startswith("withdraw_"))
async def handle_withdraw_method(callback: types.CallbackQuery):
    method = callback.data.split("_")[1]
    await callback.message.answer(f"Введите сумму для вывода {method.upper()}:")
    # Здесь должен быть FSM для дальнейшего диалога