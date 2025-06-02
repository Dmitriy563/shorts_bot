from gc import callbacks
from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from db import DB_PATH
import aiosqlite
import datetime
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()

class WithdrawState(StatesGroup):
    awaiting_amount = State()
    awaiting_confirmation = State()

# Константы
MIN_WITHDRAW = 100
MAX_WITHDRAW = 100000
COMMISSION_PERCENT = 1

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
    await callback.message.answer(
        f"Введите сумму для вывода {method.upper()} (от {MIN_WITHDRAW} до {MAX_WITHDRAW}):"
    )
    await callback.answer()
    await FSMContext.set_state(WithdrawState.awaiting_amount)

@router.message(WithdrawState.awaiting_amount)
async def process_withdraw_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        if not MIN_WITHDRAW <= amount <= MAX_WITHDRAW:
            raise ValueError
        
        # Проверка баланса пользователя (пример)
        user_balance = await check_user_balance(message.from_user.id)
        if amount > user_balance:
            raise ValueError("Недостаточно средств")
        
        commission = amount * (COMMISSION_PERCENT / 100)
        total = amount + commission
        
        await message.answer(
            f"Вы хотите вывести {amount:.2f}?\n"
            f"Комиссия: {commission:.2f}\n"
            f"Итого: {total:.2f}"
        )
        await state.update_data(amount=amount, method=callbacks.data.split('_')[1])
        await state.set_state(WithdrawState.awaiting_confirmation)
        
    except ValueError as e:
        await message.answer("Ошибка: некорректная сумма")
        logger.error(f"Ошибка ввода суммы: {e}")
    except Exception as e:
        logger.error(f"Ошибка обработки вывода: {e}")
        await message.answer("Произошла ошибка")

# Продолжение предыдущего кода

@router.message(WithdrawState.awaiting_confirmation)
async def confirm_withdraw(message: types.Message, state: FSMContext):
    if message.text.lower() in ["да", "yes"]:
        data = await state.get_data()
        amount = data['amount']
        method = data['method']
        
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "INSERT INTO withdrawals (user_id, amount, method, status, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (
                        message.from_user.id,
                        amount,
                        method,
                        "pending",
                        datetime.datetime.now()
                    )
                )
                await db.commit()
                
            await update_user_balance(message.from_user.id, -amount)
            await message.answer(f"Вывод {amount:.2f} через {method.upper()} успешно оформлен!")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения вывода: {e}")
            await message.answer("Произошла ошибка при оформлении вывода")
            
    else:
        await message.answer("Операция отменена")
        
    await state.clear()

# Обработчик отмены
@router.message(lambda msg: msg.text.lower() in ["отмена", "cancel"])
async def cancel_withdraw(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Операция отменена.")

# Дополнительные функции
async def check_user_balance(user_id):
    # Здесь должен быть код проверки баланса пользователя
    # Пример реализации:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def update_user_balance(user_id, amount):
    # Здесь должен быть код обновления баланса пользователя
    # Пример реализации:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
            (amount, user_id)
        )
        await db.commit()

# Обработчик истории выводов
@router.message(lambda msg: msg.text == "История выводов")
async def show_withdraw_history(message: types.Message):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT amount, method, status, created_at FROM withdrawals "
                "WHERE user_id = ? ORDER BY created_at DESC",
                (message.from_user.id,)
            ) as cursor:
                rows = await cursor.fetchall()
                
                if not rows:
                    await message.answer("История выводов пуста")
                    return
                    
                history_text = "История выводов:\n"
                for row in rows:
                    history_text += f"Сумма: {row[0]}\n" \
                                   f"Метод: {row[1].upper()}\n" \
                                   f"Статус: {row[2]}\n" \
                                   f"Дата: {row[3]}\n\n"
                
                await message.answer(history_text)
                
    except Exception as e:
        logger.error(f"Ошибка получения истории: {e}")
        await message.answer("Произошла ошибка при получении истории")
