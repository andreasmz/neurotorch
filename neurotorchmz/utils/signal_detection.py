""" Module to detect signals in an ImageObject """
from .image import ImageObject, ImageView

import numpy as np
from scipy.signal import find_peaks
from typing import Literal



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
    
class SigDetect_DiffMax(ISignalDetectionAlgorithm):

    def get_signal(self, imgObj: ImageObject) -> np.ndarray|None:
        return imgObj.imgDiffView(ImageView.TEMPORAL).Max
    
class SigDetect_DiffStd(ISignalDetectionAlgorithm):

    def get_signal(self, imgObj: ImageObject) -> np.ndarray|None:
        return imgObj.imgDiffView(ImageView.TEMPORAL).Std