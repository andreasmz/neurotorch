from typing import Literal
import numpy as np
from scipy.signal import find_peaks
from neurotorch.utils.image import ImgObj

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

    def GetSignal(self, imgObj: ImgObj) -> np.array:
        return imgObj.imgDiffTemporal.maxArray
    
class SigDetect_DiffStd(ISignalDetectionAlgorithm):

    def GetSignal(self, imgObj: ImgObj) -> np.array:
        return imgObj.imgDiffTemporal.stdArray