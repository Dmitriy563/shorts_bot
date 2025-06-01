import os, subprocess
import pytesseract
from PIL import Image
from config import DOWNLOAD_DIR

def extract_text_from_frame(video_path: str, frame_path: str) -> str:
    # Извлечь один кадр из видео
    command = [
        "ffmpeg",
        "-i", video_path,
        "-frames:v", "1",
        "-update", "1",      # добавлено для корректного сохранения одного кадра
        "-q:v", "2",
        "-y",
        frame_path
    ]
    process = subprocess.run(command, check=True)
    if process.returncode != 0:
        raise Exception  (f"Ошибка ffmpeg: {process.stderr}")
    # Распознать текст с кадра
    image = Image.open(frame_path)
    text = pytesseract.image_to_string(image, lang='rus+eng')
    return text

def ensure_dir():
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)