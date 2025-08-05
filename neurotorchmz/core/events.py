from typing import Any
from ..core import session

from typing import Callable, Self
import inspect

class Event:
    """ 
    Base class for all events. To trigger on an event, add the hook decorator (e.g. @Event.hook) to the function definition
    """
    HOOKS: list[Callable[[Self], None]] = []

    def __init_subclass__(cls) -> None:
        cls_init = cls.__init__

        def _init_wrapper(self: Self, *args: Any, **kwds: Any):
            cls_init(self, *args, **kwds)
            self.__call__()
        
        cls.__init__ = _init_wrapper

    @classmethod
    def hook(cls, func: Callable[[Self], None]) -> None:
        cls.HOOKS.append(func)

    def __call__(self) -> Any:
        for hook in self.__class__.HOOKS:
            try:
                hook(self)
            except Exception:
                plugin_module = inspect.getmodule(inspect.stack()[1])
                session.logger.warning(f"Failed to propagate {self.__class__.__name__} to {plugin_module.__name__ if plugin_module is not None else ''}")

        
class SessionCreateEvent(Event):
    """ Triggers after a session is created (not launched yet) s"""

    def __init__(self, session: session.Session) -> None:
        self.session = session

class ImageObjectChangedEvent(Event):
    """ Triggers after the ImageObject of a session was changed """

    def __init__(self, session: session.Session) -> None:
        self.session = session