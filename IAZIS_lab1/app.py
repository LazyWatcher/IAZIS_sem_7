import time

from flask import Flask, render_template, request, jsonify
from collections import Counter
import os
import json
import sys
import shutil
from search_engine import SearchEngine
from evaluation import EvaluationSystem
from ai_analyzer import AIDocumentAnalyzer
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'data/documents'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['ALLOWED_EXTENSIONS'] = {'txt', 'pdf'}

# Инициализация систем
search_engine = SearchEngine()
evaluation_system = EvaluationSystem(search_engine)
ai_analyzer = AIDocumentAnalyzer()

# Переменная для хранения текущей папки
current_folder = ''
# Словарь для отслеживания статуса AI анализа
ai_status = {'processing': False, 'last_completed': 0}

def allowed_file(filename):
    """Проверка расширения файла"""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/')
def index():
    """Главная страница поиска"""
    return render_template('index.html')


@app.route('/search', methods=['POST'])
def search():
    """Обработка поискового запроса"""
    query = request.form.get('query', '')
    operator = request.form.get('operator', 'AND')

    if not query:
        return render_template('results.html', query="", results=[], operator=operator)

    try:
        # Выполнение булевого поиска
        results = search_engine.search(query, operator=operator)

        # Подсветка найденных слов
        for result in results:
            result['highlighted_snippet'] = highlight_words(result.get('snippet', ''), query)

        return render_template('results.html',
                               query=query,
                               results=results,
                               operator=operator,
                               total_docs=len(search_engine.documents))

    except Exception as e:
        return render_template('results.html',
                               query=query,
                               results=[],
                               operator=operator,
                               error=str(e))


@app.route('/api/scan_folder', methods=['POST'])
def scan_folder():
    """Сканирование папки и загрузка документов напрямую"""
    global current_folder

    try:
        data = request.get_json()
        folder_path = data.get('folder_path', '')
        recursive = data.get('recursive', True)
        include_pdf = data.get('include_pdf', True)

        if not folder_path or not os.path.exists(folder_path):
            return jsonify({
                'success': False,
                'error': f'Папка не существует: {folder_path}'
            })

        if not os.path.isdir(folder_path):
            return jsonify({
                'success': False,
                'error': f'Указанный путь не является папкой: {folder_path}'
            })

        # Сохраняем текущую папку
        current_folder = folder_path

        # Сканируем папку и загружаем документы
        stats = search_engine.scan_and_load_documents(
            folder_path,
            recursive=recursive,
            include_pdf=include_pdf
        )

        return jsonify({
            'success': True,
            'message': f'Папка успешно просканирована: {folder_path}',
            'stats': stats,
            'documents_count': len(search_engine.documents)
        })

    except Exception as e:
        print(f"Ошибка сканирования папки: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Ошибка сканирования: {str(e)}'
        })


@app.route('/api/ai/recommend', methods=['POST'])
def get_ai_recommendations():
    """Получение AI-рекомендаций для поиска с защитой от зависания"""
    global ai_status

    # Проверяем, не выполняется ли уже анализ
    if ai_status['processing'] and (time.time() - ai_status['last_completed']) < 30:
        return jsonify({
            'success': False,
            'error': 'AI анализ уже выполняется. Подождите немного.',
            'recommendations': ai_analyzer._get_fallback_recommendations()
        })

    try:
        data = request.get_json()
        folder_path = data.get('folder_path', '')

        # Если папка не указана, используем текущую
        if not folder_path and current_folder:
            folder_path = current_folder

        if not folder_path or not os.path.exists(folder_path):
            return jsonify({
                'success': False,
                'error': 'Папка не указана или не существует',
                'recommendations': ai_analyzer._get_fallback_recommendations()
            })

        # Устанавливаем статус "в процессе"
        ai_status['processing'] = True

        # Генерируем рекомендации (с таймаутом)
        recommendations = ai_analyzer.analyze_folder_and_recommend(
            folder_path,
            num_recommendations=5
        )

        # Обновляем статус
        ai_status['processing'] = False
        ai_status['last_completed'] = time.time()

        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'model': ai_analyzer.model,
            'folder': folder_path,
            'timestamp': ai_status['last_completed']
        })

    except Exception as e:
        print(f"Ошибка AI анализа: {str(e)}")
        # Сбрасываем статус при ошибке
        ai_status['processing'] = False
        ai_status['last_completed'] = time.time()

        return jsonify({
            'success': False,
            'error': str(e),
            'recommendations': ai_analyzer._get_fallback_recommendations(),
            'timestamp': time.time()
        })


