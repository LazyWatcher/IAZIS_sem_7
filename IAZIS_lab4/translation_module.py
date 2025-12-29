"""
Модуль машинного перевода через OpenRouter API
"""

import json
import time
from typing import Dict, List, Optional, Any
import requests

from config import Config
from utils import logger, format_translation_result, validate_text_length


class TranslationModule:
    """Класс для машинного перевода текстов"""

    def __init__(self):
        """Инициализация модуля перевода"""
        self.api_key = Config.OPENROUTER_API_KEY
        self.api_url = Config.OPENROUTER_API_URL
        self.model = Config.OPENROUTER_MODEL

        # Кэш для хранения переводов
        self.translation_cache = {}

        # Простой и строгий промпт для перевода
        self.translation_prompt = (
            "You are a professional translator. "
            "Translate the following text from English to Russian. "
            "Return ONLY the translated text without any explanations, thoughts, or additional text."
        )

        # Словарь для хранения пользовательских терминов
        self.custom_dictionary = {}

    def translate_text(self,
                       text: str,
                       lang_pair: str = 'en-ru',
                       use_cache: bool = True) -> Dict[str, Any]:
        """
        Переводит текст с использованием Grok через OpenRouter

        Args:
            text: Текст для перевода
            lang_pair: Пара языков (например, 'en-ru')
            use_cache: Использовать кэш

        Returns:
            Словарь с результатами перевода
        """
        if not text:
            return {
                'success': False,
                'error': 'Текст для перевода пуст',
                'translated_text': '',
                'source_text': text
            }

        # Проверяем длину текста
        if not validate_text_length(text, Config.MAX_TEXT_LENGTH):
            return {
                'success': False,
                'error': f'Текст превышает максимальную длину {Config.MAX_TEXT_LENGTH} символов',
                'translated_text': '',
                'source_text': text
            }

        # Проверяем кэш
        cache_key = f"{text}_{lang_pair}"
        if use_cache and cache_key in self.translation_cache:
            logger.info(f"Используется кэшированный перевод для ключа: {cache_key[:50]}...")
            return self.translation_cache[cache_key]

        # Проверяем наличие API ключа
        if not self.api_key or self.api_key == "":
            return {
                'success': False,
                'error': 'API ключ OpenRouter не установлен. Добавьте ваш ключ в файл .env',
                'translated_text': '',
                'source_text': text,
                'suggestion': 'Создайте файл .env в корне проекта и добавьте OPENROUTER_API_KEY=ваш_ключ'
            }

        # Определяем языки
        source_lang = lang_pair.split('-')[0]
        target_lang = lang_pair.split('-')[1]

        # Строгие инструкции для перевода
        translation_instruction = (
            f"Translate the following text from {source_lang.upper()} to {target_lang.upper()}.\n\n"
            "IMPORTANT: You must return ONLY the translated text without:\n"
            "1. Any explanations or thoughts\n"
            "2. Phrases like 'Alright', 'Let me translate', 'First', etc.\n"
            "3. Any additional commentary\n"
            "4. Any markdown formatting\n"
            "5. Any prefixes like 'Translation:' or 'The translation is:'\n\n"
            "Text to translate:\n"
            f"{text}"
        )

        # Формируем полный промпт
        full_prompt = f"{self.translation_prompt}\n\n{translation_instruction}"

        try:
            # Подготавливаем запрос к API
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'http://localhost:8000',
                'X-Title': 'Machine Translation System'
            }

            payload = {
                'model': self.model,
                'messages': [
                    {'role': 'system', 'content': 'You are a professional translator. Provide only the translation without any additional text.'},
                    {'role': 'user', 'content': full_prompt}
                ],
                'max_tokens': min(len(text) * 2, 4000),
                'temperature': 0.1,  # Низкая температура для детерминированных ответов
                'top_p': 0.8
            }

            logger.info(f"Отправка запроса на перевод (длина текста: {len(text)})...")

            # Отправляем запрос
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )

            # Проверяем ответ
            if response.status_code == 200:
                try:
                    result = response.json()

                    # Проверяем структуру ответа
                    if 'choices' not in result or not result['choices']:
                        error_msg = f"Неверная структура ответа API: {result}"
                        logger.error(error_msg)
                        return {
                            'success': False,
                            'error': error_msg,
                            'translated_text': '',
                            'source_text': text
                        }

                    # Извлекаем переведенный текст
                    translated_text = result['choices'][0]['message']['content'].strip()

                    # Очищаем текст от возможных рассуждений модели
                    translated_text = self._clean_translation_output(translated_text)

                    # Форматируем результат
                    translation_result = format_translation_result(text, translated_text, lang_pair, 'general')
                    translation_result['success'] = True
                    translation_result['api_response'] = result
                    translation_result['cache_key'] = cache_key

                    # Сохраняем в кэш
                    self.translation_cache[cache_key] = translation_result

                    logger.info(f"Перевод успешно выполнен (символов: {len(translated_text)})")
                    return translation_result

                except json.JSONDecodeError as e:
                    error_msg = f"Ошибка парсинга JSON ответа: {e}. Ответ: {response.text[:200]}"
                    logger.error(error_msg)
                    return {
                        'success': False,
                        'error': error_msg,
                        'translated_text': '',
                        'source_text': text
                    }

            else:
                error_msg = f"Ошибка API: {response.status_code} - {response.text[:200]}"
                logger.error(error_msg)

                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code,
                    'translated_text': '',
                    'source_text': text
                }

        except requests.exceptions.Timeout:
            error_msg = "Таймаут при обращении к API перевода (30 секунд)"
            logger.error(error_msg)

            return {
                'success': False,
                'error': error_msg,
                'translated_text': '',
                'source_text': text
            }

        except requests.exceptions.RequestException as e:
            error_msg = f"Ошибка сети: {str(e)}"
            logger.error(error_msg)

            return {
                'success': False,
                'error': error_msg,
                'translated_text': '',
                'source_text': text
            }

        except Exception as e:
            error_msg = f"Неожиданная ошибка: {str(e)}"
            logger.error(error_msg)

            return {
                'success': False,
                'error': error_msg,
                'translated_text': '',
                'source_text': text
            }

    def _clean_translation_output(self, text: str) -> str:
        """
        Очищает вывод перевода от нежелательных элементов

        Args:
            text: Сырой вывод перевода

        Returns:
            Очищенный перевод
        """
        # Убираем распространенные префиксы
        prefixes_to_remove = [
            'Alright, ',
            'Okay, ',
            'So, ',
            'The translation is: ',
            'Translated text: ',
            'Here is the translation: ',
            'Перевод: ',
            'Вот перевод: '
        ]

        for prefix in prefixes_to_remove:
            if text.startswith(prefix):
                text = text[len(prefix):]

        # Разделяем на строки и убираем строки, которые выглядят как рассуждения
        lines = text.split('\n')
        cleaned_lines = []

        # Шаблоны строк, которые нужно удалить (рассуждения модели)
        reasoning_patterns = [
            'alright', 'let\'s', 'first', 'i need', 'the key terms',
            'now', 'putting it', 'final check', 'so the final',
            'давайте', 'сначала', 'ключевые термины',
            'теперь', 'собирая все вместе', 'итоговый перевод'
        ]

        for line in lines:
            line_lower = line.lower().strip()
            # Пропускаем пустые строки
            if not line_lower:
                continue

            # Пропускаем строки, которые являются рассуждениями
            is_reasoning = any(pattern in line_lower for pattern in reasoning_patterns)
            if not is_reasoning:
                # Также пропускаем строки, которые выглядят как команды или вопросы
                if not (line_lower.startswith(('wait', 'hmm', 'um', 'well')) or
                        line_lower.endswith('?') or
                        'let me' in line_lower or
                        'i think' in line_lower):
                    cleaned_lines.append(line.strip())

        # Если после очистки остались строки, объединяем их
        if cleaned_lines:
            text = ' '.join(cleaned_lines)
        else:
            # Если все строки были удалены, возвращаем оригинальный текст
            # но убираем только очевидные префиксы
            for prefix in prefixes_to_remove:
                if text.startswith(prefix):
                    text = text[len(prefix):]

        return text.strip()

    def batch_translate(self,
                       texts: List[str],
                       lang_pair: str = 'en-ru') -> List[Dict[str, Any]]:
        """
        Пакетный перевод нескольких текстов

        Args:
            texts: Список текстов для перевода
            lang_pair: Пара языков

        Returns:
            Список результатов перевода
        """
        results = []

        for i, text in enumerate(texts, 1):
            logger.info(f"Перевод текста {i}/{len(texts)}...")

            result = self.translate_text(text, lang_pair)
            results.append(result)

            # Небольшая задержка между запросами
            if i < len(texts):
                time.sleep(0.5)

        return results

    def add_to_custom_dictionary(self,
                                source_word: str,
                                translation: str,
                                pos_tag: str = ''):
        """
        Добавляет слово в пользовательский словарь

        Args:
            source_word: Исходное слово
            translation: Перевод
            pos_tag: Часть речи
        """
        if not source_word or not translation:
            return

        key = source_word.lower()

        if key not in self.custom_dictionary:
            self.custom_dictionary[key] = []

        self.custom_dictionary[key].append({
            'translation': translation,
            'pos_tag': pos_tag,
            'added_date': time.strftime("%Y-%m-%d %H:%M:%S")
        })

        logger.info(f"Добавлено в словарь: '{source_word}' -> '{translation}'")

    def get_custom_translation(self, word: str) -> Optional[str]:
        """
        Получает перевод из пользовательского словаря

        Args:
            word: Слово для перевода

        Returns:
            Перевод или None, если не найден
        """
        key = word.lower()

        if key in self.custom_dictionary:
            entries = self.custom_dictionary[key]

            # Возвращаем первый доступный перевод
            if entries:
                return entries[0]['translation']

        return None

    def clear_cache(self):
        """Очищает кэш переводов"""
        self.translation_cache.clear()
        logger.info("Кэш переводов очищен")

    def get_translation_stats(self) -> Dict[str, Any]:
        """
        Возвращает статистику переводов

        Returns:
            Словарь со статистикой
        """
        total_translations = len(self.translation_cache)
        total_custom_words = len(self.custom_dictionary)

        # Подсчитываем успешные переводы
        successful = sum(1 for result in self.translation_cache.values()
                        if result.get('success', False))

        return {
            'total_translations': total_translations,
            'successful_translations': successful,
            'cache_size': len(self.translation_cache),
            'custom_dictionary_size': total_custom_words,
            'success_rate': (successful / total_translations * 100) if total_translations > 0 else 0
        }

    def save_custom_dictionary(self, filepath: str):
        """
        Сохраняет пользовательский словарь в файл

        Args:
            filepath: Путь к файлу
        """
        try:
            import json
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.custom_dictionary, f, ensure_ascii=False, indent=2)
            logger.info(f"Пользовательский словарь сохранен в {filepath}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении словаря: {e}")
            return False

    def load_custom_dictionary(self, filepath: str):
        """
        Загружает пользовательский словарь из файла

        Args:
            filepath: Путь к файлу
        """
        try:
            import json
            with open(filepath, 'r', encoding='utf-8') as f:
                self.custom_dictionary = json.load(f)
            logger.info(f"Пользовательский словарь загружен из {filepath}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при загрузке словаря: {e}")
            return False