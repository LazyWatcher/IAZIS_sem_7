import wikipediaapi
import os
import time
from typing import List, Dict, Tuple
import re
import json
from datetime import datetime


class WikipediaDownloader:
    """Класс для загрузки статей из Wikipedia"""

    def __init__(self, user_agent: str = "DocumentSummarizationBot/1.0"):
        """
        Инициализация загрузчика

        Args:
            user_agent: User-Agent для запросов к Wikipedia
        """
        self.user_agent = user_agent
        self.wiki_fr = wikipediaapi.Wikipedia(
            language='fr',
            user_agent=user_agent,
            extract_format=wikipediaapi.ExtractFormat.WIKI
        )
        self.wiki_de = wikipediaapi.Wikipedia(
            language='de',
            user_agent=user_agent,
            extract_format=wikipediaapi.ExtractFormat.WIKI
        )

        # Создание структуры директорий
        self.base_dir = "wikipedia_articles"
        self.fr_cs_dir = os.path.join(self.base_dir, "french", "computer_science")
        self.fr_lit_dir = os.path.join(self.base_dir, "french", "literature")
        self.de_cs_dir = os.path.join(self.base_dir, "german", "computer_science")
        self.de_lit_dir = os.path.join(self.base_dir, "german", "literature")

        for directory in [self.fr_cs_dir, self.fr_lit_dir, self.de_cs_dir, self.de_lit_dir]:
            os.makedirs(directory, exist_ok=True)

    def clean_text(self, text: str) -> str:
        """
        Очистка текста от разметки Wikipedia

        Args:
            text: исходный текст с разметкой

        Returns:
            Очищенный текст
        """
        # Удаление ссылок [[текст|отображение]] или [[текст]]
        text = re.sub(r'\[\[[^\]]+\|([^\]]+)\]\]', r'\1', text)
        text = re.sub(r'\[\[([^\]]+)\]\]', r'\1', text)

        # Удаление внешних ссылок [http://...]
        text = re.sub(r'\[http[^\]]+\]', '', text)

        # Удаление шаблонов {{...}}
        text = re.sub(r'\{\{[^}]+\}\}', '', text)

        # Удаление HTML тегов
        text = re.sub(r'<[^>]+>', '', text)

        # Удаление лишних пробелов
        text = re.sub(r'\s+', ' ', text)

        # Удаление сносок [1], [2]...
        text = re.sub(r'\[\d+\]', '', text)

        return text.strip()

    def download_article(self, wiki: wikipediaapi.Wikipedia, title: str,
                         category: str = "computer_science") -> Tuple[bool, str]:
        """
        Загрузка одной статьи

        Args:
            wiki: объект Wikipedia для нужного языка
            title: название статьи
            category: категория статьи

        Returns:
            Кортеж (успех, текст статьи)
        """
        try:
            page = wiki.page(title)

            if not page.exists():
                print(f"Статья '{title}' не найдена")
                return False, ""

            # Получение полного текста статьи
            text = page.text

            if not text or len(text) < 500:  # Слишком короткая статья
                print(f"Статья '{title}' слишком короткая ({len(text)} символов)")
                return False, ""

            # Очистка текста
            cleaned_text = self.clean_text(text)

            # Добавление метаданных
            metadata = f"""Заголовок: {title}
URL: {page.fullurl}
Язык: {wiki.language}
Категория: {category}
Дата загрузки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Длина текста: {len(cleaned_text)} символов

"""

            return True, metadata + cleaned_text

        except Exception as e:
            print(f"Ошибка при загрузке статьи '{title}': {e}")
            return False, ""

    def download_computer_science_articles(self):
        """Загрузка статей по computer science"""
        print("\n" + "=" * 60)
        print("ЗАГРУЗКА СТАТЕЙ ПО COMPUTER SCIENCE")
        print("=" * 60)

        # Статьи по computer science на французском
        fr_cs_titles = [
            "Informatique",  # Computer science
            "Algorithmique",  # Algorithms
            "Programmation informatique",  # Programming
            "Intelligence artificielle",  # Artificial intelligence
            "Base de données",  # Database
            "Réseau informatique",  # Computer network
            "Sécurité informatique",  # Computer security
            "Système d'exploitation",  # Operating system
            "Langage de programmation",  # Programming language
            "Machine learning",  # Machine learning
        ]

        # Статьи по computer science на немецком
        de_cs_titles = [
            "Informatik",  # Computer science
            "Algorithmus",  # Algorithm
            "Programmiersprache",  # Programming language
            "Künstliche Intelligenz",  # Artificial intelligence
            "Datenbank",  # Database
            "Computernetzwerk",  # Computer network
            "IT-Sicherheit",  # IT security
            "Betriebssystem",  # Operating system
            "Softwareentwicklung",  # Software development
            "Maschinelles Lernen",  # Machine learning
        ]

        # Загрузка французских статей
        print("\nЗагрузка французских статей по computer science:")
        for title in fr_cs_titles:
            print(f"  • {title}...", end="")
            success, text = self.download_article(self.wiki_fr, title, "computer_science")
            if success:
                # Сохранение в файл
                filename = f"{title.lower().replace(' ', '_')}_fr.txt"
                filepath = os.path.join(self.fr_cs_dir, filename)

                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(text)

                print(f" ✓ ({len(text)} символов)")
            else:
                print(" ✗")

            # Пауза между запросами
            time.sleep(0.5)

        # Загрузка немецких статей
        print("\nЗагрузка немецких статей по computer science:")
        for title in de_cs_titles:
            print(f"  • {title}...", end="")
            success, text = self.download_article(self.wiki_de, title, "computer_science")
            if success:
                # Сохранение в файл
                filename = f"{title.lower().replace(' ', '_')}_de.txt"
                filepath = os.path.join(self.de_cs_dir, filename)

                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(text)

                print(f" ✓ ({len(text)} символов)")
            else:
                print(" ✗")

            # Пауза между запросами
            time.sleep(0.5)

    def download_literature_articles(self):
        """Загрузка статей по литературе"""
        print("\n" + "=" * 60)
        print("ЗАГРУЗКА СТАТЕЙ ПО ЛИТЕРАТУРЕ")
        print("=" * 60)

        # Статьи по литературе на французском
        fr_lit_titles = [
            "Littérature française",  # French literature
            "Victor Hugo",
            "Molière",
            "Gustave Flaubert",
            "Marcel Proust",
            "Honoré de Balzac",
            "Charles Baudelaire",
            "Albert Camus",
            "Jean-Paul Sartre",
            "Simone de Beauvoir",
        ]

        # Статьи по литературе на немецком
        de_lit_titles = [
            "Deutsche Literatur",  # German literature
            "Johann Wolfgang von Goethe",
            "Friedrich Schiller",
            "Thomas Mann",
            "Franz Kafka",
            "Hermann Hesse",
            "Bertolt Brecht",
            "Heinrich Heine",
            "Günter Grass",
            "Friedrich Dürrenmatt",
        ]

        # Загрузка французских статей
        print("\nЗагрузка французских статей по литературе:")
        for title in fr_lit_titles:
            print(f"  • {title}...", end="")
            success, text = self.download_article(self.wiki_fr, title, "literature")
            if success:
                # Сохранение в файл
                filename = f"{title.lower().replace(' ', '_')}_fr.txt"
                filepath = os.path.join(self.fr_lit_dir, filename)

                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(text)

                print(f" ✓ ({len(text)} символов)")
            else:
                print(" ✗")

            # Пауза между запросами
            time.sleep(0.5)

        # Загрузка немецких статей
        print("\nЗагрузка немецких статей по литературе:")
        for title in de_lit_titles:
            print(f"  • {title}...", end="")
            success, text = self.download_article(self.wiki_de, title, "literature")
            if success:
                # Сохранение в файл
                filename = f"{title.lower().replace(' ', '_')}_de.txt"
                filepath = os.path.join(self.de_lit_dir, filename)

                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(text)

                print(f" ✓ ({len(text)} символов)")
            else:
                print(" ✗")

            # Пауза между запросами
            time.sleep(0.5)

    def download_all_articles(self):
        """Загрузка всех статей"""
        print("НАЧАЛО ЗАГРУЗКИ СТАТЕЙ ИЗ WIKIPEDIA")
        print(f"Дата и время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Директория сохранения: {os.path.abspath(self.base_dir)}")

        # Загрузка статей
        self.download_computer_science_articles()
        self.download_literature_articles()

        # Создание отчета
        self.create_download_report()

        print("\n" + "=" * 60)
        print("ЗАГРУЗКА ЗАВЕРШЕНА!")
        print("=" * 60)

    def create_download_report(self):
        """Создание отчета о загруженных статьях"""
        report = {
            "download_date": datetime.now().isoformat(),
            "base_directory": os.path.abspath(self.base_dir),
            "articles": {
                "french": {
                    "computer_science": [],
                    "literature": []
                },
                "german": {
                    "computer_science": [],
                    "literature": []
                }
            }
        }

        # Сбор информации о загруженных файлах
        for lang_dir, lang_name in [(self.fr_cs_dir, "french_computer_science"),
                                    (self.fr_lit_dir, "french_literature"),
                                    (self.de_cs_dir, "german_computer_science"),
                                    (self.de_lit_dir, "german_literature")]:

            for filename in os.listdir(lang_dir):
                if filename.endswith('.txt'):
                    filepath = os.path.join(lang_dir, filename)
                    file_size = os.path.getsize(filepath)

                    # Определение категории
                    if "french" in lang_name:
                        if "computer_science" in lang_name:
                            category = report["articles"]["french"]["computer_science"]
                        else:
                            category = report["articles"]["french"]["literature"]
                    else:
                        if "computer_science" in lang_name:
                            category = report["articles"]["german"]["computer_science"]
                        else:
                            category = report["articles"]["german"]["literature"]

                    category.append({
                        "filename": filename,
                        "path": filepath,
                        "size_bytes": file_size,
                        "size_kb": round(file_size / 1024, 2)
                    })

        # Сохранение отчета в JSON
        report_path = os.path.join(self.base_dir, "download_report.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # Создание текстового отчета
        txt_report = f"""ОТЧЕТ О ЗАГРУЗКЕ СТАТЕЙ ИЗ WIKIPEDIA
==========================================

Дата загрузки: {report['download_date']}
Директория: {report['base_directory']}

СТАТИСТИКА:
-----------
Французские статьи по computer science: {len(report['articles']['french']['computer_science'])}
Французские статьи по литературе: {len(report['articles']['french']['literature'])}
Немецкие статьи по computer science: {len(report['articles']['german']['computer_science'])}
Немецкие статьи по литературе: {len(report['articles']['german']['literature'])}

ВСЕГО СТАТЕЙ: {len(report['articles']['french']['computer_science']) +
               len(report['articles']['french']['literature']) +
               len(report['articles']['german']['computer_science']) +
               len(report['articles']['german']['literature'])}

ДЕТАЛЬНЫЙ СПИСОК:
-----------------
"""

        for lang in ["french", "german"]:
            for category in ["computer_science", "literature"]:
                if report["articles"][lang][category]:
                    txt_report += f"\n{lang.upper()} - {category.upper().replace('_', ' ')}:\n"
                    for article in report["articles"][lang][category]:
                        txt_report += f"  • {article['filename']} ({article['size_kb']} KB)\n"

        txt_report_path = os.path.join(self.base_dir, "download_report.txt")
        with open(txt_report_path, 'w', encoding='utf-8') as f:
            f.write(txt_report)

        print(f"\nОтчет сохранен в:")
        print(f"  • {report_path}")
        print(f"  • {txt_report_path}")


class ConfigGenerator:
    """Класс для генерации конфигурационных файлов"""

    @staticmethod
    def generate_summarization_config():
        """Генерация конфигурационного файла для системы суммаризации"""
        config = {
            "system": {
                "name": "Automatic Document Summarization System",
                "version": "1.0",
                "author": "BSUIR Student",
                "lab_number": 9,
                "variant": 2
            },
            "languages": {
                "primary": ["french", "german"],
                "stopwords": {
                    "french": ["stopwords_fr.txt"],
                    "german": ["stopwords_de.txt"]
                }
            },
            "directories": {
                "input": "wikipedia_articles",
                "output": "summarization_results",
                "reports": "reports"
            },
            "summarization": {
                "algorithm": "sentence_extraction",
                "max_sentences": 10,
                "min_sentence_length": 5,
                "use_tfidf": True,
                "use_position_scoring": True,
                "keywords_count": 20
            },
            "wikipedia": {
                "user_agent": "DocumentSummarizationBot/1.0",
                "rate_limit_delay": 0.5,
                "min_article_length": 500
            },
            "categories": {
                "computer_science": [
                    "Informatique", "Algorithmique", "Programmation",
                    "Intelligence Artificielle", "Base de Données"
                ],
                "literature": [
                    "Littérature Française", "Victor Hugo", "Molière",
                    "Deutsche Literatur", "Goethe", "Schiller"
                ]
            }
        }

        # Создание директорий
        for dir_name in ["summarization_results", "reports"]:
            os.makedirs(dir_name, exist_ok=True)

        # Сохранение конфигурации
        config_path = "config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        print(f"Конфигурационный файл создан: {config_path}")
        return config_path


def check_dependencies():
    """Проверка и установка зависимостей"""
    import subprocess
    import sys

    required_packages = ['wikipedia-api']

    print("Проверка зависимостей...")

    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package} не установлен. Установка...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"  ✓ {package} установлен")


