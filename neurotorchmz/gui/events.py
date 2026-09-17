from ..core.events import Event
from ..core.session import Session, DetectionResult
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
    
    def menu_plugins(self, plugin_name) -> tk.Menu:
        """ Get the menu for the corosponding plugin"""
        assert self.session.window is not None
        return self.session.window.plugin_menus[plugin_name]
class WindowTKReadyEvent(WindowLoadedEvent):
    """ Triggers after the GUI has loaded and tkinter is in main loop """


class SynapseTreeviewContextMenuEvent(Event):
    """ This event is called when a SynapseTreeview is generating its context menu. As the menu is recreated on every click, a hook into the WindowLoadedEvent is not working """

    def __init__(self, import_context_menu: tk.Menu, export_context_menu: tk.Menu, detection_result: DetectionResult) -> None:
        self.import_context_menu = import_context_menu
        self.export_context_menu = export_context_menu
        self.detection_result = detection_result