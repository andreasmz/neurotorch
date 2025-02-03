__version__ = "25.1.2"
__author__ = "Andreas Brilka"

from .gui.edition import Edition
from .utils.api import API, _API
from .utils.logger import logger
import logging
import threading

neutorch_GUI = None

def Start(edition:Edition = Edition.NEUROTORCH):
    global neutorch_GUI, API
    from .gui.window import Neurotorch_GUI

    if edition == Edition.NEUROTORCH_DEBUG:
        logger.setLevel(logging.DEBUG)
        logger.info("Started Neurotorch in debugging mode")

    neutorch_GUI = Neurotorch_GUI(__version__)
    API = _API(neutorch_GUI)
    neutorch_GUI.GUI(edition)

def Start_Background(edition:Edition = Edition.NEUROTORCH):
    task = threading.Thread(target=Start, args=(edition,))
    task.start()