__version__ = "24.12.2"

from .gui.edition import Edition
from .utils.api import API, _API
import threading
import matplotlib
matplotlib.use('TkAgg')

neutorch_GUI = None

def Start(edition:Edition = Edition.NEUROTORCH):
    global neutorch_GUI, API
    from .gui.window import Neurotorch_GUI

    neutorch_GUI = Neurotorch_GUI(__version__)
    API = _API(neutorch_GUI)
    neutorch_GUI.GUI(edition)

def Start_Background(edition:Edition = Edition.NEUROTORCH):
    task = threading.Thread(target=Start, args=(edition,))
    task.start()