""" Module to detect signals in an ImageObject """
from .image import ImageObject, ImageView

import numpy as np
from scipy.signal import find_peaks
from typing import cast

class SignalObject:
    """ 
        A SignalObject holds a) references to the detected signal peaks of an ImageObject (for example stimulation) 
        b) provides a signal used for determing those peaks and c) provides a sliced image without the peaks. It is bound to
        an ImageObject, which could also be None

        :var int peakWidth_L: When providing the sliced image without the signal peaks, n frames to the left are also excluded
        :var int peakWidth_R: When providing the sliced image without the signal peaks, n frames to the right are also excluded
    
    """

    def __init__(self, imgObj: ImageObject|None):
        self._imgObj: ImageObject|None = imgObj
        self.peakWidth_L = 1
        self.peakWidth_R = 6
        self.Clear()

    def Clear(self):
        self._signal: np.ndarray|None = None
        self._peaks: list[int]|None = None
        self.ClearCache()        

    def ClearCache(self):
        self._imgObj_Sliced = None # Set to False if slice would be empty

    @property
    def signal(self) -> np.ndarray|None:
        return self._signal
    
    @signal.setter
    def signal(self, val):
        self._signal = val
        self._peaks = None

    @property
    def peaks(self) -> list[int]|None:
        return self._peaks
    
    @property
    def imgObj(self):
        return self._imgObj
    
    @imgObj.setter
    def imgObj(self, val: ImageObject|None):
        if not isinstance(val, ImageObject) or not val is None:
            raise TypeError(f"Setting the ImageObject of the SignalObject requires None or a ImageObject, but you provided {type(val)}")
        self.ClearCache()
        self._imgObj = val

    def SetPeakWidths(self, widthLeft: int, widthRight: int):
        self.peakWidth_L = widthLeft
        self.peakWidth_R = widthRight
        self.ClearCache()

    def DetectPeaks(self, prominenceFactor:float):
        if self._signal is None:
            return
        self._peaks = [int(p) for p in find_peaks(self._signal, prominence=prominenceFactor*(np.max(self._signal)-np.min(self._signal)))[0]]
        self._peaks.sort()
        self.ClearCache()

    @property
    def imgObj_Sliced(self) -> ImageObject | None:
        """
            Return a new SlicedImageObject (which is except for the name identical to an ImageObject), where diffImg has been set to the sliced version.
            Returns the sliced image object without signal or None if image or signal is not ready and False if image would be empty 
        """
        if self._imgObj is None or self._imgObj.imgDiff is None:
            return None
        if self._imgObj_Sliced is None:
            self._imgObj_Sliced = ImageObject()
            if self._peaks is None:
                return None
            if len(self._peaks) == 0:
                self._imgObj_Sliced.imgDiff = self._imgObj.imgDiff
            else:
                _slices = []
                for i, p in enumerate([*self._peaks, self._imgObj.imgDiff.shape[0]]):
                    pStart = (self._peaks[i-1]+1 + self.peakWidth_R) if i >= 1 else 0 
                    pStop = p - self.peakWidth_L if i != len(self._peaks) else p
                    if pStop <= pStart:
                        continue
                    _slices.append(slice(pStart, pStop))
                if len(_slices) > 0:
                    _sliceObj = np.s_[_slices]
                    self._imgObj_Sliced.imgDiff = np.concatenate([self._imgObj.imgDiff[_slice] for _slice in _sliceObj])
        return self._imgObj_Sliced

    def __del__(self):
        del self._imgObj

class ISignalDetectionAlgorithm:

    def __init__(self):
        pass

    def Clear(self):
        """
            This method is typically called when the GUI loads a new image
        """
        raise NotImplementedError()

    def GetSignal(self, imgObj: ImageObject) -> np.ndarray|None:
        """
            This method should return an 1D array interpretated as signal of the image
        """
        raise NotImplementedError()
    
class SigDetect_DiffMax(ISignalDetectionAlgorithm):

    def GetSignal(self, imgObj: ImageObject) -> np.ndarray|None:
        return imgObj.imgDiffView(ImageView.TEMPORAL).Max
    
class SigDetect_DiffStd(ISignalDetectionAlgorithm):

    def GetSignal(self, imgObj: ImageObject) -> np.ndarray|None:
        return imgObj.imgDiffView(ImageView.TEMPORAL).Std