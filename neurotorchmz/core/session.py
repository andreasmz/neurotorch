from .. import __version__, __author__
from ..core.settings import (Neurotorch_Settings as Settings, Neurotorch_Resources as Resources, logger, log_exception_debug, stream_logging_handler)
from ..core.serialize import Serializable
from ..utils.image import *
from ..utils.signal_detection import SignalObject
from ..utils.synapse_detection import *

from enum import Enum
import logging
import threading
from pathlib import Path

class Edition(Enum):
    """ The edition of Neurotorch which should be launched """
    NEUROTORCH = 1
    """ Standard version """
    NEUROTORCH_LIGHT = 2
    """ Launches Neurotorch without some external connectivity. Designed to minimize external dependencies and for bundling """
    NEUROTORCH_DEBUG = 10
    """ Launches the developer version with (depending on your version) additional features and debugging output """

class Session(Serializable):
    """ 
        A session is the main entry into Neurotorch. It stores the loaded data and provides update functions for the GUI

        In contrast, if you only want to access the detection functions and don't need Neurotorch to handle the images for you, use the API
    """

    def __init__(self, edition: Edition = Edition.NEUROTORCH):
        """
            A session is the main entry into Neurotorch. It stores the loaded data and provides update functions for the GUI

            :param bool headless: If set to true, no GUI is launched. This allows to use the API without launching a GUI
            :param Edition edition: Which edition of Neurotorch (for example NEUROTORCH_LIGHT, NEUROTORCH_DEBUG, ...) should be launched
        """
        self.edition: Edition = edition
        if self.edition == Edition.NEUROTORCH_DEBUG:
            stream_logging_handler.setLevel(logging.DEBUG)
            logger.debug("Enabled debugging output to console")

        self.window = None 
        self._window_thread = None

        self._image_path: Path|None = None
        self._image_object: ImageObject| None = None
        self._signal_object: SignalObject| None = None
        self._roifinder_detection_result: DetectionResult|None = DetectionResult()
        self._snalysis_detection_result: DetectionResult|None = DetectionResult()
        self._ijH = None
        self.api = SessionAPI(self)

    def launch(self, background: bool = False):
        """
            Launches the GUI. The parameter background controls if a thread is used. Can only be called once

            :raises RuntimeError: The GUI has already been started
        """
        if self.window is not None:
            raise RuntimeError("The Neurotorch GUI has already been started")
        from ..gui.window import Neurotorch_GUI
        self.window = Neurotorch_GUI(session=self)
        if background:
            task = threading.Thread(target=self.window.launch, name="Neurotorch GUI", args=(self.edition,))
            task.start()
        else:
            self.window.launch(edition=self.edition)

    @property
    def active_image_object(self) -> ImageObject|None:
        """ Retreive or set the currently active ImageObject """
        return self._image_object
    
    def set_active_image_object(self, imgObj: ImageObject|None):
        """ Replace the active ImageObject or remove it by setting it to zero. Creates a new SignalObject """
        if self._image_object is not None:
            self._image_object.Clear() # It's important to clear the object as the AxisImage, ImageProperties, ... create circular references not garbage collected
        self._image_object = imgObj
        if imgObj is None:
            self._signal_object = None
        else:
            self._signal_object = SignalObject(self._image_object)
            self._roifinder_detection_result.clear()
            self._snalysis_detection_result.clear()
        self.notify_image_object_change()
    
    @property
    def active_image_signal(self) -> SignalObject|None:
        """ Retreive the signal of the currently active ImageObject. The concept of a signal is the generalization of extrinsic synaptic stimulation """
        if self._image_object is None:
            return None
        return self._signal_object

    @property
    def roifinder_detection_result(self) -> DetectionResult:
        """ Returns the detection result object of the roi finder tab """
        return self._roifinder_detection_result
    
    @property
    def synapse_analysis_detection_result(self) -> DetectionResult:
        """ Returns the detection result object of the synapses analysis tab """
        return self._snalysis_detection_result
    
    @property
    def root(self):
        """ Returns the current tkinter root. If in headless mode, return None """
        if self.window is None:
            return None
        return self.window.root
    
    @property
    def ijH(self):
        """ Returns the ImageJHandler object or None if not yet imported """
        return self._ijH

    def import_ijh(self):
        """ Import the ImageJ helper (ijh)"""
        from neurotorchmz.utils.pyimagej import ImageJHandler
        self._ijH = ImageJHandler(self)

    def notify_image_object_change(self):
        """ When changing the ImageObject, call this function to notify the GUI about the change. Will invoke a ImageChanged TabUpdateEvent on all tabs in the window. """
        if self.window is not None:
            from ..gui.window import ImageChangedEvent # Import not in the file header to avoid circular imports. It is already imported in launch(), so minimal performance loss
            self.window.invoke_tab_update_event(ImageChangedEvent())

    def serialize(self, **kwargs) -> dict:
        pass
    
    def deserialize(self, serialize_dict:dict, **kwargs):
        pass


class SessionAPI:
    """ A class bound to a session object, which allows the user to communicate with the Neurotorch GUI. If you want to use the API without the object management of Neurotorch, use the neurotorchmz.API instead """
    
    def __init__(self, session: Session):
        self.session = session

    def open_file(self, path: Path, run_async:bool = True) -> ImageObject|Task:
        """ 
            Opens the given path in Neurotorch

            :param pathlib.Path path: The path to the file
            :param bool run_async: Controls if the task runs in a different thread (recommended, as it will not block the window)
            :returns ImageObject|Task: The ImageObject (run_async=False) or a task object. If a task is returned, use task.add_callback(function=function) to get notified once the image is loaded
            :raises AlreadyLoading: There is already a task working on this ImageObject
            :raises FileNotFoundError: Can't find the file
            :raises UnsupportedImageError: The image is unsupported or has an error
            :raises ImageShapeError: The image has an invalid shape
        """
        imgObj = ImageObject()
        self.session.set_active_image_object(imgObj)
        task = imgObj.OpenFile(Path(path), precompute=True, calc_convoluted=False, run_async=run_async)
        task.add_callback(self.session.notify_image_object_change)
        if run_async:
            return task
        return imgObj
        