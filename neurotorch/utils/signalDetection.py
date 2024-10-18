from typing import Literal
import numpy as np
from scipy.signal import find_peaks
from neurotorch.utils.image import Img as ImgObj

class Signal:
    def __init__(self):
        self.signal = None
        self.peaks = None

    def Clear(self):
        self.signal = None
        self.peaks = None

    def DetectPeaks(self, prominenceFactor:int):
        if self.signal is None:
            return
        self.peaks = None
        self.peaks, _ = find_peaks(self.signal, prominence=prominenceFactor*(np.max(self.signal)-np.min(self.signal)))

    def SetSignal(self, signal: np.array):
        self.signal = signal
        self.peaks = None

class ISignalDetectionAlgorithm:

    def __init__(self):
        pass

    def Clear(self):
        """
            This method is typically called when the GUI loads a new image
        """
        pass

    def GetSignal(self, imgObj: ImgObj) -> np.array:
        """
            This method should return an 1D array interpretated as signal of the image
        """
        return None
    
class SigDetect_DiffMax(ISignalDetectionAlgorithm):

    def __init__(self):
        super().__init__()
        self._signal = None

    def Clear(self):
        self._signal = None

    def GetSignal(self, imgObj: ImgObj) -> np.array:
        if self._signal is None:
            self._signal = np.max(imgObj.imgDiff, axis=(1,2))
        return self._signal
    
class SigDetect_DiffStd(ISignalDetectionAlgorithm):

    def __init__(self):
        super().__init__()
        self._signal = None

    def Clear(self):
        self._signal = None

    def GetSignal(self, imgObj: ImgObj) -> np.array:
        if self._signal is None:
            self._signal = np.std(np.clip(imgObj.imgDiff,a_min=0, a_max=None), axis=(1,2))
        return self._signal

"""
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
            self.signal = np.std(np.clip(self.IMG.imgDiff,a_min=0, a_max=None), axis=(1,2))
        else:
            self.signal = None
            self.peaks = None
            return
        self.peaks, _ = find_peaks(self.signal, prominence=prominenceFactor*(np.max(self.signal)-np.min(self.signal)))

    def Clear(self):
        self.signal = None
        self.peaks = None
"""