def main():
    """Основная функция"""
    print("=" * 70)
    print("СКРИПТ ЗАГРУЗКИ СТАТЕЙ ИЗ WIKIPEDIA")
    print("ДЛЯ ЛАБОРАТОРНОЙ РАБОТЫ №9 (Вариант 2)")
    print("БЕЛОРУССКИЙ ГОСУДАРСТВЕННЫЙ УНИВЕРСИТЕТ ИНФОРМАТИКИ И РАДИОЭЛЕКТРОНИКИ")
    print("=" * 70)

    # Проверка зависимостей
    check_dependencies()

    # Генерация конфигурации
    print("\n1. Генерация конфигурационных файлов...")
    config_gen = ConfigGenerator()
    config_gen.generate_summarization_config()

    # Инициализация загрузчика
    print("\n2. Инициализация загрузчика Wikipedia...")
    downloader = WikipediaDownloader(
        user_agent="BSUIR-Lab9-DocumentSummarization/1.0 (https://github.com/bsuir-student)"
    )

    # Загрузка статей
    print("\n3. Загрузка статей из Wikipedia...")
    downloader.download_all_articles()

    # Создание инструкции
    print("\n4. Создание инструкции по использованию...")
    create_usage_instructions()


def create_usage_instructions():
    """Создание файла с инструкциями"""
    instructions = """ИНСТРУКЦИЯ ПО ИСПОЛЬЗОВАНИЮ
=======================

ИСПОЛЬЗОВАНИЕ:
--------------
1. Запустите скрипт: python download_wikipedia.py
2. Скрипт автоматически:
   - Проверит зависимости
   - Создаст конфигурационный файл
   - Загрузит статьи из Wikipedia
   - Создаст отчет о загрузке

ПАРАМЕТРЫ СТАТЕЙ:
-----------------
Каждая статья содержит:
- Заголовок
- URL исходной статьи
- Язык
- Категория
- Дата загрузки
- Длину текста
- Очищенный текст статьи

ИСПОЛЬЗОВАНИЕ ДЛЯ ЛАБОРАТОРНОЙ РАБОТЫ:
--------------------------------------
1. Загруженные статьи можно использовать в системе автоматического реферирования
2. Для каждого языка и категории доступно по 10 статей
3. Всего загружается 40 статей

ПРИМЕЧАНИЯ:
-----------
- Скрипт делает паузы между запросами к Wikipedia (0.5 сек)
- Минимальная длина статьи: 500 символов
- Если статья не найдена, она пропускается
- Все тексты очищаются от разметки Wikipedia

АВТОР:
------
Скрипт разработан для лабораторной работы №9 БГУИР
Вариант 2: Французский и немецкий языки
"""

    with open("INSTRUCTIONS.txt", 'w', encoding='utf-8') as f:
        f.write(instructions)

    print("Файл с инструкциями создан: INSTRUCTIONS.txt")


if __name__ == "__main__":
    main()