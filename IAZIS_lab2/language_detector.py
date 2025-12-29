import re
import os
import math
import time
import json
import numpy as np
from collections import Counter
from bs4 import BeautifulSoup
import warnings

warnings.filterwarnings('ignore')


# ============================================
# ОБНОВЛЕННЫЙ КЛАСС ДЛЯ ОБРАБОТКИ ФАЙЛОВ
# ============================================

class FileProcessor:
    """Класс для обработки файлов разных форматов"""

    @staticmethod
    def read_html(file_path):
        """Чтение текста из HTML файла с Wikipedia"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')

                # Удаляем ненужные элементы Wikipedia
                for element in soup.find_all(['script', 'style', 'nav', 'footer',
                                              'aside', '.mw-editsection', '.reference',
                                              '.noprint', '.mw-jump-link']):
                    element.decompose()

                # Получаем основной контент статьи
                content_div = soup.find('div', {'id': 'mw-content-text'})
                if not content_div:
                    content_div = soup.find('div', {'class': 'mw-parser-output'})

                if content_div:
                    # Удаляем ссылки, но сохраняем их текст
                    for a in content_div.find_all('a'):
                        a.replace_with(a.get_text())

                    # Удаляем таблицы
                    for table in content_div.find_all('table'):
                        table.decompose()

                    # Получаем чистый текст
                    text = content_div.get_text(separator='\n', strip=True)
                    # Очищаем лишние пробелы и пустые строки
                    text = re.sub(r'\n\s*\n', '\n\n', text)
                    text = re.sub(r'\[\d+\]', '', text)  # Удаляем ссылки на источники [1], [2]

                    # Ограничиваем объем для обучения (чтобы не было слишком больших файлов)
                    if len(text) > 50000:  # ~50 КБ
                        text = text[:50000]

                    return text
                return soup.get_text()

        except Exception as e:
            print(f"Ошибка при чтении HTML файла {file_path}: {e}")
            return ""

    @staticmethod
    def read_pdf(file_path):
        """Чтение текста из PDF файла"""
        try:
            import PyPDF2
            text = ""
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    text += page.extract_text()
            return text
        except ImportError:
            print("PyPDF2 не установлен. Установите: pip install PyPDF2")
            return ""
        except Exception as e:
            print(f"Ошибка при чтении PDF файла {file_path}: {e}")
            return ""

    @staticmethod
    def read_text_file(file_path):
        """Чтение текстового файла"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Ошибка при чтении файла {file_path}: {e}")
            return ""

    @staticmethod
    def read_any_file(file_path):
        """Чтение любого файла по расширению"""
        if file_path.endswith('.html') or file_path.endswith('.htm'):
            return FileProcessor.read_html(file_path)
        elif file_path.endswith('.pdf'):
            return FileProcessor.read_pdf(file_path)
        else:
            return FileProcessor.read_text_file(file_path)


# ============================================
# КЛАСС ДЛЯ N-ГРАММНОГО МЕТОДА (ИСПРАВЛЕННЫЙ)
# ============================================

