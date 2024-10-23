import collections
from typing import Callable, Literal
import numpy as np
from scipy.ndimage import convolve, gaussian_filter
import threading
from enum import Enum
import time
import pims
import os, sys

from  neurotorch.gui.components import Job, JobState    

class ISubimage:
    """
        An interface to cache numpys mean, median, std, min, max, ... function calls on a given image object on a given axis
    """
    def __init__(self, img: np.ndarray, axis:tuple):
        self._img = img
        self._axis = axis
        self._mean = None
        self._std = None
        self._median = None
        self._min = None
        self._max = None

    @property
    def mean(self):
        if self._img is None:
            return None
        if self._mean is None:
            self._mean = np.mean(self._img, axis=self._axis)
        return self._mean
    
    @property
    def median(self):
        if self._img is None:
            return None
        if self._median is None:
            self._median = np.median(self._img, axis=self._axis)
        return self._median
    
    @property
    def std(self):
        if self._img is None:
            return None
        if self._std is None:
            self._std = np.std(self._img, axis=self._axis)
        return self._std
    
    @property
    def min(self):
        if self._img is None:
            return None
        if self._min is None:
            self._min = np.min(self._img, axis=self._axis)
        return self._min
    
    @property
    def max(self):
        if self._img is None:
            return None
        if self._max is None:
            self._max = np.max(self._img, axis=self._axis)
        return self._max

class ImageProperties(ISubimage):
    """
        A class that supports lazy loading and caching of image properties like mean, median, std, min, max and clippedMin (=np.min(0, self.min))
        Returns scalars (except for the img propertie, where it returns the image used to initializate this object.
    """

    def __init__(self, img):
        super().__init__(img, axis=None)

    @property
    def minClipped(self):
        if self.min is None:
            return None
        return np.max([0, self.min])
    
    @property
    def img(self):
        return self._img


class AxisImage(ISubimage):
    """
        A class that supports lazy loading and caching of subimages derived from an main image by calculating for example the
        mean, median, std, min or max over an given axis. Note that the axis specifies the axis which should be kept. Returns numpy.ndarrays
        Example: An AxisImage for an 3D Image (t, y, x) with argument axis=0 will calculate the mean (median, std, min, max) for each pixel.
        Providing axis=(1,2) will calculate the same for each image frame.
    """

    def __init__(self, img: np.ndarray, axis:tuple):
        super().__init__(img, axis)

    @property
    def mean(self) -> ImageProperties:
        return ImageProperties(super().mean)
    
    @property
    def median(self) -> ImageProperties:
        return ImageProperties(super().median)
    
    @property
    def std(self) -> ImageProperties:
        return ImageProperties(super().std)
    
    @property
    def min(self) -> ImageProperties:
        return ImageProperties(super().min)
    
    @property
    def max(self) -> ImageProperties:
        return ImageProperties(super().max)
    
    @property
    def meanArray(self) -> np.ndarray:
        return super().mean
    
    @property
    def medianArray(self) -> np.ndarray:
        return super().median
    
    @property
    def stdArray(self) -> np.ndarray:
        return super().std
    
    @property
    def minArray(self) -> np.ndarray:
        return super().min
    
    @property
    def maxArray(self) -> np.ndarray:
        return super().max


