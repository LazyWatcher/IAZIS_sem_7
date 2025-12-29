import os
import sys
import json
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify

# Добавляем текущую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импортируем нашу систему распознавания языка
try:
    from language_detector import LanguageRecognitionSystem, FileProcessor, TextProcessor

    SYSTEM_AVAILABLE = True
except ImportError as e:
    print(f"Ошибка импорта: {e}")
    SYSTEM_AVAILABLE = False

app = Flask(__name__)

# Инициализация системы (один раз при запуске)
SYSTEM = None
LANGUAGES = ['french', 'german']
METHODS = ['ngram', 'alphabet', 'neural']
INIT_STATUS = "Не инициализировано"
INIT_SUCCESS = False


def initialize_system():
    """Инициализация системы распознавания языка"""
    global SYSTEM, INIT_STATUS, INIT_SUCCESS

    if not SYSTEM_AVAILABLE:
        INIT_STATUS = "Ошибка: Не удалось импортировать модули системы"
        return False

    print("Инициализация системы распознавания языка...")

    try:
        SYSTEM = LanguageRecognitionSystem(
            languages=LANGUAGES,
            methods=METHODS
        )

        # Загружаем тренировочные данные
        train_dir = 'train_data'
        if not os.path.exists(train_dir):
            INIT_STATUS = f"Директория {train_dir} не найдена!"
            return False

        SYSTEM.load_training_data(train_dir)

        # Проверяем, есть ли данные для обучения
        if not SYSTEM.training_data:
            INIT_STATUS = "Нет тренировочных данных!"
            return False

        # Обучаем систему
        if not SYSTEM.train_detectors():
            INIT_STATUS = "Не удалось обучить систему!"
            return False

        INIT_SUCCESS = True
        INIT_STATUS = "Система успешно инициализирована!"
        return True

    except Exception as e:
        INIT_STATUS = f"Ошибка инициализации: {str(e)}"
        return False


# Инициализируем систему при старте приложения
INIT_SUCCESS = initialize_system()
print(INIT_STATUS)


def format_distance(value):
    """Форматирование расстояния для отображения"""
    if value is None:
        return "N/A"

    try:
        value = float(value)
        if value > 1000000:
            return f"{value / 1000000:.2f}M"
        elif value > 1000:
            return f"{value / 1000:.1f}K"
        elif value > 100:
            return f"{value:.0f}"
        elif value > 10:
            return f"{value:.1f}"
        else:
            return f"{value:.2f}"
    except:
        return str(value)


def format_confidence(value):
    """Форматирование уверенности для отображения"""
    if value is None:
        return "N/A"

    try:
        value = float(value)
        return f"{value * 100:.1f}%"
    except:
        return str(value)


@app.route('/')
def index():
    """Главная страница"""
    system_info = {
        'status': INIT_STATUS,
        'success': INIT_SUCCESS,
        'languages': LANGUAGES,
        'methods': METHODS,
        'training_data_size': 0,
        'has_test_data': os.path.exists('test_data')
    }

    # Подсчитываем объем тренировочных данных
    if INIT_SUCCESS and SYSTEM and SYSTEM.training_texts:
        for lang in LANGUAGES:
            if lang in SYSTEM.training_texts:
                system_info['training_data_size'] += len(SYSTEM.training_texts[lang])
        system_info['training_data_size'] = system_info['training_data_size'] // 1024  # в КБ

    return render_template('index.html', system_info=system_info)


@app.route('/api/status')
def api_status():
    """API для получения статуса системы"""
    return jsonify({
        'success': INIT_SUCCESS,
        'status': INIT_STATUS,
        'languages': LANGUAGES,
        'methods': METHODS,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })


