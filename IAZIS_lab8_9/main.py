import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import json
import queue
import os
from datetime import datetime
import requests
import speech_recognition as sr
import pygame
import tempfile
from gtts import gTTS
from pathlib import Path
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VoiceChatBot:
    def __init__(self, root):
        self.root = root
        self.root.title("Интеллектуальный голосовой ассистент")
        self.root.geometry("1200x800")
        self.root.configure(bg='#2c3e50')

        # Загружаем настройки в первую очередь
        self.settings = self.load_settings()

        # Стили
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('TFrame', background='#2c3e50')
        self.style.configure('TLabel', background='#2c3e50', foreground='#ecf0f1', font=('Segoe UI', 10))
        self.style.configure('TButton', font=('Segoe UI', 10), padding=6)
        self.style.configure('TNotebook', background='#2c3e50')
        self.style.configure('TNotebook.Tab', background='#34495e', foreground='#ecf0f1', padding=[10, 5])
        self.style.map('TNotebook.Tab', background=[('selected', '#1abc9c')])

        # Инициализация компонентов
        self.setup_ui()
        self.setup_audio()
        self.setup_chat()

        # Очереди
        self.audio_queue = queue.Queue()
        self.chat_queue = queue.Queue()

        # Состояние записи
        self.recording = False
        self.audio_thread = None

    def setup_ui(self):
        """Настройка пользовательского интерфейса"""
        # Заголовок
        header_frame = ttk.Frame(self.root)
        header_frame.pack(fill='x', padx=10, pady=10)

        title_label = tk.Label(
            header_frame,
            text="Интеллектуальный голосовой ассистент",
            font=('Segoe UI', 20, 'bold'),
            fg='#1abc9c',
            bg='#2c3e50'
        )
        title_label.pack(side='left')

        # Основные вкладки
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        # Вкладка чата
        self.chat_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.chat_tab, text='💬 Чат')
        self.setup_chat_tab()

        # Вкладка синтеза речи
        self.tts_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.tts_tab, text='🔊 Синтез речи')
        self.setup_tts_tab()

        # Вкладка распознавания речи
        self.stt_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.stt_tab, text='🎤 Распознавание речи')
        self.setup_stt_tab()

        # Статус бар
        self.status_bar = ttk.Label(
            self.root,
            text="Готов к работе",
            relief='sunken',
            anchor='w',
            font=('Segoe UI', 9)
        )
        self.status_bar.pack(side='bottom', fill='x', padx=10, pady=(0, 10))

    def setup_chat_tab(self):
        """Настройка вкладки чата"""
        # Основной фрейм
        main_frame = ttk.Frame(self.chat_tab)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # История чата
        chat_frame = ttk.LabelFrame(main_frame, text="История диалога", padding=10)
        chat_frame.pack(fill='both', expand=True, pady=(0, 10))

        self.chat_history = scrolledtext.ScrolledText(
            chat_frame,
            wrap='word',
            font=('Segoe UI', 11),
            bg='#34495e',
            fg='#ecf0f1',
            insertbackground='#1abc9c',
            height=15
        )
        self.chat_history.pack(fill='both', expand=True)

        # Панель ввода
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill='x', pady=(0, 10))

        self.chat_input = scrolledtext.ScrolledText(
            input_frame,
            wrap='word',
            font=('Segoe UI', 11),
            bg='#34495e',
            fg='#ecf0f1',
            insertbackground='#1abc9c',
            height=4
        )
        self.chat_input.pack(side='left', fill='both', expand=True, padx=(0, 10))

        # Кнопки ввода
        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(side='right', fill='y')

        self.send_btn = ttk.Button(
            btn_frame,
            text="Отправить",
            command=self.send_message,
            width=15
        )
        self.send_btn.pack(pady=(0, 5))


        self.speak_btn = ttk.Button(
            btn_frame,
            text="Озвучить ответ",
            command=self.speak_last_response,
            width=15
        )
        self.speak_btn.pack(pady=(5, 0))

        # Привязка клавиши Enter
        self.chat_input.bind('<Return>', lambda e: self.send_message())
        self.chat_input.bind('<Shift-Return>', lambda e: None)

    def setup_tts_tab(self):
        """Настройка вкладки синтеза речи"""
        main_frame = ttk.Frame(self.tts_tab)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Текстовое поле
        text_frame = ttk.LabelFrame(main_frame, text="Текст для озвучивания", padding=10)
        text_frame.pack(fill='both', expand=True, pady=(0, 10))

        self.tts_text = scrolledtext.ScrolledText(
            text_frame,
            wrap='word',
            font=('Segoe UI', 11),
            bg='#34495e',
            fg='#ecf0f1',
            insertbackground='#1abc9c',
            height=10
        )
        self.tts_text.pack(fill='both', expand=True)

        # Панель настроек
        settings_frame = ttk.LabelFrame(main_frame, text="Настройки синтеза", padding=10)
        settings_frame.pack(fill='x', pady=(0, 10))

        # Голос
        ttk.Label(settings_frame, text="Голос:").grid(row=0, column=0, sticky='w', pady=5)
        self.voice_var = tk.StringVar(value='ru')
        voice_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.voice_var,
            values=['ru', 'en', 'de', 'fr'],
            state='readonly',
            width=15
        )
        voice_combo.grid(row=0, column=1, padx=(5, 20), pady=5)

        # Скорость
        ttk.Label(settings_frame, text="Скорость:").grid(row=0, column=2, sticky='w', pady=5)
        self.slow_var = tk.BooleanVar(value=False)
        slow_check = ttk.Checkbutton(settings_frame, variable=self.slow_var, text="Медленно")
        slow_check.grid(row=0, column=3, padx=5, pady=5)

        # Громкость
        ttk.Label(settings_frame, text="Громкость:").grid(row=1, column=0, sticky='w', pady=5)
        self.volume_var = tk.DoubleVar(value=0.8)
        volume_scale = ttk.Scale(
            settings_frame,
            from_=0.0,
            to=1.0,
            variable=self.volume_var,
            orient='horizontal',
            length=150
        )
        volume_scale.grid(row=1, column=1, padx=5, pady=5)
        ttk.Label(settings_frame, textvariable=self.volume_var).grid(row=1, column=2, padx=(0, 20))

        # Кнопки управления
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill='x', pady=(0, 10))

        self.play_btn = ttk.Button(
            btn_frame,
            text="Воспроизвести",
            command=self.play_tts,
            width=20
        )
        self.play_btn.pack(side='left', padx=(0, 10))

        self.clear_btn = ttk.Button(
            btn_frame,
            text="Очистить",
            command=self.clear_tts_text,
            width=20
        )
        self.clear_btn.pack(side='left', padx=10)

        # Статус синтеза
        self.tts_status = ttk.Label(
            main_frame,
            text="Готов к синтезу речи",
            font=('Segoe UI', 9, 'italic')
        )
        self.tts_status.pack()

    def setup_stt_tab(self):
        """Настройка вкладки распознавания речи"""
        main_frame = ttk.Frame(self.stt_tab)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Отображение распознанного текста
        text_frame = ttk.LabelFrame(main_frame, text="Распознанный текст", padding=10)
        text_frame.pack(fill='both', expand=True, pady=(0, 10))

        self.stt_text = scrolledtext.ScrolledText(
            text_frame,
            wrap='word',
            font=('Segoe UI', 11),
            bg='#34495e',
            fg='#ecf0f1',
            insertbackground='#1abc9c',
            height=10
        )
        self.stt_text.pack(fill='both', expand=True)

        # Панель управления
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill='x', pady=(0, 10))

        self.record_btn = ttk.Button(
            control_frame,
            text="Начать запись",
            command=self.start_recording,
            width=20
        )
        self.record_btn.pack(side='left', padx=(0, 10))


        self.send_to_chat_btn = ttk.Button(
            control_frame,
            text="Отправить в чат",
            command=self.send_to_chat,
            width=20
        )
        self.send_to_chat_btn.pack(side='left', padx=10)

        self.clear_stt_btn = ttk.Button(
            control_frame,
            text="🗑Очистить",
            command=self.clear_stt_text,
            width=20
        )
        self.clear_stt_btn.pack(side='left', padx=10)

        # Индикатор записи
        self.record_indicator = tk.Canvas(
            main_frame,
            width=30,
            height=30,
            bg='#2c3e50',
            highlightthickness=0
        )
        self.record_indicator.pack(pady=(0, 10))
        self.indicator_circle = self.record_indicator.create_oval(
            5, 5, 25, 25,
            fill='#e74c3c',
            state='hidden'
        )

        # Статус распознавания
        self.stt_status = ttk.Label(
            main_frame,
            text="Готов к распознаванию речи",
            font=('Segoe UI', 9, 'italic')
        )
        self.stt_status.pack()

    def setup_audio(self):
        """Инициализация аудио компонентов"""
        pygame.mixer.init()
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()

    def setup_chat(self):
        """Инициализация чата"""
        self.chat_history_data = []
        # Загрузка API ключа и модели из файла
        self.load_api_config()

    def load_api_config(self):
        """Загрузка API конфигурации из файла"""
        config_file = Path('api_config.json')
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.api_key = config.get('api_key', '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')
                    self.model_url = config.get('model_url', 'https://openrouter.ai/api/v1/chat/completions')
                    self.model = config.get('model', 'xiaomi/mimo-v2-flash:free')
            except:
                self.api_key = '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'
                self.model_url = 'https://openrouter.ai/api/v1/chat/completions'
                self.model = 'xiaomi/mimo-v2-flash:free'
        else:
            # Создаем файл с примером
            self.api_key = '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'
            self.model_url = 'https://openrouter.ai/api/v1/chat/completions'
            self.model = 'xiaomi/mimo-v2-flash:free'
            self.save_api_config()

    def save_api_config(self):
        """Сохранение API конфигурации в файл"""
        config = {
            'api_key': self.api_key,
            'model_url': self.model_url,
            'model': self.model
        }
        with open('api_config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def load_settings(self):
        """Загрузка настроек из файла"""
        settings_file = Path('voicegpt_settings.json')
        if settings_file.exists():
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def start_recording(self):
        """Начало записи"""
        self.recording = True
        self.record_btn.config(state='disabled')
        self.record_indicator.itemconfig(self.indicator_circle, state='normal')
        self.stt_status.config(text="Запись... Говорите сейчас")

        # Очистка предыдущего текста
        self.stt_text.delete(1.0, tk.END)

        # Запуск записи в отдельном потоке
        self.audio_thread = threading.Thread(target=self.record_audio, daemon=True)
        self.audio_thread.start()

    def record_audio(self):
        """Запись аудио"""
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                # Слушаем пока recording = True
                audio = self.recognizer.listen(source, timeout=None, phrase_time_limit=None)

                # Если запись остановлена пользователем, прерываем распознавание
                if not self.recording:
                    return

                text = self.recognizer.recognize_google(audio, language='ru-RU')

                self.root.after(0, self.update_stt_text, text)
                self.root.after(0, lambda: self.stt_status.config(text="Распознавание завершено"))

        except sr.WaitTimeoutError:
            if self.recording:
                self.root.after(0, lambda: self.stt_status.config(text="Таймаут записи"))
        except sr.UnknownValueError:
            if self.recording:
                self.root.after(0, lambda: self.stt_status.config(text="Речь не распознана"))
        except sr.RequestError as e:
            if self.recording:
                error_text = f"Ошибка сервиса: {str(e)}"
                self.root.after(0, lambda: self.stt_status.config(text=error_text))
        except Exception as e:
            if self.recording:
                error_text = f"Ошибка: {str(e)}"
                self.root.after(0, lambda: self.stt_status.config(text=error_text))
        finally:
            self.root.after(0, self.reset_recording_ui)

    def reset_recording_ui(self):
        """Сброс UI записи"""
        self.recording = False
        self.record_btn.config(state='normal')
        self.record_indicator.itemconfig(self.indicator_circle, state='hidden')

    def stop_recording(self):
        """Остановка записи"""
        self.recording = False
        self.stt_status.config(text="Остановка записи...")
        # Прерываем слушание микрофона
        # В speech_recognition нет прямого способа прервать listen
        # Поэтому просто меняем флаг и ждем завершения потока

    def update_stt_text(self, text):
        """Обновление текста распознавания"""
        self.stt_text.delete(1.0, tk.END)
        self.stt_text.insert(1.0, text)

    def send_to_chat(self):
        """Отправка распознанного текста в чат"""
        text = self.stt_text.get(1.0, tk.END).strip()
        if text:
            self.chat_input.delete(1.0, tk.END)
            self.chat_input.insert(1.0, text)
            self.notebook.select(0)  # Переключение на вкладку чата

    def send_message(self):
        """Отправка сообщения в чат"""
        message = self.chat_input.get(1.0, tk.END).strip()
        if not message:
            return

        # Проверка API ключа
        if not self.api_key:
            messagebox.showerror("Ошибка", "API ключ не настроен. Создайте файл api_config.json с ключом.")
            return

        # Добавление сообщения пользователя
        self.add_to_chat_history("Вы", message)
        self.chat_input.delete(1.0, tk.END)

        # Отправка в API
        threading.Thread(target=self.get_chat_response, args=(message,), daemon=True).start()

    def get_chat_response(self, message):
        """Получение ответа от чат-бота"""
        if not self.api_key:
            return

        try:
            self.root.after(0, self.update_status, "Получение ответа от AI...")

            # Используем OpenRouter API
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "model": self.model,
                "messages": [{"role": "user", "content": message}],
                "temperature": 0.7
            }

            response = requests.post(
                self.model_url,
                headers=headers,
                json=data,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                reply = result['choices'][0]['message']['content']

                # Добавление ответа в историю
                self.root.after(0, self.add_to_chat_history, "AI", reply)
                self.root.after(0, self.update_status, "Ответ получен")

            else:
                error_msg = f"Ошибка API: {response.status_code}"
                if response.text:
                    error_msg += f" - {response.text[:100]}"
                self.root.after(0, self.add_to_chat_history, "Система", error_msg)
                self.root.after(0, self.update_status, "Ошибка API")

        except requests.exceptions.Timeout:
            self.root.after(0, self.add_to_chat_history, "Система", "Таймаут запроса")
            self.root.after(0, self.update_status, "Таймаут")
        except Exception as e:
            self.root.after(0, self.add_to_chat_history, "Система", f"Ошибка: {str(e)}")
            self.root.after(0, self.update_status, "Ошибка")

    def add_to_chat_history(self, sender, message):
        """Добавление сообщения в историю чата"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Форматирование сообщения
        if sender == "Вы":
            color = "#3498db"
            bg_color = "#2c3e50"
        elif sender == "AI":
            color = "#2ecc71"
            bg_color = "#34495e"
        else:
            color = "#e74c3c"
            bg_color = "#2c3e50"

        # Вставка сообщения
        self.chat_history.config(state='normal')

        # Добавление разделителя если это не первое сообщение
        if self.chat_history.get(1.0, tk.END).strip():
            self.chat_history.insert(tk.END, "\n" + "─" * 50 + "\n")

        # Вставка сообщения
        self.chat_history.insert(tk.END, f"[{timestamp}] {sender}:\n", f"header_{sender}")
        self.chat_history.insert(tk.END, f"{message}\n")

        # Настройка тегов для форматирования
        self.chat_history.tag_config(f"header_{sender}", foreground=color, font=('Segoe UI', 10, 'bold'))

        # Прокрутка вниз
        self.chat_history.see(tk.END)
        self.chat_history.config(state='disabled')

        # Сохранение в истории
        self.chat_history_data.append({
            'timestamp': timestamp,
            'sender': sender,
            'message': message
        })

    def play_tts(self):
        """Воспроизведение синтезированной речи"""
        text = self.tts_text.get(1.0, tk.END).strip()
        if not text:
            messagebox.showwarning("Внимание", "Введите текст для озвучивания")
            return

        try:
            self.tts_status.config(text="Синтез речи...")

            # Используем gTTS для синтеза
            tts = gTTS(
                text=text,
                lang=self.voice_var.get(),
                slow=self.slow_var.get()
            )

            # Создание временного файла
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
                tts.save(tmp_file.name)
                temp_path = tmp_file.name

            # Воспроизведение
            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.set_volume(self.volume_var.get())
            pygame.mixer.music.play()

            self.tts_status.config(text="Воспроизведение...")

            # Ожидание завершения воспроизведения
            def check_playback():
                if pygame.mixer.music.get_busy():
                    self.root.after(100, check_playback)
                else:
                    self.tts_status.config(text="Воспроизведение завершено")
                    try:
                        os.unlink(temp_path)
                    except:
                        pass

            self.root.after(100, check_playback)

        except Exception as e:
            self.tts_status.config(text=f"Ошибка: {str(e)}")


    def speak_last_response(self):
        """Озвучивание последнего ответа AI"""
        if self.chat_history_data:
            last_ai = None
            for msg in reversed(self.chat_history_data):
                if msg['sender'] == 'AI':
                    last_ai = msg['message']
                    break

            if last_ai:
                self.tts_text.delete(1.0, tk.END)
                self.tts_text.insert(1.0, last_ai)
                self.notebook.select(1)  # Переключение на вкладку TTS
                self.play_tts()
        else:
            messagebox.showinfo("Информация", "Нет ответов для озвучивания")



    def clear_tts_text(self):
        """Очистка текста TTS"""
        self.tts_text.delete(1.0, tk.END)

    def clear_stt_text(self):
        """Очистка текста STT"""
        self.stt_text.delete(1.0, tk.END)

    def update_status(self, message):
        """Обновление статус бара"""
        self.status_bar.config(text=f"Статус: {message}")

    def on_closing(self):
        """Обработка закрытия окна"""
        self.recording = False
        pygame.mixer.quit()
        self.root.destroy()


def main():
    """Основная функция"""
    root = tk.Tk()

    # Иконка приложения
    try:
        root.iconbitmap('voicegpt.ico')
    except:
        pass

    app = VoiceChatBot(root)

    # Обработка закрытия окна
    root.protocol("WM_DELETE_WINDOW", app.on_closing)

    # Запуск главного цикла
    root.mainloop()


if __name__ == "__main__":
    main()