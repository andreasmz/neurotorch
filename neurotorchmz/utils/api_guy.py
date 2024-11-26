from ..gui.window import Neurotorch_GUI
from ..gui.tab3 import TabROIFinder
from ..utils.synapse_detection import *
from ..gui.components import Job
import threading

class API_GUI():

    def __init__(self, gui: Neurotorch_GUI):
        self.gui = gui

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
        return self.gui.ImageObject
    
    @property
    def Signal(self):
        return self.gui.signal
    
    @property
    def TabROI_DetectionResult(self):
        return self.gui.tab3.detectionResult


    def SetDetectionResult(self, synapses: list[ISynapse]):
        tab3: TabROIFinder = self.gui.tabs[TabROIFinder]
        tab3.detectionResult.modified = False

        def _Detect(job: Job):
            job.SetProgress(0, "Detect ROIs")
            tab3.detectionResult.SetISynapses(synapses)
            job.SetStopped("Detecting ROIs")
            tab3.Invalidate_ROIs()

        job = Job(steps=1)
        self.gui.statusbar.AddJob(job)
        threading.Thread(target=_Detect, args=(job,), daemon=True).start()