class NGramDetector:
    """Класс для распознавания языка методом N-грамм"""

    def __init__(self, n=5, top_k=300):
        self.n = n
        self.top_k = top_k
        self.language_profiles = {}

    def build_profile(self, text, language_name):
        """Построение профиля языка"""
        cleaned_text = TextProcessor.clean_text(text)
        ngrams = TextProcessor.extract_ngrams(cleaned_text, self.n)

        if len(ngrams) < 100:  # Минимальное количество N-грамм
            print(f"Внимание: мало N-грамм ({len(ngrams)}) для языка {language_name}")
            self.language_profiles[language_name] = {}
            return {}

        top_ngrams = TextProcessor.get_top_ngrams(ngrams, self.top_k)

        # Создаем профиль: N-грамма → позиция (от 0 до top_k-1)
        profile = {}
        for i, (ngram, _) in enumerate(top_ngrams):
            profile[ngram] = i

        self.language_profiles[language_name] = profile
        return profile

    def calculate_distance(self, doc_profile, lang_profile):
        """Вычисление расстояния между профилями (Out-Of-Place метрика)"""
        if not doc_profile or not lang_profile:
            return float('inf')

        distance = 0
        max_distance = self.top_k * 2  # Увеличиваем максимальное расстояние

        # Для каждой N-граммы в профиле документа
        for doc_ngram, doc_pos in doc_profile.items():
            if doc_ngram in lang_profile:
                lang_pos = lang_profile[doc_ngram]
                distance += abs(doc_pos - lang_pos)
            else:
                # N-грамма отсутствует в профиле языка
                distance += max_distance

        return distance

    def detect_language(self, text):
        """Определение языка текста"""
        cleaned_text = TextProcessor.clean_text(text)
        ngrams = TextProcessor.extract_ngrams(cleaned_text, self.n)

        if len(ngrams) < 10:  # Слишком короткий текст
            return "unknown", {}

        top_ngrams = TextProcessor.get_top_ngrams(ngrams, self.top_k)

        # Строим профиль документа
        doc_profile = {}
        for i, (ngram, _) in enumerate(top_ngrams):
            doc_profile[ngram] = i

        # Вычисляем расстояния до всех языков
        distances = {}
        for lang_name, lang_profile in self.language_profiles.items():
            if lang_profile:  # Проверяем, что профиль не пустой
                distance = self.calculate_distance(doc_profile, lang_profile)
                distances[lang_name] = distance

        if not distances:
            return "unknown", {}

        # Выбираем язык с минимальным расстоянием
        detected_language = min(distances.items(), key=lambda x: x[1])
        return detected_language[0], distances


# ============================================
# КЛАСС ДЛЯ АЛФАВИТНОГО МЕТОДА (ИСПРАВЛЕННЫЙ)
# ============================================

class AlphabetDetector:
    """Класс для распознавания языка алфавитным методом"""

    def __init__(self):
        self.language_profiles = {}

    def build_profile(self, text, language_name):
        """Построение профиля языка на основе частот букв"""
        # Очищаем текст, оставляя только буквы (включая специальные символы)
        text = text.lower()
        # Расширенный набор символов для французского и немецкого
        letters = re.findall(r'[a-zàâäéèêëîïôöùûüçÿæœäöüß]', text)

        if len(letters) < 100:  # Минимальное количество букв
            print(f"Внимание: мало букв ({len(letters)}) для языка {language_name}")
            self.language_profiles[language_name] = {}
            return {}

        # Считаем частоты букв
        total_letters = len(letters)
        letter_freq = Counter(letters)

        # Вычисляем относительные частоты
        profile = {}
        for letter, count in letter_freq.items():
            profile[letter] = count / total_letters

        self.language_profiles[language_name] = profile
        return profile

    def calculate_distance(self, text, lang_profile):
        """Вычисление расстояния между текстом и профилем языка"""
        if not lang_profile:
            return float('inf')

        # Получаем частоты букв в тексте
        text = text.lower()
        letters = re.findall(r'[a-zàâäéèêëîïôöùûüçÿæœäöüß]', text)

        if len(letters) < 10:  # Слишком короткий текст
            return float('inf')

        total_letters = len(letters)
        text_freq = Counter(letters)
        text_profile = {}
        for letter, count in text_freq.items():
            text_profile[letter] = count / total_letters

        # Вычисляем евклидово расстояние
        distance = 0
        all_letters = set(list(lang_profile.keys()) + list(text_profile.keys()))

        for letter in all_letters:
            lang_freq = lang_profile.get(letter, 0)
            text_freq_val = text_profile.get(letter, 0)
            distance += (lang_freq - text_freq_val) ** 2

        return math.sqrt(distance)

    def detect_language(self, text):
        """Определение языка текста"""
        distances = {}
        for lang_name, lang_profile in self.language_profiles.items():
            if lang_profile:  # Проверяем, что профиль не пустой
                distance = self.calculate_distance(text, lang_profile)
                distances[lang_name] = distance

        if not distances:
            return "unknown", {}

        # Выбираем язык с минимальным расстоянием
        detected_language = min(distances.items(), key=lambda x: x[1])
        return detected_language[0], distances


