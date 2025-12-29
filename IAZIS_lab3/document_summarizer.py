import re
import math
import string
from collections import Counter
import os
import glob
from typing import List, Dict, Tuple, Set
import json
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords


class DocumentSummarizer:
    def __init__(self, language: str = 'french'):
        """
        Инициализация суммаризатора для конкретного языка

        Args:
            language: 'french' или 'german'
        """
        self.language = language
        self.stop_words = self._load_stop_words()
        self.documents_collection = []  # Коллекция всех документов для расчета IDF

        # Загрузка ресурсов NLTK
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')

        # Загрузка стоп-слов для NLTK
        try:
            if language == 'french':
                nltk.data.find('corpora/stopwords')
            elif language == 'german':
                nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords')

    def _load_stop_words(self) -> Set[str]:
        """Загрузка стоп-слов для соответствующего языка"""
        if self.language == 'french':
            try:
                return set(stopwords.words('french'))
            except:
                # Резервный набор французских стоп-слов
                return {
                    'le', 'la', 'les', 'de', 'des', 'du', 'et', 'est', 'en', 'un', 'une',
                    'dans', 'qui', 'que', 'pour', 'par', 'sur', 'avec', 'il', 'elle',
                    'nous', 'vous', 'ils', 'elles', 'ce', 'cette', 'ces', 'son', 'sa',
                    'ses', 'mon', 'ton', 'notre', 'votre', 'leur', 'mais', 'ou', 'où',
                    'donc', 'car', 'si', 'comme', 'quand', 'que', 'quoi', 'quel'
                }
        else:  # german
            try:
                return set(stopwords.words('german'))
            except:
                # Резервный набор немецких стоп-слов
                return {
                    'der', 'die', 'das', 'und', 'in', 'zu', 'den', 'von', 'mit', 'sich',
                    'des', 'auf', 'für', 'ist', 'im', 'dem', 'nicht', 'ein', 'eine',
                    'als', 'auch', 'es', 'an', 'aus', 'er', 'hat', 'dass', 'sie', 'nach',
                    'wird', 'bei', 'einer', 'um', 'am', 'sind', 'noch', 'wie', 'einem',
                    'über', 'einen', 'so', 'zum', 'war', 'haben', 'nur', 'oder', 'aber',
                    'vor', 'zur', 'bis', 'mehr', 'durch', 'man', 'sein', 'wird', 'seine'
                }

    def preprocess_text(self, text: str) -> List[str]:
        """
        Предобработка текста: токенизация, очистка

        Args:
            text: исходный текст

        Returns:
            Список очищенных слов
        """
        # Удаление метаданных (первых строк с информацией о статье)
        lines = text.split('\n')
        content_start = 0
        for i, line in enumerate(lines):
            if not line.startswith(('Заголовок:', 'URL:', 'Язык:', 'Категория:', 'Дата загрузки:', 'Длина текста:')):
                content_start = i
                break

        text = '\n'.join(lines[content_start:])

        # Удаление специальных символов и цифр
        text = re.sub(r'\d+', '', text)
        text = text.lower()

        # Удаление пунктуации
        if self.language == 'french':
            # Французская пунктуация
            text = re.sub(r'[^\w\sàâäéèêëîïôöùûüçÀÂÄÉÈÊËÎÏÔÖÙÛÜÇ-]', ' ', text)
        else:  # german
            # Немецкая пунктуация
            text = re.sub(r'[^\w\säöüÄÖÜß-]', ' ', text)

        # Токенизация
        words = word_tokenize(text, language=self.language if self.language in ['french', 'german'] else 'english')

        # Удаление стоп-слов и коротких слов
        cleaned_words = []
        for word in words:
            if (word not in self.stop_words and
                    len(word) > 2 and
                    not all(c in string.punctuation for c in word)):
                cleaned_words.append(word)

        return cleaned_words

    def _stem_word(self, word: str) -> str:
        """Упрощенная стеммизация слова"""
        # Простая реализация - оставляем как есть
        # В продакшене можно использовать SnowballStemmer из NLTK
        return word

    def calculate_tf_idf(self, documents: List[List[str]]) -> Dict[str, float]:
        """
        Расчет TF-IDF для терминов в коллекции документов

        Args:
            documents: список документов, каждый документ - список слов

        Returns:
            Словарь {термин: вес IDF}
        """
        # Количество документов
        N = len(documents)

        # Подсчет document frequency (df)
        df_counter = Counter()
        for doc in documents:
            unique_words = set(doc)
            for word in unique_words:
                df_counter[word] += 1

        # Расчет IDF
        idf_scores = {}
        for word, df in df_counter.items():
            # Избегаем деления на ноль
            if df > 0:
                idf_scores[word] = math.log(N / df)
            else:
                idf_scores[word] = 0

        return idf_scores

    def calculate_sentence_scores(self, text: str, idf_scores: Dict[str, float]) -> List[Tuple[int, float, str]]:
        """
        Расчет весов для каждого предложения в документе

        Args:
            text: исходный текст
            idf_scores: словарь с IDF весами

        Returns:
            Список кортежей (индекс, вес, текст предложения)
        """
        # Удаление метаданных для разделения на предложения
        lines = text.split('\n')
        content_text = '\n'.join([line for line in lines if not line.startswith(
            ('Заголовок:', 'URL:', 'Язык:', 'Категория:', 'Дата загрузки:', 'Длина текста:'))])

        # Разделение на предложения с помощью NLTK
        sentences = sent_tokenize(content_text,
                                  language=self.language if self.language in ['french', 'german'] else 'english')

        # Общая длина документа в символах
        total_chars = len(content_text)

        # Расчет весов для каждого предложения
        sentence_scores = []

        for idx, sentence in enumerate(sentences):
            # Позиция предложения в документе
            sentence_start = content_text.find(sentence)
            pos_d = 1 - (sentence_start / total_chars) if total_chars > 0 else 0

            # Позиция предложения в абзаце (упрощенно)
            # Находим начало абзаца
            paragraph_start = content_text.rfind('\n\n', 0, sentence_start)
            if paragraph_start == -1:
                paragraph_start = 0
            paragraph_end = content_text.find('\n\n', sentence_start)
            if paragraph_end == -1:
                paragraph_end = len(content_text)

            paragraph = content_text[paragraph_start:paragraph_end]
            sentence_in_paragraph = sentence_start - paragraph_start
            paragraph_chars = len(paragraph)

            pos_p = 1 - (sentence_in_paragraph / paragraph_chars) if paragraph_chars > 0 else pos_d

            # TF в предложении
            words_in_sentence = self.preprocess_text(sentence)
            word_freq = Counter(words_in_sentence)

            # Расчет TF-IDF для слов в документе (для формулы w(t, D))
            all_words = self.preprocess_text(content_text)
            tf_doc = Counter(all_words)
            max_tf_doc = max(tf_doc.values()) if tf_doc else 1

            # Расчет Score(Si)
            score = 0
            for word, freq in word_freq.items():
                # w(t, D) по формуле из задания
                if word in tf_doc and word in idf_scores:
                    tf_t_d = tf_doc[word]
                    w_t_d = 0.5 * (1 + (tf_t_d / max_tf_doc)) * idf_scores[word]
                    score += freq * w_t_d

            # Учет позиционных функций
            score *= pos_d * pos_p

            sentence_scores.append((idx, score, sentence.strip()))

        return sentence_scores

    def generate_classic_summary(self, text: str, num_sentences: int = 10) -> str:
        """
        Генерация классического реферата

        Args:
            text: исходный текст
            num_sentences: количество предложений в реферате

        Returns:
            Текст реферата
        """
        # Обновляем коллекцию документов
        words = self.preprocess_text(text)
        self.documents_collection.append(words)

        # Расчет IDF по всей коллекции
        idf_scores = self.calculate_tf_idf(self.documents_collection)

        # Расчет весов предложений
        sentence_scores = self.calculate_sentence_scores(text, idf_scores)

        # Если недостаточно предложений
        if len(sentence_scores) < num_sentences:
            num_sentences = len(sentence_scores)

        # Сортировка по весу и выбор топ-N предложений
        sentence_scores.sort(key=lambda x: x[1], reverse=True)
        top_sentences = sentence_scores[:num_sentences]

        # Сортировка по порядку в тексте
        top_sentences.sort(key=lambda x: x[0])

        # Формирование реферата
        summary = ' '.join([sentence for _, _, sentence in top_sentences])

        return summary

    def extract_keywords(self, text: str, num_keywords: int = 20) -> List[str]:
        """
        Извлечение ключевых слов

        Args:
            text: исходный текст
            num_keywords: количество ключевых слов

        Returns:
            Список ключевых слов
        """
        # Удаление метаданных для обработки
        lines = text.split('\n')
        content_text = '\n'.join([line for line in lines if not line.startswith(
            ('Заголовок:', 'URL:', 'Язык:', 'Категория:', 'Дата загрузки:', 'Длина текста:'))])

        # Обновляем коллекцию документов
        words = self.preprocess_text(content_text)
        self.documents_collection.append(words)

        # Расчет IDF
        idf_scores = self.calculate_tf_idf(self.documents_collection)

        # Расчет TF для документа
        tf_doc = Counter(words)
        max_tf_doc = max(tf_doc.values()) if tf_doc else 1

        # Расчет w(t, D) для каждого слова
        word_scores = {}
        for word, tf in tf_doc.items():
            if word in idf_scores:
                w_t_d = 0.5 * (1 + (tf / max_tf_doc)) * idf_scores[word]
                word_scores[word] = w_t_d

        # Сортировка по весу и выбор топ-N ключевых слов
        sorted_words = sorted(word_scores.items(), key=lambda x: x[1], reverse=True)
        keywords = [word for word, _ in sorted_words[:num_keywords]]

        return keywords

    def process_document(self, file_path: str) -> Dict:
        """
        Обработка одного документа

        Args:
            file_path: путь к файлу

        Returns:
            Словарь с результатами
        """
        # Чтение файла
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()

        # Определение языка по пути файла
        if 'french' in file_path:
            self.language = 'french'
        elif 'german' in file_path:
            self.language = 'german'
        # Если не определен по пути, проверяем по расширению
        elif '_fr.' in file_path or file_path.endswith('_fr.txt'):
            self.language = 'french'
        elif '_de.' in file_path or file_path.endswith('_de.txt'):
            self.language = 'german'

        # Обновление стоп-слов для нового языка
        self.stop_words = self._load_stop_words()

        # Генерация реферата
        summary = self.generate_classic_summary(text)

        # Извлечение ключевых слов
        keywords = self.extract_keywords(text)

        # Формирование иерархии ключевых слов
        hierarchical_keywords = self._create_hierarchical_keywords(keywords)

        # Извлечение метаданных из текста
        metadata = self._extract_metadata(text)

        return {
            'original_file': file_path,
            'language': self.language,
            'classic_summary': summary,
            'keywords': keywords,
            'hierarchical_keywords': hierarchical_keywords,
            'metadata': metadata
        }

    def _create_hierarchical_keywords(self, keywords: List[str]) -> Dict:
        """
        Создание иерархической структуры ключевых слов

        Args:
            keywords: список ключевых слов

        Returns:
            Иерархическая структура
        """
        # Группировка по тематическим категориям (упрощенно)
        categories = {
            'Технические термины': [],
            'Общие понятия': [],
            'Специфические термины': []
        }

        for keyword in keywords:
            # Определяем категорию на основе слова
            if any(tech in keyword for tech in ['programm', 'algorithm', 'data', 'code', 'system', 'network']):
                categories['Технические термины'].append(keyword)
            elif len(keyword) <= 5 or keyword in ['science', 'technology', 'information', 'computer']:
                categories['Общие понятия'].append(keyword)
            else:
                categories['Специфические термины'].append(keyword)

        # Удаляем пустые категории
        return {k: v for k, v in categories.items() if v}

    def _extract_metadata(self, text: str) -> Dict:
        """Извлечение метаданных из текста документа"""
        metadata = {}
        lines = text.split('\n')

        for line in lines:
            if line.startswith('Заголовок:'):
                metadata['title'] = line.replace('Заголовок:', '').strip()
            elif line.startswith('URL:'):
                metadata['url'] = line.replace('URL:', '').strip()
            elif line.startswith('Язык:'):
                metadata['language'] = line.replace('Язык:', '').strip()
            elif line.startswith('Категория:'):
                metadata['category'] = line.replace('Категория:', '').strip()
            elif line.startswith('Дата загрузки:'):
                metadata['download_date'] = line.replace('Дата загрузки:', '').strip()
            elif line.startswith('Длина текста:'):
                metadata['text_length'] = line.replace('Длина текста:', '').strip()

        return metadata


