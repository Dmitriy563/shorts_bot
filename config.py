import os
from typing import List, Dict
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

# Базовые настройки бота
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("Токен бота не найден")

# Настройки администрирования
ADMIN_IDS: List[int] = [
    779850852,
    547742823
]

# Настройки директорий
DOWNLOAD_DIR = os.path.abspath('./downloads')

# Тарифы CPM
CPM_RATES: Dict[str, float] = {
    'shorts': 0.05,
    'normal': 0.10
}

# Функция проверки корректности конфигурации
def validate_config():
    try:
        if not os.path.exists(DOWNLOAD_DIR):
            os.makedirs(DOWNLOAD_DIR)
        if not os.path.isdir(DOWNLOAD_DIR):
            raise ValueError(f"DOWNLOAD_DIR должен быть директорией: {DOWNLOAD_DIR}")
        if not isinstance(ADMIN_IDS, list):
            raise TypeError("ADMIN_IDS должен быть списком")
        if not isinstance(CPM_RATES, dict):
            raise TypeError("CPM_RATES должен быть словарем")
        
        # Исправленная проверка токена
        if not BOT_TOKEN.startswith(('1', '2', '3', '4', '5', '6', '7', '8', '9')):
            raise ValueError("Некорректный формат токена бота")
        if len(BOT_TOKEN.split(':')) != 2:
            raise ValueError("Токен должен содержать двоеточие")
        if not BOT_TOKEN.replace(':', '').isalnum():
            raise ValueError("Токен содержит недопустимые символы")
    except Exception as e:
        print(f"Ошибка конфигурации: {e}")
        raise

# Проверка конфигурации при импорте
validate_config()
