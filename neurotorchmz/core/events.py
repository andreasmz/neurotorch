from typing import Any, Callable, Self

from ..core.logs import logger

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

        cls.HOOKS: list[Callable[[Self], None]] = []

    @classmethod
    def hook(cls, func: Callable[[Self], None]) -> Callable[[Self], None]:
        cls.register(func)
        return func  
        
    @classmethod
    def register(cls, func: Callable[[Self], None]) -> None:
        cls.HOOKS.append(func)

    def __call__(self) -> Any:
        for hook in self.__class__.HOOKS:
            try:
                hook(self)
            except Exception:
                logger.warning(f"Failed to propagate {self.__class__.__name__} to {hook.__module__}:", exc_info=True)