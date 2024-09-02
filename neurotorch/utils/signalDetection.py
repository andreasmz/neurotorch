import numpy as np
from scipy.signal import find_peaks
from neurotorch.utils.image import Img

class Signal():

    def __init__(self, IMG: Img):
        self.IMG = IMG
        self.signal = None
        self.peaks = None


    def DetectSignal(self, algorithm:str, prominenceFactor: int):
        if (self.IMG.imgDiff is None):
            return
        if (algorithm == "diffMax"):
            self.signal = np.max(self.IMG.imgDiff, axis=(1,2))
        elif (algorithm == "diffStd"):
            self.signal = np.std(self.IMG.imgDiff, axis=(1,2))
        else:
            self.signal = None
            self.peaks = None
            return
        self.peaks, _ = find_peaks(self.signal, prominence=prominenceFactor*np.max(self.signal))

    def Clear(self):
        self.signal = None
        self.peaks = None