# ============================================
# КЛАСС ДЛЯ НЕЙРОСЕТЕВОГО МЕТОДА (ИСПРАВЛЕННЫЙ)
# ============================================

class NeuralNetworkDetector:
    """Класс для распознавания языка с помощью нейронной сети"""

    def __init__(self):
        self.model = None
        self.vectorizer = None
        self.language_map = {}
        self.reverse_language_map = {}

    def prepare_training_data(self, training_data):
        """Подготовка данных для обучения"""
        from sklearn.feature_extraction.text import CountVectorizer
        from sklearn.neural_network import MLPClassifier

        texts = []
        labels = []

        for lang_name, lang_texts in training_data.items():
            for text in lang_texts:
                if text.strip():  # Проверяем, что текст не пустой
                    texts.append(text)
                    labels.append(lang_name)

        if len(texts) < 2:  # Нужно хотя бы 2 текста для обучения
            raise ValueError("Недостаточно данных для обучения нейронной сети")

        # Создаем отображение языков в числа
        unique_labels = list(set(labels))
        self.language_map = {lang: idx for idx, lang in enumerate(unique_labels)}
        self.reverse_language_map = {idx: lang for lang, idx in self.language_map.items()}

        # Векторизуем тексты (N-граммы символов)
        self.vectorizer = CountVectorizer(
            analyzer='char',
            ngram_range=(2, 4),
            max_features=500  # Уменьшаем для быстродействия
        )

        X = self.vectorizer.fit_transform(texts)
        y = [self.language_map[label] for label in labels]

        return X, y

    def train(self, training_data):
        """Обучение модели"""
        from sklearn.neural_network import MLPClassifier

        X, y = self.prepare_training_data(training_data)

        # Создаем и обучаем модель
        self.model = MLPClassifier(
            hidden_layer_sizes=(50, 25),  # Уменьшаем размер сети
            max_iter=300,
            random_state=42,
            verbose=False
        )
        self.model.fit(X, y)

    def detect_language(self, text):
        """Определение языка текста"""
        if self.model is None or self.vectorizer is None:
            raise ValueError("Модель не обучена!")

        # Векторизуем текст
        X_test = self.vectorizer.transform([text])

        # Предсказываем
        try:
            probabilities = self.model.predict_proba(X_test)[0]
            predicted_label = self.model.predict(X_test)[0]
        except:
            # Если возникает ошибка, возвращаем равные вероятности
            num_classes = len(self.language_map)
            probabilities = [1.0 / num_classes] * num_classes
            predicted_label = 0

        # Формируем результат
        result = {}
        for idx, prob in enumerate(probabilities):
            lang_name = self.reverse_language_map.get(idx, f"lang_{idx}")
            result[lang_name] = float(prob)

        detected_language = self.reverse_language_map[predicted_label]
        return detected_language, result


# ============================================
# ОСНОВНОЙ КЛАСС СИСТЕМЫ (ОБНОВЛЕННЫЙ)
# ============================================

