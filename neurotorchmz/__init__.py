""" 
Neurotorch is a tool designed to extract regions of synaptic activity in neurons tagges with iGluSnFR, but is in general capable to find any kind of local brightness increase 
due to synaptic activity.
"""
__version__ = "25.9.3"
__author__ = "Andreas Brilka"

from .core.session import Session, Edition
from .core import api as API # pyright: ignore[reportUnusedImport]
from .core.logs import start_debugging, logger

def start(edition: Edition = Edition.NEUROTORCH, headless: bool = False, background: bool = False) -> Session:
    """ 
        Create a new session of Neurotorch. You can access it via the provided Session object returned by this function (only in background mode).
        In contrast to a session, use neurotorchmz.API if you don't want Neurotorch to manage your data and only want to access the detection functions.
    
        :param Edition edition: Choose which edition of Neurotorch you want to launch
        :param bool headless: When set to true, the tkinter GUI is not opened. Some functions may not work in headless mode
        :param bool background: Controls wether the GUI is running in a different thread. Note that tkinter may raise warnings, which can generally be ignored.
        :returns Session: A session object to interact with the GUI
    """
    session = Session(edition=edition)
    if not headless:
        session.launch(background=background)
    return session

def start_background(edition:Edition = Edition.NEUROTORCH, headless: bool = False) -> Session:
    """ 
        Create a new session of Neurotorch. You can access it via the provided Session object returned by this function (only in background mode).
        In contrast to a session, use neurotorchmz.API if you don't want Neurotorch to manage your data and only want to access the detection functions.
        
        Note: This function is an alias for start(background=True)

        :param Edition edition: Choose which edition of Neurotorch you want to launch
        :param bool headless: When set to true, the tkinter GUI is not opened. Some functions may not work in headless mode
        :param bool background: Controls wether the GUI is running in a different thread. Note that tkinter may raise warnings, which can generally be ignored.
        :returns Session: A session object to interact with the GUI
    """
    return start(edition=edition, headless=headless, background=True) 