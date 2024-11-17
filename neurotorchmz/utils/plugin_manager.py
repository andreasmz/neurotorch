import pathlib
import sys

from ..gui.settings import Neurotorch_Settings


class PluginManager:
    def __init__(self):
        self.pluginParentFolder = pathlib.Path(Neurotorch_Settings.DataPath)
        self.pluginFolder = self.pluginParentFolder / "plugins"
        self.pluginFolder.mkdir(exist_ok=True, parents=False)
        self.pluginInit = self.pluginFolder / "__init__.py"
        if not self.pluginInit.exists():
            with open(self.pluginInit, "w") as f:
                f.write("#Import here relative (!) your plugins")
        sys.path.insert(1, str(self.pluginParentFolder))
        import plugins