from typing import Callable, Literal
import numpy as np
from scipy.signal import find_peaks
from .image import ImgObj, AxisImage, ImageProperties

class SignalObj:

    def __init__(self, imgObjCallback: Callable):
        self._imgObjCallback = imgObjCallback
        self._peakWidth_L = 1
        self._peakWidth_R = 6
        self.Clear()

    def Clear(self):
        self._signal = None
        self._peaks = None
        self.ClearCache()        

    def ClearCache(self):
        self._imgObj_Sliced = None

    @property
    def signal(self) -> np.ndarray:
        return self._signal
    
    @signal.setter
    def signal(self, val):
        self._signal = val
        self._peaks = None

    @property
    def peaks(self) -> np.ndarray:
        return self._peaks
    
    @property
    def imgObjCallback(self):
        return self._imgObjCallback
    
    def SetPeakWidths(self, widthLeft: int, widthRight: int):
        self._peakWidth_L = widthLeft
        self._peakWidth_R = widthRight
        self.ClearCache()

    @imgObjCallback.setter
    def imgObjCallback(self, val):
        self.ClearCache()
        self._imgObjCallback = val
    
    def DetectPeaks(self, prominenceFactor:int):
        if self._signal is None:
            return
        self._peaks, _ = find_peaks(self._signal, prominence=prominenceFactor*(np.max(self._signal)-np.min(self._signal))) 
        self._peaks.sort()
        self.ClearCache()

    @property
    def imgObj_Sliced(self) -> ImgObj | None:
        if self._imgObjCallback is None:
            return None
        imgObj: ImgObj = self._imgObjCallback()
        if imgObj is None or imgObj.imgDiff is None or self._imgObj_Sliced is False:
            return None
        if self._imgObj_Sliced is None:
            self._imgObj_Sliced = ImgObj()
            if self._peaks is None:
                return None
            if len(self._peaks) == 0:
                self._imgObj_Sliced.imgDiff = imgObj.imgDiff
            else:
                _slices = []
                for i, p in enumerate([*self._peaks, imgObj.imgDiff.shape[0]]):
                    pStart = (self._peaks[i-1]+1 + self._peakWidth_R) if i >= 1 else 0 
                    pStop = p - self._peakWidth_L
                    if pStop <= pStart:
                        continue
                    _slices.append(slice(pStart, pStop))
                if len(_slices) > 0:
                    _sliceObj = np.s_[_slices]
                    self._imgObj_Sliced.imgDiff = np.concatenate([imgObj.imgDiff[_slice] for _slice in _sliceObj])
                else:
                    self._imgObj_Sliced = False
                    return None
        return self._imgObj_Sliced


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
        return imgObj.imgDiffView(ImgObj.TEMPORAL).Max
    
class SigDetect_DiffStd(ISignalDetectionAlgorithm):

    def GetSignal(self, imgObj: ImgObj) -> np.array:
        return imgObj.imgDiffView(ImgObj.TEMPORAL).Std