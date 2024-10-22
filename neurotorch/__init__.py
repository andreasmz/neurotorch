from .gui.window import Neurotorch_GUI
from .utils.api_guy import API_GUI as _api_gui_class
import threading

neutorch_GUI = None
_apiGUI = None

def Get_API():
    if neutorch_GUI is None:
        return None
    return _apiGUI

def Start():
    global neutorch_GUI, _apiGUI
    neutorch_GUI = Neurotorch_GUI()
    _apiGUI = _api_gui_class(neutorch_GUI)
    neutorch_GUI.GUI()

def Start_Background():
    task = threading.Thread(target=Start)
    task.start()
    
if __name__ == "__main__":
    Start()

