""" 
The plugin module provides a base class all plugins should implement. Hooks can be conveniently registered via decorators
"""

from typing import Self

class Plugin:
    """
    Base class for every plugin
    """

    NAME: str = "GenericPlugin"
    VERSION: str = "1.0.0"

    def __init_subclass__(cls: type[Self]) -> None:
        assert hasattr(cls, "NAME"), f"Plugin {cls.__name__} does not define a name"
        assert hasattr(cls, "VERSION"), f"{cls.NAME} does not define a version"
