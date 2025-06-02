from aiogram import Router, types, F
import aiosqlite
from db import DB_PATH
import urllib.parse
import logging

logger = logging.getLogger(__name__)

router = Router()

def escape_md(text: str) -> str:
    """Экранирует специальные символы MarkdownV2."""
    escape_chars = r"\_*()~`>#+-=|{}.!"
    return ''.join(f"\\{c}" if c in escape_chars else c for c in str(text))

def escape_md_url(url: str) -> str:
    """Безопасная ссылка для MarkdownV2 (экранирует только нужные части)"""
    if not url.startswith("http"):
        url = f"https://youtu.be/{url}"
    return urllib.parse.quote(url, safe=':/?&=#')

@router.message(F.text == "📊Мои видео")
async def get_my_videos(message: types.Message):
    user_id = message.from_user.id
    
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT video_id, link, status, cpm, added_at FROM videos WHERE user_id = ? ORDER BY added_at DESC LIMIT 10",
                (user_id,)
            )
            videos = await cursor.fetchall()
            
            if not videos:
                await message.answer("У вас пока нет добавленных видео.")
                return
                
            response = f"{escape_md('Ваши видео (последние 10):')}\n\n"
            
            for video_id, link, status, cpm, added_at in videos:
                video_url = escape_md_url(link or video_id)
                estimated_views = 1000  # можно сделать динамическим
                estimated_income = (cpm * estimated_views) / 1000 if cpm else 0
                
                response += (
                    f"[Ссылка]({video_url})\n"
                    f"Добавлено: {escape_md(added_at)}\n"
                    f"Статус: {escape_md(status)}\n"
                    f"CPM: {escape_md(cpm)}₽ | Доход: {escape_md(f'{estimated_income:.2f}')}₽\n"
                    f"/удалить {escape_md(video_id)}\n\n"
                )
            
            await message.answer(response, parse_mode="MarkdownV2", disable_web_page_preview=True)
            
    except Exception as e:
        logger.error(f"Ошибка при получении видео: {e}")
        await message.answer("Произошла ошибка при получении списка видео.")

@router.message(F.text.regexp(r"^/удалить\s+[\w\-]{11}$"))
async def delete_video(message: types.Message):
    user_id = message.from_user.id
    parts = message.text.strip().split(maxsplit=1)
    
    if len(parts) != 2:
        await message.answer("Неверный формат команды. Используйте: /удалить VIDEO_ID")
        return
    
    video_id = parts[1]
    
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "DELETE FROM videos WHERE user_id = ? AND video_id = ?", (user_id, video_id)
            )
            await db.commit()
            
            if cursor.rowcount == 0:
                await message.answer(
                    f"Видео с ID {escape_md(video_id)} не найдено у вас.",
                    parse_mode="MarkdownV2"
                )
                return
                
        await message.answer(
            f"Видео {escape_md(video_id)} успешно удалено.",
            parse_mode="MarkdownV2"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при удалении видео: {e}")
        await message.answer("Произошла ошибка при удалении видео.")

__all__ = ["router"]