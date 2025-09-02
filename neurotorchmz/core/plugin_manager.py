""" The plugin manager provides methods to load plugins and provides a list of all loaded plugins """

from ..core.logs import logger

import pkgutil
import importlib.util
import sys
from types import ModuleType
from pathlib import Path
import inspect

plugins: list[ModuleType] = []

def load_plugins_from_dir(path: Path, prefix: str) -> None:
    """ Load all valid plugins from the given path """
    global plugins
    if not path.is_dir() or not path.exists():
        raise FileExistsError(f"Invalid path {path} to import plugins from")
    for module_info in pkgutil.iter_modules(path=[path], prefix=prefix+"."):
        module_spec = module_info.module_finder.find_spec(module_info.name, None)
        if module_spec is None or module_spec.loader is None:
            raise RuntimeError(f"Can't import plugin {module_info.name}")
        module_type = importlib.util.module_from_spec(module_spec)
        try:
            sys.modules[module_info.name] = module_type
            module_spec.loader.exec_module(module_type)
        except Exception:
            logger.error(f"Failed to import plugin {module_info.name}:", exc_info=True)
            continue
        try:
            assert hasattr(module_type, "__plugin_name__"), "The plugin is missing the __plugin_name__ string"
            assert hasattr(module_type, "__plugin_desc__"), "The plugin is missing the __plugin_desc__ string"
            assert hasattr(module_type, "__version__"), "The plugin is missing the __version__ string"
            assert hasattr(module_type, "__author__"), "The plugin is missing the __author__ string"
        except AssertionError as ex:
            logger.error(f"Failed to import plugin {module_info.name}: {str(ex)}")
            continue
        plugins.append(module_type)
        logger.debug(f"Loaded plugin {module_info.name}")

def get_module() -> ModuleType:
    """ Returns the module of the caller """
    frame = inspect.currentframe()
    if frame is None:
        raise RuntimeError(f"Unexpected empty frame when trying to retrieve the plugin")
    caller_frame = frame.f_back
    caller_module = inspect.getmodule(caller_frame)
    if caller_module is None:
        raise RuntimeError(f"Failed to get the module of the plugin")
    
    return caller_module