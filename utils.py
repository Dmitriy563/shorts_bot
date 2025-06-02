import os
import subprocess
import pytesseract
from PIL import Image
from config import DOWNLOAD_DIR
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_text_from_frame(video_path: str, frame_path: str) -> str:
    try:
        # Извлечь один кадр из видео
        command = [
            "ffmpeg",
            "-i", video_path,
            "-frames:v", "1",
            "-update", "1",
            "-q:v", "2",
            "-y",
            frame_path
        ]
        
        # Улучшенная обработка subprocess
        process = subprocess.run(command, capture_output=True, text=True)
        
        if process.returncode != 0:
            logger.error(f"Ошибка ffmpeg: {process.stderr}")
            raise Exception(f"Ошибка ffmpeg: {process.stderr}")
        
        # Распознать текст с кадра
        try:
            image = Image.open(frame_path)
            text = pytesseract.image_to_string(image, lang='rus+eng')
            return text
        except Exception as e:
            logger.error(f"Ошибка при обработке изображения: {e}")
            raise
    
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        raise

def ensure_dir():
    try:
        if not os.path.exists(DOWNLOAD_DIR):
            logger.info(f"Создаю директорию: {DOWNLOAD_DIR}")
            os.makedirs(DOWNLOAD_DIR)
    except Exception as e:
        logger.error(f"Ошибка при создании директории: {e}")
        raise