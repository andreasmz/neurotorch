from .. import __version__, __author__
from ..core.settings import (Neurotorch_Settings as Settings, Neurotorch_Resources as Resources, logger, log_exception_debug)
from ..utils.image import ImageProperties, AxisImage, ImageObject, ImageView
from ..utils.signalDetection import SignalObject
from ..gui.window import Neurotorch_GUI

from enum import Enum
import logging

class Edition(Enum):
    NEUROTORCH = 1
    NEUROTORCH_LIGHT = 2
    NEUROTORCH_DEBUG = 10


class Session:
    """ A session is the main entry into Neurotorch. It stores the loaded data and provides update functions for the GUI """

    def __init__(self, headless: bool = False, edition: Edition = Edition.NEUROTORCH):
        """
            A session is the main entry into Neurotorch. It stores the loaded data and provides update functions for the GUI

            :param bool headless: If set to true, no GUI is launched. This allows to use the API without launching a GUI
            :param Edition edition: Which edition of Neurotorch (for example NEUROTORCH_LIGHT, NEUROTORCH_DEBUG, ...) should be launched
        """
        self.edition: Edition = edition
        if self.edition == Edition.NEUROTORCH_DEBUG:
            Settings.stream_logging_handler.setLevel(logging.DEBUG)
            logger.debug("Enabled debugging output to console")
        self.window: Neurotorch_GUI|None = None    
        if not headless:
            self.window = Neurotorch_GUI()

        self._image_object: ImageObject| None = None
        self._signal_object: SignalObject| None = None
        self._ijH = None

    def launch(self):
        """ Launches the GUI if not headless mode """
        if self.window is None:
            raise RuntimeError("Can't launch the GUI if in headless mode")
        self.window.launch(edition=self.edition, session=self)

    @property
    def active_image_object(self) -> ImageObject|None:
        """ Retreive the currently active ImageObject """
        return self._image_object
    
    def set_active_image_object(self, imgObj: ImageObject|None):
        """ Replace the active ImageObject or remove it by setting it to zero. Creates a new SignalObject """
        self._image_object = imgObj
        self._signal_object = SignalObject(self._image_object)
    
    @property
    def active_image_signal(self) -> SignalObject|None:
        """ Retreive the signal of the currently active ImageObject. The concept of a signal is the generalization of extrinsic synaptic stimulation """
        if self._image_object is None:
            return None
        return self._signal_object
    
    @property
    def root(self):
        """ Returns the current tkinter root. If in headless mode, return None """
        if self.window is None:
            return None
        return self.window.root


    def _OpenImage_Callback(self, imgObj: ImageObject):
        """ Used when opening an ImageObject """
        self.set_active_image_object(imgObj)

    def _OpenImage_CallbackError(self, code, msg=""):
        match(code):
            case "FileNotFound":
                logger.warning(f"The given path doesn't exist or can't be opened. {msg}")
            case "AlreadyLoading":
                logger.warning(f"Please wait until the current image is loaded. {msg}")
            case "ImageUnsupported":
                logger.warning(f"The provided file is not supported. {msg}")
            case "WrongShape":
                logger.warning(f"The image has wrong shape ({msg}). It needs to have (t, y, x)")
            case _:
                logger.warning(f"An unkown error happend opening this image. {msg}") 
        if self.window is not None:
            self.window._OpenImage_CallbackError(code, msg)

        
# class SessionStorage:
#     """ A session storage holds data for the current session and is for example passed between tabs in the GUI """

#     def __init__(self):
#         self._image_object: ImageObject| None = None

#     @property
#     def active_image_object(self) -> ImageObject|None:
#         """ Retreive the currently active ImageObject """
#         return self._image_object
