import collections
from typing import Callable, Literal
import numpy as np
import pims.bioformats
import psutil
from scipy.ndimage import gaussian_filter
import threading
import pims
import os
import logging
import gc

from  ..gui.components.general import Job    

class ImageProperties:
    """
        A class that supports lazy loading and caching of image properties like mean, median, std, min, max and clippedMin (=np.min(0, self.min))
        Returns scalars (except for the img property, where it returns the image used to initializate this object.
    """

    def __init__(self, img):
        self._img = img
        self._mean = None
        self._std = None
        self._median = None
        self._min = None
        self._max = None

    @property
    def mean(self) -> float:
        if self._img is None:
            return None
        if self._mean is None:
            self._mean = np.mean(self._img)
        return self._mean
    
    @property
    def median(self) -> float:
        if self._img is None:
            return None
        if self._median is None:
            self._median = np.median(self._img)
        return self._median
    
    @property
    def std(self) -> float:
        if self._img is None:
            return None
        if self._std is None:
            self._std = np.std(self._img, mean=self.mean)
        return self._std
    
    @property
    def min(self) -> float:
        if self._img is None:
            return None
        if self._min is None:
            self._min = np.min(self._img)
        return self._min
    
    @property
    def max(self) -> float:
        if self._img is None:
            return None
        if self._max is None:
            self._max = np.max(self._img)
        return self._max

    @property
    def minClipped(self) -> float:
        if self.min is None:
            return None
        return np.max([0, self.min])
    
    @property
    def img(self) -> np.ndarray:
        return self._img


