import os
import json
import requests
from typing import List, Dict
from collections import Counter
from dotenv import load_dotenv

load_dotenv()


class AIDocumentAnalyzer:
    def __init__(self, openrouter_api_key: str = None):
        self.api_key = openrouter_api_key or os.getenv("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1"
        self.model = "tngtech/deepseek-r1t-chimera:free"

    def analyze_folder_and_recommend(self, folder_path: str, num_recommendations: int = 5) -> List[str]:
        """Анализ папки и генерация простых рекомендаций (без операторов)"""
        if not os.path.exists(folder_path):
            print(f"Папка не существует: {folder_path}")
            return self._get_fallback_recommendations()

        try:
            # Собираем информацию о файлах в папке (быстро, без чтения всего)
            folder_info = self._quick_scan_folder(folder_path)

            if folder_info['total_files'] == 0:
                print(f"В папке нет поддерживаемых файлов: {folder_path}")
                return self._get_fallback_recommendations()

            # Создаем улучшенный промпт для простых запросов
            prompt = self._create_simple_prompt(folder_info)

            # Получаем рекомендации от AI
            recommendations = self._call_openrouter_api(prompt, num_recommendations)

            # Фильтруем и очищаем рекомендации
            clean_recommendations = self._clean_recommendations(recommendations)

            return clean_recommendations[:num_recommendations]

        except Exception as e:
            print(f"Ошибка AI анализа: {e}")
            return self._get_fallback_recommendations()

    def _quick_scan_folder(self, folder_path: str) -> Dict:
        """Быстрое сканирование папки (только имена файлов и размеры)"""
        folder_info = {
            'folder_path': folder_path,
            'folder_name': os.path.basename(folder_path),
            'total_files': 0,
            'file_types': Counter(),
            'file_names': [],
            'avg_file_size': 0,
            'total_size': 0
        }

        try:
            # Собираем только первые 30 файлов для скорости
            for root, dirs, files in os.walk(folder_path):
                for filename in files[:30]:  # Ограничиваем количество
                    file_ext = os.path.splitext(filename)[1].lower()

                    if file_ext in ['.txt', '.pdf']:
                        folder_info['total_files'] += 1
                        folder_info['file_types'][file_ext] += 1

                        # Сохраняем только имя файла (без пути)
                        folder_info['file_names'].append(filename)

                        # Получаем размер файла
                        try:
                            file_path = os.path.join(root, filename)
                            size = os.path.getsize(file_path)
                            folder_info['total_size'] += size
                        except:
                            pass

                # Прерываем после первого уровня для скорости
                break

            # Вычисляем средний размер
            if folder_info['total_files'] > 0:
                folder_info['avg_file_size'] = folder_info['total_size'] / folder_info['total_files']

        except Exception as e:
            print(f"Ошибка сканирования папки: {e}")

        return folder_info

    def _create_simple_prompt(self, folder_info: Dict) -> str:
        """Создание простого промпта для генерации поисковых запросов"""

        prompt = """Ты - помощник для поисковой системы. Анализируй имена файлов в папке и предложи простые поисковые запросы.

В папке "{folder_name}" найдено {total_files} файлов.
Типы файлов: {file_types}

Имена некоторых файлов:
{file_names}

На основе имен файлов предложи {num_recomm} простых поисковых запросов на английском языке.

ПРАВИЛА:
1. ТОЛЬКО простые фразы из 1-3 слов
2. НИКАКИХ операторов (AND, OR, скобок и т.д.)
3. НИКАКИХ кавычек вокруг запросов
4. ТОЛЬКО ключевые слова на английском
5. Запросы должны быть релевантны именам файлов

Примеры ПРАВИЛЬНЫХ запросов:
- machine learning
- data analysis
- neural networks
- python programming
- artificial intelligence

Примеры НЕПРАВИЛЬНЫХ запросов:
- "machine learning" (без кавычек!)
- python AND java (без операторов!)
- (data OR information) (без скобок!)
- "artificial intelligence" OR AI (слишком сложно!)

Формат ответа - ТОЛЬКО JSON:
{{
  "recommendations": ["query1", "query2", "query3"]
}}
""".format(
            folder_name=folder_info['folder_name'],
            total_files=folder_info['total_files'],
            file_types=', '.join([f"{k}: {v}" for k, v in folder_info['file_types'].items()]),
            file_names='\n'.join([f"- {name}" for name in folder_info['file_names'][:10]]),
            num_recomm=min(5, folder_info['total_files'])
        )

        return prompt

    def _call_openrouter_api(self, prompt: str, num_recommendations: int) -> List[str]:
        """Вызов OpenRouter API с улучшенной обработкой"""
        if not self.api_key:
            print("OpenRouter API ключ не найден")
            return self._get_fallback_recommendations()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5000",
            "X-Title": "AI Search System"
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "Ты генерируешь простые поисковые запросы на основе имен файлов. Отвечай ТОЛЬКО в формате JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,  # Низкая температура для более предсказуемых ответов
            "max_tokens": 200
        }

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=15  # Уменьшаем таймаут
            )

            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]

                # Очищаем ответ от лишних символов
                content = self._clean_ai_response(content)

                # Парсим JSON
                try:
                    data = json.loads(content)
                    recommendations = data.get("recommendations", [])

                    # Проверяем, что это простые строки
                    if isinstance(recommendations, list) and all(isinstance(r, str) for r in recommendations):
                        return recommendations
                    else:
                        return self._extract_simple_queries(content, num_recommendations)

                except json.JSONDecodeError:
                    return self._extract_simple_queries(content, num_recommendations)
            else:
                print(f"Ошибка API ({response.status_code}): {response.text[:200]}")
                return self._get_fallback_recommendations()

        except requests.Timeout:
            print("Таймаут запроса к AI")
            return self._get_fallback_recommendations()
        except Exception as e:
            print(f"Ошибка при вызове AI: {e}")
            return self._get_fallback_recommendations()

    def _clean_ai_response(self, text: str) -> str:
        """Очистка ответа AI от лишних символов"""
        import re

        # Удаляем markdown коды
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)

        # Удаляем лишние пробелы и переносы
        text = ' '.join(text.split())

        # Находим JSON в тексте
        json_pattern = r'\{.*"recommendations".*\}'
        match = re.search(json_pattern, text, re.DOTALL)

        if match:
            return match.group(0)

        return text

    def _extract_simple_queries(self, text: str, num: int) -> List[str]:
        """Извлечение простых запросов из текста"""
        import re

        queries = []

        # Ищем простые фразы в кавычках
        quoted = re.findall(r'"([^"]+)"', text)
        for q in quoted:
            if 2 <= len(q.split()) <= 4 and q.isascii():
                queries.append(q)

        # Ищем простые фразы без кавычек
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            # Пропускаем строки с JSON или сложными символами
            if '{' in line or '}' in line or '[' in line or ']' in line or '(' in line or ')' in line:
                continue

            # Ищем простые английские фразы
            words = line.split()
            if 1 <= len(words) <= 3:
                # Проверяем, что это простые слова
                simple_line = ' '.join(words)
                if (simple_line.isascii() and
                        len(simple_line) > 3 and
                        'AND' not in simple_line.upper() and
                        'OR' not in simple_line.upper()):
                    queries.append(simple_line)

        # Убираем дубликаты
        unique_queries = []
        seen = set()
        for q in queries:
            q_lower = q.lower()
            if q_lower not in seen:
                seen.add(q_lower)
                unique_queries.append(q)

        return unique_queries[:num]

    def _clean_recommendations(self, recommendations: List[str]) -> List[str]:
        """Очистка рекомендаций от операторов и лишних символов"""
        import re

        clean_recs = []

        for rec in recommendations:
            if not rec or not isinstance(rec, str):
                continue

            # Удаляем операторы и скобки
            rec_clean = re.sub(r'\b(AND|OR|NOT)\b', '', rec, flags=re.IGNORECASE)
            rec_clean = re.sub(r'[()\[\]{}"]', '', rec_clean)

            # Удаляем лишние пробелы
            rec_clean = ' '.join(rec_clean.split())

            # Проверяем, что осталась нормальная строка
            if (rec_clean and
                    len(rec_clean.split()) <= 4 and
                    rec_clean.isascii() and
                    len(rec_clean) >= 3):
                clean_recs.append(rec_clean.lower())

        # Если после очистки ничего не осталось, используем запасные варианты
        if not clean_recs:
            return self._get_fallback_recommendations()

        # Убираем дубликаты
        unique_recs = []
        seen = set()
        for rec in clean_recs:
            if rec not in seen:
                seen.add(rec)
                unique_recs.append(rec)

        return unique_recs[:5]

    def _get_fallback_recommendations(self) -> List[str]:
        """Запасные простые рекомендации"""
        return [
            "machine learning",
            "data analysis",
            "artificial intelligence",
            "computer science",
            "programming"
        ]