class ImgObj:
    """
        A class for holding a) the image provided in form an three dimensional numpy array (time, y, x) and b) the derived images and properties, for example
        the difference Image (imgDiff). All properties are lazy loaded, i. e. they are calculated on first access
    """
    
    # Static Values
    nd2_relevantMetadata = {
                            "Microscope": "Microscope",
                            "Modality": "Modality",
                            "EmWavelength": "Emission Wavelength", 
                            "ExWavelength": "Exitation Wavelength", 
                            "Exposure": "Exposure Time [ms]",
                            "Zoom": "Zoom",
                            "m_dXYPositionX0": "X Position",
                            "m_dXYPositionY0": "Y Position",
                            "m_dZPosition0": "Z Position",
                            }
    
    
    def __init__(self, lazyLoading = True):
        self.Clear()

    def Clear(self):
        self._img = None
        self._imgProps = None
        self._imgS = None # Image with signed dtype
        self._imgSpatial = None
        self._imgTemporal = None
        self._pimsmetadata = None

        self._imgDiff_mode = 0 #0: regular imgDiff, 1: convoluted imgDiff
        self._imgDiff = None
        self._imgDiffProps = None
        self._imgDiffConvFunc : Callable = self.Conv_GaussianBlur
        self._imgDiffConvArgs : tuple = (2,)
        self._imgDiffConv = {}
        self._imgDiffConvProps = {}
        self._imgDiffSpatial = None
        self._imgDiffTemporal = None
        self._imgDiffCSpatial = {}
        self._imgDiffCTemporal = {}

        self._customImages = {}
        self._customImagesProps = {}

        self._loadingThread : threading.Thread = None
        self._name = None

    @property
    def name(self) -> str:
        if self._name is None:
            return ""
        return self._name
    
    @name.setter
    def name(self, val):
        self._name = val

    @property
    def img(self) -> np.ndarray | None:
        """
            Returns the provided image in form of an np.ndarray or None if not loaded
        """
        return self._img
    
    @img.setter
    def img(self, image: np.ndarray) -> bool:
        self.Clear()
        if not ImgObj._IsValidImagestack(image): return False
        self._img = image
        return True

    @property
    def imgProps(self) -> ImageProperties | None:
        if self._img is None:
            return None
        if self._imgProps is None:
            self._imgProps = ImageProperties(self._img)
        return self._imgProps
    
    @property
    def imgS(self) -> np.ndarray | None:
        """
            Returns the provided image or None, but converted to an signed datatype (needed for example for calculating diffImg)
        """
        if self._img is None:
            return None
        if self._imgS is None:
            match (self._img.dtype):
                case "uint8":
                    self._imgS = self._img.view("int8")
                case "uint16":
                    self._imgS = self._img.view("int16")
                case "uint32":
                    self._imgS = self._img.view("int32")
                case "uint64":
                    self._imgS = self._img.view("int64")
                case _:
                    self._imgS = self._img
        return self._imgS

    @property
    def imgSpatial(self) -> AxisImage | None:
        """
            Returns the ImageProperties (mean, median, max, min, ...) for each pixel
        """
        if self._img is None:
            return None
        if self._imgSpatial is None:
            self._imgSpatial = AxisImage(self.img, axis=0)
        return self._imgSpatial
    
    @property
    def imgTemporal(self) -> AxisImage | None:
        """
            Returns the ImageProperties (mean, median, max, min, ...) per frame
        """
        if self._img is None:
            return None
        if self._imgTemporal is None:
            self._imgTemporal = AxisImage(self.img, axis=(1,2))
        return self._imgTemporal
    
    @property
    def imgDiff_Mode(self) -> Literal["Normal", "Convoluted"]:
        if self._imgDiff_mode == 1:
            return "Convoluted"
        return "Normal" 

    @imgDiff_Mode.setter
    def imgDiff_Mode(self, mode: Literal["Normal", "Convoluted"]):
        if mode == "Normal":
            self._imgDiff_mode = 0
        elif mode == "Convoluted":
            self._imgDiff_mode = 1
        else:
            raise ValueError("The mode parameter must be 'Normal' or 'Convoluted'")

    @property
    def imgDiff_Normal(self) -> np.ndarray | None:
        if self._imgDiff is None:
            if self._img is None:
                return None
            self._imgDiff = np.diff(self.imgS, axis=0)
        return self._imgDiff
    
    @property
    def imgDiff_Conv(self) -> np.ndarray | None:
        if self.imgDiff_Normal is None or self._imgDiffConvFunc is None or self._imgDiffConvArgs is None:
            return None
        _n = self._imgDiffConvFunc.__name__+str(self._imgDiffConvArgs)
        if _n not in self._imgDiffConv.keys():
            self._imgDiffConv[_n] = self._imgDiffConvFunc(args=self._imgDiffConvArgs)
        return self._imgDiffConv[_n]
    
    @property
    def imgDiff_NormalProps(self) -> ImageProperties | None:
        if self.imgDiff_Normal is None:
            return None
        if self._imgDiffProps is None:
            self._imgDiffProps = ImageProperties(self.imgDiff_Normal)
        return self._imgDiffProps

    @property
    def imgDiff_ConvProps(self) -> ImageProperties | None:
        if self.imgDiff_Conv is None or self._imgDiffConvFunc is None or self._imgDiffConvArgs is None:
            return None
        _n = self._imgDiffConvFunc.__name__+str(self._imgDiffConvArgs)
        if _n not in self._imgDiffConvProps.keys():
            self._imgDiffConvProps[_n] = ImageProperties(self.imgDiff_Conv)
        return self._imgDiffConvProps[_n]
    
    @property
    def imgDiff_NormalSpatial(self) -> AxisImage | None:
        if self.imgDiff_Normal is None:
            return None
        if self._imgDiffSpatial is None:
            self._imgDiffSpatial = AxisImage(self.imgDiff_Normal, axis=0)
        return self._imgDiffSpatial
    
    @property
    def imgDiff_NormalTemporal(self) -> AxisImage | None:
        if self.imgDiff_Normal is None:
            return None
        if self._imgDiffTemporal is None:
            self._imgDiffTemporal = AxisImage(self.imgDiff_Normal, axis=(1,2))
        return self._imgDiffTemporal
    
    @property
    def imgDiff_ConvSpatial(self) -> AxisImage | None:
        if self.imgDiff_Conv is None or self._imgDiffConvFunc is None or self._imgDiffConvArgs is None:
            return None
        _n = self._imgDiffConvFunc.__name__+str(self._imgDiffConvArgs)
        if _n not in self._imgDiffCSpatial.keys():
            self._imgDiffCSpatial[_n] = AxisImage(self.imgDiff_Conv, axis=0)
        return self._imgDiffCSpatial[_n]
    
    @property
    def imgDiff_ConvTemporal(self) -> AxisImage | None:
        if self.imgDiff_Conv is None or self._imgDiffConvFunc is None or self._imgDiffConvArgs is None:
            return None
        _n = self._imgDiffConvFunc.__name__+str(self._imgDiffConvArgs)
        if _n not in self._imgDiffCTemporal.keys():
            self._imgDiffCTemporal[_n] = AxisImage(self.imgDiff_Conv, axis=(1,2))
        return self._imgDiffCTemporal[_n]
    
    @property
    def imgDiff(self) -> np.ndarray | None:
        if self.imgDiff_Mode == "Convoluted":
            return self.imgDiff_Conv
        return self.imgDiff_Normal

    @imgDiff.setter
    def imgDiff(self, image: np.ndarray) -> bool:
        if not ImgObj._IsValidImagestack(image): return False
        self.Clear()
        self._imgDiff = image
        self._imgDiff_mode = "Normal"
        return True

    @property
    def imgDiffProps(self) -> ImageProperties | None:
        if self.imgDiff_Mode == "Convoluted":
            return self.imgDiff_ConvProps
        return self.imgDiff_NormalProps

    @property
    def imgDiffSpatial(self) -> AxisImage | None:
        if self.imgDiff_Mode == "Convoluted":
            return self.imgDiff_ConvSpatial
        return self.imgDiff_NormalSpatial
    
    @property
    def imgDiffTemporal(self) -> AxisImage | None:
        if self.imgDiff_Mode == "Convoluted":
            return self.imgDiff_ConvTemporal
        return self.imgDiff_NormalTemporal
    
    def GetCustomImage(self, name: str):
        if name in self._customImages.keys():
            return self._customImages[name]
        else:
            return None
        
    def GetCustomImagesProps(self, name: str):
        if name in self._customImagesProps.keys():
            return self._customImagesProps[name]
        else:
            return None
        
    def SetCustomImage(self, name: str, img: np.ndarray):
        self._customImages[name] = img
        self._customImagesProps = ImageProperties(self._customImages[name])
    

    @property
    def pims_metadata(self) -> collections.OrderedDict | None:
        return self._pimsmetadata

    def _IsValidImagestack(image):
        if not isinstance(image, np.ndarray):
            return False
        if len(image.shape) != 3:
            return False
        return True
    
    def SetConvolutionFunction(self, func: Callable, args: tuple):
        self._imgDiffConvFunc = func
        self._imgDiffConvArgs = args
    
    def Conv_GaussianBlur(self, args: tuple) -> np.ndarray | None:
        if self.imgDiff_Normal is None:
            return None
        if len(args) != 1:
            return None
        sigma = args[0]
        return gaussian_filter(self.imgDiff_Normal, sigma=sigma, axes=(1,2))
    

    def SetImage_Precompute(self, image: np.ndarray, name="", callback = None, errorcallback = None, convolute: bool = False) -> Literal["AlreadyLoading", "ImageUnsupported"] | Job:

        def _Precompute(job: Job):
            job.SetProgress(2, text="Calculating Spatial Image View")
            self.imgSpatial.meanArray
            self.imgSpatial.stdArray
            job.SetProgress(3, text="Calculating imgDiff")
            self.imgDiff
            if convolute:
                job.SetProgress(4, text="Applying Gaussian Filter on imgDiff")
                self.imgDiff_Mode = "Convoluted"
                self.imgDiff
            job.SetProgress(5, text="Calculating Spatial and Temporal imgDiff View")
            self.imgDiffSpatial.meanArray
            self.imgDiffSpatial.maxArray
            self.imgDiffSpatial.stdArray
            self.imgDiffTemporal.maxArray
            self.imgDiffTemporal.stdArray
            job.SetProgress(6, text="Loading Image")
            job.SetStopped("Loading Image")
            if callable is not None:
                callback(self)

        if self._loadingThread is not None and self._loadingThread.is_alive():
            if errorcallback is not None: errorcallback("AlreadyLoading")
            return "AlreadyLoading"

        self.Clear()
        if not isinstance(image, np.ndarray):
            if errorcallback is not None: errorcallback("ImageUnsupported")
            return "ImageUnsupported"
        if len(image.shape) != 3:
            if errorcallback is not None: errorcallback("ImageUnsupported", f"The image needs to have shape (t, y, x). Your shape is {image.shape}")
            return "ImageUnsupported"
        self._img = image
        self._name = name
        job = Job(steps=6)
        self._loadingThread = threading.Thread(target=_Precompute, args=(job,), daemon=True)
        self._loadingThread.start()
        return job

    def OpenFile(self, path: str, callback = None, errorcallback = None, convolute: bool = False) -> Literal["FileNotFound", "AlreadyLoading", "ImageUnsupported", "Wrong Shape"] | Job:

        def _Precompute(job: Job):
            job.SetProgress(0, "Opening File")
            try:
                _pimsImg = pims.open(path)
            except FileNotFoundError:
                job.SetStopped("File not found")
                if errorcallback is not None: errorcallback("FileNotFound")
                return "FileNotFound"
            except Exception as ex:
                job.SetStopped("Image Unsupported")
                if errorcallback is not None: errorcallback("ImageUnsupported", ex)
                return "ImageUnsupported"
            
            job.SetProgress(1, "Converting Image")
            imgNP = np.array([np.array(_pimsImg[i]) for i in range(_pimsImg.shape[0])])    
            if len(imgNP.shape) != 3:
                job.SetStopped("Image Unsupported")
                if errorcallback is not None: errorcallback("ImageUnsupported", f"The image needs to have shape (t, y, x). Your shape is {imgNP.shape}")
                return "ImageUnsupported"
            self.img = imgNP
            if getattr(_pimsImg, "get_metadata_raw", None) != None:
                self._pimsmetadata = collections.OrderedDict(sorted(_pimsImg.get_metadata_raw().items()))

            job.SetProgress(2, text="Calculating Spatial Image View")
            self.imgSpatial.meanArray
            self.imgSpatial.stdArray
            job.SetProgress(3, text="Calculating imgDiff")
            self.imgDiff
            if convolute:
                job.SetProgress(4, text="Applying Gaussian Filter on imgDiff")
                self.imgDiff_Mode = "Convoluted"
                self.imgDiff
            job.SetProgress(5, text="Calculating Spatial and Temporal imgDiff View")
            self.imgDiffSpatial.meanArray
            self.imgDiffSpatial.maxArray
            self.imgDiffSpatial.stdArray
            self.imgDiffTemporal.maxArray
            self.imgDiffTemporal.stdArray
            job.SetProgress(6, text="Loading Image")
            job.SetStopped("Loading Image")
            if callable is not None:
                callback(self)

        if self._loadingThread is not None and self._loadingThread.is_alive():
            return "AlreadyLoading"

        if path is None or path == "":
            return "FileNotFound"
        
        self.Clear()
        self.name = os.path.splitext(os.path.basename(path))[0]
        job = Job(steps=6)
        self._loadingThread = threading.Thread(target=_Precompute, args=(job,), daemon=True)
        self._loadingThread.start()
        return job