@app.route('/api/detect', methods=['POST'])
def detect_language():
    """API для распознавания языка текста"""
    if not SYSTEM or not INIT_SUCCESS:
        return jsonify({
            'success': False,
            'error': 'Система не инициализирована'
        })

    # Получаем текст из запроса
    data = request.json
    text = data.get('text', '').strip()

    if not text:
        return jsonify({
            'success': False,
            'error': 'Текст не может быть пустым'
        })

    try:
        # Распознаем язык
        results = SYSTEM.detect_language(text)

        # Форматируем результаты для отображения
        formatted_results = {}
        detailed_results = {}

        for method, result in results.items():
            if result.get('language') == 'error':
                formatted_results[method] = {
                    'language': 'error',
                    'display': f"Ошибка: {result.get('error', 'Неизвестная ошибка')}",
                    'type': 'error',
                    'details': {}
                }
                detailed_results[method] = formatted_results[method]
            else:
                detected_lang = result['language']
                result_type = result.get('type', 'unknown')

                if result_type == 'probability':
                    # Нейросеть - вероятности
                    details = result.get('confidence', {})
                    details_display = {lang: format_confidence(conf) for lang, conf in details.items()}
                    details_str = ", ".join([f"{lang}: {conf}" for lang, conf in details_display.items()])

                    formatted_results[method] = {
                        'language': detected_lang,
                        'display': f"Вероятность: {details_str}",
                        'type': 'probability',
                        'details': details_display,
                        'raw_details': details
                    }

                elif result_type == 'distance':
                    # N-граммный и алфавитный методы - расстояния
                    details = result.get('distance', {})
                    details_display = {lang: format_distance(dist) for lang, dist in details.items()}
                    details_str = ", ".join([f"{lang}: {dist}" for lang, dist in details_display.items()])

                    formatted_results[method] = {
                        'language': detected_lang,
                        'display': f"Расстояние: {details_str}",
                        'type': 'distance',
                        'details': details_display,
                        'raw_details': details
                    }
                else:
                    formatted_results[method] = {
                        'language': detected_lang,
                        'display': f"Результат: {detected_lang}",
                        'type': 'unknown',
                        'details': {},
                        'raw_details': {}
                    }

                detailed_results[method] = formatted_results[method]

        return jsonify({
            'success': True,
            'text': text[:500] + ('...' if len(text) > 500 else ''),
            'text_length': len(text),
            'results': formatted_results,
            'detailed_results': detailed_results,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/test', methods=['POST'])
def test_system():
    """API для тестирования системы"""
    if not SYSTEM or not INIT_SUCCESS:
        return jsonify({
            'success': False,
            'error': 'Система не инициализирована'
        })

    try:
        # Тестируем систему на тестовых данных
        test_dir = 'test_data'
        if not os.path.exists(test_dir):
            return jsonify({
                'success': False,
                'error': f'Директория {test_dir} не найдена'
            })

        # Простое тестирование (упрощенная версия)
        test_results = {}
        total_tests = 0
        correct_by_method = {method: 0 for method in METHODS}

        for lang in LANGUAGES:
            lang_dir = os.path.join(test_dir, lang)
            if not os.path.exists(lang_dir):
                continue

            test_results[lang] = {}

            files = os.listdir(lang_dir)
            for file_name in files[:5]:  # Ограничиваем 5 файлами на язык
                file_path = os.path.join(lang_dir, file_name)

                # Читаем файл
                text = FileProcessor.read_any_file(file_path)
                if not text.strip():
                    continue

                total_tests += 1
                test_results[lang][file_name] = {}

                # Распознаем язык
                results = SYSTEM.detect_language(text)

                for method in METHODS:
                    if method in results:
                        detected_lang = results[method].get('language', 'unknown')
                        test_results[lang][file_name][method] = detected_lang

                        # Проверяем правильность
                        if detected_lang.lower() == lang.lower():
                            correct_by_method[method] += 1

        # Вычисляем точность
        accuracy_results = {}
        for method in METHODS:
            if total_tests > 0:
                accuracy = correct_by_method[method] / total_tests * 100
                accuracy_results[method] = {
                    'accuracy': accuracy,
                    'correct': correct_by_method[method],
                    'total': total_tests
                }

        return jsonify({
            'success': True,
            'test_results': test_results,
            'accuracy_results': accuracy_results,
            'total_tests': total_tests,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """API для загрузки файла"""
    if not SYSTEM or not INIT_SUCCESS:
        return jsonify({
            'success': False,
            'error': 'Система не инициализирована'
        })

    if 'file' not in request.files:
        return jsonify({
            'success': False,
            'error': 'Файл не загружен'
        })

    file = request.files['file']

    if file.filename == '':
        return jsonify({
            'success': False,
            'error': 'Файл не выбран'
        })

    try:
        # Сохраняем временный файл
        import tempfile
        import shutil

        # Создаем временную директорию
        temp_dir = tempfile.mkdtemp()
        temp_filepath = os.path.join(temp_dir, file.filename)

        # Сохраняем файл
        file.save(temp_filepath)

        # Читаем файл
        text = FileProcessor.read_any_file(temp_filepath)

        # Удаляем временную директорию
        shutil.rmtree(temp_dir)

        if not text.strip():
            return jsonify({
                'success': False,
                'error': 'Не удалось извлечь текст из файла'
            })

        # Распознаем язык
        results = SYSTEM.detect_language(text)

        # Форматируем результаты
        formatted_results = {}
        for method, result in results.items():
            if result.get('language') == 'error':
                formatted_results[method] = {
                    'language': 'error',
                    'display': f"Ошибка: {result.get('error', 'Неизвестная ошибка')}",
                    'type': 'error'
                }
            else:
                detected_lang = result['language']
                result_type = result.get('type', 'unknown')

                if result_type == 'probability':
                    details = result.get('confidence', {})
                    details_display = {lang: format_confidence(conf) for lang, conf in details.items()}
                    details_str = ", ".join([f"{lang}: {conf}" for lang, conf in details_display.items()])

                    formatted_results[method] = {
                        'language': detected_lang,
                        'display': f"Вероятность: {details_str}",
                        'type': 'probability'
                    }

                elif result_type == 'distance':
                    details = result.get('distance', {})
                    details_display = {lang: format_distance(dist) for lang, dist in details.items()}
                    details_str = ", ".join([f"{lang}: {dist}" for lang, dist in details_display.items()])

                    formatted_results[method] = {
                        'language': detected_lang,
                        'display': f"Расстояние: {details_str}",
                        'type': 'distance'
                    }
                else:
                    formatted_results[method] = {
                        'language': detected_lang,
                        'display': f"Результат: {detected_lang}",
                        'type': 'unknown'
                    }

        return jsonify({
            'success': True,
            'filename': file.filename,
            'file_size': len(text),
            'text_preview': text[:500] + ('...' if len(text) > 500 else ''),
            'results': formatted_results,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/stats')
def get_stats():
    """API для получения статистики системы"""
    if not SYSTEM or not INIT_SUCCESS:
        return jsonify({
            'success': False,
            'error': 'Система не инициализирована'
        })

    try:
        stats = {
            'languages': LANGUAGES,
            'methods': METHODS,
            'training_data': {},
            'status': INIT_STATUS
        }

        # Информация о тренировочных данных
        if SYSTEM.training_texts:
            for lang in LANGUAGES:
                if lang in SYSTEM.training_texts:
                    text = SYSTEM.training_texts[lang]
                    stats['training_data'][lang] = {
                        'size_kb': len(text) // 1024,
                        'characters': len(text),
                        'words': len(text.split()),
                        'has_data': True
                    }
                else:
                    stats['training_data'][lang] = {
                        'size_kb': 0,
                        'characters': 0,
                        'words': 0,
                        'has_data': False
                    }

        # Проверяем наличие тестовых данных
        test_data_exists = os.path.exists('test_data')
        stats['test_data'] = {
            'exists': test_data_exists,
            'languages': {}
        }

        if test_data_exists:
            for lang in LANGUAGES:
                lang_dir = os.path.join('test_data', lang)
                if os.path.exists(lang_dir):
                    files = os.listdir(lang_dir)
                    stats['test_data']['languages'][lang] = {
                        'file_count': len(files),
                        'files': files[:5]  # Первые 5 файлов
                    }

        return jsonify({
            'success': True,
            'stats': stats,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


# Добавляем метод read_any_file_from_bytes в FileProcessor для обработки загруженных файлов
def read_any_file_from_bytes(content, filename):
    """Чтение файла из байтов по расширению"""
    from bs4 import BeautifulSoup
    import io

    try:
        # Определяем формат по расширению
        if filename.lower().endswith(('.html', '.htm')):
            soup = BeautifulSoup(content, 'html.parser')
            for element in soup.find_all(['script', 'style', 'nav', 'footer']):
                element.decompose()
            return soup.get_text()
        elif filename.lower().endswith('.pdf'):
            try:
                import PyPDF2
                pdf_file = io.BytesIO(content)
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text()
                return text
            except ImportError:
                return "PDF обработка недоступна. Установите PyPDF2."
        else:
            # Предполагаем текстовый файл
            return content.decode('utf-8', errors='ignore')
    except Exception as e:
        return f"Ошибка чтения файла: {str(e)}"


# Добавляем метод в FileProcessor
if SYSTEM_AVAILABLE:
    FileProcessor.read_any_file_from_bytes = staticmethod(read_any_file_from_bytes)

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("ВЕБ-ПРИЛОЖЕНИЕ ДЛЯ РАСПОЗНАВАНИЯ ЯЗЫКА ТЕКСТА")
    print("=" * 60)
    print(f"Языки: {', '.join(LANGUAGES)}")
    print(f"Методы: {', '.join(METHODS)}")
    print(f"Статус: {INIT_STATUS}")
    print("=" * 60)
    print("Приложение запущено на http://localhost:5000")
    print("Откройте этот адрес в браузере")
    print("=" * 60 + "\n")

    # Создаем необходимые папки
    folders = ['train_data/french', 'train_data/german', 'test_data/french', 'test_data/german']
    for folder in folders:
        os.makedirs(folder, exist_ok=True)

    app.run(debug=False, host='0.0.0.0', port=5000)