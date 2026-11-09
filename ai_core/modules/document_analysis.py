"""
Модуль рекурсивного анализа документов и долгосрочной памяти.
Работает как лёгкий NotebookLM:
- рекурсивно читает файлы и папки
- строит индекс по ключевым словам
- извлекает релевантный контекст
- автоматически подключается к text_work, web_search, programming и логам
"""

import os
import re
import json
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Any


class Module:
    def __init__(self):
        self.name = "document_analysis"
        self.index = defaultdict(list)          # keyword -> list of (file, snippet)
        self.file_contents = {}                 # path -> content
        self.supported_extensions = {'.py', '.txt', '.md', '.log', '.json', '.jsonl', '.csv'}

    def run(self, params: dict) -> dict:
        mode = params.get("mode", "analyze")
        query = params.get("original_input", "") or params.get("query", "")
        paths = params.get("paths", [])
        base_dir = Path(params.get("base_dir", "."))

        # Автоматически добавляем папки памяти и знаний
        default_paths = [
            base_dir / "memory",
            base_dir / "knowledge",
            base_dir / "modules"
        ]
        all_paths = paths + [str(p) for p in default_paths if p.exists()]

        if mode == "build_index" or not self.index:
            self._build_index(all_paths)

        if mode == "search" or query:
            results = self._search(query, top_k=8)
            context = self._build_context(results)
            return {
                "output": context,
                "results_count": len(results),
                "indexed_files": len(self.file_contents)
            }

        # Режим полного анализа
        summary = self._make_summary()
        return {
            "output": summary,
            "indexed_files": len(self.file_contents)
        }

    def _build_index(self, paths: List[str]):
        """Рекурсивно обходит папки и индексирует файлы"""
        self.index.clear()
        self.file_contents.clear()

        for path_str in paths:
            path = Path(path_str)
            if not path.exists():
                continue

            if path.is_file():
                self._index_file(path)
            else:
                for root, _, files in os.walk(path):
                    for file in files:
                        file_path = Path(root) / file
                        if file_path.suffix.lower() in self.supported_extensions:
                            self._index_file(file_path)

    def _index_file(self, file_path: Path):
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            self.file_contents[str(file_path)] = content

            # Простая токенизация + ключевые слова
            words = re.findall(r'\b\w{3,}\b', content.lower())
            for word in set(words):
                # Сохраняем небольшой сниппет
                idx = content.lower().find(word)
                snippet = content[max(0, idx-80):idx+120].replace('\n', ' ')
                self.index[word].append({
                    "file": str(file_path),
                    "snippet": snippet.strip()
                })
        except Exception:
            pass

    def _search(self, query: str, top_k: int = 8) -> List[Dict]:
        if not query:
            return []

        query_words = re.findall(r'\b\w{3,}\b', query.lower())
        scores = defaultdict(float)
        matched = defaultdict(list)

        for word in query_words:
            for item in self.index.get(word, []):
                key = item["file"]
                scores[key] += 1.0
                matched[key].append(item["snippet"])

        # Сортируем по релевантности
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        results = []
        for file_path, score in ranked:
            results.append({
                "file": file_path,
                "score": score,
                "snippets": matched[file_path][:3]
            })
        return results

    def _build_context(self, results: List[Dict]) -> str:
        if not results:
            return "Релевантный контекст не найден."

        parts = ["=== Релевантный контекст из документов и памяти ===\n"]
        for res in results:
            parts.append(f"Файл: {res['file']} (релевантность: {res['score']})")
            for snip in res["snippets"]:
                parts.append(f"  → {snip}...")
            parts.append("")
        return "\n".join(parts)

    def _make_summary(self) -> str:
        return (
            f"Проиндексировано файлов: {len(self.file_contents)}\n"
            f"Уникальных ключевых слов: {len(self.index)}\n"
            f"Готов к поиску по контексту и логам."
        )