class LanguageRecognitionSystem:
    """Основная система распознавания языка текста"""

    def __init__(self, languages, methods=None):
        self.languages = languages
        self.methods = methods or ['ngram', 'alphabet', 'neural']

        # Инициализация детекторов
        self.detectors = {}

        if 'ngram' in self.methods:
            self.detectors['ngram'] = NGramDetector(n=3, top_k=200)  # Уменьшаем параметры

        if 'frequent' in self.methods:
            # Если нужен метод частотных слов
            from .frequent_words import FrequentWordsDetector
            self.detectors['frequent'] = FrequentWordsDetector()

        if 'alphabet' in self.methods:
            self.detectors['alphabet'] = AlphabetDetector()

        if 'neural' in self.methods:
            try:
                self.detectors['neural'] = NeuralNetworkDetector()
            except Exception as e:
                print(f"Нейронная сеть недоступна: {e}")
                # Создаем простую заглушку
                self.detectors['neural'] = SimpleNeuralDetector()

        # Тренировочные данные
        self.training_data = {}
        self.training_texts = {}

    def load_training_data(self, train_dir):
        """Загрузка тренировочных данных из файлов"""
        print(f"Загрузка тренировочных данных из {train_dir}...")

        for lang in self.languages:
            lang_dir = os.path.join(train_dir, lang)
            if not os.path.exists(lang_dir):
                print(f"ОШИБКА: Директория {lang_dir} не существует!")
                print(f"Создайте папку {lang_dir} и добавьте файлы в формате .html, .txt или .pdf")
                continue

            self.training_data[lang] = []
            self.training_texts[lang] = ""

            files_loaded = 0
            total_size = 0

            for file_name in os.listdir(lang_dir):
                file_path = os.path.join(lang_dir, file_name)

                # Проверяем, что это файл
                if not os.path.isfile(file_path):
                    continue

                # Читаем файл независимо от расширения
                text = FileProcessor.read_any_file(file_path)

                if text.strip():
                    text_len = len(text)
                    self.training_data[lang].append(text)
                    self.training_texts[lang] += " " + text
                    files_loaded += 1
                    total_size += text_len / 1024  # в КБ
                    print(f"    {file_name}: {text_len} символов")

            print(f"  Язык {lang}: {files_loaded} файлов, {total_size:.1f} КБ")

            if files_loaded == 0:
                print(f"  ВНИМАНИЕ: Нет данных для языка {lang}!")

    def train_detectors(self):
        """Обучение всех детекторов"""
        print("\nОбучение детекторов...")

        # Проверяем, есть ли данные для обучения
        if not self.training_data:
            print("ОШИБКА: Нет тренировочных данных!")
            return False

        # Обучение статистических методов
        for method, detector in self.detectors.items():
            if method != 'neural':
                print(f"  Обучение метода {method}...")
                for lang in self.languages:
                    if lang in self.training_texts and self.training_texts[lang]:
                        detector.build_profile(self.training_texts[lang], lang)

        # Обучение нейросетевого метода
        if 'neural' in self.detectors:
            print("  Обучение нейронной сети...")
            try:
                self.detectors['neural'].train(self.training_data)
                print("  Нейронная сеть успешно обучена!")
            except Exception as e:
                print(f"  Ошибка при обучении нейронной сети: {e}")
                print("  Создаю простой детектор на основе ключевых слов...")
                self.detectors['neural'] = SimpleNeuralDetector(self.languages)

        return True

    def detect_language(self, text):
        """Определение языка текста всеми методами (с правильным отображением)"""
        results = {}

        for method_name, detector in self.detectors.items():
            try:
                detected_lang, details = detector.detect_language(text)

                # Форматируем результат в зависимости от метода
                if method_name == 'neural':
                    # Нейросеть возвращает вероятности (0-1)
                    results[method_name] = {
                        'language': detected_lang,
                        'confidence': details,  # Проценты
                        'type': 'probability'
                    }
                else:
                    # N-граммный и алфавитный методы возвращают расстояния
                    results[method_name] = {
                        'language': detected_lang,
                        'distance': details,  # Расстояния (чем меньше, тем лучше)
                        'type': 'distance'
                    }

            except Exception as e:
                results[method_name] = {
                    'language': 'error',
                    'error': str(e),
                    'type': 'error'
                }

        return results

    def format_result_for_display(self, result):
        """Форматирование результата для отображения"""
        if result['type'] == 'probability':
            confidences = []
            for lang, prob in result['confidence'].items():
                confidences.append(f"{lang}: {prob * 100:.1f}%")
            return ", ".join(confidences)

        elif result['type'] == 'distance':
            distances = []
            for lang, dist in result['distance'].items():
                # Форматируем большие числа
                if dist > 1000000:
                    formatted = f"{dist / 1000000:.2f}M"
                elif dist > 1000:
                    formatted = f"{dist / 1000:.1f}K"
                else:
                    formatted = f"{dist:.2f}"
                distances.append(f"{lang}: {formatted}")
            return ", ".join(distances)

        elif result['type'] == 'error':
            return f"Ошибка: {result.get('error', 'неизвестная')}"

        return "Неизвестный тип результата"


