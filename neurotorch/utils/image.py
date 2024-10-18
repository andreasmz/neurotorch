from typing import Literal
import numpy as np
from scipy.ndimage import convolve, gaussian_filter
import threading
from enum import Enum
import time

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
        return np.min(0, self.min)


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


class ImgObj:
    """
        A class for holding a) the image provided in form an three dimensional numpy array (time, y, x) and b) the derived images and properties, for example
        the difference Image (imgDiff). All properties are lazy loaded, i. e. they are calculated on first access
    """
    def __init__(self, lazyLoading = True):
        self.Clear()

    def Clear(self):
        self._img = None
        self._imgProps = None
        self._imgS = None # Image with signed dtype
        self._imgSpatial = None
        self._imgTemporal = None

        self._imgDiff_mode = 0 #0: regular imgDiff, 1: convoluted imgDiff
        self._imgDiff = None
        self._imgDiffProps = None
        self._imgDiffConv = None
        self._imgDiffConvProps = None
        self._imgDiffSpatial = None
        self._imgDiffTemporal = None
        self._imgDiffCSpatial = None
        self._imgDiffCTemporal = None

        self._loadingThread : threading.Thread = None

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
        if self.imgDiff_Normal is None:
            return None
        if self._imgDiffConv is None:
            self._imgDiffConv = gaussian_filter(self.imgDiff_Normal, sigma=2, axes=(1,2))
        return self._imgDiffConv
    
    @property
    def imgDiff_NormalProps(self) -> ImageProperties | None:
        if self.imgDiff_Normal is None:
            return None
        if self._imgDiffProps is None:
            self._imgDiffProps = ImageProperties(self.imgDiff_Normal)
        return self._imgDiffProps

    @property
    def imgDiff_ConvProps(self) -> ImageProperties | None:
        if self.imgDiff_Conv is None:
            return None
        if self._imgDiffConvProps is None:
            self._imgDiffConvProps = ImageProperties(self.imgDiff_Conv)
        return self._imgDiffConvProps
    
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
        if self.imgDiff_Conv is None:
            return None
        if self._imgDiffCSpatial is None:
            self._imgDiffCSpatial = AxisImage(self.imgDiff_Conv, axis=0)
        return self._imgDiffCSpatial
    
    @property
    def imgDiff_ConvTemporal(self) -> AxisImage | None:
        if self.imgDiff_Conv is None:
            return None
        if self._imgDiffCTemporal is None:
            self._imgDiffCTemporal = AxisImage(self.imgDiff_Conv, axis=(1,2))
        return self._imgDiffCTemporal
    
    @property
    def imgDiff(self) -> np.ndarray | None:
        if self.imgDiff_Mode == "Convoluted":
            return self.imgDiff_Conv
        return self.imgDiff_Normal

    @imgDiff.setter
    def imgDiff(self, image: np.ndarray) -> bool:
        self.Clear()
        if not ImgObj._IsValidImagestack(image): return False
        self._imgDiff = image
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

    def _IsValidImagestack(image):
        if not isinstance(image, np.ndarray):
            return False
        if image.shape != 3:
            return False

    def SetImage_Precompute(self, image: np.ndarray, convolute: bool = False) -> Literal["AlreadyLoading", "ImageUnsupported"] | Job:

        def _Precompute(job: Job):
            job.SetProgress(2, text="Calculating Spatial Image View")
            self.imgSpatial.mean
            self.imgSpatial.std
            job.SetProgress(3, text="Calculating imgDiff")
            self.imgDiff
            if convolute:
                job.SetProgress(4, text="Applying Gaussian Filter on imgDiff")
                self.imgDiff_Mode = "Convoluted"
                self.imgDiff
            job.SetProgress(5, text="Calculating Spatial and Temporal imgDiff View")
            self.imgDiffSpatial.max
            self.imgDiffSpatial.std
            self.imgDiffTemporal.max
            self.imgDiffTemporal.std
            job.SetProgress(6, text="Loading Image")
            job.SetStopped("Loading Image")

        if self._loadingThread is not None and self._loadingThread.is_alive():
            return "AlreadyLoading"

        self.Clear()
        if not ImgObj._IsValidImagestack(image): return "ImageUnsupported"
        self._img = image
        job = Job(steps=6)
        self._loadingThread = threading.Thread(_Precompute, args=(job))
        self._loadingThread.start()
        return job



















