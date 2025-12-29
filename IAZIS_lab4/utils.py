"""
Вспомогательные утилиты для системы перевода
"""

import re
import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional


# Настройка логирования
def setup_logging():
    """Настраивает логирование системы"""
    from config import Config

    # Создаем директорию для логов если её нет
    os.makedirs(Config.LOGS_DIR, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(Config.LOGS_DIR, 'translation_system.log')),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

def clean_text(text: str) -> str:
    """
    Очищает текст от лишних пробелов и символов

    Args:
        text: Исходный текст

    Returns:
        Очищенный текст
    """
    if not text:
        return ""

    # Удаляем множественные пробелы
    text = re.sub(r'\s+', ' ', text)
    # Удаляем пробелы в начале и конце
    text = text.strip()
    # Заменяем кавычки на стандартные
    text = text.replace('"', "'")

    return text


def save_to_file(data: Any, filepath: str, encoding: str = 'utf-8'):
    """
    Сохраняет данные в файл

    Args:
        data: Данные для сохранения
        filepath: Путь к файлу
        encoding: Кодировка файла
    """
    try:
        with open(filepath, 'w', encoding=encoding) as f:
            if isinstance(data, (dict, list)):
                json.dump(data, f, ensure_ascii=False, indent=2)
            else:
                f.write(str(data))
        logger.info(f"Данные сохранены в файл: {filepath}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при сохранении в файл {filepath}: {e}")
        return False


def load_from_file(filepath: str, encoding: str = 'utf-8') -> Any:
    """
    Загружает данные из файла

    Args:
        filepath: Путь к файлу
        encoding: Кодировка файла

    Returns:
        Загруженные данные или None при ошибке
    """
    try:
        if filepath.endswith('.json'):
            with open(filepath, 'r', encoding=encoding) as f:
                return json.load(f)
        else:
            with open(filepath, 'r', encoding=encoding) as f:
                return f.read()
    except Exception as e:
        logger.error(f"Ошибка при загрузке файла {filepath}: {e}")
        return None


def validate_text_length(text: str, max_length: int = 5000) -> bool:
    """
    Проверяет длину текста

    Args:
        text: Проверяемый текст
        max_length: Максимальная допустимая длина

    Returns:
        True если длина допустима, иначе False
    """
    length = len(text)
    if length > max_length:
        logger.warning(f"Текст превышает максимальную длину: {length} > {max_length}")
        return False
    return True


def get_timestamp() -> str:
    """
    Возвращает текущую метку времени

    Returns:
        Строка с меткой времени
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def format_translation_result(source_text: str, translated_text: str,
                              lang_pair: str, domain: str) -> Dict[str, Any]:
    """
    Форматирует результат перевода

    Args:
        source_text: Исходный текст
        translated_text: Переведенный текст
        lang_pair: Пара языков
        domain: Предметная область

    Returns:
        Словарь с отформатированными результатами
    """
    from config import Config

    return {
        'timestamp': get_timestamp(),
        'language_pair': lang_pair,
        'domain': domain,
        'source_language': Config.SUPPORTED_LANGUAGES.get(lang_pair, {}).get('source', 'Unknown'),
        'target_language': Config.SUPPORTED_LANGUAGES.get(lang_pair, {}).get('target', 'Unknown'),
        'source_text': source_text,
        'translated_text': translated_text,
        'source_length': len(source_text),
        'translated_length': len(translated_text)
    }