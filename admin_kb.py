from gc import callbacks
from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from db import DB_PATH
import aiosqlite
from config import ADMIN_IDS
from aiogram.filters import Command

router = Router()

# Состояния FSM для админки
class AdminStates(StatesGroup):
    waiting_admin_message = State()
    waiting_broadcast_text = State()
    waiting_user_id = State()

# Функция для создания клавиатуры модерации видео
def admin_video_moderation_kb(video_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("Реклама найдена", callback_data=f"approve_ad:{video_id}")],
        [InlineKeyboardButton("Рекламы нет", callback_data=f"reject_ad:{video_id}")]
    ])

# Обработчик подтверждения рекламы
@router.callback_query(lambda c: c.data and c.data.startswith("approve_ad:"))
async def approve_ad(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer(text="Доступ запрещён.", show_alert=True)
        return
    
    video_id = callback.data.split(":")[1]
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE videos SET status='approved', manually_checked=1 WHERE id=?", (video_id,))
        await db.commit()

    await callback.message.edit_caption(caption="Реклама подтверждена.")
    await callback.answer()
async def send_to_monetization(video_id):
    await send_to_monetization(video_id)

# Обработчик отклонения рекламы
@router.callback_query(lambda c: c.data and c.data.startswith("reject_ad:"))
async def reject_ad(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer(text="Доступ запрещён.", show_alert=True)
        return
    
    video_id = callback.data.split(":")[1]
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE videos SET status='rejected', manually_checked=1 WHERE id=?", (video_id,))
        await db.commit()
    
    await callback.message.edit_caption(caption="Рекламы нет в видео.")
    await callback.answer()
async def handle_reject(video_id):
    await handle_reject(video_id) 

# Бан пользователя
@router.callback_query(lambda c: c.data and c.data.startswith("ban_user:"))
async def ban_user(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Доступ запрещён.", show_alert=True)
        return
    user_id = int(callback.data.split(":")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET banned=1 WHERE id=?", (user_id,))
        await db.commit()
    await callback.message.answer(f"Пользователь {user_id} заблокирован.")
    await callback.answer()

# Разбан пользователя
@router.callback_query(lambda c: c.data and c.data.startswith("unban_user:"))
async def unban_user(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Доступ запрещён.", show_alert=True)
        return
    user_id = int(callback.data.split(":")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET banned=0 WHERE id=?", (user_id,))
        await db.commit()
        # Просмотр заявок на вывод пользователя
@router.callback_query(lambda c: c.data and c.data.startswith("user_withdrawals_user:"))
async def user_withdrawals(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer(text="Доступ запрещён.", show_alert=True)
        return
    
    user_id = int(callback.data.split(":")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id, amount, status, created_at FROM withdrawals WHERE user_id=? ORDER BY created_at DESC",
            (user_id,)
        )
        rows = await cursor.fetchall()
    
    if not rows:
        await callback.message.answer(f"У пользователя {user_id} нет заявок на вывод.")
    else:
        text = f"Заявки на вывод пользователя {user_id}:\n\n"
        for row in rows:
            w_id, amount, status, created_at = row
            text += f"ID: {w_id} | Сумма: {amount} | Статус: {status} | Дата: {created_at}\n"
        await callback.message.answer(text)
    await callback.answer()

# Просмотр загруженных видео пользователя
@router.callback_query(lambda c: c.data and c.data.startswith("user_videos:"))
async def user_videos(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer(text="Доступ запрещён.", show_alert=True)
        return
    
    user_id = int(callback.data.split(":")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT video_id, status FROM videos WHERE user_id=?", (user_id,))
        videos = await cursor.fetchall()
    
    if not videos:
        await callback.message.answer(f"У пользователя {user_id} нет загруженных видео.")
    else:
        text = f"Видео пользователя {user_id}:\n\n"
        for vid_id, status in videos:
            text += f"ID: {vid_id} | Статус: {status}\n"
        await callback.message.answer(text)
    await callback.answer()

# Запуск рассылки
@router.callback_query(lambda c: c.data == "admin_broadcast")
async def send_broadcast(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Доступ запрещён.", show_alert=True)
        return
    
    await callback.message.answer("Введите текст рассылки:")
    await state.set_state(AdminStates.waiting_broadcast_text)
    await callback.answer()

@router.message(AdminStates.waiting_broadcast_text)
async def send_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    text = message.text
    success, failed = 0, 0
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id FROM users WHERE banned=0") as cursor:
            async for row in cursor:
                user_id = row[0]
                try:
                    await message.bot.send_message(user_id, text)
                    success += 1
                except Exception:
                    failed += 1
    
    await message.answer(f"Рассылка завершена.\nУспешно: {success}\nНе доставлено: {failed}")
    await state.clear()
