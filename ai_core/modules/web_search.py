"""
Модуль поиска в интернете и глубокого изучения.
Использует только стандартную библиотеку + urllib (максимально легковесно).
"""

import urllib.request
import urllib.parse
import re
from html.parser import HTMLParser


class Module:
    def __init__(self):
        self.name = "web_search"

    def run(self, params: dict) -> dict:
        query = params.get("original_input", "")
        # Простой поиск через DuckDuckGo HTML (без API-ключей)
        try:
            url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="ignore")

            # Очень грубое извлечение сниппетов
            snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)
            clean = [re.sub(r'<[^>]+>', '', s).strip() for s in snippets[:5]]
            result = "\n".join(f"- {s}" for s in clean if s)
            return {"output": f"Результаты поиска по '{query}':\n{result or 'Ничего не найдено'}"}
        except Exception as e:
            return {"output": f"Ошибка поиска: {e}"}
