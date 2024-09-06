import sys, os
sys.path.insert(1, os.path.abspath(os.path.join(os.path.join(__file__, os.pardir), os.pardir)))

import neurotorch.gui.window as window
import neurotorch.gui.settings as settings

settings.UserSettings.ReadSettings()
window.GUI.GUI(window.Edition.NEUROTORCH)