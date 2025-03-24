from .image import ImageObject, ImageView

import numpy as np
from scipy.signal import find_peaks

class SlicedImageObject(ImageObject):
    """ A subclass of ImageObject for displaying a sliced image """

    # The only modification necessary is to disable the the automatic imgDiff calculation.

    @property
    def imgDiff_Normal(self) -> np.ndarray | None:
        # Removed the imgDiff calculation
        return self._imgDiff

class SignalObject:
    """ 
        A SignalObject holds a) references to the detected signal peaks of an ImageObject (for example stimulation) 
        b) provides a signal used for determing those peaks and c) provides a sliced image without the peaks. It is bound to
        an ImageObject, which could also be None

        :var int peakWidth_L: When providing the sliced image without the signal peaks, n frames to the left are also excluded
        :var int peakWidth_R: When providing the sliced image without the signal peaks, n frames to the right are also excluded
    
    """

    def __init__(self, imgObj: ImageObject|None):
        self._imgObj = imgObj
        self.peakWidth_L = 1
        self.peakWidth_R = 6
        self.Clear()

    def Clear(self):
        self._signal = None
        self._peaks = None
        self.ClearCache()        

    def ClearCache(self):
        self._imgObj_Sliced = None # Set to False if slice would be empty

    @property
    def signal(self) -> np.ndarray:
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

    def DetectPeaks(self, prominenceFactor:int):
        if self._signal is None:
            return
        self._peaks, _ = find_peaks(self._signal, prominence=prominenceFactor*(np.max(self._signal)-np.min(self._signal))) 
        self._peaks = [int(p) for p in self._peaks]
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
        pass

    def GetSignal(self, imgObj: ImageObject) -> np.array:
        """
            This method should return an 1D array interpretated as signal of the image
        """
        return None
    
class SigDetect_DiffMax(ISignalDetectionAlgorithm):

    def GetSignal(self, imgObj: ImageObject) -> np.array:
        return imgObj.imgDiffView(ImageView.TEMPORAL).Max
    
class SigDetect_DiffStd(ISignalDetectionAlgorithm):

    def GetSignal(self, imgObj: ImageObject) -> np.array:
        return imgObj.imgDiffView(ImageView.TEMPORAL).Std