# ============================================
# ПРОСТОЙ ДЕТЕКТОР (ЗАГЛУШКА)
# ============================================

class SimpleNeuralDetector:
    """Простой детектор на основе ключевых слов (если нейросеть недоступна)"""

    def __init__(self, languages=None):
        self.languages = languages or ['french', 'german']

    def detect_language(self, text):
        """Определение языка по ключевым словам"""
        text_lower = text.lower()

        # Ключевые слова для каждого языка
        keywords = {
            'french': ['le', 'la', 'les', 'un', 'une', 'des', 'et', 'est', 'dans', 'pour'],
            'german': ['der', 'die', 'das', 'ein', 'eine', 'und', 'ist', 'in', 'für', 'mit']
        }

        scores = {}
        for lang in self.languages:
            score = 0
            for keyword in keywords.get(lang, []):
                score += text_lower.count(keyword)
            scores[lang] = score

        # Нормализуем до вероятностей
        total = sum(scores.values())
        if total > 0:
            probabilities = {lang: score / total for lang, score in scores.items()}
        else:
            probabilities = {lang: 1.0 / len(self.languages) for lang in self.languages}

        # Выбираем язык с максимальным счетом
        detected_language = max(scores.items(), key=lambda x: x[1])[0]
        return detected_language, probabilities


# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

