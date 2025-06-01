from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from db import DB_PATH
import aiosqlite
from config import ADMIN_IDS, CPM_RATES

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
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Общая статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="Найти пользователя", callback_data="admin_search_user")],
        [InlineKeyboardButton(text="Заявки на вывод", callback_data="admin_withdrawals")],
        [InlineKeyboardButton(text="Рассылка", callback_data="admin_broadcast")],
    ])
    return kb

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
    # videos = list of tuples (id, link, status)
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
        buttons = []
        if wd[2] == "pending":
            buttons.append(InlineKeyboardButton(text=f"Подтвердить {wd[0]}", callback_data=f"approve_wd:{wd[0]}:{user_id}"))
            buttons.append(InlineKeyboardButton(text=f"Отклонить {wd[0]}", callback_data=f"reject_wd:{wd[0]}:{user_id}"))
            kb.row(*buttons)
    kb.add(InlineKeyboardButton(text="Назад", callback_data=f"user_profile:{user_id}"))
    return kb

# --- Хендлеры ---

@router.message(Command("admin"))
async def admin_main_menu(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет доступа к админке.")
        return
    await message.answer("Главное меню админа", reply_markup=main_admin_kb())

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
    user_id_text = message.text.strip()
    if not user_id_text.isdigit():
        await message.answer("Неверный ID.Введите числовой ID пользователя.")
        return
    user_id = int(user_id_text)
    await show_user_profile(message, user_id)
    await state.clear()

async def show_user_profile(event, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT balance, income, banned FROM users WHERE user_id = ?", (user_id,))
        user = await cursor.fetchone()
        if not user:
            if isinstance(event, types.CallbackQuery):
                await event.answer(f"Пользователь {user_id} не найден.", show_alert=True)
            else:
                await event.reply(f"Пользователь {user_id} не найден.")
            return
        balance, income, banned = user

        cursor = await db.execute("SELECT COUNT(*) FROM videos WHERE user_id = ?", (user_id,))
        total_videos = (await cursor.fetchone())[0]

        text = (
            f"Профиль пользователя {user_id}\n"
            f"Баланс: {balance}\n"
            f"Доход: {income}\n"
            f"Заблокирован: {'Да' if banned else 'Нет'}\n"
            f"Всего видео: {total_videos}"
        )

    kb = user_profile_kb(user_id, banned)
    if isinstance(event, types.CallbackQuery):
        await event.message.edit_text(text, reply_markup=kb)
        await event.answer()
    else:
        await event.reply(text, reply_markup=kb)

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
    except Exception:
        await message.answer("Не удалось отправить сообщение пользователю.")
    await state.clear()

@router.callback_query(F.data.startswith("ban_user:"))
async def ban_user_handler(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    user_id = int(callback.data.split(":")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET banned = 1 WHERE user_id = ?", (user_id,))
        await db.commit()
    await callback.message.answer(f"Пользователь {user_id} заблокирован.")
    await callback.answer()

@router.callback_query(F.data.startswith("unban_user:"))
async def unban_user_handler(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    user_id = int(callback.data.split(":")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET banned = 0 WHERE user_id = ?", (user_id,))
        await db.commit()
    await callback.message.answer(f"Пользователь {user_id} разблокирован.")
    await callback.answer()

@router.callback_query(F.data.startswith("user_videos:"))
async def user_videos_handler(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
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