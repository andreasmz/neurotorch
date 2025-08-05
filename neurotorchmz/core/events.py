from typing import Any
from ..core import session

from typing import Callable, Self
import inspect

class Event:
    HOOKS: list[Callable[[Self], None]] = []

    def __init_subclass__(cls) -> None:
        cls_init = cls.__init__

        def _init_wrapper(self: Self, *args: Any, **kwds: Any):
            cls_init(self, *args, **kwds)
            for hook in cls.HOOKS:
                hook(self)
        
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

    def __init__(self, session: session.Session) -> None:
        self.session = session