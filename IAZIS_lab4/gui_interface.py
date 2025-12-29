"""
Модуль графического интерфейса системы перевода
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
from datetime import datetime
from typing import Optional, Callable, Dict, Any, List
import hashlib
import os

from config import Config
from text_processor import TextProcessor
from translation_module import TranslationModule
from database import get_database
from utils import logger, save_to_file

class TranslationApp:
    """Графический интерфейс системы машинного перевода"""

    def __init__(self, translator: TranslationModule, processor: TextProcessor):
        """
        Инициализация приложения

        Args:
            translator: Модуль перевода
            processor: Модуль обработки текста
        """
        self.translator = translator
        self.processor = processor
        self.db = get_database()

        # Текущие данные
        self.current_translation: Optional[Dict[str, Any]] = None
        self.current_frequency_list: List[Dict[str, Any]] = []
        self.current_syntax_tree: Optional[Dict[str, Any]] = None

        # Создаем главное окно
        self.root = tk.Tk()
        self.root.title("Система машинного перевода текстов")
        self.root.geometry("1200x800")

        # Настройка стилей
        self._setup_styles()

        # Создаем интерфейс
        self._create_menu()
        self._create_main_frame()
        self._create_status_bar()

        # Настройка горячих клавиш
        self._setup_keyboard_shortcuts()

        # Устанавливаем обработчики событий
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _setup_styles(self):
        """Настройка стилей интерфейса"""
        style = ttk.Style()
        style.theme_use('clam')

        # Настраиваем цвета
        self.root.configure(bg='#f0f0f0')

        # Настраиваем стили для виджетов
        style.configure('Title.TLabel',
                       font=('Helvetica', 14, 'bold'),
                       background='#f0f0f0')

        style.configure('Header.TLabel',
                       font=('Helvetica', 11, 'bold'),
                       background='#f0f0f0')

        style.configure('Status.TLabel',
                       font=('Helvetica', 9),
                       background='#e0e0e0')

    def _create_menu(self):
        """Создает меню приложения"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # Меню "Файл"
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Открыть файл...", command=self._open_file)
        file_menu.add_command(label="Сохранить результаты...", command=self._save_results)
        file_menu.add_separator()
        file_menu.add_command(label="Экспорт словаря...", command=self._export_dictionary)
        file_menu.add_command(label="Импорт словаря...", command=self._import_dictionary)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self._on_closing)

        # Меню "Настройки"
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Настройки", menu=settings_menu)
        settings_menu.add_command(label="Настройки перевода...", command=self._open_settings)
        settings_menu.add_command(label="Очистить кэш", command=self._clear_cache)

        # Меню "Справка"
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Справка", menu=help_menu)
        help_menu.add_command(label="О программе", command=self._show_about)
        help_menu.add_command(label="Документация", command=self._show_help)

    def _create_main_frame(self):
        """Создает основную область интерфейса"""
        # Создаем Notebook для вкладок
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Вкладка 1: Перевод и частотный анализ
        self._create_translation_tab()

        # Вкладка 2: Синтаксический анализ
        self._create_syntax_tab()

        # Вкладка 3: Словарь
        self._create_dictionary_tab()

        # Вкладка 4: История
        self._create_history_tab()

    def _create_translation_tab(self):
        """Создает вкладку для перевода и частотного анализа"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Перевод")

        # Панель с кнопкой перевода
        button_frame = ttk.Frame(frame, padding=10)
        button_frame.pack(fill=tk.X, padx=5, pady=5)

        # Кнопка перевода
        self.translate_btn = ttk.Button(button_frame, text="Перевести текст",
                                       command=self._translate_text)
        self.translate_btn.pack(side=tk.LEFT, padx=5)

        # Область для исходного текста
        input_frame = ttk.LabelFrame(frame, text="Исходный текст (английский)", padding=10)
        input_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.input_text = scrolledtext.ScrolledText(input_frame, wrap=tk.WORD,
                                                   height=10, font=('Arial', 10))
        self.input_text.pack(fill=tk.BOTH, expand=True)

        # Область для переведенного текста
        output_frame = ttk.LabelFrame(frame, text="Переведенный текст (русский)", padding=10)
        output_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD,
                                                    height=10, font=('Arial', 10),
                                                    state='disabled')
        self.output_text.pack(fill=tk.BOTH, expand=True)

        # Область для статистики
        stats_frame = ttk.LabelFrame(frame, text="Статистика", padding=10)
        stats_frame.pack(fill=tk.X, padx=5, pady=5)

        self.stats_label = ttk.Label(stats_frame, text="Слов: 0 | Уникальных: 0")
        self.stats_label.pack(side=tk.LEFT, padx=5)

        # Таблица частотного анализа
        freq_frame = ttk.LabelFrame(frame, text="Частотный анализ слов", padding=10)
        freq_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Создаем Treeview для отображения частот
        columns = ('word', 'frequency', 'percentage', 'pos', 'translation')
        self.freq_tree = ttk.Treeview(freq_frame, columns=columns, show='headings')

        # Настраиваем колонки
        self.freq_tree.heading('word', text='Слово')
        self.freq_tree.heading('frequency', text='Частота')
        self.freq_tree.heading('percentage', text='%')
        self.freq_tree.heading('pos', text='Часть речи')
        self.freq_tree.heading('translation', text='Перевод')

        self.freq_tree.column('word', width=150)
        self.freq_tree.column('frequency', width=80)
        self.freq_tree.column('percentage', width=60)
        self.freq_tree.column('pos', width=150)
        self.freq_tree.column('translation', width=200)

        # Добавляем прокрутку
        scrollbar = ttk.Scrollbar(freq_frame, orient=tk.VERTICAL, command=self.freq_tree.yview)
        self.freq_tree.configure(yscrollcommand=scrollbar.set)

        self.freq_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _create_syntax_tab(self):
        """Создает вкладку для синтаксического анализа"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Синтаксический анализ")

        # Область для ввода предложения
        input_frame = ttk.LabelFrame(frame, text="Предложение для анализа", padding=10)
        input_frame.pack(fill=tk.X, padx=5, pady=5)

        self.sentence_entry = ttk.Entry(input_frame, font=('Arial', 11))
        self.sentence_entry.pack(fill=tk.X, expand=True, padx=5, pady=5)

        # Кнопка анализа
        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        self.analyze_btn = ttk.Button(btn_frame, text="Анализировать",
                                     command=self._analyze_syntax)
        self.analyze_btn.pack(side=tk.LEFT, padx=5)

        # Область для отображения дерева
        tree_frame = ttk.LabelFrame(frame, text="Дерево синтаксического разбора", padding=10)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.tree_display = scrolledtext.ScrolledText(tree_frame, wrap=tk.WORD,
                                                     font=('Courier', 10))
        self.tree_display.pack(fill=tk.BOTH, expand=True)

        # Область для информации о фразах
        phrases_frame = ttk.LabelFrame(frame, text="Выделенные фразы", padding=10)
        phrases_frame.pack(fill=tk.X, padx=5, pady=5)

        self.phrases_text = scrolledtext.ScrolledText(phrases_frame, wrap=tk.WORD,
                                                     height=5, font=('Arial', 10))
        self.phrases_text.pack(fill=tk.X)

    def _create_dictionary_tab(self):
        """Создает вкладку для работы со словарем"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Словарь")

        # Панель поиска
        search_frame = ttk.LabelFrame(frame, text="Поиск в словаре", padding=10)
        search_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(search_frame, text="Поиск:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.search_entry = ttk.Entry(search_frame, width=30)
        self.search_entry.grid(row=0, column=1, sticky=tk.W, padx=5)

        self.search_in_source = tk.BooleanVar(value=True)
        self.search_in_target = tk.BooleanVar(value=False)

        ttk.Checkbutton(search_frame, text="В исходных",
                       variable=self.search_in_source).grid(row=0, column=2, padx=5)
        ttk.Checkbutton(search_frame, text="В переводах",
                       variable=self.search_in_target).grid(row=0, column=3, padx=5)

        self.search_btn = ttk.Button(search_frame, text="Найти",
                                    command=self._search_dictionary)
        self.search_btn.grid(row=0, column=4, padx=10)

        # Кнопка добавления в словарь
        self.add_to_dict_btn = ttk.Button(search_frame, text="Добавить в словарь",
                                         command=self._open_add_dialog)
        self.add_to_dict_btn.grid(row=0, column=5, padx=5)

        # Таблица словаря
        dict_frame = ttk.LabelFrame(frame, text="Словарь", padding=10)
        dict_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        columns = ('source', 'target', 'pos', 'frequency')
        self.dict_tree = ttk.Treeview(dict_frame, columns=columns, show='headings')

        # Настраиваем колонки
        self.dict_tree.heading('source', text='Исходное слово')
        self.dict_tree.heading('target', text='Перевод')
        self.dict_tree.heading('pos', text='Часть речи')
        self.dict_tree.heading('frequency', text='Использовано')

        self.dict_tree.column('source', width=150)
        self.dict_tree.column('target', width=150)
        self.dict_tree.column('pos', width=100)
        self.dict_tree.column('frequency', width=80)

        # Добавляем прокрутку
        scrollbar = ttk.Scrollbar(dict_frame, orient=tk.VERTICAL, command=self.dict_tree.yview)
        self.dict_tree.configure(yscrollcommand=scrollbar.set)

        self.dict_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Контекстное меню для словаря
        self.dict_menu = tk.Menu(self.root, tearoff=0)
        self.dict_menu.add_command(label="Удалить", command=self._delete_dictionary_entry)
        self.dict_menu.add_command(label="Редактировать", command=self._edit_dictionary_entry)

        self.dict_tree.bind("<Button-3>", self._show_dict_context_menu)

    def _create_history_tab(self):
        """Создает вкладку для истории переводов"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="История")

        # Таблица истории
        history_frame = ttk.LabelFrame(frame, text="История переводов", padding=10)
        history_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        columns = ('id', 'date', 'source_lang', 'target_lang', 'words')
        self.history_tree = ttk.Treeview(history_frame, columns=columns, show='headings')

        # Настраиваем колонки
        self.history_tree.heading('id', text='ID')
        self.history_tree.heading('date', text='Дата')
        self.history_tree.heading('source_lang', text='Из')
        self.history_tree.heading('target_lang', text='В')
        self.history_tree.heading('words', text='Слов')

        self.history_tree.column('id', width=50)
        self.history_tree.column('date', width=120)
        self.history_tree.column('source_lang', width=50)
        self.history_tree.column('target_lang', width=50)
        self.history_tree.column('words', width=60)

        # Добавляем прокрутку
        scrollbar = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)

        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Кнопка обновления истории
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        self.refresh_btn = ttk.Button(btn_frame, text="Обновить",
                                     command=self._load_history)
        self.refresh_btn.pack(side=tk.LEFT, padx=5)

        self.clear_history_btn = ttk.Button(btn_frame, text="Очистить историю",
                                           command=self._clear_history)
        self.clear_history_btn.pack(side=tk.LEFT, padx=5)

    def _create_status_bar(self):
        """Создает строку состояния"""
        self.status_bar = ttk.Label(self.root, text="Готово", relief=tk.SUNKEN,
                                   style='Status.TLabel')
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _update_status(self, message: str):
        """Обновляет строку состояния"""
        self.status_bar.config(text=message)
        self.root.update_idletasks()

    def _translate_text(self):
        """Выполняет перевод текста"""
        # Получаем текст для перевода
        source_text = self.input_text.get("1.0", tk.END).strip()

        if not source_text:
            messagebox.showwarning("Предупреждение", "Введите текст для перевода")
            return

        # Обновляем статус
        self._update_status("Перевод выполняется...")
        self.translate_btn.config(state='disabled')

        # Запускаем перевод в отдельном потоке
        thread = threading.Thread(target=self._perform_translation,
                                 args=(source_text,))
        thread.daemon = True
        thread.start()

    def _perform_translation(self, source_text: str):
        """Выполняет перевод (вызывается в отдельном потоке)"""
        try:
            # Выполняем перевод (без указания предметной области)
            result = self.translator.translate_text(source_text, 'en-ru')

            if result.get('success', False):
                # Сохраняем текущий перевод
                self.current_translation = result

                # Обрабатываем текст
                processed = self.processor.preprocess_text(source_text)
                frequency_list = self.processor.calculate_word_frequencies(source_text)
                self.current_frequency_list = frequency_list

                # Обновляем интерфейс в главном потоке
                self.root.after(0, self._update_translation_results,
                               result['translated_text'], processed, frequency_list)

                # Сохраняем в базу данных
                self._save_translation_to_db(source_text, result['translated_text'],
                                           processed, frequency_list)

                self._update_status("Перевод завершен успешно")
            else:
                error_msg = result.get('error', 'Неизвестная ошибка')
                self.root.after(0, messagebox.showerror, "Ошибка перевода", error_msg)
                self._update_status(f"Ошибка: {error_msg}")

        except Exception as e:
            logger.error(f"Ошибка при выполнении перевода: {e}")
            self.root.after(0, messagebox.showerror, "Ошибка", f"Ошибка при переводе: {str(e)}")
            self._update_status(f"Ошибка: {str(e)}")

        finally:
            # Включаем кнопку обратно
            self.root.after(0, lambda: self.translate_btn.config(state='normal'))

    def _update_translation_results(self, translated_text: str,
                                  processed: Dict[str, Any],
                                  frequency_list: List[Dict[str, Any]]):
        """Обновляет результаты перевода в интерфейсе"""
        # Обновляем переведенный текст
        self.output_text.config(state='normal')
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert("1.0", translated_text)
        self.output_text.config(state='disabled')

        # Обновляем статистику
        word_count = processed.get('word_count', 0)
        unique_words = len(set(processed.get('tokens', [])))
        self.stats_label.config(text=f"Слов: {word_count} | Уникальных: {unique_words}")

        # Обновляем таблицу частот
        self._update_frequency_table(frequency_list)

    def _update_frequency_table(self, frequency_list: List[Dict[str, Any]]):
        """Обновляет таблицу частотного анализа"""
        # Очищаем таблицу
        for item in self.freq_tree.get_children():
            self.freq_tree.delete(item)

        # Добавляем новые данные
        for item in frequency_list[:50]:  # Показываем топ-50
            word = item.get('word', '')
            frequency = item.get('frequency', 0)
            percentage = item.get('percentage', 0)
            pos = item.get('pos_explanation', '')

            # Ищем перевод в словаре
            translation_entry = self.db.get_translation(word)
            translation = translation_entry['target_word'] if translation_entry else ''

            self.freq_tree.insert('', tk.END,
                                 values=(word, frequency, f"{percentage:.2f}%", pos, translation))

    def _analyze_syntax(self):
        """Выполняет синтаксический анализ предложения"""
        sentence = self.sentence_entry.get().strip()

        if not sentence:
            messagebox.showwarning("Предупреждение", "Введите предложение для анализа")
            return

        self._update_status("Анализ синтаксиса...")
        self.analyze_btn.config(state='disabled')

        # Запускаем анализ в отдельном потоке
        thread = threading.Thread(target=self._perform_syntax_analysis,
                                 args=(sentence,))
        thread.daemon = True
        thread.start()

    def _perform_syntax_analysis(self, sentence: str):
        """Выполняет синтаксический анализ (в отдельном потоке)"""
        try:
            # Выполняем анализ
            result = self.processor.parse_sentence_syntax(sentence)

            if result:
                self.current_syntax_tree = result

                # Обновляем интерфейс
                self.root.after(0, self._update_syntax_results, result)

                # Сохраняем в базу данных
                self.db.save_syntax_tree(sentence, result)

                self._update_status("Синтаксический анализ завершен")
            else:
                self.root.after(0, messagebox.showerror, "Ошибка",
                               "Не удалось выполнить синтаксический анализ")
                self._update_status("Ошибка анализа")

        except Exception as e:
            logger.error(f"Ошибка при синтаксическом анализе: {e}")
            self.root.after(0, messagebox.showerror, "Ошибка",
                           f"Ошибка при анализе: {str(e)}")
            self._update_status(f"Ошибка: {str(e)}")

        finally:
            self.root.after(0, lambda: self.analyze_btn.config(state='normal'))

    def _update_syntax_results(self, result: Dict[str, Any]):
        """Обновляет результаты синтаксического анализа"""
        # Отображаем дерево
        self.tree_display.delete("1.0", tk.END)

        if 'tree_diagram' in result:
            self.tree_display.insert("1.0", result['tree_diagram'])
        elif 'error' in result:
            self.tree_display.insert("1.0", f"Ошибка: {result['error']}")

        # Отображаем фразы
        self.phrases_text.delete("1.0", tk.END)

        if 'phrases' in result:
            phrases = result['phrases']
            for phrase_type, phrase_list in phrases.items():
                self.phrases_text.insert(tk.END, f"{phrase_type}:\n")
                for phrase in phrase_list:
                    self.phrases_text.insert(tk.END, f"  - {phrase}\n")
                self.phrases_text.insert(tk.END, "\n")

    def _search_dictionary(self):
        """Выполняет поиск в словаре"""
        search_term = self.search_entry.get().strip()

        if not search_term:
            messagebox.showwarning("Предупреждение", "Введите поисковый запрос")
            return

        self._update_status("Поиск в словаре...")

        try:
            # Выполняем поиск
            print(f"DEBUG: Поиск слова: '{search_term}'")
            print(f"DEBUG: search_in_source: {self.search_in_source.get()}")
            print(f"DEBUG: search_in_target: {self.search_in_target.get()}")

            results = self.db.search_dictionary(
                search_term=search_term,
                search_in_source=self.search_in_source.get(),
                search_in_target=self.search_in_target.get()
            )

            print(f"DEBUG: Найдено результатов: {len(results)}")

            # Обновляем таблицу
            self._update_dictionary_table(results)

            self._update_status(f"Найдено {len(results)} записей")

        except Exception as e:
            logger.error(f"Ошибка при поиске в словаре: {e}")
            import traceback
            logger.error(f"Стек вызовов: {traceback.format_exc()}")
            messagebox.showerror("Ошибка", f"Ошибка при поиске: {str(e)}")
            self._update_status("Ошибка при поиске")

    def _update_dictionary_table(self, results: List[Dict[str, Any]]):
        """Обновляет таблицу словаря"""
        # Очищаем таблицу
        for item in self.dict_tree.get_children():
            self.dict_tree.delete(item)

        # Добавляем новые данные
        for item in results:
            self.dict_tree.insert('', tk.END,
                                values=(
                                    item.get('source_word', ''),
                                    item.get('target_word', ''),
                                    item.get('pos_explanation', ''),
                                    item.get('frequency', 0)
                                ))

    def _open_add_dialog(self):
        """Открывает диалог добавления слова в словарь"""
        # Создаем диалоговое окно
        dialog = tk.Toplevel(self.root)
        dialog.title("Добавить слово в словарь")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()

        # Поля для ввода
        ttk.Label(dialog, text="Исходное слово:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=10)
        source_entry = ttk.Entry(dialog, width=30)
        source_entry.grid(row=0, column=1, padx=10, pady=10)

        ttk.Label(dialog, text="Перевод:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=10)
        target_entry = ttk.Entry(dialog, width=30)
        target_entry.grid(row=1, column=1, padx=10, pady=10)

        ttk.Label(dialog, text="Часть речи:").grid(row=2, column=0, sticky=tk.W, padx=10, pady=10)
        pos_entry = ttk.Entry(dialog, width=30)
        pos_entry.grid(row=2, column=1, padx=10, pady=10)

        # Кнопки
        def add_word():
            source = source_entry.get().strip()
            target = target_entry.get().strip()
            pos = pos_entry.get().strip()

            if not source or not target:
                messagebox.showwarning("Предупреждение", "Заполните исходное слово и перевод")
                return

            # Добавляем в словарь
            self.db.add_word_to_dictionary(
                source_word=source,
                target_word=target,
                pos_tag=pos if pos else None,
                pos_explanation=self.processor.pos_tags_explanation.get(pos, '') if pos else ''
            )

            # Обновляем таблицу
            self._search_dictionary()

            dialog.destroy()
            messagebox.showinfo("Успех", f"Слово '{source}' добавлено в словарь")

        def cancel():
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=20)

        ttk.Button(btn_frame, text="Добавить", command=add_word).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Отмена", command=cancel).pack(side=tk.LEFT, padx=10)

    def _show_dict_context_menu(self, event):
        """Показывает контекстное меню для словаря"""
        try:
            self.dict_tree.selection_set(self.dict_tree.identify_row(event.y))
            self.dict_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.dict_menu.grab_release()

    def _delete_dictionary_entry(self):
        """Удаляет выбранную запись из словаря"""
        selected = self.dict_tree.selection()
        if not selected:
            return

        item = self.dict_tree.item(selected[0])
        word = item['values'][0]

        if messagebox.askyesno("Подтверждение", f"Удалить слово '{word}' из словаря?"):
            try:
                # Удаляем из базы данных
                cursor = self.db.connection.cursor()
                cursor.execute('DELETE FROM dictionary WHERE source_word = ?', (word,))
                self.db.connection.commit()

                # Обновляем таблицу
                self._search_dictionary()
                self._update_status(f"Слово '{word}' удалено из словаря")

            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при удалении: {str(e)}")

    def _edit_dictionary_entry(self):
        """Редактирует выбранную запись в словаре"""
        selected = self.dict_tree.selection()
        if not selected:
            return

        item = self.dict_tree.item(selected[0])
        source_word = item['values'][0]
        current_translation = item['values'][1]
        current_pos = item['values'][2]

        # Создаем диалоговое окно
        dialog = tk.Toplevel(self.root)
        dialog.title("Редактировать слово в словаре")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()

        # Поля для ввода
        ttk.Label(dialog, text="Исходное слово:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=10)
        source_label = ttk.Label(dialog, text=source_word, font=('Arial', 10, 'bold'))
        source_label.grid(row=0, column=1, padx=10, pady=10, sticky=tk.W)

        ttk.Label(dialog, text="Перевод:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=10)
        target_entry = ttk.Entry(dialog, width=30)
        target_entry.insert(0, current_translation)
        target_entry.grid(row=1, column=1, padx=10, pady=10)

        ttk.Label(dialog, text="Часть речи:").grid(row=2, column=0, sticky=tk.W, padx=10, pady=10)
        pos_entry = ttk.Entry(dialog, width=30)
        pos_entry.insert(0, current_pos)
        pos_entry.grid(row=2, column=1, padx=10, pady=10)

        # Кнопки
        def save_changes():
            target = target_entry.get().strip()
            pos = pos_entry.get().strip()

            if not target:
                messagebox.showwarning("Предупреждение", "Заполните перевод")
                return

            try:
                # Обновляем запись в базе данных
                cursor = self.db.connection.cursor()
                cursor.execute('''
                    UPDATE dictionary 
                    SET target_word = ?, pos_tag = ?, pos_explanation = ?
                    WHERE source_word = ?
                ''', (target, pos, self.processor.pos_tags_explanation.get(pos, ''), source_word))
                self.db.connection.commit()

                # Обновляем таблицу
                self._search_dictionary()

                dialog.destroy()
                messagebox.showinfo("Успех", f"Слово '{source_word}' обновлено")

            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при обновлении: {str(e)}")

        def cancel():
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=20)

        ttk.Button(btn_frame, text="Сохранить", command=save_changes).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Отмена", command=cancel).pack(side=tk.LEFT, padx=10)

    def _load_history(self):
        """Загружает историю переводов"""
        self._update_status("Загрузка истории...")

        try:
            history = self.db.get_translation_history(limit=100)

            # Очищаем таблицу
            for item in self.history_tree.get_children():
                self.history_tree.delete(item)

            # Добавляем данные
            for item in history:
                date_str = item.get('created_at', '')
                if len(date_str) > 19:
                    date_str = date_str[:19]

                self.history_tree.insert('', tk.END,
                                       values=(
                                           item.get('id', ''),
                                           date_str,
                                           item.get('source_lang', ''),
                                           item.get('target_lang', ''),
                                           item.get('word_count', 0)
                                       ))

            self._update_status(f"Загружено {len(history)} записей истории")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при загрузке истории: {str(e)}")
            self._update_status("Ошибка загрузки истории")

    def _clear_history(self):
        """Очищает историю переводов"""
        if messagebox.askyesno("Подтверждение",
                              "Вы уверены, что хотите очистить всю историю переводов?"):
            try:
                cursor = self.db.connection.cursor()
                cursor.execute('DELETE FROM translation_history')
                cursor.execute('DELETE FROM frequency_lists')
                cursor.execute('DELETE FROM syntax_trees')
                self.db.connection.commit()

                # Очищаем таблицу
                for item in self.history_tree.get_children():
                    self.history_tree.delete(item)

                self._update_status("История очищена")

            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при очистке истории: {str(e)}")

    def _save_translation_to_db(self,
                               source_text: str,
                               translated_text: str,
                               processed: Dict[str, Any],
                               frequency_list: List[Dict[str, Any]]):
        """Сохраняет результаты перевода в базу данных"""
        try:
            # Сохраняем историю перевода
            word_count = processed.get('word_count', 0)
            translation_id = self.db.save_translation_history(
                source_text=source_text,
                translated_text=translated_text,
                source_lang='en',
                target_lang='ru',
                domain='general',
                word_count=word_count,
                translated_count=word_count,
                translation_time=0.0
            )

            # Сохраняем частотный список
            text_hash = hashlib.md5(source_text.encode()).hexdigest()
            self.db.save_frequency_list(text_hash, frequency_list)

            # Добавляем слова в словарь (топ-10 слов)
            for item in frequency_list[:10]:
                word = item.get('word', '')
                if not word:
                    continue  # Пропускаем пустые слова

                # Ищем перевод в пользовательском словаре
                translation = self.translator.get_custom_translation(word)

                if translation:  # Проверяем, что translation не None и не пустая строка
                    # Получаем значения, если они есть
                    pos_tag_value = item.get('pos_tag', '')
                    pos_explanation_value = item.get('pos_explanation', '')

                    # Преобразуем пустые строки в None
                    pos_tag_to_save = pos_tag_value if pos_tag_value else None
                    pos_explanation_to_save = pos_explanation_value if pos_explanation_value else None

                    self.db.add_word_to_dictionary(
                        source_word=word,
                        target_word=translation,
                        source_lang='en',
                        target_lang='ru',
                        pos_tag=pos_tag_to_save,
                        pos_explanation=pos_explanation_to_save,
                        domain='general'
                    )

            logger.info(f"Результаты перевода сохранены в БД (ID: {translation_id})")

        except Exception as e:
            logger.error(f"Ошибка при сохранении результатов в БД: {e}")
            # Выводим дополнительную отладочную информацию
            import traceback
            logger.error(f"Стек вызовов: {traceback.format_exc()}")

    def _open_file(self):
        """Открывает текстовый файл"""
        filepath = filedialog.askopenfilename(
            title="Открыть текстовый файл",
            filetypes=[
                ("Текстовые файлы", "*.txt"),
                ("Все файлы", "*.*")
            ]
        )

        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                self.input_text.delete("1.0", tk.END)
                self.input_text.insert("1.0", content)

                self._update_status(f"Файл загружен: {filepath}")

            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при загрузке файла: {str(e)}")

    def _save_results(self):
        """Сохраняет результаты перевода в файл"""
        if not self.current_translation:
            messagebox.showwarning("Предупреждение", "Нет данных для сохранения")
            return

        filepath = filedialog.asksaveasfilename(
            title="Сохранить результаты",
            defaultextension=".txt",
            filetypes=[
                ("Текстовые файлы", "*.txt"),
                ("Все файлы", "*.*")
            ]
        )

        if filepath:
            try:
                # Подготавливаем данные для сохранения
                output_text = self.processor.prepare_translation_output(
                    source_text=self.current_translation.get('source_text', ''),
                    translated_text=self.current_translation.get('translated_text', ''),
                    frequency_list=self.current_frequency_list
                )

                # Сохраняем в файл
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(output_text)

                self._update_status(f"Результаты сохранены в {filepath}")

            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при сохранении: {str(e)}")

    def _export_dictionary(self):
        """Экспортирует словарь в файл"""
        filepath = filedialog.asksaveasfilename(
            title="Экспорт словаря",
            defaultextension=".json",
            filetypes=[
                ("JSON файлы", "*.json"),
                ("CSV файлы", "*.csv"),
                ("Текстовые файлы", "*.txt"),
                ("Все файлы", "*.*")
            ]
        )

        if filepath:
            # Определяем формат по расширению
            if filepath.endswith('.csv'):
                format = 'csv'
            elif filepath.endswith('.txt'):
                format = 'txt'
            else:
                format = 'json'

            success = self.db.export_dictionary(filepath, format)

            if success:
                self._update_status(f"Словарь экспортирован в {filepath}")
            else:
                messagebox.showerror("Ошибка", "Не удалось экспортировать словарь")

    def _import_dictionary(self):
        """Импортирует словарь из файла"""
        filepath = filedialog.askopenfilename(
            title="Импорт словаря",
            filetypes=[
                ("JSON файлы", "*.json"),
                ("CSV файлы", "*.csv"),
                ("Все файлы", "*.*")
            ]
        )

        if filepath:
            # Определяем формат по расширению
            if filepath.endswith('.csv'):
                format = 'csv'
            else:
                format = 'json'

            if messagebox.askyesno("Подтверждение",
                                  "Импортировать словарь? Существующие записи будут обновлены."):
                success = self.db.import_dictionary(filepath, format)

                if success:
                    self._update_status(f"Словарь импортирован из {filepath}")
                else:
                    messagebox.showerror("Ошибка", "Не удалось импортировать словарь")

    def _open_settings(self):
        """Открывает окно настроек"""
        # Создаем диалоговое окно настроек
        dialog = tk.Toplevel(self.root)
        dialog.title("Настройки перевода")
        dialog.geometry("500x300")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Настройки системы перевода",
                 font=('Helvetica', 12, 'bold')).pack(pady=10)

        # Настройка API
        api_frame = ttk.LabelFrame(dialog, text="Настройки API", padding=10)
        api_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(api_frame, text="API ключ OpenRouter:").grid(row=0, column=0, sticky=tk.W, padx=5)
        api_key_var = tk.StringVar(value=self.translator.api_key if self.translator.api_key else "")
        api_key_entry = ttk.Entry(api_frame, textvariable=api_key_var, width=40, show="*")
        api_key_entry.grid(row=0, column=1, padx=5)

        def save_settings():
            # В реальной системе здесь нужно сохранять настройки
            # Для демонстрации просто показываем сообщение
            messagebox.showinfo("Настройки", "Настройки сохранены (в демо-режиме)")
            dialog.destroy()

        def cancel():
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=20)

        ttk.Button(btn_frame, text="Сохранить", command=save_settings).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Отмена", command=cancel).pack(side=tk.LEFT, padx=10)

    def _clear_cache(self):
        """Очищает кэш переводов"""
        if messagebox.askyesno("Подтверждение", "Очистить кэш переводов?"):
            self.translator.clear_cache()
            self._update_status("Кэш переводов очищен")

    def _show_about(self):
        """Показывает информацию о программе"""
        about_text = f"""
Система машинного перевода текстов
Версия 1.0

Лабораторная работа №4
Вариант 2: Англо-русский перевод

Используемые технологии:
- Grok API через OpenRouter
- NLTK для грамматического анализа
- SQLite для хранения словаря

Функции:
- Перевод текстов с английского на русский
- Грамматический и частотный анализ
- Синтаксический разбор предложений
- Управление словарем
- Сохранение истории переводов

Разработчик: Лабораторная работа
"""
        messagebox.showinfo("О программе", about_text)

    def _show_help(self):
        """Показывает справку"""
        help_text = """
ИНСТРУКЦИЯ ПО ИСПОЛЬЗОВАНИЮ

1. ВКЛАДКА "ПЕРЕВОД":
   - Введите или загрузите текст на английском языке
   - Нажмите "Перевести текст"
   - Результаты появятся в поле перевода и таблице частот

2. ВКЛАДКА "СИНТАКСИЧЕСКИЙ АНАЛИЗ":
   - Введите предложение для анализа
   - Нажмите "Анализировать"
   - Просмотрите дерево разбора и выделенные фразы

3. ВКЛАДКА "СЛОВАРЬ":
   - Используйте поиск для нахождения слов
   - Добавляйте, редактируйте или удаляйте записи
   - Экспортируйте/импортируйте словарь

4. ВКЛАДКА "ИСТОРИЯ":
   - Просматривайте историю переводов
   - Очищайте историю при необходимости

ФАЙЛОВЫЕ ОПЕРАЦИИ:
   - Открытие текстовых файлов (.txt)
   - Сохранение результатов перевода
   - Экспорт/импорт словаря

ТРЕБОВАНИЯ:
   - Для работы перевода через API необходим ключ OpenRouter
   - Без API ключа доступны все функции кроме перевода через Grok
"""
        # Создаем окно справки
        help_window = tk.Toplevel(self.root)
        help_window.title("Справка")
        help_window.geometry("600x400")

        text_widget = scrolledtext.ScrolledText(help_window, wrap=tk.WORD, font=('Arial', 10))
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget.insert("1.0", help_text)
        text_widget.config(state='disabled')

        close_btn = ttk.Button(help_window, text="Закрыть",
                              command=help_window.destroy)
        close_btn.pack(pady=10)

    def _on_closing(self):
        """Обработчик закрытия приложения"""
        if messagebox.askokcancel("Выход", "Вы уверены, что хотите выйти?"):
            # Закрываем соединение с БД
            if hasattr(self, 'db'):
                self.db.close()

            # Закрываем приложение
            self.root.destroy()

    def _setup_keyboard_shortcuts(self):
        """Настройка горячих клавиш"""

        # Для всех текстовых полей
        def select_all(event):
            event.widget.tag_add('sel', '1.0', 'end')
            return 'break'

        def copy_text(event):
            event.widget.event_generate('<<Copy>>')
            return 'break'

        def paste_text(event):
            event.widget.event_generate('<<Paste>>')
            return 'break'

        def cut_text(event):
            event.widget.event_generate('<<Cut>>')
            return 'break'

        # Регистрируем хоткеи для всех текстовых полей
        widgets = [
            self.input_text,
            self.output_text,
            self.tree_display,
            self.phrases_text
        ]

        for widget in widgets:
            if widget:  # Проверяем, что виджет существует
                # Ctrl+A - выделить все
                widget.bind('<Control-a>', select_all)
                widget.bind('<Control-A>', select_all)

                # Ctrl+C - копировать
                widget.bind('<Control-c>', copy_text)
                widget.bind('<Control-C>', copy_text)

                # Ctrl+V - вставить
                widget.bind('<Control-v>', paste_text)
                widget.bind('<Control-V>', paste_text)

                # Ctrl+X - вырезать
                widget.bind('<Control-x>', cut_text)
                widget.bind('<Control-X>', cut_text)

        # Для поля ввода предложения
        if hasattr(self, 'sentence_entry'):
            self.sentence_entry.bind('<Control-v>', lambda e: self.sentence_entry.event_generate('<<Paste>>'))
            self.sentence_entry.bind('<Control-V>', lambda e: self.sentence_entry.event_generate('<<Paste>>'))
            self.sentence_entry.bind('<Control-c>', lambda e: self.sentence_entry.event_generate('<<Copy>>'))
            self.sentence_entry.bind('<Control-C>', lambda e: self.sentence_entry.event_generate('<<Copy>>'))
            self.sentence_entry.bind('<Control-x>', lambda e: self.sentence_entry.event_generate('<<Cut>>'))
            self.sentence_entry.bind('<Control-X>', lambda e: self.sentence_entry.event_generate('<<Cut>>'))
            self.sentence_entry.bind('<Control-a>', lambda e: self.sentence_entry.select_range(0, tk.END))
            self.sentence_entry.bind('<Control-A>', lambda e: self.sentence_entry.select_range(0, tk.END))
    def run(self):
        """Запускает главный цикл приложения"""
        # Загружаем историю при запуске
        self._load_history()

        # Запускаем главный цикл
        self.root.mainloop()