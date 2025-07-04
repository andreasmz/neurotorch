""" Neurotorch is a tool designed to extract regions of synaptic activity in neurons tagges with iGluSnFR, but is in general capable to find any kind of local brightness increase due to synaptic activity  """
__version__ = "25.4.1"
__author__ = "Andreas Brilka"

from .core.session import Session, Edition
from .utils.api import API

def Start(edition: Edition = Edition.NEUROTORCH, headless: bool = False, background: bool = False) -> Session:
    """ 
        Create a new session of Neurotorch. You can access it via the provided Session object returned by this function (only in background mode).

        In contrast to a session, use the API if you don't want Neurotorch to manage your data and only want to access the detection functions.
    
        :param Edition edition: Choose which edition of Neurotorch you want to launch
        :param bool headless: When set to true, the tkinter GUI is not opened. Some functions may not work in headless mode
        :param bool background: Controls wether the GUI is running in a different thread. Note that tkinter may raise warnings, which can generally be ignored.
    """
    session = Session(edition=edition)
    if not headless:
        session.launch(background=background)
    return session

def Start_Background(edition:Edition = Edition.NEUROTORCH, headless=False) -> Session:
    """ 
        Create a new session of NeurotorchMZ. The same as calling Start with background=True
    """
    return Start(edition=edition, headless=headless, background=True) 