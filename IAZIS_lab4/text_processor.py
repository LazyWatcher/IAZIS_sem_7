"""
Модуль обработки текста и грамматического анализа
"""

import re
import string
from typing import List, Dict, Tuple, Any, Optional
from collections import Counter, defaultdict
import nltk
from nltk import pos_tag, word_tokenize
from nltk.tree import Tree
from nltk.chunk import conlltags2tree, tree2conlltags
import nltk.data

from config import Config
from utils import logger, clean_text


class TextProcessor:
    """Класс для обработки текста и грамматического анализа"""

    def __init__(self):
        """Инициализация обработчика текста"""
        self._download_nltk_resources()
        self._initialize_grammar_tags()

    def _download_nltk_resources(self):
        """Загружает необходимые ресурсы NLTK"""
        required_resources = [
            'punkt',
            'averaged_perceptron_tagger',
            'maxent_ne_chunker',
            'words'
        ]

        for resource in required_resources:
            try:
                nltk.data.find(f'tokenizers/{resource}' if resource == 'punkt' else f'taggers/{resource}'
                if resource == 'averaged_perceptron_tagger' else f'chunkers/{resource}'
                if resource == 'maxent_ne_chunker' else f'corpora/{resource}')
            except LookupError:
                print(f"Загрузка ресурса NLTK: {resource}...")
                nltk.download(resource, quiet=True)

    def _initialize_grammar_tags(self):
        """Инициализация словаря грамматических тегов"""
        # Расшифровка POS-тегов NLTK для английского языка
        self.pos_tags_explanation = {
            'CC': 'сочинительный союз',
            'CD': 'числительное',
            'DT': 'определитель',
            'EX': 'экзистенциальное there',
            'FW': 'иностранное слово',
            'IN': 'предлог или подчинительный союз',
            'JJ': 'прилагательное',
            'JJR': 'прилагательное в сравнительной степени',
            'JJS': 'прилагательное в превосходной степени',
            'LS': 'маркер списка',
            'MD': 'модальный глагол',
            'NN': 'существительное, единственное число',
            'NNS': 'существительное, множественное число',
            'NNP': 'имя собственное, единственное число',
            'NNPS': 'имя собственное, множественное число',
            'PDT': 'предопределитель',
            'POS': 'притяжательное окончание',
            'PRP': 'личное местоимение',
            'PRP$': 'притяжательное местоимение',
            'RB': 'наречие',
            'RBR': 'наречие в сравнительной степени',
            'RBS': 'наречие в превосходной степени',
            'RP': 'частица',
            'SYM': 'символ',
            'TO': 'to',
            'UH': 'междометие',
            'VB': 'глагол, базовая форма',
            'VBD': 'глагол, прошедшее время',
            'VBG': 'глагол, герундий/причастие настоящего времени',
            'VBN': 'глагол, причастие прошедшего времени',
            'VBP': 'глагол, настоящее время, не 3-е лицо единственное число',
            'VBZ': 'глагол, настоящее время, 3-е лицо единственное число',
            'WDT': 'wh-определитель',
            'WP': 'wh-местоимение',
            'WP$': 'притяжательное wh-местоимение',
            'WRB': 'wh-наречие'
        }

        # Теги для русского языка (упрощенные)
        self.russian_pos_tags = {
            'S': 'существительное',
            'A': 'прилагательное',
            'V': 'глагол',
            'ADV': 'наречие',
            'PR': 'предлог',
            'CONJ': 'союз',
            'PART': 'частица',
            'INTJ': 'междометие',
            'NUM': 'числительное',
            'NPRO': 'местоимение'
        }

    def preprocess_text(self, text: str) -> Dict[str, Any]:
        """
        Предварительная обработка текста

        Args:
            text: Исходный текст

        Returns:
            Словарь с обработанным текстом и метаданными
        """
        if not text:
            return {
                'original': '',
                'cleaned': '',
                'tokens': [],
                'sentences': [],
                'word_count': 0
            }

        # Очищаем текст
        cleaned_text = clean_text(text)

        # Разбиваем на предложения
        sentences = self._split_into_sentences(cleaned_text)

        # Токенизируем слова
        tokens = self._tokenize_words(cleaned_text)

        return {
            'original': text,
            'cleaned': cleaned_text,
            'tokens': tokens,
            'sentences': sentences,
            'word_count': len(tokens),
            'sentence_count': len(sentences)
        }

    def _split_into_sentences(self, text: str) -> List[str]:
        """Разбивает текст на предложения"""
        if not text:
            return []

        try:
            # Используем NLTK для английского языка
            sent_detector = nltk.data.load('tokenizers/punkt/english.pickle')
            sentences = sent_detector.tokenize(text)
            return [s.strip() for s in sentences if s.strip()]
        except:
            # Простая разбивка по знакам препинания
            sentences = re.split(r'(?<=[.!?])\s+', text)
            return [s.strip() for s in sentences if s.strip()]

    def _tokenize_words(self, text: str) -> List[str]:
        """Токенизирует текст на слова"""
        if not text:
            return []

        try:
            # Используем NLTK токенизатор
            tokens = word_tokenize(text)
            # Убираем чисто знаки препинания
            tokens = [token for token in tokens if token not in string.punctuation]
            return tokens
        except:
            # Простая токенизация
            words = re.findall(r'\b\w+\b', text.lower())
            return words

    def analyze_grammar(self, text: str) -> Dict[str, Any]:
        """
        Грамматический анализ текста

        Args:
            text: Текст для анализа

        Returns:
            Словарь с грамматической информацией
        """
        if not text:
            return {
                'pos_tags': [],
                'tag_counts': {},
                'word_info': []
            }

        try:
            # Токенизация и определение частей речи
            tokens = word_tokenize(text)
            pos_tags_result = pos_tag(tokens)  # ← Изменяем имя переменной

            # Подсчет тегов
            tag_counts = Counter(tag for word, tag in pos_tags_result)

            # Создаем подробную информацию о словах
            word_info = []
            for word, tag in pos_tags_result:
                word_info.append({
                    'word': word,
                    'pos_tag': tag,
                    'pos_explanation': self.pos_tags_explanation.get(tag, 'неизвестно'),
                    'is_punctuation': word in string.punctuation,
                    'length': len(word)
                })

            return {
                'pos_tags': pos_tags_result,
                'tag_counts': dict(tag_counts),
                'word_info': word_info,
                'total_words': len(tokens),
                'unique_words': len(set(tokens))
            }

        except Exception as e:
            logger.error(f"Ошибка при грамматическом анализе: {e}")
            return {
                'pos_tags': [],
                'tag_counts': {},
                'word_info': [],
                'error': str(e)
            }


    def calculate_word_frequencies(self, text: str) -> List[Dict[str, Any]]:
        """
        Рассчитывает частоту слов в тексте

        Args:
            text: Текст для анализа

        Returns:
            Список словарей с информацией о словах, отсортированный по частоте
        """
        if not text:
            return []

        # Токенизируем текст
        tokens = self._tokenize_words(text)

        if not tokens:
            return []

        # Подсчитываем частоту
        frequency = Counter(tokens)

        # Сортируем по убыванию частоты
        sorted_freq = sorted(frequency.items(), key=lambda x: x[1], reverse=True)

        # Пробуем получить POS-теги
        try:
            pos_tags_dict = dict(pos_tag(tokens))
        except Exception as e:
            # Если не получается, создаем пустой словарь
            pos_tags_dict = {}
            logger.warning(f"Не удалось получить POS-теги: {e}")

        result = []
        for word, count in sorted_freq:
            # Получаем тег части речи
            current_pos_tag = pos_tags_dict.get(word, 'UNKNOWN')

            # Получаем объяснение тега
            pos_explanation_value = self.pos_tags_explanation.get(current_pos_tag, 'неизвестно')

            result.append({
                'word': word,
                'frequency': count,
                'percentage': round(count / len(tokens) * 100, 2),
                'pos_tag': current_pos_tag,  # ← Используем новое имя переменной
                'pos_explanation': pos_explanation_value
            })

        return result

    def parse_sentence_syntax(self, sentence: str) -> Optional[Dict[str, Any]]:
        """
        Синтаксический разбор предложения

        Args:
            sentence: Предложение для разбора

        Returns:
            Словарь с информацией о синтаксическом дереве
        """
        if not sentence:
            return None

        try:
            # Токенизация и определение частей речи
            tokens = word_tokenize(sentence)
            pos_tags = pos_tag(tokens)

            # Создаем дерево разбора (упрощенное)
            # В реальной системе можно использовать более сложные парсеры
            grammar = r"""
                NP: {<DT|JJ|NN.*>+}          # Именная группа
                PP: {<IN><NP>}               # Предложная группа
                VP: {<VB.*><NP|PP>*}         # Глагольная группа
            """

            chunk_parser = nltk.RegexpParser(grammar)
            parsed_tree = chunk_parser.parse(pos_tags)

            # Преобразуем дерево в строку
            tree_str = str(parsed_tree)

            # Преобразуем в формат для отображения
            tree_diagram = self._format_tree_diagram(parsed_tree)

            # Извлекаем фразы
            phrases = self._extract_phrases(parsed_tree)

            return {
                'sentence': sentence,
                'tokens': tokens,
                'pos_tags': pos_tags,
                'tree_string': tree_str,
                'tree_diagram': tree_diagram,
                'phrases': phrases,
                'depth': parsed_tree.height() if hasattr(parsed_tree, 'height') else 0
            }

        except Exception as e:
            logger.error(f"Ошибка при синтаксическом разборе: {e}")
            return {
                'sentence': sentence,
                'error': str(e),
                'tree_diagram': f"Ошибка разбора: {e}"
            }

    def _format_tree_diagram(self, tree) -> str:
        """Форматирует дерево для отображения"""
        if isinstance(tree, str):
            return tree

        try:
            # Используем метод draw для создания ASCII-диаграммы
            # В реальном приложении можно использовать графическую визуализацию
            result = []
            self._print_tree(tree, result, level=0)
            return "\n".join(result)
        except:
            return str(tree)

    def _print_tree(self, tree, result, level=0):
        """Рекурсивно печатает дерево"""
        if isinstance(tree, Tree):
            result.append("  " * level + f"[{tree.label()}]")
            for child in tree:
                self._print_tree(child, result, level + 1)
        else:
            result.append("  " * level + f"{tree[0]}/{tree[1]}")

    def _extract_phrases(self, tree) -> Dict[str, List[str]]:
        """Извлекает фразы из дерева разбора"""
        phrases = defaultdict(list)

        if isinstance(tree, Tree):
            if tree.label() in ['NP', 'VP', 'PP']:
                # Извлекаем слова из фразы
                words = []
                for leaf in tree.leaves():
                    if isinstance(leaf, tuple):
                        words.append(leaf[0])
                    else:
                        words.append(str(leaf))

                if words:
                    phrases[tree.label()].append(" ".join(words))

            # Рекурсивно обрабатываем дочерние узлы
            for child in tree:
                if isinstance(child, Tree):
                    child_phrases = self._extract_phrases(child)
                    for label, phrase_list in child_phrases.items():
                        phrases[label].extend(phrase_list)

        return dict(phrases)

    def get_word_statistics(self, text: str) -> Dict[str, Any]:
        """
        Получает статистику по словам в тексте

        Args:
            text: Текст для анализа

        Returns:
            Словарь со статистикой
        """
        if not text:
            return {}

        tokens = self._tokenize_words(text)

        if not tokens:
            return {}

        # Подсчитываем различные метрики
        word_lengths = [len(word) for word in tokens]

        return {
            'total_words': len(tokens),
            'unique_words': len(set(tokens)),
            'avg_word_length': sum(word_lengths) / len(word_lengths) if word_lengths else 0,
            'max_word_length': max(word_lengths) if word_lengths else 0,
            'min_word_length': min(word_lengths) if word_lengths else 0,
            'lexical_diversity': len(set(tokens)) / len(tokens) if tokens else 0,
            'most_common_words': Counter(tokens).most_common(5)
        }

    def prepare_translation_output(self,
                                   source_text: str,
                                   translated_text: str,
                                   frequency_list: List[Dict[str, Any]]) -> str:
        """
        Подготавливает форматированный вывод для сохранения

        Args:
            source_text: Исходный текст
            translated_text: Переведенный текст
            frequency_list: Список частот слов

        Returns:
            Форматированная строка для сохранения
        """
        output = []
        output.append("=" * 60)
        output.append("РЕЗУЛЬТАТЫ ПЕРЕВОДА")
        output.append("=" * 60)
        output.append("")

        # Исходный текст
        output.append("ИСХОДНЫЙ ТЕКСТ:")
        output.append("-" * 40)
        output.append(source_text)
        output.append("")

        # Переведенный текст
        output.append("ПЕРЕВЕДЕННЫЙ ТЕКСТ:")
        output.append("-" * 40)
        output.append(translated_text)
        output.append("")

        # Статистика
        source_stats = self.get_word_statistics(source_text)
        trans_stats = self.get_word_statistics(translated_text)

        output.append("СТАТИСТИКА:")
        output.append("-" * 40)
        output.append(f"Исходный текст: {source_stats.get('total_words', 0)} слов, "
                      f"{source_stats.get('unique_words', 0)} уникальных")
        output.append(f"Переведенный текст: {trans_stats.get('total_words', 0)} слов, "
                      f"{trans_stats.get('unique_words', 0)} уникальных")
        output.append("")

        # Частотный список
        output.append("ЧАСТОТНЫЙ СПИСОК СЛОВ (топ-20):")
        output.append("-" * 40)
        output.append(f"{'Слово':<20} {'Частота':<10} {'%':<10} {'Часть речи':<30}")
        output.append("-" * 70)

        for i, item in enumerate(frequency_list[:20]):
            word = item.get('word', '')
            freq = item.get('frequency', 0)
            perc = item.get('percentage', 0)
            pos_exp = item.get('pos_explanation', '')

            # Обрезаем слишком длинные слова
            if len(word) > 18:
                word = word[:15] + "..."

            output.append(f"{word:<20} {freq:<10} {perc:<10.2f} {pos_exp:<30}")

        output.append("")

        # Грамматическая информация
        output.append("ГРАММАТИЧЕСКАЯ ИНФОРМАЦИЯ:")
        output.append("-" * 40)
        grammar_info = self.analyze_grammar(source_text)
        tag_counts = grammar_info.get('tag_counts', {})

        for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True):
            explanation = self.pos_tags_explanation.get(tag, 'неизвестно')
            output.append(f"{tag}: {explanation} - {count}")

        return "\n".join(output)