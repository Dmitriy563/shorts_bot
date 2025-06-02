from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from db import DB_PATH
import aiosqlite
from config import ADMIN_IDS
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()

# --- FSM состояния ---
class AdminStates(StatesGroup):
    waiting_user_id = State()
    waiting_balance = State()
    waiting_message = State()
    waiting_withdrawal_comment = State()
    waiting_broadcast_content = State()
    waiting_broadcast_confirm = State()

# --- Проверка админа ---
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# --- Клавиатуры ---
def main_admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Общая статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="Найти пользователя", callback_data="admin_search_user")],
        [InlineKeyboardButton(text="Заявки на вывод", callback_data="admin_withdrawals")],
        [InlineKeyboardButton(text="Рассылка", callback_data="admin_broadcast")],
    ])

def user_profile_kb(user_id: int, banned: bool):
    buttons = [
        [InlineKeyboardButton(text="Изменить баланс", callback_data=f"change_balance:{user_id}")],
        [InlineKeyboardButton(text="Отправить сообщение", callback_data=f"send_message:{user_id}")],
        [InlineKeyboardButton(text="Список видео", callback_data=f"user_videos:{user_id}")],
        [InlineKeyboardButton(text="Заявки на вывод", callback_data=f"user_withdrawals:{user_id}")],
        [InlineKeyboardButton(text="Назад", callback_data="admin_back_main")]
    ]
    if banned:
        buttons.insert(2, [InlineKeyboardButton(text="Разблокировать", callback_data=f"unban_user:{user_id}")])
    else:
        buttons.insert(2, [InlineKeyboardButton(text="Заблокировать", callback_data=f"ban_user:{user_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def videos_list_kb(videos: list, user_id: int):
    kb = InlineKeyboardMarkup(row_width=2)
    for vid in videos:
        kb.insert(InlineKeyboardButton(text=f"Удалить {vid[0]}", callback_data=f"del_video:{vid[0]}:{user_id}"))
        kb.insert(InlineKeyboardButton(text=f"Деактивировать {vid[0]}", callback_data=f"deactivate_video:{vid[0]}:{user_id}"))
    kb.add(InlineKeyboardButton(text="Назад", callback_data=f"user_profile:{user_id}"))
    return kb

def withdrawals_list_kb(withdrawals: list, user_id: int):
    kb = InlineKeyboardMarkup(row_width=2)
    for wd in withdrawals:
        # wd = (id, amount, status, comment)
        if wd[2] == "pending":
            kb.row(
                InlineKeyboardButton(text=f"Подтвердить {wd[0]}", callback_data=f"approve_wd:{wd[0]}:{user_id}"),
                InlineKeyboardButton(text=f"Отклонить {wd[0]}", callback_data=f"reject_wd:{wd[0]}:{user_id}")
            )
    kb.add(InlineKeyboardButton(text="Назад", callback_data=f"user_profile:{user_id}"))
    return kb

# --- Обработчики ---

@router.message(Command("admin"))
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id):
        return await message.answer("У вас нет доступа.")
    try:
        await message.answer("Админ-панель:", reply_markup=main_admin_kb())
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {e}")

@router.callback_query(F.data == "admin_stats")
async def show_admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Нет доступа.")
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            rows = await db.execute("""
                SELECT 
                (SELECT COUNT(*) FROM users) as users_count,
                (SELECT COUNT(*) FROM videos) as videos_count,
                (SELECT SUM(balance) FROM users) as total_balance
            """)
            result = await rows.fetchone()
            users_count, videos_count, total_balance = result

            await callback.message.edit_text(
                f"Общая статистика\n\n"
                f"Пользователей: {users_count}\n"
                f"Видео: {videos_count}\n"
                f"Общий баланс: {total_balance or 0.0:.2f} руб",
                reply_markup=main_admin_kb()
            )
            await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        await callback.answer("Произошла ошибка при получении статистики.")

@router.callback_query(F.data == "admin_withdrawals")
async def show_withdrawals(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Нет доступа.")
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            rows = await db.execute("""
                SELECT id, user_id, amount, status 
                FROM withdrawals 
                ORDER BY id DESC 
                LIMIT 10
            """)
            rows = await rows.fetchall()

        if not rows:
            await callback.message.edit_text("Нет заявок на вывод.", reply_markup=main_admin_kb())
            await callback.answer()
            return

        text = "<b>Последние заявки на вывод:</b>\n\n"
        for withdrawal_id, user_id, amount, status in rows:
            text += f"🔹 #{withdrawal_id} — <code>{amount} руб</code> от пользователя <code>{user_id}</code> — Статус: <b>{status}</b>\n"

        await callback.message.edit_text(text, reply_markup=main_admin_kb())
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при получении заявок на вывод: {e}")
        await callback.answer("Произошла ошибка при получении заявок.")

@router.callback_query(F.data == "admin_search_user")
async def admin_search_user_handler(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.answer("Введите ID пользователя:")
    await state.set_state(AdminStates.waiting_user_id)
    await callback.answer()

@router.message(AdminStates.waiting_user_id)
async def process_user_id(message: types.Message, state: FSMContext):
    try:
        user_id_text = message.text.strip()
        if not user_id_text.isdigit():
            await message.answer("Неверный ID. Введите числовой ID пользователя.")
            return
        user_id = int(user_id_text)
        
        # Проверяем, что ID положительный
        if user_id <= 0:
            await message.answer("ID должен быть положительным числом.")
            return
            
        await show_user_profile(message, user_id)
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при поиске пользователя: {e}")
        await message.answer("Произошла ошибка при поиске пользователя.")

# Функция отображения профиля пользователя
async def show_user_profile(event, user_id: int):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT balance, banned FROM users WHERE user_id = ?", (user_id,))
            user = await cursor.fetchone()
            
            if not user:
                text = f"Пользователь {user_id} не найден."
                if isinstance(event, types.CallbackQuery):
                    await event.answer(text, show_alert=True)
                else:
                    await event.reply(text)
                return
            
            # Если пользователь найден, формируем ответ
            balance, banned = user
            text = f"Профиль пользователя {user_id}:\n"
            text += f"Баланс: {balance}\n"
            text += f"Заблокирован: {'Да' if banned else 'Нет'}"
            
            if isinstance(event, types.CallbackQuery):
                await event.message.edit_text(text)
            else:
                await event.reply(text)
                
    except Exception as e:
        logger.error(f"Ошибка при получении данных пользователя: {e}")
        if isinstance(event, types.CallbackQuery):
            await event.answer("Произошла ошибка при получении данных.", show_alert=True)
        else:
            await event.reply("Произошла ошибка при получении данных.")

# Улучшенная версия функции для получения профиля
# Функция получения профиля пользователя
async def get_user_profile(user_id: int):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Получаем данные пользователя
            cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user = await cursor.fetchone()
            
            if user:
                # Преобразуем результат в словарь
                return dict(zip([desc[0] for desc in cursor.description], user))
            return None
        
    except Exception as e:
        logger.error(f"Ошибка при получении профиля пользователя: {e}")
        return None

# Функция отображения профиля пользователя
async def show_user_profile(event, user_id: int):
    try:
        # Получаем профиль пользователя
        user_data = await get_user_profile(user_id)
        
        if not user_data:
            text = f"Пользователь {user_id} не найден."
            if isinstance(event, types.CallbackQuery):
                await event.answer(text, show_alert=True)
            else:
                await event.reply(text)
            return
        
        # Получаем дополнительные данные о видео
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM videos WHERE user_id = ?", (user_id,))
            total_videos = (await cursor.fetchone())[0]
            
        # Формируем текст ответа
        text = (
            f"Профиль пользователя {user_id}\n"
            f"Баланс: {user_data.get('balance', 0)}\n"
            f"Заблокирован: {'Да' if user_data.get('banned', 0) else 'Нет'}\n"
            f"Всего видео: {total_videos}"
        )
        
        # Создаем клавиатуру
        kb = user_profile_kb(user_id, user_data.get('banned', 0))
        
        if isinstance(event, types.CallbackQuery):
            await event.message.edit_text(text, reply_markup=kb)
            await event.answer()
        else:
            await event.reply(text, reply_markup=kb)
            
    except Exception as e:
        logger.error(f"Ошибка при получении профиля пользователя: {e}")
        await event.answer("Произошла ошибка при получении профиля.")

# Обработчик ввода ID пользователя
@router.message(AdminStates.waiting_user_id)
async def process_user_id(message: types.Message, state: FSMContext):
    try:
        user_id_text = message.text.strip()
        if not user_id_text.isdigit():
            await message.answer("Неверный ID. Введите числовой ID пользователя.")
            return
        user_id = int(user_id_text)
        
        # Проверяем, что ID положительный
        if user_id <= 0:
            await message.answer("ID должен быть положительным числом.")
            return
        
        await show_user_profile(message, user_id)
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при поиске пользователя: {e}")
        await message.answer("Произошла ошибка при поиске пользователя.")


@router.callback_query(F.data.startswith("change_balance:"))
async def change_balance_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    user_id = int(callback.data.split(":")[1])
    await state.update_data(user_id=user_id)
    await callback.message.answer("Введите новое значение баланса:")
    await state.set_state(AdminStates.waiting_balance)
    await callback.answer()

@router.message(AdminStates.waiting_balance)
async def process_new_balance(message: types.Message, state: FSMContext):
    try:
        if not is_admin(message.from_user.id):
            await message.answer("Нет доступа.")
            await state.clear()
            return
        
        data = await state.get_data()
        user_id = data.get("user_id")
        if not message.text.isdigit():
            await message.answer("Введите корректное число.")
            return

        new_balance = int(message.text)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
            await db.commit()
        await message.answer(f"Баланс пользователя {user_id} обновлен до {new_balance}.")
        await show_user_profile(message, user_id)
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при изменении баланса: {e}")
        await message.answer("Произошла ошибка при обновлении баланса.")
@router.callback_query(F.data.startswith("send_message:"))
async def send_message_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    user_id = int(callback.data.split(":")[1])
    await state.update_data(user_id=user_id)
    await callback.message.answer("Введите сообщение для отправки пользователю:")
    await state.set_state(AdminStates.waiting_message)
    await callback.answer()

@router.message(AdminStates.waiting_message)
async def process_send_message(message: types.Message, state: FSMContext):
    try:
        if not is_admin(message.from_user.id):
            await message.answer("Нет доступа.")
            await state.clear()
            return
        
        data = await state.get_data()
        user_id = data.get("user_id")
        text = message.text
        
        try:
            await message.bot.send_message(user_id, f"Сообщение от администрации:\n\n{text}")
            await message.answer("Сообщение отправлено.")
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения: {e}")
            await message.answer("Не удалось отправить сообщение пользователю.")
        
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}")
        await message.answer("Произошла ошибка при отправке сообщения.")

@router.callback_query(F.data.startswith("ban_user:"))
async def ban_user_handler(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    try:
        user_id = int(callback.data.split(":")[1])
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET banned = 1 WHERE user_id = ?", (user_id,))
            await db.commit()
        await callback.message.answer(f"Пользователь {user_id} заблокирован.")
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при блокировке пользователя: {e}")
        await callback.answer("Произошла ошибка при блокировке.")

@router.callback_query(F.data.startswith("unban_user:"))
async def unban_user_handler(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    try:
        user_id = int(callback.data.split(":")[1])
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET banned = 0 WHERE user_id = ?", (user_id,))
            await db.commit()
        await callback.message.answer(f"Пользователь {user_id} разблокирован.")
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при разблокировке пользователя: {e}")
        await callback.answer("Произошла ошибка при разблокировке.")

@router.callback_query(F.data.startswith("user_videos:"))
async def user_videos_handler(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    try:
        user_id = int(callback.data.split(":")[1])
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT id, link, status FROM videos WHERE user_id = ?", (user_id,))
            videos = await cursor.fetchall()
        
        if not videos:
            await callback.message.answer("У пользователя нет видео.")
            await callback.answer()
            return
        
        kb = videos_list_kb(videos, user_id)
        text = f"Видео пользователя {user_id}:"
        await callback.message.edit_text(text, reply_markup=kb)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при получении списка видео: {e}")
        await callback.answer("Произошла ошибка при получении видео.")