class TextProcessor:
    """Класс для предварительной обработки текста"""

    @staticmethod
    def clean_text(text):
        """Очистка текста от лишних символов"""
        text = text.lower()
        text = re.sub(r'[^a-zàâäéèêëîïôöùûüçÿæœäöüß\s]', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    @staticmethod
    def extract_ngrams(text, n=3):
        """Извлечение N-грамм из текста"""
        ngrams = []
        text = text.replace(' ', '_')
        for i in range(len(text) - n + 1):
            ngram = text[i:i + n]
            ngrams.append(ngram)
        return ngrams

    @staticmethod
    def get_top_ngrams(ngrams, top_k=200):
        """Получение наиболее частых N-грамм"""
        counter = Counter(ngrams)
        return counter.most_common(top_k)


# ============================================
# ОСНОВНАЯ ФУНКЦИЯ (ОБНОВЛЕННАЯ)
# ============================================

def main():
    """Основная функция программы"""

    print("=" * 60)
    print("СИСТЕМА АВТОМАТИЧЕСКОГО РАСПОЗНАВАНИЯ ЯЗЫКА ТЕКСТА")
    print("=" * 60)
    print("БГУИР - Лабораторная работа №8")
    print("Вариант 2: Французский, Немецкий")
    print("Методы: N-грамм, алфавитный, нейросетевой")
    print("=" * 60)

    # Проверяем наличие библиотек
    try:
        import sklearn
        print("✓ scikit-learn установлен")
    except ImportError:
        print("✗ scikit-learn не установлен. Установите: pip install scikit-learn")
        print("  Нейронная сеть будет заменена простым детектором")

    # Параметры
    LANGUAGES = ['french', 'german']
    METHODS = ['ngram', 'alphabet', 'neural']

    # Создаем систему
    system = LanguageRecognitionSystem(
        languages=LANGUAGES,
        methods=METHODS
    )

    # Загружаем тренировочные данные
    train_dir = 'train_data'
    system.load_training_data(train_dir)

    # Проверяем наличие данных
    if not system.training_data:
        print("\nОШИБКА: Не удалось загрузить тренировочные данные!")
        print("\nЧтобы система работала:")
        print("1. Создайте папки train_data/french/ и train_data/german/")
        print("2. Добавьте текстовые файлы (.txt, .html, .pdf) на соответствующих языках")
        print("\nИли запустите скрипт для скачивания данных:")
        print("python download_wikipedia_data.py")
        return

    # Обучаем систему
    if not system.train_detectors():
        print("\nНе удалось обучить систему. Проверьте данные.")
        return

    # Меню
    while True:
        print("\n" + "=" * 60)
        print("МЕНЮ:")
        print("1. Распознать введенный текст")
        print("2. Распознать текст из файла")
        print("3. Тестировать систему на test_data/")
        print("4. Выход")
        print("=" * 60)

        choice = input("Выберите опцию (1-4): ").strip()

        if choice == '1':
            print("\nВведите текст (или 'exit' для выхода):")
            text = input("> ").strip()

            if text.lower() in ['exit', 'выход']:
                continue

            if not text:
                print("Текст не может быть пустым!")
                continue

            results = system.detect_language(text)

            print("\nРезультаты распознавания:")
            print("-" * 40)
            for method, result in results.items():
                formatted = system.format_result_for_display(result)
                print(f"{method.upper()}: {result['language']}")
                print(f"  {formatted}")

        elif choice == '2':
            file_path = input("\nВведите путь к файлу: ").strip()

            if not os.path.exists(file_path):
                print("Файл не найден!")
                continue

            text = FileProcessor.read_any_file(file_path)

            if not text.strip():
                print("Не удалось прочитать файл или файл пуст!")
                continue

            print(f"Текст из файла ({len(text)} символов):")
            print(text[:200] + ("..." if len(text) > 200 else ""))

            results = system.detect_language(text)

            print("\nРезультаты распознавания:")
            print("-" * 40)
            for method, result in results.items():
                formatted = system.format_result_for_display(result)
                print(f"{method.upper()}: {result['language']}")
                print(f"  {formatted}")

        elif choice == '3':
            test_dir = 'test_data'
            if not os.path.exists(test_dir):
                print(f"Директория {test_dir} не существует!")
                continue

            print(f"\nТестирование системы на данных из {test_dir}...")

            # Простое тестирование
            for lang in LANGUAGES:
                lang_dir = os.path.join(test_dir, lang)
                if not os.path.exists(lang_dir):
                    print(f"  Пропуск тестов для {lang} (директория не существует)")
                    continue

                files = os.listdir(lang_dir)
                if not files:
                    print(f"  Нет файлов для тестирования {lang}")
                    continue

                print(f"\n  Тестирование языка: {lang}")
                print("  " + "-" * 30)

                for file_name in files[:3]:  # Тестируем максимум 3 файла
                    file_path = os.path.join(lang_dir, file_name)
                    text = FileProcessor.read_any_file(file_path)

                    if not text.strip():
                        continue

                    results = system.detect_language(text)

                    # Определяем основной результат (по N-граммному методу)
                    main_result = results.get('ngram', {}).get('language', 'unknown')

                    print(f"  {file_name}: {main_result} {'✓' if main_result == lang else '✗'}")

        elif choice == '4':
            print("\nВыход из программы...")
            break

        else:
            print("\nНеверный выбор. Попробуйте снова.")


# ============================================
# ЗАПУСК ПРОГРАММЫ
# ============================================

if __name__ == "__main__":
    # Создаем необходимые папки
    folders = ['train_data/french', 'train_data/german', 'test_data/french', 'test_data/german']
    for folder in folders:
        os.makedirs(folder, exist_ok=True)

    main()