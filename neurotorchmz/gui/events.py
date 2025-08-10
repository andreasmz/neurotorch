from ..core.events import Event
from ..core.session import Session
from ..core.plugin_manager import plugins
import tkinter as tk
from types import ModuleType
import inspect

class ImageObjectChangedEvent(Event):
    """ Triggers after the ImageObject of a session was changed """

    def __init__(self, session: Session) -> None:
        self.session = session

class WindowLoadedEvent(Event):
    """ Triggers after the GUI has loaded """

    def __init__(self, session: Session) -> None:
        self.session = session

    @property
    def menu_settings(self) -> tk.Menu:
        assert self.session.window is not None
        return self.session.window.menu_settings
    
    def menu_plugins(self, plugin_module) -> tk.Menu:
        """ Get the menu for the corosponding plugin"""
        global plugins

        assert self.session.window is not None
        for p in plugins:
            if p.__name__ in plugin_module.__name__:
                plugin = p
                break
        else:
            raise RuntimeError(f"Called menu_plugin from a non plugin")
        return self.session.window.plugin_menus[plugin]

class WindowTKReadyEvent(WindowLoadedEvent):
    """ Triggers after the GUI has loaded and tkinter is in main loop """


class SynapseTreeviewContextMenuEvent(Event):
    """ This event is called when a SynapseTreeview is generating its context menu. As the menu is recreated on every click, a hook into the WindowLoadedEvent is not working """

    def __init__(self, import_context_menu: tk.Menu, export_context_menu: tk.Menu) -> None:
        self.import_context_menu = import_context_menu
        self.export_context_menu = export_context_menu