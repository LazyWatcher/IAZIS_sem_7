import os
import sys


class EvaluationSystem:
    def __init__(self, search_engine):
        self.search_engine = search_engine
        self.qrels = {}  # Эталонные данные: {query: {doc_id: relevance}}
        # Маппинг между оригинальными именами и простыми ID
        self.id_mapping = {}

    def load_qrels(self, file_path='data/qrels.txt'):
        """Загрузка эталонных данных из файла с автоматическим созданием если файла нет"""
        self.qrels = {}
        self.id_mapping = {}

        # Создаем директорию если не существует
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Проверяем существование файла
        if not os.path.exists(file_path):
            print(f"⚠️  Файл {file_path} не найден. Создаем демо-данные...")
            self._create_demo_qrels_file(file_path)
        else:
            print(f"✅ Файл qrels найден: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                lines_loaded = 0
                for line in file:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    parts = line.split()
                    if len(parts) >= 3:
                        # Запрос (может содержать подчеркивания)
                        query = ' '.join(parts[:-2])
                        # Оригинальное имя документа из qrels
                        original_doc_id = parts[-2]
                        relevance = int(parts[-1])

                        # Преобразуем запрос: заменяем подчеркивания на пробелы
                        query = query.replace('_', ' ').lower()

                        # Получаем простой ID для документа
                        simple_id = self.search_engine.get_simple_id(original_doc_id)

                        if not simple_id:
                            # Если не нашли, пробуем использовать оригинальное имя как есть
                            simple_id = original_doc_id

                        if query not in self.qrels:
                            self.qrels[query] = {}

                        # Сохраняем маппинг
                        self.id_mapping[original_doc_id] = simple_id

                        # Сохраняем с простым ID
                        self.qrels[query][simple_id] = relevance
                        lines_loaded += 1

            print(f"✅ Загружено {lines_loaded} записей из эталонных данных")
            print(f"✅ Загружено {len(self.qrels)} уникальных запросов")

            # Показываем маппинг ID
            print(f"✅ Маппинг ID: {self.id_mapping}")

        except Exception as e:
            print(f"❌ Ошибка загрузки файла {file_path}: {str(e)}")
            import traceback
            traceback.print_exc()
            # Создание демо-данных
            self._create_demo_qrels()

    def _create_demo_qrels_file(self, file_path):
        """Создание демонстрационного файла qrels"""
        demo_content = """# Файл оценки качества (qrels)
# Формат: запрос <табуляция> ID_документа <табуляция> релевантность (1=релевантный, 0=нерелевантный)

# Пример для тестирования:
artificial_intelligence doc1 1
artificial_intelligence doc2 1
artificial_intelligence doc3 0

machine_learning doc1 1
machine_learning doc4 1
machine_learning doc5 0

computer_science doc2 1
computer_science doc3 1
computer_science doc1 0
"""

        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(demo_content)
            print(f"✅ Создан демо-файл qrels: {file_path}")

            # Загружаем созданный файл
            self.load_qrels(file_path)

        except Exception as e:
            print(f"❌ Ошибка создания файла qrels: {str(e)}")
            # Создаем демо-данные в памяти
            self._create_demo_qrels()

    def _create_demo_qrels(self):
        """Создание демонстрационных эталонных данных в памяти"""
        print("Создаем демо-данные для оценки...")

        # Используем простые ID документов, которые есть в системе
        doc_ids = list(self.search_engine.documents.keys())

        if not doc_ids:
            print("⚠️  В системе нет документов. Используем фиктивные ID.")
            doc_ids = ['doc1', 'doc2', 'doc3', 'doc4', 'doc5']

        # Создаем простые qrels
        self.qrels = {
            'artificial intelligence': {},
            'machine learning': {},
            'computer science': {}
        }

        # Распределяем документы по запросам
        for i, query in enumerate(self.qrels.keys()):
            # Первые 2 документа релевантны, остальные нет
            for j, doc_id in enumerate(doc_ids[:5]):
                relevance = 1 if j < 2 else 0
                self.qrels[query][doc_id] = relevance

        print(f"✅ Создано {len(self.qrels)} демо-запросов")

    def evaluate_query(self, query, retrieved_docs):
        """Оценка одного запроса"""
        query = query.lower()

        if query not in self.qrels:
            print(f"⚠️  Запрос '{query}' не найден в эталонных данных")
            return None

        # Получаем релевантные документы из qrels
        relevant_docs = set(doc_id for doc_id, rel in self.qrels[query].items() if rel > 0)

        # Получаем ID найденных документов
        retrieved_ids = set(doc['id'] for doc in retrieved_docs)

        print(f"  Релевантные документы из qrels: {relevant_docs}")
        print(f"  Найденные документы: {retrieved_ids}")

        # Вычисление метрик
        true_positive = len(retrieved_ids.intersection(relevant_docs))
        false_positive = len(retrieved_ids - relevant_docs)
        false_negative = len(relevant_docs - retrieved_ids)

        # Для accuracy нужно знать true_negative (документы которые не релевантны и не были найдены)
        all_docs = set(self.search_engine.documents.keys())
        non_relevant_docs = all_docs - relevant_docs
        true_negative = len(non_relevant_docs.intersection(all_docs - retrieved_ids))

        # Расчет метрик
        precision = true_positive / (true_positive + false_positive) if (true_positive + false_positive) > 0 else 0
        recall = true_positive / (true_positive + false_negative) if (true_positive + false_negative) > 0 else 0

        # F-мера
        f_measure = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        # Accuracy
        total = true_positive + false_positive + false_negative + true_negative
        accuracy = (true_positive + true_negative) / total if total > 0 else 0

        print(f"  TP: {true_positive}, FP: {false_positive}, FN: {false_negative}, TN: {true_negative}")
        print(
            f"  Precision: {precision:.3f}, Recall: {recall:.3f}, F-measure: {f_measure:.3f}, Accuracy: {accuracy:.3f}")

        return {
            'precision': round(precision, 4),
            'recall': round(recall, 4),
            'accuracy': round(accuracy, 4),
            'f_measure': round(f_measure, 4),
            'true_positive': true_positive,
            'false_positive': false_positive,
            'false_negative': false_negative,
            'true_negative': true_negative,
            'retrieved_count': len(retrieved_ids),
            'relevant_count': len(relevant_docs),
            'total_docs': len(self.search_engine.documents),
            'relevant_docs': list(relevant_docs),
            'retrieved_docs': list(retrieved_ids)
        }

    def evaluate_all_queries(self, operator='AND'):
        """Оценка всех запросов из эталонных данных"""
        if not self.qrels:
            print("❌ Эталонные данные не загружены")
            return {
                "error": "Эталонные данные не загружены",
                "per_query": {},
                "macro": {
                    'precision': 0,
                    'recall': 0,
                    'accuracy': 0,
                    'f_measure': 0
                }
            }

        per_query_metrics = {}
        all_precision = []
        all_recall = []
        all_accuracy = []
        all_f_measure = []

        print(f"\n{'=' * 60}")
        print(f"НАЧАЛО ОЦЕНКИ КАЧЕСТВА (оператор: {operator})")
        print(f"Эталонных запросов: {len(self.qrels)}")
        print(f"Документов в системе: {len(self.search_engine.documents)}")
        print(f"Простые ID документов: {list(self.search_engine.documents.keys())}")
        print(f"{'=' * 60}\n")

        for i, query in enumerate(self.qrels.keys(), 1):
            print(f"[{i}/{len(self.qrels)}] Оценка запроса: '{query}'")

            # Выполнение булевого поиска для запроса
            retrieved_docs = self.search_engine.search(query, operator=operator)

            # Оценка качества
            metrics = self.evaluate_query(query, retrieved_docs)
            if metrics:
                per_query_metrics[query] = metrics
                all_precision.append(metrics['precision'])
                all_recall.append(metrics['recall'])
                all_accuracy.append(metrics['accuracy'])
                all_f_measure.append(metrics['f_measure'])
            print()

        # Макроусреднение
        macro_metrics = {
            'precision': sum(all_precision) / len(all_precision) if all_precision else 0,
            'recall': sum(all_recall) / len(all_recall) if all_recall else 0,
            'accuracy': sum(all_accuracy) / len(all_accuracy) if all_accuracy else 0,
            'f_measure': sum(all_f_measure) / len(all_f_measure) if all_f_measure else 0
        }

        print(f"{'=' * 60}")
        print(f"РЕЗУЛЬТАТЫ ОЦЕНКИ:")
        print(f"Precision (макро): {macro_metrics['precision']:.3f}")
        print(f"Recall (макро): {macro_metrics['recall']:.3f}")
        print(f"F-measure (макро): {macro_metrics['f_measure']:.3f}")
        print(f"Accuracy (макро): {macro_metrics['accuracy']:.3f}")
        print(f"{'=' * 60}")

        return {
            'per_query': per_query_metrics,
            'macro': macro_metrics,
            'operator': operator,
            'total_queries': len(per_query_metrics),
            'documents_count': len(self.search_engine.documents)
        }