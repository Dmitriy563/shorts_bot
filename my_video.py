from aiogram import Router, types, F
import aiosqlite
from db import DB_PATH
import urllib.parse

router = Router()

def escape_md(text: str) -> str:
    """Экранирует специальные символы MarkdownV2."""
    escape_chars = r"\_*[]()~`>#+-=|{}.!"
    return ''.join(f"\\{c}" if c in escape_chars else c for c in str(text))

def escape_md_url(url: str) -> str:
    """Безопасная ссылка для MarkdownV2 (экранирует только нужные части)"""
    return urllib.parse.quote(url, safe=':/?&=#')

@router.message(F.text == "📊Мои видео")
async def get_my_videos(message: types.Message):
    user_id = message.from_user.id

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT video_id, link, status, cpm, added_at FROM videos WHERE user_id = ? ORDER BY added_at DESC LIMIT 10",
            (user_id,)
        )
        videos = await cursor.fetchall()

    if not videos:
        await message.answer("У вас пока нет добавленных видео.")
        return

    response = escape_md("Ваши видео (последние 10):") + "\n\n"

    for video_id, link, status, cpm, added_at in videos:
        video_url = link if link and link.startswith("http") else f"https://youtu.be/{video_id}"
        estimated_views = 1000
        estimated_income = (cpm * estimated_views) / 1000 if cpm else 0

        response += (
            f"[Ссылка]({escape_md_url(video_url)})\n"
            f"Добавлено: {escape_md(added_at)}\n"
            f"Статус: {escape_md(status)}\n"
            f"CPM: {escape_md(cpm)}₽ \\| Доход: {escape_md(f'{estimated_income:.2f}')}₽\n"
            f"/удалить {escape_md(video_id)}\n\n"
        )

    await message.answer(response, parse_mode="MarkdownV2", disable_web_page_preview=True)

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
    except Exception as e:
        await message.answer(
            f"Ошибка при удалении видео: {escape_md(str(e))}",
            parse_mode="MarkdownV2"
        )
        return

    await message.answer(
        f"Видео {escape_md(video_id)} успешно удалено.",
        parse_mode="MarkdownV2"
    )

__all__ = ["router"]