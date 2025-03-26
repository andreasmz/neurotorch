import pkgutil
import importlib

from ..core.session import *
from ..gui.window import *

from .. import plugins

class Plugin:
    """ Abstract class for a Neurotorch plugin. All plugins must be a child of this class """

    NAME = ""
    VERSION = ""
    AUTHOR = ""
    DESC = ""

    def __init__(self, session: Session):
        """ Subclasses should not overwrite the constructor """
        self.session = session

    def menu_create_event(self, menu: tk.Menu):
        """ 
            Called by the GUI when creating the menubar. Overwritte this function (but keep still calling the
            base method with super().menu_create_event(menu=menu))
        """
        self.menu = menu
        self.menu.add_command()

    @property
    def plugin_menubar(self) -> tk.Menu:
        return self.session.window.menuPlugins

class PluginManager:
    """ The PluginManager is used by a window to load plugins """

    def __init__(self, session: Session):
        self.plugins: list[Plugin] = []
        self.session = session
    
    def load_plugins(self, path: Path):
        """ Load all plugins from a given path """
        for plugin_module_info in pkgutil.iter_modules(str(path)):
            plugin_module = importlib.import_module(str(path) + "." + plugin_module_info.name)