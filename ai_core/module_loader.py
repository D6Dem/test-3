#!/usr/bin/env python3
"""
Динамический загрузчик модулей.
Модули — это простые Python-файлы с классом, у которого есть метод run(params).
"""

import importlib.util
import sys
from pathlib import Path
from typing import Dict, Any


class ModuleLoader:
    def __init__(self, modules_dir: Path):
        self.modules_dir = Path(modules_dir)
        self.modules_dir.mkdir(exist_ok=True)

    def load_all(self) -> Dict[str, Any]:
        loaded = {}
        for py_file in self.modules_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            name = py_file.stem
            try:
                module = self._load_module(name, py_file)
                if hasattr(module, "Module"):
                    instance = module.Module()
                    loaded[name] = instance
                    print(f"[Loader] Модуль '{name}' загружен")
                else:
                    print(f"[Loader] В {name}.py нет класса Module")
            except Exception as e:
                print(f"[Loader] Ошибка загрузки {name}: {e}")
        return loaded

    def _load_module(self, name: str, path: Path):
        spec = importlib.util.spec_from_file_location(f"modules.{name}", path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"modules.{name}"] = module
        spec.loader.exec_module(module)
        return module
