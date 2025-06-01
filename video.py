from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import CPM_RATES, ADMIN_IDS
from db import DB_PATH
from handlers.admin_kb import admin_video_moderation_kb

import yt_dlp
import os
import aiosqlite
import datetime
import shutil
import re
import subprocess
import uuid
import asyncio

from PIL import Image
import pytesseract
from aiogram.types import FSInputFile

router = Router()

class UploadState(StatesGroup):
    awaiting_link = State()

# --- Вспомогательные функции ---

def extract_frame_at_time(video_path: str, time_sec: float, frame_path: str):
    command = [
        "ffmpeg", "-ss", str(time_sec), "-i", video_path,
        "-frames:v", "1", "-q:v", "2", "-y", frame_path
    ]
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def preprocess_image(image_path: str):
    image = Image.open(image_path).convert("L")
    return image.point(lambda x: 0 if x < 150 else 255, '1')
import cv2 
import numpy as np

def get_motion_mask(frame1, frame2, threshold=30):
    """
    Возвращает маску движущихся областей между двумя кадрами.
    :param frame1: первый кадр (BGR или grayscale)
    :param frame2: второй кадр того же размера и типа
    :param threshold: порог для определения движения
    :return: маска (0/255) движущихся областей
    """
    # Если кадры цветные, переводим в оттенки серого
    if len(frame1.shape) == 3:
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
    else:
        gray1 = frame1
        gray2 = frame2

    # Вычисляем абсолютную разницу
    diff = cv2.absdiff(gray1, gray2)

    # Применяем порог, чтобы выделить значимые изменения
    _, motion_mask = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)

    # Можно применить морфологические операции для удаления шума
    kernel = np.ones((3, 3), np.uint8)
    motion_mask = cv2.morphologyEx(motion_mask, cv2.MORPH_OPEN, kernel)

    return motion_mask
def ocr_from_image(frame_path: str) -> str:
    image = preprocess_image(frame_path)
    return pytesseract.image_to_string(image, lang='rus+eng')

def fuzzy_check_ad(text: str) -> bool:
    keywords = [
        "РЕКЛАМА", "DRAGON MONEY", "DRAGONMONEY", "ДРАГОН МАНИ", "DRAGON", "CASINO", "MONEY", "профиля", "ПРОФИЛЯ", "в описании", "депозит", "депозиту", "ДЕПОЗИТ", "ДЕПОЗИТУ",
        "ПОДАРОК", "БОНУС", "ПРОМОКОД", "1XBET", "XBET", "RIOBET", "ВУЛКАН", "Вулкан", "вулкан","ПРОМОКОДУ"
    ]
    text = text.upper()
    return any(keyword in text for keyword in keywords)

def cleanup_files(paths: list):
    for path in paths:
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            else:
                os.remove(path)

async def check_ad_with_timeout(video_path: str, temp_dir: str, timeout_sec: int = 15) -> str:
    loop = asyncio.get_event_loop()
    def blocking_check():
        os.makedirs(temp_dir, exist_ok=True)
        for t in [round(x * 0.15, 1) for x in range(0, 100)]:
            frame_path = os.path.join(temp_dir, f"frame_{t}.jpg")
            extract_frame_at_time(video_path, t, frame_path)
            text = ocr_from_image(frame_path)
            print(f"[OCR {t} сек]: {repr(text)}")
            if fuzzy_check_ad(text):
                return "found"
        return "not_found"

    try:
        result = await asyncio.wait_for(loop.run_in_executor(None, blocking_check), timeout=timeout_sec)
    except asyncio.TimeoutError:
        result = "moderation"

    cleanup_files([temp_dir])
    return result

async def save_video_to_db(user_id: int, video_id: str, link: str, status: str):
    cpm = CPM_RATES.get('shorts', 0) if status == "found" else 0
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT INTO videos (user_id, video_id, link, status, cpm, platform, added_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, video_id, link, status,
            cpm, 'shorts', datetime.datetime.now().isoformat()
        ))
        await db.commit()

# --- Хендлеры ---

@router.message(F.text == "📥Загрузить видео")
async def ask_video_link(message: types.Message, state: FSMContext):
    await message.answer("Отправьте ссылку на ваше видео (YouTube Shorts).")
    await state.set_state(UploadState.awaiting_link)

@router.message(UploadState.awaiting_link)
async def process_link(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    link = message.text.strip()

    # Проверка на бан и лимит загрузок
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT banned FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        if row and row[0] == 1:
            await message.answer("Вы заблокированы и не можете загружать видео.")
            await state.clear()
            return

        today = datetime.datetime.now().date().isoformat()
        cursor = await db.execute("""SELECT COUNT(*) FROM videos
            WHERE user_id = ? AND substr(added_at,1,10) = ?
        """, (user_id, today))
        count = (await cursor.fetchone())[0]

    if count >= 100:
        await message.answer("Вы превысили лимит в 100 видео на день.")
        await state.clear()
        return

    # Извлечение ID видео
    match = re.search(r'(?:v=|\/shorts\/|\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})', link)
    if not match:
        await message.answer("Не удалось определить ID видео. Убедитесь, что ссылка корректна.")
        await state.clear()
        return
    video_id = match.group(1)

    # Подготовка путей
    os.makedirs("downloads", exist_ok=True)
    video_path = os.path.abspath(f"downloads/{video_id}.mp4")
    temp_dir = os.path.abspath(f"downloads/temp_{uuid.uuid4().hex}")

    # Проверка ffmpeg
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        await message.answer("ffmpeg не найден. Установите его и добавьте в PATH.")
        await state.clear()
        return

    # Скачивание видео
    ydl_opts = {
        'outtmpl': video_path,
        'format': 'mp4/best',
        'quiet': True,
        'no_warnings': True,
        'ffmpeg_location': ffmpeg_path
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([link])
    except Exception as e:
        await message.answer(f"Ошибка при загрузке видео: {e}")
        await state.clear()
        return

    # Анализ рекламы
    try:
        status = await check_ad_with_timeout(video_path, temp_dir, timeout_sec=15)
    except Exception as e:
        await message.answer(f"Ошибка при анализе видео: {e}")
        cleanup_files([video_path])
        await state.clear()
        return

    # Сохранение результата
    await save_video_to_db(user_id, video_id, link, status)
    await state.clear()

    # Ответ пользователю
    if status == "found":
        await message.answer("✅ Видео прошло проверку и добавлено в монетизацию.")
    elif status == "moderation":
        await message.answer("⚠️ Видео не содержит явной рекламы. Отправлено на модерацию.")
    else:
        await message.answer("❌ Видео не содержит рекламной вставки. Загрузка отклонена.")

    # Уведомление админам
    for admin_id in ADMIN_IDS:
        try:
            if status == "moderation":
                video_file = FSInputFile(video_path)
                await message.bot.send_video(
                chat_id=admin_id,
                video=video_file,
                caption=(
                    f"❗ Видео пользователя [{message.from_user.full_name}](tg://user?id={user_id}) "
                    f"требует ручной модерации.\nСсылка: {link}"
                ),
                reply_markup=admin_video_moderation_kb(video_id),
                parse_mode="Markdown"
            )
            else:
                await message.bot.send_message(
                chat_id=admin_id,
                text=(
                    f"Пользователь [{message.from_user.full_name}](tg://user?id={user_id}) загрузил видео: {link}\n"
                    f"Статус: `{status}`"
                ),
                parse_mode="Markdown"
            )
        except Exception as e:
         print(f"Ошибка отправки админам: {e}")

# Удаление видео после отправки
