from ..core.events import Event
from ..core.session import Session
import tkinter as tk

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
    
    @property
    def menu_plugins(self) -> tk.Menu:
        assert self.session.window is not None
        return self.session.window.menu_plugins
    

class WindowTKReadyEvent(WindowLoadedEvent):
    """ Triggers after the GUI has loaded and tkinter is in main loop """