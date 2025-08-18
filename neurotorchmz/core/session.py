""" Module holding code to launch and manage a Neurotorch program """
from .. import __version__, __author__
from ..core import logs, settings, resources, plugin_manager, events # pyright: ignore[reportUnusedImport]
from ..core.logs import logger
from ..core.serialize import Serializable
from ..core.task_system import Task
from ..utils.image import *
from ..utils.signal_detection import *
from ..utils.convolution_functions import denoising # pyright: ignore[reportUnusedImport]
from ..utils.synapse_detection import *

from enum import Enum
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

            :param Edition edition: Which edition of Neurotorch (for example NEUROTORCH_LIGHT, NEUROTORCH_DEBUG, ...) should be launched
        """

        self.edition: Edition = edition
        if self.edition == Edition.NEUROTORCH_DEBUG:
            logs.start_debugging()

        self.window = None 
        self._window_thread: threading.Thread|None = None

        self._image_path: Path|None = None
        self._image_object: ImageObject| None = None
        self._roifinder_detection_result: DetectionResult = DetectionResult()
        self._snalysis_detection_result: DetectionResult = DetectionResult()
        self.api = SessionAPI(self)
        SessionCreateEvent(session=self)


    def launch(self, background: bool = False):
        """
            Launches the GUI. The parameter background controls if a thread is used. Can only be called once

            :raises RuntimeError: The GUI has already been started
        """
        global window, window_events
        if self.window is not None:
            raise RuntimeError("The Neurotorch GUI has already been started")
        from ..gui import window
        from ..gui import events as window_events
        if not hasattr(window.tk, "_default_root") or window.tk._default_root is not None: # pyright: ignore[reportAttributeAccessIssue]
            raise RuntimeError("A different session is already bound to the GUI")
        self.window = window.Neurotorch_GUI(session=self)
        logger.info(f"Started NeurotorchMZ (GUI) version {__version__}")
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
        from ..gui.events import ImageObjectChangedEvent
        if self._image_object is not None:
            self._image_object.clear() # It's important to clear the object as the AxisImage, ImageProperties, ... create circular references not garbage collected
        self._image_object = imgObj
        if self._image_object is None:
            logger.debug(f"Cleared the active ImageObject")
        else:
            logger.debug(f"'{self._image_object.name}' is now the active ImageObject")
        self.notify_image_object_change()
        ImageObjectChangedEvent(session=self)

    @property
    def roifinder_detection_result(self) -> DetectionResult:
        """ Returns the detection result object of the roi finder tab """
        return self._roifinder_detection_result
    
    @property
    def synapse_analysis_detection_result(self) -> DetectionResult:
        """ Returns the detection result object of the synapses analysis tab """
        return self._snalysis_detection_result
    
    @property
    def root(self) -> "window.tk.Tk|None":
        """ Returns the current tkinter root. If in headless mode, return None """
        if self.window is None:
            return None
        return self.window.root

    def notify_image_object_change(self):
        """ When changing the ImageObject, call this function to notify the GUI about the change. Will invoke a ImageChanged TabUpdateEvent on all tabs in the window. """
        if self.window is not None:
            self.window.invoke_tab_update_event(window.ImageChangedEvent())

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
        task = imgObj.open_file(Path(path), precompute=True, run_async=run_async)
        task.add_callback(lambda: self.session.set_active_image_object(imgObj))
        if run_async:
            return task
        return imgObj
    
class SessionCreateEvent(events.Event):
    """ Triggers after a session is created (not launched yet) """

    def __init__(self, session: Session) -> None:
        self.session = session

plugin_manager.load_plugins_from_dir(path=Path(str(__file__)).parent.parent / "plugins", prefix="neurotorchmz.plugins")
plugin_manager.load_plugins_from_dir(path=settings.user_plugin_path, prefix="neurotorchmz.user.plugins")