@app.route('/api/ai/status')
def get_ai_status():
    """Получение статуса AI анализа"""
    return jsonify({
        'processing': ai_status['processing'],
        'last_completed': ai_status['last_completed'],
        'seconds_since_last': time.time() - ai_status['last_completed'] if ai_status['last_completed'] > 0 else None
    })


@app.route('/api/system/info')
def system_info():
    """Информация о системе"""
    global current_folder

    file_types = Counter()
    for doc in search_engine.documents.values():
        file_types[doc['file_type']] += 1

    # Проверяем наличие qrels файла
    qrels_exists = os.path.exists('data/qrels.txt')
    qrels_size = os.path.getsize('data/qrels.txt') if qrels_exists else 0

    info = {
        'documents_count': len(search_engine.documents),
        'file_types': dict(file_types),
        'indexed_terms': len(search_engine.inverted_index),
        'current_folder': current_folder,
        'search_type': 'Boolean (AND/OR)',
        'ai_status': 'active' if hasattr(ai_analyzer, 'api_key') and ai_analyzer.api_key else 'disabled',
        'qrels_exists': qrels_exists,
        'qrels_size': qrels_size,
        'evaluation_ready': len(search_engine.documents) > 0 and qrels_exists
    }
    return jsonify(info)


@app.route('/api/qrels/info')
def get_qrels_info():
    """Информация о файле qrels"""
    qrels_file = 'data/qrels.txt'

    info = {
        'exists': os.path.exists(qrels_file),
        'path': os.path.abspath(qrels_file),
        'size': 0,
        'lines': 0,
        'queries': 0,
        'content_preview': ''
    }


