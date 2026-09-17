""" The plugin manager provides methods to load plugins and provides a list of all loaded plugins """

from ..core.logs import logger
from ..core.settings import UserSettings

import importlib
from importlib.metadata import entry_points
from types import ModuleType

plugins: dict[str, ModuleType] = {}
plugins_inactive: list[str] = []
plugins_error: list[str] = []

def load_plugins() -> None:
    """ Load all installed plugins """
    eps = entry_points(group="neurotorchmz.plugins")

    for ep in eps:
        if not isinstance(ep, ModuleType):
            logger.warning(f"Detected malformed plugin {ep.name} (plugin is not a module)")
            continue
        plugin_setting = UserSettings.config_parser.getboolean("PLUGINS", ep.name, fallback=None)
        if plugin_setting is None:
            logger.info(f"Detected new plugin {ep.name}")
            UserSettings.config_parser.set("PLUGINS", ep.name, str(True))
            UserSettings.save_config()
        elif plugin_setting == True:
            try:
                plugin = ep.load()
            except Exception as ex:
                logger.error(f"Failed to load plugin {ep.name}:", exc_info=True)
                continue
            if not isinstance(plugin, ModuleType):
                logger.error(f"Detected malformed plugin {ep.name}: not a module)")
                continue
            _load_plugin(plugin)
        else:
            plugins_inactive.append(ep.name)
            logger.debug(f"Skipped loading disabled plugin {ep.name}")

def load_plugin(plugin_name: str):
    try:
        m = importlib.import_module(plugin_name)
    except Exception as ex:
        logger.error(f"Importing '{plugin_name}' raised an error:", exc_info=True)
        return False
    _load_plugin(m)

def _load_plugin(plugin: ModuleType) -> None:
    name = plugin.__name__
    if name in plugins.keys():
        logger.warning(f"Trying to load plugin {name} twice")
        return
    logger.debug(f"Loading plugin {name}")

    try:
        assert hasattr(plugin, "__plugin_name__"), "The plugin is missing the __plugin_name__ string"
        assert hasattr(plugin, "__plugin_desc__"), "The plugin is missing the __plugin_desc__ string"
        assert hasattr(plugin, "__version__"), "The plugin is missing the __version__ string"
        assert hasattr(plugin, "__author__"), "The plugin is missing the __author__ string"
    except AssertionError as ex:
        logger.error(f"Failed to import plugin {name}: {str(ex)}")
        plugins_error.append(name)
        return

    plugins[name] = plugin
    plugins_inactive.append(name)
    logger.debug(f"Loaded plugin {name}")


def enable_plugin(name: str) -> None:
    s = UserSettings.config_parser.getboolean("PLUGINS", name, fallback=None)
    if s is None:
        logger.warning(f"Trying to enable unkown plugin {name}")
        return
    UserSettings.config_parser.set("PLUGINS", name, str(True))
    UserSettings.save_config()

def disable_plugin(name: str) -> None:
    s = UserSettings.config_parser.getboolean("PLUGINS", name, fallback=None)
    if s is None:
        logger.info(f"Trying to disable unkown plugin {name}. Continue however")
    UserSettings.config_parser.set("PLUGINS", name, str(False))
    UserSettings.save_config()