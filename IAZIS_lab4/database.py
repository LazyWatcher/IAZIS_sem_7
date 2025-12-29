"""
Модуль для работы с базой данных словаря и хранения результатов
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import threading

from config import Config
from utils import logger


class DatabaseManager:
    """Менеджер базы данных для системы перевода"""

    def __init__(self, db_path: str = None):
        """
        Инициализация менеджера базы данных

        Args:
            db_path: Путь к файлу базы данных
        """
        if db_path is None:
            db_path = Config.get_dictionary_file('general', 'main')
            db_path = db_path.replace('.json', '.db')

        self.db_path = db_path
        self.connection = None
        self._local = threading.local()  # Для хранения соединений по потокам
        self._init_database()

    def _init_database(self):
        """Инициализация базы данных и создание таблиц"""
        try:
            # Создаем соединение для инициализации
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Таблица для слов и их переводов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS dictionary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_word TEXT NOT NULL,
                    source_lang TEXT NOT NULL,
                    target_word TEXT NOT NULL,
                    target_lang TEXT NOT NULL,
                    pos_tag TEXT,
                    pos_explanation TEXT,
                    domain TEXT,
                    frequency INTEGER DEFAULT 0,
                    last_used TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(source_word, target_lang, domain)
                )
            ''')

            # Таблица для истории переводов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS translation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_text TEXT NOT NULL,
                    translated_text TEXT NOT NULL,
                    source_lang TEXT NOT NULL,
                    target_lang TEXT NOT NULL,
                    domain TEXT,
                    word_count INTEGER,
                    translated_count INTEGER,
                    translation_time REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Таблица для синтаксических деревьев
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS syntax_trees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sentence TEXT NOT NULL,
                    tree_json TEXT NOT NULL,
                    parse_time REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Таблица для частотных списков
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS frequency_lists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text_hash TEXT NOT NULL,
                    word TEXT NOT NULL,
                    frequency INTEGER NOT NULL,
                    percentage REAL,
                    pos_tag TEXT,
                    translation_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (translation_id) REFERENCES dictionary(id)
                )
            ''')

            # Таблица для пользовательских настроек
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    setting_key TEXT UNIQUE NOT NULL,
                    setting_value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Индексы для ускорения поиска
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_dictionary_source ON dictionary(source_word, target_lang)')
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_history_lang ON translation_history(source_lang, target_lang)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_frequency_hash ON frequency_lists(text_hash, word)')

            conn.commit()
            conn.close()
            logger.info(f"База данных инициализирована: {self.db_path}")

        except sqlite3.Error as e:
            logger.error(f"Ошибка при инициализации базы данных: {e}")
            raise

    def get_connection(self):
        """Получает соединение с базой данных для текущего потока"""
        thread_id = threading.current_thread().ident
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(self.db_path)
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection

    def add_word_to_dictionary(self,
                               source_word: str,
                               target_word: str,
                               source_lang: str = 'en',
                               target_lang: str = 'ru',
                               pos_tag: str = None,
                               pos_explanation: str = None,
                               domain: str = 'general') -> bool:
        """
        Добавляет слово и его перевод в словарь

        Args:
            source_word: Исходное слово
            target_word: Перевод
            source_lang: Исходный язык
            target_lang: Целевой язык
            pos_tag: Часть речи (может быть None)
            pos_explanation: Расшифровка части речи (может быть None)
            domain: Предметная область

        Returns:
            True если добавлено успешно, иначе False
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Проверяем, существует ли уже такая запись
            cursor.execute('''
                SELECT id, frequency FROM dictionary 
                WHERE source_word = ? AND target_lang = ? AND domain = ?
            ''', (source_word.lower(), target_lang, domain))

            existing = cursor.fetchone()

            if existing:
                # Обновляем частоту и время использования
                new_frequency = existing['frequency'] + 1
                cursor.execute('''
                    UPDATE dictionary 
                    SET frequency = ?, last_used = CURRENT_TIMESTAMP,
                        target_word = ?, pos_tag = ?, pos_explanation = ?
                    WHERE id = ?
                ''', (new_frequency, target_word, pos_tag, pos_explanation, existing['id']))
            else:
                # Добавляем новую запись
                cursor.execute('''
                    INSERT INTO dictionary 
                    (source_word, source_lang, target_word, target_lang, 
                     pos_tag, pos_explanation, domain, frequency, last_used)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
                ''', (source_word.lower(), source_lang, target_word, target_lang,
                      pos_tag, pos_explanation, domain))

            conn.commit()
            logger.info(f"Добавлено в словарь: '{source_word}' -> '{target_word}'")
            return True

        except sqlite3.Error as e:
            logger.error(f"Ошибка при добавлении слова в словарь: {e}")
            return False

    def get_translation(self,
                        source_word: str,
                        target_lang: str = 'ru',
                        domain: str = None) -> Optional[Dict[str, Any]]:
        """
        Получает перевод слова из словаря

        Args:
            source_word: Исходное слово
            target_lang: Целевой язык
            domain: Предметная область (опционально)

        Returns:
            Словарь с информацией о переводе или None
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            if domain:
                # Ищем с учетом предметной области
                cursor.execute('''
                    SELECT * FROM dictionary 
                    WHERE source_word = ? AND target_lang = ? AND domain = ?
                    ORDER BY frequency DESC
                    LIMIT 1
                ''', (source_word.lower(), target_lang, domain))
            else:
                # Ищем без учета предметной области
                cursor.execute('''
                    SELECT * FROM dictionary 
                    WHERE source_word = ? AND target_lang = ?
                    ORDER BY frequency DESC
                    LIMIT 1
                ''', (source_word.lower(), target_lang))

            result = cursor.fetchone()

            if result:
                # Обновляем частоту использования
                cursor.execute('''
                    UPDATE dictionary 
                    SET frequency = frequency + 1, last_used = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (result['id'],))
                conn.commit()

                return dict(result)

            return None

        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении перевода: {e}")
            return None

    def save_translation_history(self,
                                 source_text: str,
                                 translated_text: str,
                                 source_lang: str = 'en',
                                 target_lang: str = 'ru',
                                 domain: str = None,
                                 word_count: int = 0,
                                 translated_count: int = 0,
                                 translation_time: float = 0.0) -> int:
        """
        Сохраняет историю перевода

        Returns:
            ID сохраненной записи
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO translation_history 
                (source_text, translated_text, source_lang, target_lang, 
                 domain, word_count, translated_count, translation_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (source_text, translated_text, source_lang, target_lang,
                  domain, word_count, translated_count, translation_time))

            record_id = cursor.lastrowid
            conn.commit()

            logger.info(f"Сохранена история перевода ID: {record_id}")
            return record_id

        except sqlite3.Error as e:
            logger.error(f"Ошибка при сохранении истории перевода: {e}")
            return -1

    def save_frequency_list(self,
                            text_hash: str,
                            frequency_list: List[Dict[str, Any]]) -> bool:
        """
        Сохраняет частотный список слов

        Args:
            text_hash: Хэш исходного текста
            frequency_list: Список частот слов

        Returns:
            True если успешно, иначе False
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Удаляем старые записи для этого хэша
            cursor.execute('DELETE FROM frequency_lists WHERE text_hash = ?', (text_hash,))

            # Добавляем новые записи
            for item in frequency_list:
                word = item.get('word', '')
                frequency = item.get('frequency', 0)
                percentage = item.get('percentage', 0.0)
                pos_tag = item.get('pos_tag', '')

                # Ищем ID перевода в словаре
                translation = self.get_translation(word)
                translation_id = translation['id'] if translation else None

                cursor.execute('''
                    INSERT INTO frequency_lists 
                    (text_hash, word, frequency, percentage, pos_tag, translation_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (text_hash, word, frequency, percentage, pos_tag, translation_id))

            conn.commit()
            logger.info(f"Сохранен частотный список для хэша: {text_hash}")
            return True

        except sqlite3.Error as e:
            logger.error(f"Ошибка при сохранении частотного списка: {e}")
            return False

    def save_syntax_tree(self,
                         sentence: str,
                         tree_data: Dict[str, Any]) -> int:
        """
        Сохраняет синтаксическое дерево

        Returns:
            ID сохраненной записи
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            tree_json = json.dumps(tree_data, ensure_ascii=False)
            parse_time = tree_data.get('parse_time', 0.0)

            cursor.execute('''
                INSERT INTO syntax_trees (sentence, tree_json, parse_time)
                VALUES (?, ?, ?)
            ''', (sentence, tree_json, parse_time))

            record_id = cursor.lastrowid
            conn.commit()

            logger.info(f"Сохранено синтаксическое дерево ID: {record_id}")
            return record_id

        except sqlite3.Error as e:
            logger.error(f"Ошибка при сохранении синтаксического дерева: {e}")
            return -1

    def get_translation_history(self,
                                limit: int = 50,
                                source_lang: str = None,
                                target_lang: str = None) -> List[Dict[str, Any]]:
        """
        Получает историю переводов

        Args:
            limit: Максимальное количество записей
            source_lang: Фильтр по исходному языку
            target_lang: Фильтр по целевому языку

        Returns:
            Список записей истории
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            query = 'SELECT * FROM translation_history'
            params = []

            conditions = []
            if source_lang:
                conditions.append('source_lang = ?')
                params.append(source_lang)
            if target_lang:
                conditions.append('target_lang = ?')
                params.append(target_lang)

            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)

            query += ' ORDER BY created_at DESC LIMIT ?'
            params.append(limit)

            cursor.execute(query, params)
            results = cursor.fetchall()

            return [dict(row) for row in results]

        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении истории переводов: {e}")
            return []

    def search_dictionary(self,
                          search_term: str,
                          search_in_source: bool = True,
                          search_in_target: bool = False,
                          domain: str = None,
                          limit: int = 100) -> List[Dict[str, Any]]:
        """
        Поиск в словаре

        Args:
            search_term: Термин для поиска
            search_in_source: Искать в исходных словах
            search_in_target: Искать в переводах
            domain: Фильтр по предметной области
            limit: Максимальное количество результатов

        Returns:
            Список найденных записей
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            search_pattern = f'%{search_term.lower()}%'

            # Базовый запрос
            query = 'SELECT * FROM dictionary WHERE '
            params = []
            conditions = []

            # Построение условий для поиска
            if search_in_source and search_in_target:
                conditions.append('(source_word LIKE ? OR target_word LIKE ?)')
                params.append(search_pattern)
                params.append(search_pattern)
            elif search_in_source:
                conditions.append('source_word LIKE ?')
                params.append(search_pattern)
            elif search_in_target:
                conditions.append('target_word LIKE ?')
                params.append(search_pattern)
            else:
                # Если оба флага False, ищем везде
                conditions.append('(source_word LIKE ? OR target_word LIKE ?)')
                params.append(search_pattern)
                params.append(search_pattern)

            # Добавляем условие по домену
            if domain:
                conditions.append('domain = ?')
                params.append(domain)

            # Объединяем условия
            if conditions:
                query += ' AND '.join(conditions)
            else:
                # Если нет условий, убираем WHERE
                query = 'SELECT * FROM dictionary'

            # Добавляем сортировку и ограничение
            query += ' ORDER BY frequency DESC, last_used DESC LIMIT ?'
            params.append(limit)

            cursor.execute(query, params)
            results = cursor.fetchall()

            return [dict(row) for row in results]

        except sqlite3.Error as e:
            logger.error(f"Ошибка при поиске в словаре: {e}")
            import traceback
            logger.error(f"Стек вызовов: {traceback.format_exc()}")
            return []

    def get_dictionary_stats(self) -> Dict[str, Any]:
        """
        Получает статистику словаря

        Returns:
            Словарь со статистикой
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            stats = {}

            # Общее количество слов
            cursor.execute('SELECT COUNT(*) as count FROM dictionary')
            result = cursor.fetchone()
            stats['total_words'] = result['count'] if result else 0

            # Количество по языкам
            cursor.execute('SELECT target_lang, COUNT(*) as count FROM dictionary GROUP BY target_lang')
            stats['by_language'] = {row['target_lang']: row['count'] for row in cursor.fetchall()}

            # Количество по предметным областям
            cursor.execute('SELECT domain, COUNT(*) as count FROM dictionary GROUP BY domain')
            stats['by_domain'] = {row['domain']: row['count'] for row in cursor.fetchall()}

            # Самые частые слова
            cursor.execute('SELECT source_word, frequency FROM dictionary ORDER BY frequency DESC LIMIT 10')
            stats['top_words'] = [{'source_word': row['source_word'], 'frequency': row['frequency']}
                                  for row in cursor.fetchall()]

            # Обновляем статистику в настройках
            self._update_statistics_in_settings(stats)

            return stats

        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении статистики словаря: {e}")
            return {}

    def _update_statistics_in_settings(self, stats: Dict[str, Any]):
        """Обновляет статистику в таблице настроек"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            stats_json = json.dumps(stats, ensure_ascii=False)

            cursor.execute('''
                INSERT OR REPLACE INTO user_settings (setting_key, setting_value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', ('dictionary_stats', stats_json))

            conn.commit()

        except sqlite3.Error as e:
            logger.error(f"Ошибка при обновлении статистики: {e}")

    def export_dictionary(self,
                          filepath: str,
                          format: str = 'json') -> bool:
        """
        Экспортирует словарь в файл

        Args:
            filepath: Путь к файлу
            format: Формат экспорта (json, csv, txt)

        Returns:
            True если успешно, иначе False
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Получаем все записи словаря
            cursor.execute('SELECT * FROM dictionary ORDER BY source_word')
            rows = cursor.fetchall()
            data = [dict(row) for row in rows]

            if format.lower() == 'json':
                import json
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

            elif format.lower() == 'csv':
                import csv
                if data:
                    with open(filepath, 'w', encoding='utf-8', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=data[0].keys())
                        writer.writeheader()
                        writer.writerows(data)

            elif format.lower() == 'txt':
                with open(filepath, 'w', encoding='utf-8') as f:
                    for item in data:
                        line = f"{item['source_word']} -> {item['target_word']} "
                        line += f"[{item['pos_tag'] or ''}] "
                        line += f"({item['domain']}) "
                        line += f"использовано: {item['frequency']} раз\n"
                        f.write(line)

            logger.info(f"Словарь экспортирован в {filepath} ({len(data)} записей)")
            return True

        except Exception as e:
            logger.error(f"Ошибка при экспорте словаря: {e}")
            return False

    def import_dictionary(self, filepath: str, format: str = 'json') -> bool:
        """
        Импортирует словарь из файла

        Args:
            filepath: Путь к файлу
            format: Формат импорта

        Returns:
            True если успешно, иначе False
        """
        try:
            if format.lower() == 'json':
                import json
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)

            elif format.lower() == 'csv':
                import csv
                with open(filepath, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    data = list(reader)

            else:
                logger.error(f"Неподдерживаемый формат: {format}")
                return False

            # Импортируем данные
            imported_count = 0
            for item in data:
                success = self.add_word_to_dictionary(
                    source_word=item.get('source_word', ''),
                    target_word=item.get('target_word', ''),
                    source_lang=item.get('source_lang', 'en'),
                    target_lang=item.get('target_lang', 'ru'),
                    pos_tag=item.get('pos_tag'),
                    pos_explanation=item.get('pos_explanation'),
                    domain=item.get('domain', 'general')
                )
                if success:
                    imported_count += 1

            logger.info(f"Импортировано {imported_count} записей из {filepath}")
            return True

        except Exception as e:
            logger.error(f"Ошибка при импорте словаря: {e}")
            return False

    def backup_database(self, backup_path: str = None) -> bool:
        """
        Создает резервную копию базы данных

        Args:
            backup_path: Путь для сохранения бэкапа

        Returns:
            True если успешно, иначе False
        """
        try:
            if backup_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"{self.db_path}.backup_{timestamp}"

            # Создаем соединение для бэкапа
            conn = self.get_connection()
            backup_conn = sqlite3.connect(backup_path)
            conn.backup(backup_conn)
            backup_conn.close()

            logger.info(f"Создана резервная копия базы данных: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"Ошибка при создании резервной копии: {e}")
            return False

    def close(self):
        """Закрывает соединение с базой данных"""
        # Закрываем соединение для текущего потока
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            logger.info(f"Соединение с базой данных закрыто для потока {threading.current_thread().ident}")

    def __enter__(self):
        """Контекстный менеджер для работы с базой данных"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Завершение работы контекстного менеджера"""
        self.close()


# Создаем синглтон экземпляр базы данных для удобства использования
_db_instance = None


def get_database() -> DatabaseManager:
    """
    Получает экземпляр базы данных (синглтон)

    Returns:
        Экземпляр DatabaseManager
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager()
    return _db_instance