class SummarizationSystem:
    """Основной класс системы суммаризации для новой структуры проекта"""

    def __init__(self, config_path: str = 'config.json'):
        self.processor_fr = DocumentSummarizer('french')
        self.processor_de = DocumentSummarizer('german')
        self.results = []

        # Загрузка конфигурации
        self.config = self._load_config(config_path)

        # Создание выходных директорий
        self._create_output_dirs()

    def _load_config(self, config_path: str) -> Dict:
        """Загрузка конфигурационного файла"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # Конфигурация по умолчанию
            return {
                'directories': {
                    'input': 'wikipedia_articles',
                    'output': 'summarization_results',
                    'reports': 'reports'
                }
            }

    def _create_output_dirs(self):
        """Создание выходных директорий"""
        output_dirs = [
            self.config['directories']['output'],
            self.config['directories']['reports'],
            os.path.join(self.config['directories']['output'], 'french', 'computer_science'),
            os.path.join(self.config['directories']['output'], 'french', 'literature'),
            os.path.join(self.config['directories']['output'], 'german', 'computer_science'),
            os.path.join(self.config['directories']['output'], 'german', 'literature')
        ]

        for directory in output_dirs:
            os.makedirs(directory, exist_ok=True)

    def process_all_documents(self):
        """
        Обработка всех документов из входной директории
        согласно новой структуре проекта
        """
        input_dir = self.config['directories']['input']

        if not os.path.exists(input_dir):
            print(f"Входная директория не найдена: {input_dir}")
            return

        print(f"Обработка документов из: {input_dir}")

        # Структура директорий для обхода
        language_dirs = ['french', 'german']
        category_dirs = ['computer_science', 'literature']

        total_files = 0

        for language in language_dirs:
            for category in category_dirs:
                source_dir = os.path.join(input_dir, language, category)

                if not os.path.exists(source_dir):
                    print(f"Директория не найдена: {source_dir}")
                    continue

                # Поиск всех текстовых файлов
                txt_files = glob.glob(os.path.join(source_dir, '*.txt'))

                print(f"\nОбработка {language}/{category}: найдено {len(txt_files)} файлов")

                for file_path in txt_files:
                    print(f"  • {os.path.basename(file_path)}...", end="")

                    # Выбор процессора по языку
                    if language == 'french':
                        processor = self.processor_fr
                    else:
                        processor = self.processor_de

                    # Обработка документа
                    try:
                        result = processor.process_document(file_path)
                        self.results.append(result)

                        # Сохранение результатов
                        self._save_single_result(result)

                        print(" ✓")
                        total_files += 1
                    except Exception as e:
                        print(f" ✗ (Ошибка: {str(e)})")

        print(f"\nВсего обработано документов: {total_files}")

        # Генерация отчета
        self._generate_comprehensive_report()

    def _save_single_result(self, result: Dict):
        """Сохранение результатов для одного документа"""
        # Определение пути для сохранения
        file_path = result['original_file']
        filename = os.path.basename(file_path)

        # Определение категории по исходному пути
        if 'computer_science' in file_path:
            category = 'computer_science'
        elif 'literature' in file_path:
            category = 'literature'
        else:
            category = 'other'

        # Создание пути для сохранения
        output_dir = os.path.join(
            self.config['directories']['output'],
            result['language'],
            category
        )

        os.makedirs(output_dir, exist_ok=True)

        output_path = os.path.join(output_dir, f"summary_{filename}")

        # Формирование содержимого
        content = self._format_result_content(result)

        # Запись в файл
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def _format_result_content(self, result: Dict) -> str:
        """Форматирование результата для сохранения в файл"""
        content = f"""
{'=' * 60}
АВТОМАТИЧЕСКОЕ РЕФЕРИРОВАНИЕ ДОКУМЕНТА
{'=' * 60}

