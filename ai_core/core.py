#!/usr/bin/env python3
"""
Ядро блочной нейросети.
Отвечает только за:
- размышление / планирование
- вызов модулей
- манипуляцию файлами
- долгосрочное логирование (включено по умолчанию)
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable

# Пути
BASE_DIR = Path(__file__).parent.resolve()
MEMORY_DIR = BASE_DIR / "memory"
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
MODULES_DIR = BASE_DIR / "modules"
LOG_FILE = MEMORY_DIR / "long_term.log"

MEMORY_DIR.mkdir(exist_ok=True)
KNOWLEDGE_DIR.mkdir(exist_ok=True)

# === Долгосрочная память (логирование) ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("Core")


class Core:
    """
    Ядро. Не содержит знаний о конкретных доменах.
    Только управление, файлы, вызов модулей и память.
    """

    def __init__(self, name: str = "Ассистент"):
        self.name = name
        self.modules: Dict[str, Any] = {}
        self.active_modules: List[str] = []
        self.last_activity = time.time()
        self.idle_threshold = 30 * 60  # 30 минут
        self.running = True

        logger.info(f"Ядро '{self.name}' запущено. Долгосрочная память активна.")

        # Автоматическая загрузка модулей
        self._load_modules()

        # Модуль обучения всегда должен быть доступен
        if "learning" not in self.modules:
            logger.warning("Модуль learning не найден! Обучение будет недоступно.")

    def _load_modules(self):
        """Динамическая загрузка всех модулей из папки modules/"""
        from module_loader import ModuleLoader
        loader = ModuleLoader(MODULES_DIR)
        self.modules = loader.load_all()
        logger.info(f"Загружено модулей: {list(self.modules.keys())}")

    def log_action(self, action: str, details: Dict[str, Any] = None):
        """Запись действия в долгосрочную память"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details or {}
        }
        logger.info(f"ACTION: {action} | {json.dumps(details or {}, ensure_ascii=False)}")

        # Дополнительно пишем в JSONL для удобного анализа
        jsonl_path = MEMORY_DIR / "actions.jsonl"
        with open(jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def think(self, user_input: str, context: Dict = None) -> Dict[str, Any]:
        """
        Основной цикл размышления.
        Возвращает план: какие модули вызвать и с какими параметрами.
        """
        self.last_activity = time.time()
        self.log_action("think", {"input": user_input[:200]})

        # Простое эвристическое планирование (можно заменить на LLM-вызов)
        plan = {
            "modules_to_call": [],
            "reason": "",
            "params": {}
        }

        lower = user_input.lower()

        # Правила активации модулей (можно расширять)
        if any(w in lower for w in ["код", "программ", "напиши скрипт", "python", "функци"]):
            plan["modules_to_call"].append("programming")
        if any(w in lower for w in ["найди", "поиск", "интернет", "что такое", "как сделать"]):
            plan["modules_to_call"].append("web_search")
        if any(w in lower for w in ["текст", "анализ", "стилизуй", "перепиши", "юридический", "рассказ"]):
            plan["modules_to_call"].append("text_work")
        if any(w in lower for w in ["видео", "ролик", "youtube", "mp4", "извлеки из видео"]):
            plan["modules_to_call"].append("video")
        if any(w in lower for w in ["аудио", "голос", "запись", "wav", "mp3"]):
            plan["modules_to_call"].append("audio_voice")

        # Если ничего не определили — используем text_work как fallback
        if not plan["modules_to_call"]:
            plan["modules_to_call"].append("text_work")
            plan["reason"] = "fallback to text"

        # Можно вызывать минимум 2 модуля одновременно
        plan["params"]["original_input"] = user_input
        plan["params"]["context"] = context or {}

        self.log_action("plan_created", plan)
        return plan

    def execute_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Выполнение плана — вызов одного или нескольких модулей"""
        results = {}
        modules = plan.get("modules_to_call", [])

        for mod_name in modules:
            if mod_name not in self.modules:
                logger.warning(f"Модуль {mod_name} не загружен")
                continue

            try:
                module = self.modules[mod_name]
                self.log_action("call_module", {"module": mod_name})
                result = module.run(plan["params"])
                results[mod_name] = result
                self.active_modules.append(mod_name)
            except Exception as e:
                logger.error(f"Ошибка в модуле {mod_name}: {e}")
                results[mod_name] = {"error": str(e)}

        self.last_activity = time.time()
        return results

    def process(self, user_input: str, context: Dict = None) -> str:
        """Полный цикл: подумать → выполнить → вернуть ответ"""
        plan = self.think(user_input, context)
        results = self.execute_plan(plan)

        # Простая агрегация результатов
        answer_parts = []
        for mod, res in results.items():
            if isinstance(res, dict) and "output" in res:
                answer_parts.append(f"[{mod}]: {res['output']}")
            else:
                answer_parts.append(f"[{mod}]: {str(res)}")

        final = "\n\n".join(answer_parts) if answer_parts else "Не удалось получить результат."
        self.log_action("response", {"preview": final[:300]})
        return final

    def check_idle_and_learn(self):
        """Проверка простоя и запуск модуля обучения"""
        idle_time = time.time() - self.last_activity
        if idle_time >= self.idle_threshold:
            logger.info(f"Простой {int(idle_time)} сек. Запускаю модуль обучения...")
            if "learning" in self.modules:
                self.modules["learning"].run({
                    "mode": "idle_update",
                    "knowledge_dir": str(KNOWLEDGE_DIR),
                    "memory_dir": str(MEMORY_DIR)
                })
            self.last_activity = time.time()  # сбрасываем таймер после обучения

    def file_ops(self, operation: str, path: str, content: str = None) -> Any:
        """Базовые файловые операции (единственный навык ядра)"""
        p = Path(path)
        try:
            if operation == "read":
                return p.read_text(encoding="utf-8")
            elif operation == "write":
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content or "", encoding="utf-8")
                self.log_action("file_write", {"path": str(p)})
                return True
            elif operation == "append":
                with open(p, "a", encoding="utf-8") as f:
                    f.write(content or "")
                return True
            elif operation == "list":
                return list(p.iterdir()) if p.is_dir() else []
            elif operation == "exists":
                return p.exists()
            else:
                return None
        except Exception as e:
            logger.error(f"File op error: {e}")
            return None


# Точка входа
if __name__ == "__main__":
    core = Core(name="Блок")
    print("Ядро запущено. Введите 'exit' для выхода.")
    print("Команды: просто текст → размышление + вызов модулей")

    while core.running:
        try:
            user = input("\nВы: ").strip()
            if user.lower() in ("exit", "выход", "quit"):
                break
            if not user:
                core.check_idle_and_learn()
                continue

            answer = core.process(user)
            print("\n" + answer)

            # Проверяем простой после каждого ответа
            core.check_idle_and_learn()

        except KeyboardInterrupt:
            break

    logger.info("Ядро остановлено.")
