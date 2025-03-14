__version__ = "25.3.1"
__author__ = "Andreas Brilka"

import threading
import logging
from enum import Enum

class Edition(Enum):
    NEUROTORCH = 1
    NEUROTORCH_LIGHT = 2
    NEUROTORCH_DEBUG = 10

from gui.settings import logger, file_logging_handler
from .utils.api import *

neutorch_GUI = None



def Start(edition:Edition = Edition.NEUROTORCH):
    global neutorch_GUI, API
    from .gui.window import Neurotorch_GUI

    if edition == Edition.NEUROTORCH_DEBUG:
        file_logging_handler.setLevel(logging.DEBUG)
        logger.debug("Enabled debugging output to console")

    neutorch_GUI = Neurotorch_GUI(__version__)
    API = _API(neutorch_GUI)
    logger.debug(f"Started NeurotorchMZ version {__version__}")
    neutorch_GUI.GUI(edition)

def Start_Background(edition:Edition = Edition.NEUROTORCH):
    task = threading.Thread(target=Start, args=(edition,))
    task.start()