МЕТАДАННЫЕ:
-----------
Файл: {result['original_file']}
Язык: {result['language']}
Заголовок: {result['metadata'].get('title', 'Не указан')}
URL: {result['metadata'].get('url', 'Не указан')}
Категория: {result['metadata'].get('category', 'Не указана')}
Дата загрузки: {result['metadata'].get('download_date', 'Не указана')}
Длина текста: {result['metadata'].get('text_length', 'Не указана')}

{'=' * 60}
КЛАССИЧЕСКИЙ РЕФЕРАТ (10 предложений)
{'=' * 60}
{result['classic_summary']}

{'=' * 60}
КЛЮЧЕВЫЕ СЛОВА (20 терминов)
{'=' * 60}
{', '.join(result['keywords'])}

{'=' * 60}
ИЕРАРХИЧЕСКИЙ СПИСОК КЛЮЧЕВЫХ СЛОВ
{'=' * 60}
"""

        for category, words in result['hierarchical_keywords'].items():
            content += f"\n{category}:\n"
            for word in words:
                content += f"  • {word}\n"

        content += f"\n{'=' * 60}\n"
        content += f"Дата создания реферата: {self._get_current_timestamp()}\n"
        content += f"{'=' * 60}"

        return content

    def _get_current_timestamp(self) -> str:
        """Получение текущей даты и времени"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def _generate_comprehensive_report(self):
        """Генерация комплексного отчета"""
        report_path = os.path.join(self.config['directories']['reports'], 'comprehensive_report.txt')

        report = self._create_report_content()

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"\nКомплексный отчет сохранен в: {report_path}")

    def _create_report_content(self) -> str:
        """Создание содержания отчета"""
        report = f"""
ОТЧЕТ ПО ЛАБОРАТОРНОЙ РАБОТЕ №9
«АВТОМАТИЧЕСКОЕ РЕФЕРИРОВАНИЕ ДОКУМЕНТОВ»
Вариант 2
Дата создания: {self._get_current_timestamp()}

{'=' * 80}
1. ОБЩАЯ ИНФОРМАЦИЯ
{'=' * 80}
Всего обработано документов: {len(self.results)}

Распределение по языкам:
• Французский: {len([r for r in self.results if r['language'] == 'french'])}
• Немецкий: {len([r for r in self.results if r['language'] == 'german'])}

Распределение по категориям:
• Computer Science: {len([r for r in self.results if 'computer_science' in r['original_file']])}
• Литература: {len([r for r in self.results if 'literature' in r['original_file']])}

{'=' * 80}
2. СТАТИСТИКА РЕЗУЛЬТАТОВ
{'=' * 80}
"""

        # Статистика по рефератам
        avg_summary_length = sum(len(r['classic_summary'].split()) for r in self.results) / len(
            self.results) if self.results else 0
        avg_keywords = sum(len(r['keywords']) for r in self.results) / len(self.results) if self.results else 0

        report += f"""
Средняя длина реферата: {avg_summary_length:.1f} слов
Среднее количество ключевых слов: {avg_keywords:.1f}
Минимальная длина реферата: {min(len(r['classic_summary'].split()) for r in self.results) if self.results else 0} слов
Максимальная длина реферата: {max(len(r['classic_summary'].split()) for r in self.results) if self.results else 0} слов

{'=' * 80}
3. ПРИМЕРЫ РЕЗУЛЬТАТОВ
{'=' * 80}
"""

        # Примеры для каждого языка и категории
        examples_added = 0
        for result in self.results[:5]:  # Первые 5 результатов
            report += f"""
Файл: {os.path.basename(result['original_file'])}
Язык: {result['language']}
Категория: {'computer_science' if 'computer_science' in result['original_file'] else 'literature'}

Первые 3 ключевых слова: {', '.join(result['keywords'][:3])}
Длина реферата: {len(result['classic_summary'].split())} слов

"""
            examples_added += 1

        report += f"""
{'=' * 80}
4. ВЫВОДЫ И РЕКОМЕНДАЦИИ
{'=' * 80}
Система успешно обработала {len(self.results)} документов из Wikipedia.
Результаты сохранены в директории: {self.config['directories']['output']}

Рекомендации по улучшению:
1. Добавить более сложные алгоритмы стемминга
2. Внедрить нейросетевые модели для улучшения качества
3. Добавить оценку качества рефератов с помощью метрик ROUGE
4. Расширить поддержку языков

{'=' * 80}
5. СТРУКТУРА ПРОЕКТА
{'=' * 80}
Входные данные: {self.config['directories']['input']}/
  ├── french/
  │   ├── computer_science/
  │   └── literature/
  └── german/
      ├── computer_science/
      └── literature/

Выходные данные: {self.config['directories']['output']}/
  (та же структура, что и для входных данных)

Отчеты: {self.config['directories']['reports']}/
  ├── comprehensive_report.txt (этот файл)
  └── дополнительные отчеты при необходимости
"""

        return report


def main():
    """Основная функция для запуска системы"""
    print("=" * 70)
    print("СИСТЕМА АВТОМАТИЧЕСКОГО РЕФЕРИРОВАНИЯ ДОКУМЕНТОВ")
    print("Вариант 2: Французский и Немецкий языки")
    print("Новая структура проекта")
    print("=" * 70)

    # Инициализация системы
    print("\n1. Инициализация системы...")
    system = SummarizationSystem()

    # Обработка документов
    print("\n2. Обработка документов...")
    system.process_all_documents()

    print("\n" + "=" * 70)
    print("ОБРАБОТКА ЗАВЕРШЕНА!")
    print(f"Результаты сохранены в: {system.config['directories']['output']}")
    print(f"Отчеты сохранены в: {system.config['directories']['reports']}")
    print("=" * 70)


if __name__ == "__main__":
    # Проверка и установка зависимостей NLTK
    try:
        import nltk

        nltk.data.find('tokenizers/punkt')
    except:
        print("Установка необходимых ресурсов NLTK...")
        nltk.download('punkt')
        nltk.download('stopwords')

    main()