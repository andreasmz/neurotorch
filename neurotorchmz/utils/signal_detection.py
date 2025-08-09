""" Module to detect signals in an ImageObject """
from ..utils.image import *

import numpy as np

class ISignalDetectionAlgorithm:

    def __init__(self):
        pass

    def clear(self):
        """
            This method is typically called when the GUI loads a new image
        """
        raise NotImplementedError()

    def get_signal(self, imgObj: ImageObject) -> np.ndarray|None:
        """
            This method should return an 1D array interpretated as signal of the image
        """
        raise NotImplementedError()

class SignalObject:
    """ 
        A SignalObject holds a) references to the detected signal peaks of an ImageObject (for example stimulation) 
        b) provides a signal used for determing those peaks and c) provides a sliced image without the peaks. It is bound to
        an ImageObject, which could also be None

        :var int peakWidth_L: When providing the sliced image without the signal peaks, n frames to the left are also excluded
        :var int peakWidth_R: When providing the sliced image without the signal peaks, n frames to the right are also excluded
    
    """

    PEAK_WIDTH_LEFT: int = 1
    PEAK_WIDTH_RIGHT: int = 6
    ALGORITHM: ISignalDetectionAlgorithm = ISignalDetectionAlgorithm()

    def __init__(self, imgObj: ImageObject|None):
        self.imgObj: ImageObject|None = imgObj
        self.clear()

    def clear(self):
        self._signal: np.ndarray|None = None
        self._peaks: list[int]|None = None
        self.clear_cache()        

    def clear_cache(self):
        self._imgObj_sliced: None|Literal[False]|ImageObject = None # Set to False if slice would be empty

    @property
    def signal(self) -> np.ndarray|None:
        if self.imgObj is None:
            return None
        if self._signal is None:
            self._signal = self.__class__.ALGORITHM.get_signal(self.imgObj)
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
        self.clear_cache()
        self._imgObj = val

    def detect_peaks(self, prominenceFactor:float):
        if self.signal is None:
            return
        self._peaks = [int(p) for p in find_peaks(self._signal, prominence=prominenceFactor*(np.max(self.signal)-np.min(self.signal)))[0]]
        self._peaks.sort()
        self.clear_cache()

    @property
    def imgObj_sliced(self) -> ImageObject | Literal[False] | None:
        """
            Return a new SlicedImageObject (which is except for the name identical to an ImageObject), where diffImg has been set to the sliced version.
            Returns the sliced image object without signal or None if image or signal is not ready and False if image would be empty 
        """
        if self._imgObj is None or self._imgObj.imgDiff is None:
            return None
        if self._imgObj_sliced is None:
            self._imgObj_sliced = ImageObject()
            if self._peaks is None:
                return None
            if len(self._peaks) == 0:
                self._imgObj_sliced.imgDiff = self._imgObj.imgDiff
            else:
                _slices = []
                for i, p in enumerate([*self._peaks, self._imgObj.imgDiff.shape[0]]):
                    pStart = (self._peaks[i-1]+1 + SignalObject.PEAK_WIDTH_RIGHT) if i >= 1 else 0 
                    pStop = p - SignalObject.PEAK_WIDTH_LEFT if i != len(self._peaks) else p
                    if pStop <= pStart:
                        continue
                    _slices.append(slice(pStart, pStop))
                if len(_slices) > 0:
                    _sliceObj = np.s_[_slices]
                    self._imgObj_sliced.imgDiff = np.concatenate([self._imgObj.imgDiff[_slice] for _slice in _sliceObj])
        return self._imgObj_sliced
    
    @classmethod
    def load_settings(cls) -> None:
        cls.PEAK_WIDTH_LEFT = UserSettings.SIGNAL_DETECTION.peak_width_left.get()
        cls.PEAK_WIDTH_RIGHT = UserSettings.SIGNAL_DETECTION.peak_width_right.get()

    @classmethod
    def set_settings(cls, peak_width_left: int|None = None, peak_width_right: int|None = None) -> None:
        if peak_width_left is not None and peak_width_left != cls.PEAK_WIDTH_LEFT:
            cls.PEAK_WIDTH_LEFT = peak_width_left
            UserSettings.SIGNAL_DETECTION.peak_width_left.set(peak_width_left)
        if peak_width_right is not None and peak_width_right != cls.PEAK_WIDTH_RIGHT:
            UserSettings.SIGNAL_DETECTION.peak_width_right.set(peak_width_right)



SignalObject.load_settings()
    
class SigDetect_DiffMax(ISignalDetectionAlgorithm):

    def get_signal(self, imgObj: ImageObject) -> np.ndarray|None:
        return imgObj.imgDiffView(ImageView.TEMPORAL).Max
    
class SigDetect_DiffStd(ISignalDetectionAlgorithm):

    def get_signal(self, imgObj: ImageObject) -> np.ndarray|None:
        return imgObj.imgDiffView(ImageView.TEMPORAL).Std