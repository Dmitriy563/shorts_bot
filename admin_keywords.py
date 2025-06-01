from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMIN_IDS
from admin_kb import keyword_menu_kb
import aiosqlite
from db import DB_PATH

router = Router()

class KeywordFSM(StatesGroup):
    awaiting_keyword_to_add = State()
    awaiting_keyword_to_remove = State()

def ADMIN_IDS(user_id: int) -> bool:
    return user_id in ADMIN_IDS

@router.message(F.text == "Ключевые слова")
async def show_keywords(message: types.Message):
    if not ADMIN_IDS(message.from_user.id):
        return await message.answer("У вас нет доступа к этой команде.")
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT keyword FROM keywords ORDER BY keyword") as cursor:
            rows = await cursor.fetchall()
            keywords = [row[0] for row in rows]

    if keywords:
        text = "Ключевые слова для рекламы:\n\n" + "\n".join(f"• {kw}" for kw in keywords)
    else:
        text = "Ключевых слов пока нет."
    await message.answer(text, reply_markup=keyword_menu_kb)

@router.message(F.text == "Добавить ключ")
async def ask_keyword_to_add(message: types.Message, state: FSMContext):
    if not ADMIN_IDS(message.from_user.id):
        return await message.answer("У вас нет доступа к этой команде.")
    await message.answer("Введите новое ключевое слово:")
    await state.set_state(KeywordFSM.awaiting_keyword_to_add)

@router.message(KeywordFSM.awaiting_keyword_to_add)
async def add_keyword(message: types.Message, state: FSMContext):
    keyword = message.text.strip().upper()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT 1 FROM keywords WHERE keyword = ?", (keyword,))
        exists = await cursor.fetchone()
        if exists:
            await message.answer(f"Ключевое слово '{keyword}' уже существует.")
            return
        await db.execute("INSERT INTO keywords (keyword) VALUES (?)", (keyword,))
        await db.commit()
    await message.answer(f"Ключевое слово '{keyword}' успешно добавлено.")
    await state.clear()

@router.message(F.text == "Удалить ключ")
async def ask_keyword_to_remove(message: types.Message, state: FSMContext):
    if not ADMIN_IDS(message.from_user.id):
        return await message.answer("У вас нет доступа к этой команде.")
    await message.answer("Введите ключевое слово для удаления:")
    await state.set_state(KeywordFSM.awaiting_keyword_to_remove)

@router.message(KeywordFSM.awaiting_keyword_to_remove)
async def remove_keyword(message: types.Message, state: FSMContext):
    keyword = message.text.strip().upper()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT 1 FROM keywords WHERE keyword = ?", (keyword,))
        exists = await cursor.fetchone()
        if not exists:
            await message.answer(f"Ключевое слово '{keyword}' не найдено.")
            return
        await db.execute("DELETE FROM keywords WHERE keyword = ?", (keyword,))
        await db.commit()
    await message.answer(f"Ключевое слово '{keyword}' успешно удалено.")
    await state.clear()