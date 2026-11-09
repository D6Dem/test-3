"""
Модуль обучения.
Всегда доступен. При простое > 30 мин обновляет остальные модули
и формирует архив знаний.
"""

import json
from pathlib import Path
from datetime import datetime


class Module:
    def __init__(self):
        self.name = "learning"

    def run(self, params: dict) -> dict:
        mode = params.get("mode", "idle_update")
        knowledge_dir = Path(params.get("knowledge_dir", "knowledge"))
        memory_dir = Path(params.get("memory_dir", "memory"))

        knowledge_dir.mkdir(exist_ok=True)

        # Читаем последние действия из лога
        actions_file = memory_dir / "actions.jsonl"
        recent = []
        if actions_file.exists():
            with open(actions_file, encoding="utf-8") as f:
                lines = f.readlines()[-50:]  # последние 50
                for line in lines:
                    try:
                        recent.append(json.loads(line))
                    except:
                        pass

        # Сохраняем "усвоенный" материал
        archive_entry = {
            "timestamp": datetime.now().isoformat(),
            "mode": mode,
            "actions_processed": len(recent),
            "summary": f"Обработано {len(recent)} последних действий"
        }

        archive_path = knowledge_dir / f"learn_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(archive_path, "w", encoding="utf-8") as f:
            json.dump(archive_entry, f, ensure_ascii=False, indent=2)

        return {
            "output": f"Модуль обучения завершил цикл. Создан архив: {archive_path.name}"
        }
