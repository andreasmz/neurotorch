__version__ = "24.11.6"

from .gui.window import Neurotorch_GUI, Edition
from .utils.api_guy import API_GUI as _api_gui_class
import threading

neutorch_GUI = None
_apiObj = None

def Get_API():
    if neutorch_GUI is None:
        return None
    return _apiObj

def Start(edition:Edition = Edition.NEUROTORCH):
    global neutorch_GUI, _apiObj
    neutorch_GUI = Neurotorch_GUI(__version__)
    _apiObj = _api_gui_class(neutorch_GUI)
    neutorch_GUI.GUI(edition)

def Start_Background(edition:Edition = Edition.NEUROTORCH):
    task = threading.Thread(target=Start, args=(edition,))
    task.start()