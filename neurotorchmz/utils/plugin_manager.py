import pathlib
import sys
import pkgutil
import logging

logger = logging.getLogger("NeurotorchMZ")

from ..gui.window import Neurotorch_GUI
from ..gui.settings import Neurotorch_Settings
from ..plugins import load_plugins


class PluginManager:
    def __init__(self, gui: Neurotorch_GUI):


    def __init__(self, gui: Neurotorch_GUI):
        self.gui = gui

        load_plugins(self.gui)

        self.userPluginParenterFolder = pathlib.Path(Neurotorch_Settings.DataPath)
        self.userPluginFolder = self.userPluginParenterFolder / "user_plugins"
        self.userPluginFolder.mkdir(exist_ok=True, parents=False)

        self.pluginInit = self.userPluginFolder / "__init__.py"
        if not self.pluginInit.exists():
            with open(self.pluginInit, "w") as f:
                f.write("#Import here relative (!) your plugins")
        sys.path.insert(1, str(self.userPluginParenterFolder))
        import user_plugins
        sys.path.remove(str(self.userPluginParenterFolder))