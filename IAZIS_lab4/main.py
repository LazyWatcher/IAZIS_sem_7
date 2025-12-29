#!/usr/bin/env python3
"""
Основной файл системы машинного перевода
Лабораторная работа №4, Вариант 2: Англо-русский перевод
"""

import sys
import os
import argparse

# Добавляем текущую директорию в путь для импорта модулей
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
from translation_module import TranslationModule
from text_processor import TextProcessor
from database import get_database
from gui_interface import TranslationApp





def run_cli():
    """Запуск системы в режиме командной строки"""
    print("=" * 60)
    print("СИСТЕМА МАШИННОГО ПЕРЕВОДА ТЕКСТОВ - КОМАНДНАЯ СТРОКА")
    print("=" * 60)

    # Проверяем наличие API ключа
    if not Config.OPENROUTER_API_KEY:
        print("\nОШИБКА: Не найден API ключ OpenRouter!")
        print("Пожалуйста, добавьте ваш ключ в файл .env")
        print("или установите переменную окружения OPENROUTER_API_KEY")
        return

    # Создаем экземпляры модулей
    translator = TranslationModule()
    processor = TextProcessor()
    db = get_database()

    print(f"\nНаправление перевода: {Config.SUPPORTED_LANGUAGES['en-ru']['source']} -> "
          f"{Config.SUPPORTED_LANGUAGES['en-ru']['target']}")
    print(f"Предметные области: {Config.DOMAINS['computer_science']}, "
          f"{Config.DOMAINS['literature']}")

    # Пример работы с системой
    print("\nПример работы:")
    print("-" * 40)

    test_text = "Hello world! This is a test of machine translation system."
    print(f"Исходный текст: {test_text}")

    # Обработка текста
    processed = processor.preprocess_text(test_text)
    print(f"Количество слов: {processed['word_count']}")

    # Перевод
    translation = translator.translate_text(test_text, 'en-ru', 'computer_science')
    if translation.get('success', False):
        print(f"Перевод: {translation['translated_text']}")

        # Сохранение в БД
        db.save_translation_history(
            source_text=test_text,
            translated_text=translation['translated_text'],
            source_lang='en',
            target_lang='ru',
            domain='computer_science',
            word_count=processed['word_count'],
            translated_count=processed['word_count']
        )
        print("Результат сохранен в базу данных")
    else:
        print(f"Ошибка перевода: {translation.get('error', 'Неизвестная ошибка')}")

    # Статистика
    print("\nСтатистика системы:")
    print("-" * 40)
    trans_stats = translator.get_translation_stats()
    dict_stats = db.get_dictionary_stats()

    print(f"Всего переводов: {trans_stats.get('total_translations', 0)}")
    print(f"Успешных переводов: {trans_stats.get('successful_translations', 0)}")
    print(f"Слов в словаре: {dict_stats.get('total_words', 0)}")

    db.close()


def run_gui():
    """Запуск графического интерфейса"""
    print("=" * 60)
    print("СИСТЕМА МАШИННОГО ПЕРЕВОДА ТЕКСТОВ - ГРАФИЧЕСКИЙ ИНТЕРФЕЙС")
    print("=" * 60)

    # Проверяем наличие API ключа
    if not Config.OPENROUTER_API_KEY:
        print("\nОШИБКА: Не найден API ключ OpenRouter!")
        print("Пожалуйста, добавьте ваш ключ в файл .env")
        print("или установите переменную окружения OPENROUTER_API_KEY")

        # Все равно запускаем GUI, но с предупреждением
        print("\nЗапуск GUI в режиме без API...")

    # Создаем экземпляры модулей
    translator = TranslationModule()
    processor = TextProcessor()

    # Запускаем интерфейс
    print("\nЗапуск графического интерфейса...")
    app = TranslationApp(translator, processor)
    app.run()


def show_system_info():
    """Показывает информацию о системе"""
    print("=" * 60)
    print("ИНФОРМАЦИЯ О СИСТЕМЕ МАШИННОГО ПЕРЕВОДА")
    print("=" * 60)

    print(f"\nВерсия: 1.0.0")
    print(f"Лабораторная работа №4, Вариант 2")
    print(f"\nНаправление перевода: Английский -> Русский")
    print(f"\nПредметные области:")
    for key, value in Config.DOMAINS.items():
        print(f"  - {key}: {value}")

    print(f"\nПоддерживаемые языковые пары:")
    for key, value in Config.SUPPORTED_LANGUAGES.items():
        print(f"  - {key}: {value['source']} -> {value['target']}")

    print(f"\nМаксимальная длина текста: {Config.MAX_TEXT_LENGTH} символов")

    if Config.OPENROUTER_API_KEY:
        print(f"\nAPI ключ: {'*' * 10}{Config.OPENROUTER_API_KEY[-4:]}")
    else:
        print(f"\nAPI ключ: НЕ НАЙДЕН")

    print(f"\nДиректории:")
    print(f"  - Данные: {Config.DATA_DIR}")
    print(f"  - Словари: {Config.DICTIONARIES_DIR}")
    print(f"  - Логи: {Config.LOGS_DIR}")


def main():
    """Основная функция запуска системы"""
    parser = argparse.ArgumentParser(
        description='Система машинного перевода текстов',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s              # Запуск графического интерфейса
  %(prog)s --cli        # Запуск в режиме командной строки
  %(prog)s --info       # Показать информацию о системе
  %(prog)s --text "Hello" --domain computer_science  # Быстрый перевод
        """
    )

    parser.add_argument('--cli', action='store_true',
                        help='Запуск в режиме командной строки')
    parser.add_argument('--gui', action='store_true',
                        help='Запуск графического интерфейса (по умолчанию)')
    parser.add_argument('--info', action='store_true',
                        help='Показать информацию о системе')
    parser.add_argument('--text', type=str,
                        help='Быстрый перевод текста')
    parser.add_argument('--domain', type=str, default='computer_science',
                        help='Предметная область для перевода (computer_science, literature)')
    parser.add_argument('--output', type=str,
                        help='Файл для сохранения результатов')

    args = parser.parse_args()

    # Обработка аргументов
    if args.info:
        show_system_info()
        sys.exit(0)

    elif args.text:
        # Быстрый перевод текста
        if not Config.OPENROUTER_API_KEY:
            print("ОШИБКА: API ключ не найден")
            sys.exit(1)

        translator = TranslationModule()
        processor = TextProcessor()

        print(f"Перевод текста: {args.text}")
        print(f"Предметная область: {args.domain}")

        result = translator.translate_text(args.text, 'en-ru', args.domain)

        if result.get('success', False):
            print(f"\nПеревод: {result['translated_text']}")

            if args.output:
                # Сохраняем в файл
                import json
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                print(f"Результат сохранен в {args.output}")
        else:
            print(f"\nОшибка: {result.get('error', 'Неизвестная ошибка')}")
            sys.exit(1)

    elif args.cli:
        run_cli()

    else:
        # По умолчанию запускаем GUI
        run_gui()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nПрограмма прервана пользователем")
        sys.exit(0)
    except Exception as e:
        print(f"\nКритическая ошибка: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)