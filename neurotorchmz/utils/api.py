from .synapse_detection import *
from ..gui.components.general import Job
import threading

class _API():

    def __init__(self, gui = None):
        self.gui = None
        if gui is not None:
            from ..gui.window import Neurotorch_GUI
            from ..gui.tab3 import TabROIFinder
            self.gui:  Neurotorch_GUI = gui
            self._tab3Type = TabROIFinder


    @property
    def GUI(self):
        """
            The GUI object is holding all objects when running Neurotorch GUI including the loaded Image, the extracted data and the
            gui objects.
        """
        return self.gui
    
    @property
    def ImageObject(self):
        """
            The open image is stored into this wrapper class next to the calculated image data, for example the diffImage or the image
            stats (min, max, median, ...)
        """
        if self.gui is None: raise RuntimeError("The ImageObject is not available in headless mode")
        return self.gui.ImageObject
    
    @property
    def Signal(self):
        if self.gui is None: raise RuntimeError("The Signal is not available in headless mode")
        return self.gui.signal
    

    @property
    def TabROIFinder_DetectionResult(self):
        if self.gui is None: raise RuntimeError("The Detection result of Tab ROI Finder is not available in headless mode")
        tab3: self._tab3Type = self.gui.tabs[self._tab3Type]
        return tab3.detectionResult


    def SetDetectionResult(self, synapses: list[ISynapse]):
        if self.gui is None: raise RuntimeError("The Setting of the Detection Result is not available in headless mode")
        tab3: self._tab3Type = self.gui.tabs[self._tab3Type]
        tab3.detectionResult.modified = False

        def _Detect(job: Job):
            job.SetProgress(0, "Detect ROIs")
            tab3.detectionResult.SetISynapses(synapses)
            job.SetStopped("Detecting ROIs")
            tab3.Invalidate_ROIs()

        job = Job(steps=1)
        self.gui.statusbar.AddJob(job)
        threading.Thread(target=_Detect, args=(job,), daemon=True).start()

    def OpenFile(self, path: str, waitCompletion:bool=False):
        """
            Opens a file in neurotorch. Set waitCompletion to True to join the loading thread
        """
        if self.gui is None: raise RuntimeError("The Setting of the Detection Result is not available in headless mode")
        self.gui.statusbar._jobs.append(ImgObj().OpenFile(path, callback=self.gui._OpenImage_Callback, errorcallback=self.gui._OpenImage_CallbackError, waitCompletion=waitCompletion))

    def AutoDetect(self, waitCompletion:bool=False):
        """
            This function is equivalent to pushing the button 'Detect' in Tab ROI Finder. Set waitCompletion to True to join the loading thread
        """
        if self.gui is None: raise RuntimeError("The Setting of the Detection Result is not available in headless mode")
        tab3: self._tab3Type = self.gui.tabs[self._tab3Type]
        tab3.Detect(waitCompletion=waitCompletion)
    
    def ExportAsCSV(self, path:str|None=None, dropFrameIndex:bool = False):
        if self.gui is None: raise RuntimeError("The Setting of the Detection Result is not available in headless mode")
        tab3: self._tab3Type = self.gui.tabs[self._tab3Type]
        tab3.ExportCSVMultiM(path=path, dropFrame=dropFrameIndex)


API = _API()