class AxisImage:
    """
        A class that supports lazy loading and caching of subimages derived from an main image by calculating for example the
        mean, median, std, min or max over an given axis. Note that the axis specifies the axis which should be kept. Returns the image or the ImageProperties
        
        Example for the axis: An AxisImage for an 3D Image (t, y, x) with argument axis=0 will calculate the mean (median, std, min, max) for each pixel.
        Providing axis=(1,2) will calculate the same for each image frame.
    """

    def __init__(self, img: np.ndarray, axis:tuple):
        self._img = img
        self._axis = axis
        self._Mean : ImageProperties = None
        self._MeanNormed : ImageProperties = None
        self._Std : ImageProperties = None
        self._StdNormed : ImageProperties = None
        self._Median : ImageProperties = None
        self._MedianNormed : ImageProperties = None
        self._Min : ImageProperties = None
        self._Max : ImageProperties = None

    @property
    def Mean(self) -> np.ndarray:
        """ Mean image over the specified axis """
        if self.MeanProps is None: return None
        return self._Mean.img

    @property
    def MeanNormed(self) -> np.ndarray:
        """ Normalized Mean image (max value is garanter to be 255 or 0) over the specified axis """
        if self.MedianNormedProps is None: return None
        return self._MeanNormed.img
    
    @property
    def Median(self) -> np.ndarray:
        """ Median image over the specified axis """
        if self.MedianProps is None: return None
        return self._Median.img
    
    @property
    def MedianNormed(self) -> np.ndarray:
        """ Normalized Median image (max value is garanter to be 255 or 0) over the specified axis """
        if self.MedianNormedProps is None: return None
        return self._MedianNormed.img
    
    @property
    def Std(self) -> np.ndarray:
        """ Std image over the specified axis """
        if self.StdProps is None: return None
        return self._Std.img
    
    @property
    def StdNormed(self) -> np.ndarray:
        """ Normalized Std image (max value is garanter to be 255 or 0) over the specified axis """
        if self.StdNormedProps is None: return None
        return self._StdNormed.img
    
    @property
    def Min(self) -> np.ndarray:
        """ Minimum image over the specified axis """
        if self.MinProps is None: return None
        return self._Min.img
    
    @property
    def Max(self) -> np.ndarray:
        """ Maximum image over the specified axis """
        if self.MaxProps is None: return None
        return self._Max.img

    @property
    def MeanProps(self) -> ImageProperties | None:
        if self._img is None:
            return None
        if self._Mean is None:
            logging.debug("AxisImage: Calculating MeanProps")
            self._Mean = ImageProperties(np.mean(self._img, axis=self._axis, dtype="float32").astype("float64")) # Use float32 for calculations (!) to lower peak memory usage
        return self._Mean
    
    @property
    def MeanNormedProps(self) -> ImageProperties | None:
        if self._img is None:
            return None
        if self._MeanNormed is None:
            if self.MeanProps.max == 0:
                self._MeanNormed = self._Mean
            else:
                self._MeanNormed = ImageProperties((self.Mean*255/self.MeanProps.max).astype(self._img.dtype))
        return self._MeanNormed
    
    @property
    def MedianProps(self) -> ImageProperties | None:
        if self._img is None:
            return None
        if self._Median is None:
            logging.debug("AxisImage: Calculating MedianProps")
            self._Median = ImageProperties(np.median(self._img, axis=self._axis, dtype="float32").astype("float64")) # Use float32 for calculations (!) to lower peak memory usage
        return self._Median
    
    @property
    def MedianNormedProps(self) -> ImageProperties | None:
        if self._img is None:
            return None
        if self._MedianNormed is None:
            if self.MedianProps.max == 0:
                self._MedianNormed = self._Median
            else: 
                self._MedianNormed = ImageProperties((self.Median*255/self.MedianProps.max).astype(self._img.dtype))
        return self._MedianNormed
    
    @property
    def StdProps(self) -> ImageProperties | None:
        if self._img is None:
            return None
        if self._Std is None:
            logging.debug("AxisImage: Calculating StdProps")
            self._Std = ImageProperties(np.std(self._img, axis=self._axis, dtype="float32").astype("float64")) # Use float32 for calculations (!) to lower peak memory usage
        return self._Std
    
    @property
    def StdNormedProps(self) -> ImageProperties | None:
        if self._img is None:
            return None
        if self._StdNormed is None:
            if self.StdProps.max == 0:
                self._StdNormed = self._Std
            else:
                self._StdNormed = ImageProperties((self.Std*255/self.StdProps.max).astype(self._img.dtype))
        return self._StdNormed
    
    @property
    def MinProps(self) -> ImageProperties | None:
        if self._img is None:
            return None
        if self._Min is None:
            logging.debug("AxisImage: Calculating MinProps")
            self._Min = ImageProperties(np.min(self._img, axis=self._axis))
        return self._Min
    
    @property
    def MaxProps(self) -> ImageProperties | None:
        if self._img is None:
            return None
        if self._Max is None:
            logging.debug("AxisImage: Calculating MaxProps")
            self._Max = ImageProperties(np.max(self._img, axis=self._axis))
        return self._Max
    


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
    
    SPATIAL = (0)
    TEMPORAL = (1,2)
    
    def __init__(self, lazyLoading = True):
        self.Clear()

    def Clear(self):
        self._img: np.ndarray = None
        self._imgDenoised: np.ndarray = None
        self._imgMode: int = 0 # 0: Use given image, 1: use denoised image
        self._imgProps: ImageProperties = None
        self._imgS: np.ndarray = None # Image with signed dtype
        self._imgSpatial: AxisImage = None
        self._imgTemporal: AxisImage = None
        self._pimsmetadata = None

        self._imgDiff_mode = 0 #0: regular imgDiff, 1: convoluted imgDiff
        self._imgDiff: np.ndarray = None
        self._imgDiffProps: ImageProperties = None
        self._imgDiffConvFunc : Callable = self.Conv_GaussianBlur
        self._imgDiffConvArgs : tuple = (2,)
        self._imgDiffConv: dict[str, np.ndarray] = {}
        self._imgDiffConvProps: ImageProperties = {}
        self._imgDiffSpatial: AxisImage= None
        self._imgDiffTemporal: AxisImage = None
        self._imgDiffCSpatial: dict[str, AxisImage] = {}
        self._imgDiffCTemporal: dict[str, AxisImage] = {}

        self._customImages = {}
        self._customImagesProps = {}

        self._openFileThread : threading.Thread = None
        self._loadingThread : threading.Thread = None
        self._name: str|None = None

    @property
    def name(self) -> str:
        if self._name is None:
            return ""
        return self._name
    
    @name.setter
    def name(self, val):
        if val is None or isinstance(val, str):
            self._name = val

    @property
    def img(self) -> np.ndarray | None:
        """
            Returns the provided image in form of an np.ndarray or None if not loaded
        """
        if self._imgMode == 1:
            if self._imgDenoised is None:
                if self.imgDiff_Conv is None:
                    return None
                self._imgDenoised = self.imgView(ImgObj.SPATIAL).Median + np.cumsum(self.imgDiff_Conv, axis=(1,2)) 
            return self._imgDenoised
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
    
    def img_FrameProps(self, frame:int) -> ImageProperties | None:
        # Edge case, do not use caching
        if self._img is None or frame < 0 or frame >= self._img.shape[0]:
            return None
        return ImageProperties(self._img[frame])
    
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

    def imgView(self, mode) -> AxisImage | None:
        if self._img is None:
            return None
        match mode:
            case ImgObj.SPATIAL:
                if self._imgSpatial is None:
                    self._imgSpatial = AxisImage(self._img, ImgObj.SPATIAL)
                return self._imgSpatial
            case ImgObj.TEMPORAL:
                if self._imgTemporal is None:
                    self._imgTemporal = AxisImage(self._img, ImgObj.TEMPORAL)
                return self._imgTemporal
            case _:
                raise ValueError("The axis must be either SPATIAL or TEMPORAL")
    
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
        if self.imgDiff_Normal is None or self._imgDiffConvFunc is None:
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
        if self.imgDiff_Conv is None or self._imgDiffConvFunc is None:
            return None
        _n = self._imgDiffConvFunc.__name__+str(self._imgDiffConvArgs)
        if _n not in self._imgDiffConvProps.keys():
            self._imgDiffConvProps[_n] = ImageProperties(self.imgDiff_Conv)
        return self._imgDiffConvProps[_n]
    
    def imgDiff_NormalView(self, mode) -> AxisImage | None:
        if self.imgDiff is None:
            return None
        match mode:
            case ImgObj.SPATIAL:
                if self._imgDiffSpatial is None:
                    self._imgDiffSpatial = AxisImage(self._imgDiff, ImgObj.SPATIAL)
                return self._imgDiffSpatial
            case ImgObj.TEMPORAL:
                if self._imgDiffTemporal is None:
                    self._imgDiffTemporal = AxisImage(self._imgDiff, ImgObj.TEMPORAL)
                return self._imgDiffTemporal
            case _:
                raise ValueError("The axis must be either SPATIAL or TEMPORAL")
            
    def imgDiff_ConvView(self, mode) -> AxisImage | None:
        if self.imgDiff_Conv is None:
            return None
        _n = self._imgDiffConvFunc.__name__+str(self._imgDiffConvArgs)
        match mode:
            case ImgObj.SPATIAL:
                if _n not in self._imgDiffCSpatial.keys():
                    self._imgDiffCSpatial[_n] = AxisImage(self.imgDiff_Conv, ImgObj.SPATIAL)
                return self._imgDiffCSpatial[_n]
            case ImgObj.TEMPORAL:
                if _n not in self._imgDiffCTemporal.keys():
                    self._imgDiffCTemporal[_n] = AxisImage(self.imgDiff_Conv, ImgObj.TEMPORAL)
                return self._imgDiffCTemporal[_n]
            case _:
                raise ValueError("The axis must be either SPATIAL or TEMPORAL")
    
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
    
    def imgDiffView(self, mode) -> AxisImage | None:
        if self.imgDiff_Mode == "Convoluted":
            return self.imgDiff_ConvView(mode)
        return self.imgDiff_NormalView(mode)

    @property
    def imgDiffProps(self) -> ImageProperties | None:
        if self.imgDiff_Mode == "Convoluted":
            return self.imgDiff_ConvProps
        return self.imgDiff_NormalProps
    
    def imgDiff_FrameProps(self, frame:int) -> ImageProperties | None:
        # Edge case, do not use caching
        if self.imgDiff is None or frame < 0 or frame >= self.imgDiff.shape[0]:
            return None
        return ImageProperties(self.imgDiff[frame])
    
    @property
    def pims_metadata(self) -> collections.OrderedDict | None:
        return self._pimsmetadata
    
    
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
    

    def ClearCache(self):
        """Clears all currently not actively used internal variables (currently only the convoluted imgDiff)"""
        for internalvar, property in [(self._imgDiffConv, self.imgDiff_Conv),
                                       (self._imgDiffConvProps, self.imgDiff_ConvProps),
                                       (self._imgDiffCSpatial, self.imgDiff_ConvView(ImgObj.SPATIAL)),
                                       (self._imgDiffCTemporal, self.imgDiff_ConvView(ImgObj.TEMPORAL))]:
            for k in list(internalvar.keys()).copy():
                if internalvar[k] is not property:
                    del internalvar[k]

    def _IsValidImagestack(image):
        if not isinstance(image, np.ndarray):
            return False
        if len(image.shape) != 3:
            return False
        return True
    
    def SetConvolutionFunction(self, func: Callable, args: tuple|None):
        self._imgDiffConvFunc = func
        self._imgDiffConvArgs = args
    
    def Conv_GaussianBlur(self, args: tuple|None) -> np.ndarray | None:
        if self.imgDiff_Normal is None:
            return None
        if len(args) != 1:
            return None
        sigma = args[0]
        return gaussian_filter(self.imgDiff_Normal, sigma=sigma, axes=(1,2))
    
    def Conv_MeanMaxDiff(self, args: tuple|None) -> np.ndarray | None:
        if self._img is None:
            return None
        
        return (self.imgS - self.imgView(ImgObj.SPATIAL).Mean).astype(self.imgS.dtype)
    
    def PrecomputeImage(self, callback = None, errorcallback = None, convolute: bool = False, job:Job = None, waitCompletion:bool = False) -> Literal["AlreadyLoading", "WrongShape"] | Job:
        if self._loadingThread is not None and self._loadingThread.is_alive():
            if errorcallback is not None: errorcallback("AlreadyLoading")
            return "AlreadyLoading"

        def _Precompute(job:Job):
            _progIni = job.Progress
            job.SetProgress(_progIni, text="Precalculating ImgView (Spatial Mean)")
            self.imgView(ImgObj.SPATIAL).Mean
            job.SetProgress(_progIni, text="Precalculating ImgView (Spatial Std)")
            self.imgView(ImgObj.SPATIAL).Std
            gc.collect()
            job.SetProgress(1+_progIni, text="Calculating imgDiff")
            self.imgDiff
            if convolute:
                job.SetProgress(2+_progIni, text="Applying Gaussian Filter on imgDiff")
                self.imgDiff_Mode = "Convoluted"
                self.imgDiff
            gc.collect()
            job.SetProgress(3+_progIni, text="Precalculating ImgDiffView (Spatial Max)")
            self.imgDiffView(ImgObj.SPATIAL).Max
            job.SetProgress(3+_progIni, text="Precalculating ImgDiffView (Spatial Std)")
            self.imgDiffView(ImgObj.SPATIAL).StdNormed
            gc.collect()
            job.SetProgress(3+_progIni, text="Precalculating ImgDiffView (Temporal Max)")
            self.imgDiffView(ImgObj.TEMPORAL).Max
            job.SetProgress(3+_progIni, text="Precalculating ImgDiffView (Temporal Std)")
            self.imgDiffView(ImgObj.TEMPORAL).Std
            gc.collect()
            job.SetStopped("Loading Image")
            if callable is not None:
                callback(self)

        if job is None:
            job = Job(steps=4, showSteps=True)
        self._loadingThread = threading.Thread(target=_Precompute, args=(job,), daemon=True)
        self._loadingThread.start()
        if waitCompletion:
            self._loadingThread.join()
        else:
            return job
        
    def SetImagePrecompute(self, img:np.ndarray, name:str = None, callback = None, errorcallback = None, convolute: bool = False, job:Job = None, waitCompletion:bool = False) -> Literal["FileNotFound", "AlreadyLoading", "ImageUnsupported", "WrongShape"] | Job:
        if not ImgObj._IsValidImagestack(img):
            if errorcallback is not None: errorcallback("ImageUnsupported")
            return "ImageUnsupported"
        self.img = img
        self.name = name
        return self.PrecomputeImage(callback=callback,errorcallback=errorcallback, convolute=convolute, job=job, waitCompletion=waitCompletion)


    def OpenFile(self, path: str, callback = None, errorcallback = None, convolute: bool = False, waitCompletion:bool = False) -> Literal["FileNotFound", "AlreadyLoading", "ImageUnsupported", "WrongShape"] | Job:
        if (self._loadingThread is not None and self._loadingThread.is_alive()) or (self._openFileThread is not None and self._openFileThread.is_alive()):
            if errorcallback is not None: errorcallback("AlreadyLoading")
            return "AlreadyLoading"
        
        if path is None or path == "":
            if errorcallback is not None: errorcallback("FileNotFound")
            return "FileNotFound"
        self.Clear()

        def _Load(job: Job):
            job.SetProgress(0, "Opening File")
            try:
                _pimsImg = pims.open(path)
            except FileNotFoundError:
                if errorcallback is not None: errorcallback("FileNotFound")
                return "FileNotFound"
            except Exception as ex:
                if errorcallback is not None: errorcallback("ImageUnsupported", ex)
                return "ImageUnsupported"
            if len(_pimsImg.shape) != 3:
                if errorcallback is not None: errorcallback("WrongShape", _pimsImg.shape)
                return "WrongShape"
            job.SetProgress(1, "Converting image")
            imgNP = np.zeros(shape=_pimsImg.shape, dtype=_pimsImg.dtype)
            for i in range(_pimsImg.shape[0]):
                imgNP[i] = _pimsImg[i]

            self.img = imgNP
            self.name = os.path.basename(path)
            if getattr(_pimsImg, "get_metadata_raw", None) != None:
                self._pimsmetadata = collections.OrderedDict(sorted(_pimsImg.get_metadata_raw().items()))

            return self.PrecomputeImage(callback=callback, errorcallback=errorcallback, convolute=convolute, job=job, waitCompletion=waitCompletion)

        job = Job(steps=6)
        self._openFileThread = threading.Thread(target=_Load, args=(job,), daemon=True)
        self._openFileThread.start()
        if waitCompletion:
            self._openFileThread.join()
        else:
            return job
    