import neurotorch.gui.window as window
import neurotorch.gui.settings as settings
import neurotorch.utils.resourcemanager as rsm
from neurotorch.utils.api import API
import threading

def Start():
    settings.UserSettings.ReadSettings()
    window.GUI.GUI()

def Start_Background():
    task = threading.Thread(target=Start)
    task.start()
    
if __name__ == "__main__":
    Start()