class Img:

    #Convention: Img (time, y (top to bottom), x)

    def __init__(self):
        self.img = None
        self.imgMean = None
        self.imgStd = None
        self.imgMedian = None
        self.img_Stats = None

        self.imgDiff = None
        self.imgDiff_Stats = None
        self.imgDiffMaxTime = None
        self.imgDiffMaxTime_Stats = None
        self.imgDiffMaxSpatial = None
        self.imgDiffStdTime = None

        #self.imgDiff2 = None
        #self.imgDiff2_Stats = None
        #self.imgDiff2MaxTime = None
        #self.imgDiff2StdTime = None

        self.name = None

    def SetIMG(self, img:np.ndarray, name:str="", denoise=False):
        _time = time.time()
        print(round(time.time() - _time, 3), "s   ", "SetImg")
        if (len(img.shape) != 3):
            return False
        match (img.dtype):
            case "uint8":
                self.img = img.astype("int8")
            case "uint16":
                self.img = img.astype("int16")
            case "uint32":
                self.img = img.astype("int32")   
            case _:
                self.img = img
        print(round(time.time() - _time, 3), "s   ", "Convert Int8")

        self.imgMean = np.mean(self.img, axis=0)
        self.imgStd = np.std(self.img, axis=0)
        self.imgMedian = np.mean(self.img, axis=0)
        print(round(time.time() - _time, 3), "s   ", "Mean, Std, Median")
        self.name = name
        _imgMin = np.min(self.img)
        self.img_Stats = {"Max": np.max(self.img), "Min": _imgMin, "ClipMin": max(0, _imgMin)}
        print(round(time.time() - _time, 3), "s   ", "Img Stats")
        self.CalcDiff(denoise=denoise)
        print(round(time.time() - _time, 3), "s   ", "Diff")
        self.CalcDiffMax()
        print(round(time.time() - _time, 3), "s   ", "DiffMax")
        return True
    
    def CalcDiff(self, denoise=False):
        if self.img is None: return
        if self.img.shape[0] <= 1:
            return
        
        self.imgDiff = np.diff(self.img, axis=0)
        #self.imgDiff2 = np.diff(self.img, axis=0, n=2)
        if denoise:
            self.imgDiff = gaussian_filter(self.imgDiff, sigma=2, axes=(1,2))
            #self.imgDiff2 = gaussian_filter(self.imgDiff2, sigma=2, axes=(1,2))  
        self.imgDiff_Stats = {"ClipMin": max(0, np.min(self.imgDiff)), "Max": np.max(self.imgDiff)}
        #self.imgDiff2_Stats = {"ClipMin": max(0, np.min(self.imgDiff2)), "Max": np.max(self.imgDiff2)}
    
    def CalcDiffMax(self):
        if self.imgDiff is None: return
        self.imgDiffMaxTime = np.max(self.imgDiff, axis=0)
        self.imgDiffMaxSpatial = np.max(self.imgDiff, axis=(1,2))
        self.imgDiffStdTime = np.std(self.imgDiff, axis=0)

        self.imgDiffMaxTime_Stats = {"Min": np.min(self.imgDiffMaxTime), 
                                     "Max": np.max(self.imgDiffMaxTime),
                                     "Std": np.std(self.imgDiffMaxTime),
                                     "Median": np.median(self.imgDiffMaxTime),
                                     "Mean": np.mean(self.imgDiffMaxTime)}
        
        self.imgDiffStdTime_Stats = {"Min": np.min(self.imgDiffStdTime), 
                                     "Max": np.max(self.imgDiffStdTime),
                                     "Std": np.std(self.imgDiffStdTime),
                                     "Median": np.median(self.imgDiffStdTime),
                                     "Mean": np.mean(self.imgDiffStdTime)}

        #self.imgDiff2MaxTime = np.max(-self.imgDiff2, axis=0)
        #self.imgDiff2StdTime = np.std(self.imgDiff2, axis=0)

"""
    # Point (X, Y)
    def GetImgROIAt(self, point, radius) -> np.ndarray:
        xmax = self.img.shape[2]
        ymax = self.img.shape[1]
        return np.array([self.img[:,y,x] for x in range(point[0]-radius,point[0]+2*radius+1) for y in range(point[1]-radius,point[1]+2*radius+1)
                     if ((x-point[0])**2+(y-point[1])**2)<radius**2+2**(1/2) and x >= 0 and y >= 0 and x < xmax and y < ymax])

        #mask, n = self._Circle_FullMask(point, radius)
        #_ret = np.empty(shape=self.img.shape)
        #for t in range(self.img.shape[0]):
        #    _ret[t] = np.multiply(self.img[t], mask)
        #return (_ret, n)

    def _CircleMask(self, radius: int) -> (np.ndarray, int):
        x = np.arange(-radius, +radius+1)
        y = np.arange(-radius, +radius+1)
        mask = np.array((x[np.newaxis,:])**2 + (y[:,np.newaxis])**2 <= radius**2, dtype="int32")
        n = np.count_nonzero(mask==1)
        return (mask,n)
    
    def _Circle_FullMask(self, point, radius: int) -> np.ndarray:
        x = np.arange(0, self.imgDiff.shape[2])
        y = np.arange(0, self.imgDiff.shape[1])
        mask = np.array((x[np.newaxis,:] - point[0])**2 + (y[:,np.newaxis] - point[1])**2 <= radius**2, dtype="int32")
        n = np.count_nonzero(mask==1)
        return (mask, n)
    
    def _ConvTask(self, radius: int):
        mask, n = self._CircleMask(radius)
        mask3 = mask[np.newaxis, :]
        self.imgConv = convolve(self.img,mask3)/n

    def ConvCorr(self, radius: int):
        if not self.ImgProvided(): return
        t1 = threading.Thread(target=self._ConvTask, args=(radius))
        t1.start()

"""