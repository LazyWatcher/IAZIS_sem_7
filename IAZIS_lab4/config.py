"""
Конфигурация системы машинного перевода
"""

import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()


class Config:
    """Класс конфигурации системы"""

    # API настройки
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
    OPENROUTER_MODEL = "tngtech/deepseek-r1t-chimera:free"

    # Настройки системы
    MAX_TEXT_LENGTH = 5000  # Максимальная длина текста для перевода
    SUPPORTED_LANGUAGES = {
        'en-ru': {'source': 'английский', 'target': 'русский'},
        'en-de': {'source': 'английский', 'target': 'немецкий'},
        'en-fr': {'source': 'английский', 'target': 'французский'}
    }

    # Настройки путей
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    DICTIONARIES_DIR = os.path.join(DATA_DIR, 'dictionaries')
    LOGS_DIR = os.path.join(BASE_DIR, 'logs')

    # Предметные области
    DOMAINS = {
        'computer_science': 'компьютерные науки',
        'literature': 'литература',
        'general': 'общая'
    }

    # Создаем необходимые директории
    @staticmethod
    def create_directories():
        """Создает необходимые директории для работы системы"""
        directories = [
            Config.DATA_DIR,
            Config.DICTIONARIES_DIR,
            Config.LOGS_DIR
        ]

        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                print(f"Создана директория: {directory}")

    # Настройки файлов
    @staticmethod
    def get_dictionary_file(lang_pair, domain='general'):
        """Возвращает путь к файлу словаря"""
        filename = f"dict_{lang_pair}_{domain}.json"
        return os.path.join(Config.DICTIONARIES_DIR, filename)

    @staticmethod
    def get_output_file():
        """Возвращает путь к файлу для сохранения результатов"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"translation_output_{timestamp}.txt"
        return os.path.join(Config.DATA_DIR, filename)


# Создаем директории при импорте
Config.create_directories()

# Проверяем API ключ
if not Config.OPENROUTER_API_KEY:
    print("ВНИМАНИЕ: OPENROUTER_API_KEY не найден в переменных окружения.")
    print("Пожалуйста, создайте файл .env в корне проекта и добавьте:")
    print("OPENROUTER_API_KEY=ваш_ключ_здесь")