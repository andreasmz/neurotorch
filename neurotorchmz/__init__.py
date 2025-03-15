__version__ = "25.3.1"
__author__ = "Andreas Brilka"

import threading
from .core.session import Session, Edition

def Start(headless: bool = False, edition: Edition = Edition.NEUROTORCH):
    session = Session(headless=headless, edition=edition)
    session.launch()

def Start_Background(edition:Edition = Edition.NEUROTORCH) -> Session:
    session = Session(headless=False, edition=edition)
    task = threading.Thread(target=session.launch)
    task.start()
    return session