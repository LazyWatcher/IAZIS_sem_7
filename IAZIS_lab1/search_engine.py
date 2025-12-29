import os
import re
import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
from collections import defaultdict, Counter
import sys

# PDF processing libraries
try:
    import PyPDF2

    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    import pdfplumber

    PDFPLUMBER_SUPPORT = True
except ImportError:
    PDFPLUMBER_SUPPORT = False

# Загрузка необходимых данных NLTK
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')


class SearchEngine:
    def __init__(self):
        self.documents = {}
        self.inverted_index = defaultdict(set)
        self.stemmer = PorterStemmer()
        self.stop_words = set(stopwords.words('english'))
        # Словарь для соответствия между упрощенными ID и реальными именами файлов
        self.id_mapping = {}
        self.next_doc_id = 1

    def scan_and_load_documents(self, folder_path, recursive=True, include_pdf=True):
        """Сканирование папки и загрузка документов напрямую"""
        self.documents.clear()
        self.inverted_index.clear()
        self.id_mapping.clear()
        self.next_doc_id = 1

        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"Папка не существует: {folder_path}")

        stats = {
            'total_files': 0,
            'processed_files': 0,
            'failed_files': 0,
            'file_types': Counter(),
            'total_size': 0
        }

        # Определяем поддерживаемые расширения
        supported_extensions = ['.txt']
        if include_pdf and PDF_SUPPORT:
            supported_extensions.append('.pdf')

        # Сканируем папку
        if recursive:
            # Рекурсивный обход
            for root, dirs, files in os.walk(folder_path):
                for filename in files:
                    self._process_file(root, filename, supported_extensions, stats)
        else:
            # Только указанная папка
            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)
                if os.path.isfile(file_path):
                    self._process_file(folder_path, filename, supported_extensions, stats)

        # Строим индекс
        self._build_index()

        print(f"\n✅ Сканирование завершено:")
        print(f"   Всего файлов: {stats['total_files']}")
        print(f"   Обработано: {stats['processed_files']}")
        print(f"   Не удалось: {stats['failed_files']}")
        print(f"   Типы файлов: {dict(stats['file_types'])}")
        print(f"   Загружено документов: {len(self.documents)}")
        print(f"   Индексировано терминов: {len(self.inverted_index)}")

        # Форматируем для ответа
        stats['file_types'] = [f"{k}: {v}" for k, v in stats['file_types'].items()]

        return stats

    def _process_file(self, root, filename, supported_extensions, stats):
        """Обработка одного файла"""
        stats['total_files'] += 1

        file_ext = os.path.splitext(filename)[1].lower()

        if file_ext not in supported_extensions:
            return

        file_path = os.path.join(root, filename)

        try:
            # Создаем уникальный ID документа (используем базовое имя файла без расширения)
            base_name = os.path.splitext(filename)[0]

            # Создаем простой ID для поиска (doc1, doc2, ...)
            simple_id = f"doc{self.next_doc_id}"
            self.next_doc_id += 1

            # Сохраняем маппинг
            self.id_mapping[simple_id] = {
                'simple_id': simple_id,
                'filename': filename,
                'base_name': base_name,
                'file_path': file_path
            }

            # Читаем содержимое файла
            content = self._read_file_content(file_path, file_ext)

            if content and content.strip():
                self.documents[simple_id] = {
                    'content': content,
                    'title': filename,
                    'simple_id': simple_id,
                    'original_name': base_name,
                    'file_type': file_ext[1:].upper() if file_ext.startswith('.') else file_ext.upper(),
                    'snippet': self._create_snippet(content),
                    'tokens': self._preprocess_text(content),
                    'path': file_path
                }

                stats['processed_files'] += 1
                stats['file_types'][file_ext] += 1
                stats['total_size'] += os.path.getsize(file_path)

                print(f"✓ Обработан: {filename} -> {simple_id}")
            else:
                stats['failed_files'] += 1
                print(f"✗ Пустой файл: {filename}")

        except Exception as e:
            stats['failed_files'] += 1
            print(f"✗ Ошибка обработки {filename}: {str(e)}", file=sys.stderr)

    def _read_file_content(self, file_path, file_ext):
        """Чтение содержимого файла"""
        try:
            if file_ext == '.pdf':
                return self._extract_text_from_pdf(file_path)
            else:  # .txt
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
        except Exception as e:
            print(f"Ошибка чтения {file_path}: {str(e)}", file=sys.stderr)
            return ""

    def _extract_text_from_pdf(self, pdf_path):
        """Извлечение текста из PDF-файла"""
        text = ""

        if not PDF_SUPPORT:
            print(f"PDF поддержка отключена: {pdf_path}")
            return text

        # Пробуем сначала pdfplumber
        if PDFPLUMBER_SUPPORT:
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                if text.strip():
                    return text
            except Exception as e:
                print(f"pdfplumber не смог обработать {pdf_path}: {e}", file=sys.stderr)

        # Если pdfplumber не сработал, используем PyPDF2
        if PDF_SUPPORT:
            try:
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page in pdf_reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
            except Exception as e:
                print(f"PyPDF2 не смог обработать {pdf_path}: {e}", file=sys.stderr)

        return text

    def _preprocess_text(self, text):
        """Предобработка текста"""
        text = text.lower()
        text = re.sub(r'[^a-z\s]', ' ', text)
        tokens = word_tokenize(text)

        processed_tokens = []
        for token in tokens:
            if token not in self.stop_words and len(token) > 2:
                stemmed = self.stemmer.stem(token)
                processed_tokens.append(stemmed)

        return processed_tokens

    def _create_snippet(self, content, max_length=200):
        """Создание сниппета"""
        content = re.sub(r'\s+', ' ', content).strip()
        if len(content) <= max_length:
            return content
        return content[:max_length] + "..."

    def _build_index(self):
        """Построение инвертированного индекса"""
        for doc_id, doc_data in self.documents.items():
            tokens = doc_data['tokens']
            for token in set(tokens):
                self.inverted_index[token].add(doc_id)

    def _boolean_search(self, query, operator='AND'):
        """Булев поиск с операторами AND/OR"""
        query_tokens = self._preprocess_text(query)

        if not query_tokens:
            return []

        if operator.upper() == 'OR':
            # OR: объединение результатов
            result_docs = set()
            for token in query_tokens:
                token_docs = self.inverted_index.get(token, set())
                result_docs = result_docs.union(token_docs)
            return list(result_docs)
        else:
            # AND: пересечение результатов
            result_docs = None
            for token in query_tokens:
                token_docs = self.inverted_index.get(token, set())
                if result_docs is None:
                    result_docs = token_docs
                else:
                    result_docs = result_docs.intersection(token_docs)

            return list(result_docs) if result_docs else []

    def search(self, query, operator='AND'):
        """Основная функция поиска"""
        query_tokens = self._preprocess_text(query)

        if not query_tokens:
            return []

        doc_ids = self._boolean_search(query, operator)

        results = []
        for doc_id in doc_ids:
            if doc_id in self.documents:
                doc_data = self.documents[doc_id]
                matched_terms = self._get_matched_terms(query, doc_id)

                results.append({
                    'id': doc_id,
                    'original_name': doc_data.get('original_name', ''),
                    'title': doc_data['title'],
                    'file_type': doc_data['file_type'],
                    'snippet': doc_data['snippet'],
                    'matched_terms': matched_terms,
                    'score': len(matched_terms),
                    'operator': operator,
                    'path': doc_data.get('path', '')
                })

        # Сортируем по релевантности
        results.sort(key=lambda x: x['score'], reverse=True)
        return results

    def _get_matched_terms(self, query, doc_id):
        """Получение совпавших терминов"""
        query_tokens = self._preprocess_text(query)
        doc_tokens = self.documents[doc_id]['tokens']
        matched = set(query_tokens).intersection(set(doc_tokens))
        return list(matched)

    def get_document_by_id(self, doc_id):
        """Получение документа по ID (поддерживает простые ID и оригинальные имена)"""
        # Пробуем найти по простому ID
        if doc_id in self.documents:
            return self.documents[doc_id]

        # Пробуем найти по оригинальному имени
        for doc in self.documents.values():
            if doc.get('original_name') == doc_id:
                return doc

        return None

    def get_simple_id(self, original_name):
        """Получение простого ID по оригинальному имени"""
        for simple_id, mapping in self.id_mapping.items():
            if mapping.get('base_name') == original_name:
                return simple_id
        return None