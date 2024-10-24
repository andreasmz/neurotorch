from neurotorch.gui.window import Neurotorch_GUI

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
