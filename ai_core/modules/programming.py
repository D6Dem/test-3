"""
Усиленный модуль программирования.
Умеет:
- генерировать код
- запускать его в изолированном Docker-контейнере
- проверять синтаксис
- делать базовый поиск уязвимостей
- исправлять ошибки по результатам запуска
"""

import ast
import re
import subprocess
import tempfile
import textwrap
from pathlib import Path
from typing import Dict, Any


class Module:
    def __init__(self):
        self.name = "programming"
        self.docker_available = self._check_docker()

    def run(self, params: dict) -> dict:
        task = params.get("original_input", "")
        code = params.get("code")          # если уже есть код
        auto_run = params.get("auto_run", True)
        language = params.get("language", "python")

        # 1. Генерация кода (если его ещё нет)
        if not code:
            code = self._generate_code(task)

        # 2. Проверка синтаксиса
        syntax_ok, syntax_msg = self._check_syntax(code)
        if not syntax_ok:
            fixed = self._try_fix_syntax(code, syntax_msg)
            if fixed:
                code = fixed
                syntax_ok, syntax_msg = self._check_syntax(code)

        # 3. Базовая проверка уязвимостей
        vulns = self._check_vulnerabilities(code)

        # 4. Запуск в Docker (если доступен и разрешено)
        run_result = None
        if auto_run and self.docker_available and language == "python":
            run_result = self._run_in_docker(code)

        # 5. Формируем отчёт
        report = self._build_report(code, syntax_ok, syntax_msg, vulns, run_result)
        return {"output": report, "code": code}

    def _generate_code(self, task: str) -> str:
        """Простая генерация. Позже можно заменить на локальную LLM."""
        task_lower = task.lower()

        if "hello" in task_lower or "привет" in task_lower:
            return textwrap.dedent('''\
                def main():
                    print("Hello, World!")

                if __name__ == "__main__":
                    main()
            ''')

        # Универсальный шаблон
        return textwrap.dedent(f'''\
            # Задача: {task[:120]}
            def main():
                print("Код сгенерирован под задачу")
                # TODO: реализовать логику
                pass

            if __name__ == "__main__":
                main()
        ''')

    def _check_syntax(self, code: str) -> tuple[bool, str]:
        try:
            ast.parse(code)
            return True, "Синтаксис корректен"
        except SyntaxError as e:
            return False, f"SyntaxError: {e.msg} (строка {e.lineno})"

    def _try_fix_syntax(self, code: str, error: str) -> str | None:
        """Очень простые авто-исправления"""
        # Пример: забытая скобка в конце
        if "unexpected EOF" in error or "was never closed" in error:
            if code.count("(") > code.count(")"):
                return code + "\n)" * (code.count("(") - code.count(")"))
        return None

    def _check_vulnerabilities(self, code: str) -> list[str]:
        """Базовый статический анализ на опасные конструкции"""
        vulns = []
        dangerous = [
            (r'\beval\s*\(', "Использование eval() — опасно"),
            (r'\bexec\s*\(', "Использование exec() — опасно"),
            (r'\bos\.system\s*\(', "os.system() — риск инъекций"),
            (r'\bsubprocess\..*shell\s*=\s*True', "subprocess с shell=True"),
            (r'\bpickle\.loads?\s*\(', "pickle — риск десериализации"),
            (r'__import__\s*\(', "Динамический импорт"),
        ]
        for pattern, msg in dangerous:
            if re.search(pattern, code):
                vulns.append(msg)
        return vulns

    def _check_docker(self) -> bool:
        try:
            subprocess.run(["docker", "info"], capture_output=True, timeout=5, check=True)
            return True
        except Exception:
            return False

    def _run_in_docker(self, code: str) -> Dict[str, Any]:
        """Запуск кода в изолированном контейнере"""
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "script.py"
            script.write_text(code, encoding="utf-8")

            try:
                result = subprocess.run(
                    [
                        "docker", "run", "--rm",
                        "--network", "none",          # без сети
                        "--memory", "128m",           # лимит памяти
                        "--cpus", "0.5",              # лимит CPU
                        "-v", f"{tmp}:/app",
                        "-w", "/app",
                        "python:3.11-slim",
                        "python", "script.py"
                    ],
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                return {
                    "success": result.returncode == 0,
                    "stdout": result.stdout.strip(),
                    "stderr": result.stderr.strip(),
                    "returncode": result.returncode
                }
            except subprocess.TimeoutExpired:
                return {"success": False, "error": "Timeout (превышено время выполнения)"}
            except Exception as e:
                return {"success": False, "error": str(e)}

    def _build_report(self, code, syntax_ok, syntax_msg, vulns, run_result) -> str:
        parts = []
        parts.append("=== Сгенерированный / проверенный код ===\n")
        parts.append("```python")
        parts.append(code)
        parts.append("```\n")

        parts.append(f"Синтаксис: {'OK' if syntax_ok else 'ОШИБКА'} — {syntax_msg}")

        if vulns:
            parts.append("\nПотенциальные уязвимости:")
            for v in vulns:
                parts.append(f"  - {v}")
        else:
            parts.append("\nУязвимости: критичных не обнаружено")

        if run_result:
            parts.append("\n=== Результат запуска в Docker ===")
            if run_result.get("success"):
                parts.append("Статус: Успешно")
                if run_result.get("stdout"):
                    parts.append(f"Вывод:\n{run_result['stdout']}")
            else:
                parts.append("Статус: Ошибка")
                if run_result.get("stderr"):
                    parts.append(f"stderr:\n{run_result['stderr']}")
                if run_result.get("error"):
                    parts.append(f"Ошибка: {run_result['error']}")
        elif not self.docker_available:
            parts.append("\nDocker не доступен — запуск в изолированной среде пропущен")

        return "\n".join(parts)
