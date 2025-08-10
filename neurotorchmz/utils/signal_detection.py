""" Module to detect signals in an ImageObject """
from ..utils.image import *
from ..core.settings import UserSettings

import numpy as np
from scipy.signal import find_peaks
from typing import Literal

class ISignalDetectionAlgorithm:
    """ Abstract base class for a detection algorithm for signals. Must only implement a get_signal method"""

    def __init__(self):
        pass

    def get_signal(self, imgObj: ImageObject) -> np.ndarray|None:
        """
            This method should return an 1D array (t,) interpretated as signal of the image
        """
        raise NotImplementedError()

class SignalObject:
    """ 
        A SignalObject holds a) references to the detected signal peaks of an ImageObject (for example stimulation) 
        b) provides a signal used for determing those peaks and c) provides a sliced image including only / no peak frames. 
        It is bound to an ImageObject and calculates its values lazy. The ImageObject is reponsible to call clear() when the
        underlying images (e.g. through a convolution of loading a new image) have changed.

        :var int peakWidth_L: When providing the sliced image without the signal peaks, n frames to the left are also excluded
        :var int peakWidth_R: When providing the sliced image without the signal peaks, n frames to the right are also excluded
    
    """

    PEAK_WIDTH_LEFT: int = 1
    PEAK_WIDTH_RIGHT: int = 6
    ALGORITHM: ISignalDetectionAlgorithm = ISignalDetectionAlgorithm()

    def __init__(self, imgObj: ImageObject):
        self.imgObj: ImageObject = imgObj
        self._prominence_factor: float = 1.1
        self.clear()

    def clear(self):
        """ Calling clear() will forget the current signal and found peaks. Should be called, when the underlying images of the ImageObject change """
        self._signal: np.ndarray|None = None
        self.clear_peaks()

    def clear_peaks(self):
        """ Clears the peaks and the cached sliced images. """
        self._peaks: list[int]|None = None

        self._img_without_signal_views: dict[ImageView, AxisImage] = {}
        self._img_only_signal_views: dict[ImageView, AxisImage] = {}
        self._img_diff_without_signal_views: dict[ImageView, AxisImage] = {}
        self._img_diff_only_signal_views: dict[ImageView, AxisImage] = {}

    @property
    def signal(self) -> np.ndarray|None:
        """ Returns the signal from the image by calculating it using SignalObject.ALGORITHM on the first call"""
        if self._signal is None:
            self._signal = self.__class__.ALGORITHM.get_signal(self.imgObj)
        return self._signal

    @property
    def prominence_factor(self) -> float:
        """ 
        The prominence factor is used to find peaks in the signal, as scipy.signal.find_peaks with prominence = factor*(max(signal)-min(signal)) is used
        """
        return self._prominence_factor
    
    @prominence_factor.setter
    def prominence_factor(self, val: float) -> None:
        self._prominence_factor = val
        self.clear_peaks()

    @property
    def peaks(self) -> list[int]|None:
        """ Returns the peaks given the current signal and prominence as sorted interger list (ascending). The peaks are calculated on first call """
        if self.signal is None:
            return None
        if self._peaks is None:
            self._peaks = [int(p) for p in find_peaks(self.signal, prominence=self.prominence_factor*(np.max(self.signal)-np.min(self.signal)))[0]]
            self._peaks.sort()
        return self._peaks
    
    @property
    def img_props_only_signal(self) -> ImageProperties:
        return self.get_view("img", "only_signal", mode=ImageView.DEFAULT).ImageProps
    
    @property
    def img_props_without_signal(self) -> ImageProperties:
        return self.get_view("img", "without_signal", mode=ImageView.DEFAULT).ImageProps
    
    @property
    def img_diff_props_only_signal(self) -> ImageProperties:
        return self.get_view("img_diff", "only_signal", mode=ImageView.DEFAULT).ImageProps
    
    @property
    def img_diff_props_without_signal(self) -> ImageProperties:
        return self.get_view("img_diff", "without_signal", mode=ImageView.DEFAULT).ImageProps
    
    def img_only_signal_view(self, mode: ImageView) -> AxisImage:
        return self.get_view("img", "only_signal", mode)

    def img_without_signal_view(self, mode: ImageView) -> AxisImage:
        return self.get_view("img", "without_signal", mode)

    def img_diff_only_signal_view(self, mode: ImageView) -> AxisImage:
        return self.get_view("img_diff", "only_signal", mode)

    def img_diff_without_signal_view(self, mode: ImageView) -> AxisImage:
        return self.get_view("img_diff", "without_signal", mode)


    def get_view(self, img_type: Literal["img", "img_diff"], slice_type: Literal["only_signal", "without_signal"], mode: ImageView) -> AxisImage:
        """ Internal function to get a view for every combination of img/img_diff and with or without signal frames """
        match img_type:
            case "img":
                _img = self.imgObj.img
                p_offset = 1
                match slice_type:
                    case "only_signal":
                        _views = self._img_only_signal_views
                    case "without_signal":
                        _views = self._img_without_signal_views
                    case _:
                        raise ValueError(f"Invalid value '{slice_type}' for parameter slice_type")
            case "img_diff":
                _img = self.imgObj.imgDiff
                p_offset = 0
                match slice_type:
                    case "only_signal":
                        _views = self._img_diff_only_signal_views
                    case "without_signal":
                        _views = self._img_diff_without_signal_views
                    case _:
                        raise ValueError(f"Invalid value '{slice_type}' for parameter slice_type")
            case _:
                raise ValueError(f"Invalid value '{img_type}' for parameter img_type")
            
        if _img is None or self.peaks is None:
            return AxisImage(None, axis=mode.value, name=self.imgObj.name)
        
        if not ImageView.DEFAULT in _views.keys():
            logger.debug(f"Calculating {slice_type} slice for {img_type}")
            _slices = []
            if slice_type == "only_signal":
                for p in self.peaks:
                    p += p_offset
                    pStart = max((p - SignalObject.PEAK_WIDTH_LEFT), 0)
                    pStop = min((p + SignalObject.PEAK_WIDTH_RIGHT + 1) , _img.shape[0])
                    _slices.append(slice(pStart, pStop))
            elif slice_type == "without_signal":
                for i, p in enumerate([*self.peaks, _img.shape[0]]):
                    pStart = (self.peaks[i-1]+1+p_offset + SignalObject.PEAK_WIDTH_RIGHT) if i >= 1 else 0
                    pStop = p + p_offset - SignalObject.PEAK_WIDTH_LEFT if i != len(self.peaks) else p
                    if pStop <= pStart:
                        continue
                    _slices.append(slice(pStart, pStop))
            if len(_slices) > 0:
                _sliceObj = np.s_[_slices]
                _views[ImageView.DEFAULT] = AxisImage(img=np.concatenate([_img[_slice] for _slice in _sliceObj]), axis=ImageView.DEFAULT.value, name=f"{self.imgObj.name}-{img_type}-{slice_type}")
            else:
                _views[ImageView.DEFAULT] = AxisImage(img=None, axis=ImageView.DEFAULT.value, name=f"{self.imgObj.name}-{img_type}-{slice_type}")

        if mode not in _views.keys():
            _views[mode] = AxisImage(_views[ImageView.DEFAULT].image, axis=mode.value, name=f"{self.imgObj.name}-{img_type}-{slice_type}")
        return _views[mode]
    
    def export_img_only_signal(self, path: Path) -> None:
        """ Export the current img """
        if self.img_props_only_signal.img is None:
            raise NoImageError()
        if not path.is_file() or not path.parent.exists():
            raise ValueError(f"The path '{str(path)}' is invalid")
        match path.suffix.lower():
            case ".tif"|".tiff":
                tifffile.imwrite(path, data=self.img_props_only_signal.img, metadata=self.imgObj.metadata)
            case _:
                raise UnsupportedExtensionError(f"The extension '{path.suffix}' is not supported for exporting")
        logger.info(f"Exported the video as '{path.name}'")
    
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