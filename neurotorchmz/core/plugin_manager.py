""" The plugin manager provides methods to load plugins and provides a list of all loaded plugins """

from ..core.logs import logger

import pkgutil
import importlib.util
import sys
from types import ModuleType
from pathlib import Path

plugins: list[ModuleType] = []

def load_plugins_from_dir(path: Path, prefix: str) -> None:
    """ Load all valid plugins from the given path """
    global plugins
    if not path.is_dir() or not path.exists():
        raise FileExistsError(f"Invalid path {path} to import plugins from")
    for module_info in pkgutil.iter_modules(path=[path], prefix=prefix+"."):
        module_spec = module_info.module_finder.find_spec(module_info.name, str(module_info.module_finder.path)) # type: ignore
        if module_spec is None or module_spec.loader is None:
            raise RuntimeError(f"Can't import plugin {module_info.name}")
        module_type = importlib.util.module_from_spec(module_spec)
        try:
            sys.modules[module_info.name] = module_type
            module_spec.loader.exec_module(module_type)
        except Exception:
            logger.error(f"Failed to import plugin {module_info.name}:", exc_info=True)
        else:
            plugins.append(module_type)
            logger.debug(f"Loaded plugin {module_info.name}")