@app.route('/api/qrels/create_demo', methods=['POST'])
def create_demo_qrels():
    """Создание демо-файла qrels"""
    try:
        # Создаем демо qrels файл
        evaluation_system._create_demo_qrels_file('data/qrels.txt')

        return jsonify({
            'success': True,
            'message': 'Демо-файл qrels создан',
            'path': os.path.abspath('data/qrels.txt')
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

def highlight_words(text, query):
    """Подсветка слов запроса в тексте"""
    words = query.lower().split()
    for word in words:
        if len(word) > 2:
            text = text.replace(word, f'<mark>{word}</mark>')
            text = text.replace(word.title(), f'<mark>{word.title()}</mark>')
    return text

@app.route('/evaluation')
def evaluation():
    """Страница оценки качества"""
    return render_template('evaluation.html')


@app.route('/api/evaluate', methods=['POST'])
def api_evaluate():
    """API для оценки качества системы"""
    try:
        data = request.get_json()
        qrels_file = data.get('qrels_file', 'data/qrels.txt')
        operator = data.get('operator', 'AND')

        print(f"\n🔍 Начинаем оценку качества...")
        print(f"   Файл qrels: {qrels_file}")
        print(f"   Оператор: {operator}")
        print(f"   Документов в системе: {len(search_engine.documents)}")

        # Загрузка эталонных данных (файл создастся автоматически если его нет)
        evaluation_system.load_qrels(qrels_file)

        # Выполнение оценки
        metrics = evaluation_system.evaluate_all_queries(operator=operator)

        # Генерация графиков
        plot_data = generate_evaluation_plots(metrics)

        return jsonify({
            'success': True,
            'metrics': metrics,
            'plots': plot_data,
            'operator': operator,
            'qrels_file': qrels_file,
            'documents_count': len(search_engine.documents)
        })

    except Exception as e:
        print(f"❌ Ошибка оценки: {str(e)}")
        import traceback
        traceback.print_exc()

        return jsonify({
            'success': False,
            'error': str(e),
            'details': 'Проверьте наличие файла data/qrels.txt или создайте его вручную'
        })



@app.route('/api/metrics/details')
def get_metrics_details():
    """Получение детальной информации о метриках"""
    metrics_info = {
        'precision': {
            'name': 'Точность (Precision)',
            'description': 'Доля релевантных документов среди найденных',
            'formula': 'Precision = TP / (TP + FP)'
        },
        'recall': {
            'name': 'Полнота (Recall)',
            'description': 'Доля найденных релевантных документов от общего числа релевантных',
            'formula': 'Recall = TP / (TP + FN)'
        },
        'f_measure': {
            'name': 'F-мера',
            'description': 'Среднее гармоническое точности и полноты',
            'formula': 'F = 2 * Precision * Recall / (Precision + Recall)'
        },
        'accuracy': {
            'name': 'Аккуратность (Accuracy)',
            'description': 'Доля правильных решений системы',
            'formula': 'Accuracy = (TP + TN) / (TP + FP + FN + TN)'
        }
    }
    return jsonify(metrics_info)


def generate_evaluation_plots(metrics):
    """Генерация графиков для оценки качества"""
    plots = {}

    if 'per_query' not in metrics or not metrics['per_query']:
        print("⚠️  Нет данных для построения графиков")
        return plots

    try:
        # График Precision-Recall
        plt.figure(figsize=(10, 6))
        queries = list(metrics['per_query'].keys())
        precision_values = [metrics['per_query'][q]['precision'] for q in queries]
        recall_values = [metrics['per_query'][q]['recall'] for q in queries]

        plt.scatter(recall_values, precision_values, alpha=0.7, s=100)
        plt.xlabel('Recall (Полнота)', fontsize=12)
        plt.ylabel('Precision (Точность)', fontsize=12)
        plt.title(f'Precision-Recall по запросам (Оператор: {metrics.get("operator", "AND")})', fontsize=14)
        plt.grid(True, alpha=0.3)
        plt.xlim(-0.05, 1.05)
        plt.ylim(-0.05, 1.05)

        # Добавление подписей для точек
        for i, query in enumerate(queries):
            plt.annotate(f'Q{i + 1}', (recall_values[i], precision_values[i]),
                         xytext=(5, 5), textcoords='offset points', fontsize=9)

        # Сохранение графика
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        plots['precision_recall'] = base64.b64encode(buffer.getvalue()).decode()
        plt.close()

        # График сравнения метрик
        plt.figure(figsize=(12, 6))
        metric_names = ['Precision', 'Recall', 'F-measure', 'Accuracy']
        macro_values = [
            metrics['macro']['precision'],
            metrics['macro']['recall'],
            metrics['macro']['f_measure'],
            metrics['macro']['accuracy']
        ]

        colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12']
        bars = plt.bar(metric_names, macro_values, color=colors)
        plt.ylim(0, 1)
        plt.title('Сравнение метрик качества (макроусреднение)', fontsize=14)
        plt.ylabel('Значение', fontsize=12)
        plt.grid(axis='y', alpha=0.3)

        # Добавление значений на столбцы
        for i, (bar, v) in enumerate(zip(bars, macro_values)):
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width() / 2., height + 0.01,
                     f'{v:.3f}', ha='center', va='bottom', fontsize=11)

        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        plots['metrics_comparison'] = base64.b64encode(buffer.getvalue()).decode()
        plt.close()

        print("✅ Графики успешно сгенерированы")

    except Exception as e:
        print(f"❌ Ошибка генерации графиков: {str(e)}")
        import traceback
        traceback.print_exc()

    return plots


@app.route('/debug/search')
def debug_search():
    """Страница для отладки поиска"""
    query = request.args.get('query', 'artificial intelligence')
    operator = request.args.get('operator', 'AND')

    # Выполнение поиска - передаем operator
    results = search_engine.search(query, operator=operator)

    # Отладочная информация
    debug_info = {
        'query': query,
        'operator': operator,
        'total_documents': len(search_engine.documents),
        'indexed_terms': len(search_engine.inverted_index),
        'results_count': len(results)
    }

    return render_template('debug_search.html',
                           debug_info=debug_info,
                           results=results,
                           query=query,
                           operator=operator)


@app.route('/debug/index')
def debug_index():
    """Просмотр инвертированного индекса"""
    index_stats = {
        'total_terms': len(search_engine.inverted_index),
        'sample_terms': list(search_engine.inverted_index.items())[:50],
        'terms_per_doc_avg': sum(len(docs) for docs in search_engine.inverted_index.values()) / len(
            search_engine.inverted_index) if search_engine.inverted_index else 0
    }
    return jsonify(index_stats)


if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    print("🚀 Запуск AI Boolean Search System...")
    print(f"📁 Рабочая директория: {os.getcwd()}")
    print(f"📊 Файл qrels: {os.path.abspath('data/qrels.txt')}")

    # Проверяем наличие необходимых директорий
    if not os.path.exists('data'):
        os.makedirs('data')
        print("✅ Создана папка 'data'")

    # Загружаем документы из папки data/documents если она существует
    if os.path.exists('data/documents'):
        print("📂 Загружаем документы из data/documents...")
        search_engine.scan_and_load_documents('data/documents')

    # Не загружаем документы при старте - ждем выбора папки
    app.run(debug=False, host='0.0.0.0', port=5000)