import collections
from typing import Callable, Literal, Self
import numpy as np
import pims
import tifffile
import nd2
from pathlib import Path
from scipy.ndimage import gaussian_filter
import gc
import logging

logger = logging.getLogger("NeurotorchMZ")

from ..core.task_system import Task  
from ..core.serialize import Serializable

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
    
    def __del__(self):
        del self._img


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
    
    def __del__(self):
        del self._img

class ImageObject(Serializable):
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

    # Dict used for serialization; key is property name, value is tuple of serialization name and conversion function for the given data to give at least a minimal property from 
    _serialize_dict = {"_name":("name", str), "_path":("path", Path), "_imgMode":("imgMode", int), "_pimsmetadata": ("pimsmetadata", collections.OrderedDict)}
    
    def __init__(self, lazyLoading = True):
        self._task_open_image = Task(lambda:_, "ImageObject", run_async=True, keep_alive=False)
        self.Clear()

    def Clear(self):
        self._name: str|None = None
        self._img: np.ndarray = None
        self._imgDenoised: np.ndarray = None
        self._imgMode: int = 0 # 0: Use given image, 1: use denoised image
        self._imgProps: ImageProperties = None
        self._imgS: np.ndarray = None # Image with signed dtype
        self._imgSpatial: AxisImage = None
        self._imgTemporal: AxisImage = None
        self._pimsmetadata: dict|None = None
        self._nd2metadata: dict|None = None
        self._path: Path|None = None # Path of the image file, if given

        self._imgDiff_mode = 0 #0: regular imgDiff, 1: convoluted imgDiff
        self._imgDiff: np.ndarray = None
        self._imgDiffProps: ImageProperties = None
        self._imgDiffConvFunc : Callable = ImageObject.Conv_GaussianBlur
        self._imgDiffConvArgs : dict|None = {"sigma": 2}
        self._imgDiffConv: dict[str, np.ndarray] = {}
        self._imgDiffConvProps: ImageProperties = {}
        self._imgDiffSpatial: AxisImage= None
        self._imgDiffTemporal: AxisImage = None
        self._imgDiffCSpatial: dict[str, AxisImage] = {}
        self._imgDiffCTemporal: dict[str, AxisImage] = {}

        self._customImages = {}
        self._customImagesProps = {}

    def serialize(self, **kwargs) -> dict:
        """ 
            Serializes the ImageObject into a dictionary and do not include image data (only the path is included). Note that only properties, which could not be calculated from other ones, are included

            Please note: If the ImageObject has no path, the image data itself will not be serialized
        """
        r = {}
        for prop_name, (serialize_name, dtype_func) in ImageObject._serialize_dict.items():
            if (a := self.__getattribute__(prop_name)) is not None:
                r[serialize_name] = a
        return r


    
    def deserialize(self, serialize_dict: dict, **kwargs):
        """ Load data from a serialization dict """
        self.Clear()
        for prop_name, (serialize_name, dtype_func) in ImageObject._serialize_dict.items():
            if serialize_name in serialize_dict.keys():
                self.__setattr__(prop_name, dtype_func(serialize_dict))

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
    def path(self) -> Path|None:
        """ The path of the image file, if given """
        return self._path

    @property
    def img(self) -> np.ndarray | None:
        """
            Returns the provided image in form of an np.ndarray or None if not loaded
        """
        if self._imgMode == 1:
            if self._imgDenoised is None:
                if self.imgDiff_Conv is None:
                    return None
                self._imgDenoised = self.imgView(ImageView.SPATIAL).Median + np.cumsum(self.imgDiff_Conv, axis=(1,2)) 
            return self._imgDenoised
        return self._img
    
    @img.setter
    def img(self, image: np.ndarray) -> bool:
        self.Clear()
        if not ImageObject._IsValidImagestack(image): return False
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
            case ImageView.SPATIAL:
                if self._imgSpatial is None:
                    self._imgSpatial = AxisImage(self._img, ImageView.SPATIAL)
                return self._imgSpatial
            case ImageView.TEMPORAL:
                if self._imgTemporal is None:
                    self._imgTemporal = AxisImage(self._img, ImageView.TEMPORAL)
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
            self._imgDiffConv[_n] = self._imgDiffConvFunc(imgObj=self, **self._imgDiffConvArgs)
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
            case ImageView.SPATIAL:
                if self._imgDiffSpatial is None:
                    self._imgDiffSpatial = AxisImage(self._imgDiff, ImageView.SPATIAL)
                return self._imgDiffSpatial
            case ImageView.TEMPORAL:
                if self._imgDiffTemporal is None:
                    self._imgDiffTemporal = AxisImage(self._imgDiff, ImageView.TEMPORAL)
                return self._imgDiffTemporal
            case _:
                raise ValueError("The axis must be either SPATIAL or TEMPORAL")
            
    def imgDiff_ConvView(self, mode) -> AxisImage | None:
        if self.imgDiff_Conv is None:
            return None
        _n = self._imgDiffConvFunc.__name__+str(self._imgDiffConvArgs)
        match mode:
            case ImageView.SPATIAL:
                if _n not in self._imgDiffCSpatial.keys():
                    self._imgDiffCSpatial[_n] = AxisImage(self.imgDiff_Conv, ImageView.SPATIAL)
                return self._imgDiffCSpatial[_n]
            case ImageView.TEMPORAL:
                if _n not in self._imgDiffCTemporal.keys():
                    self._imgDiffCTemporal[_n] = AxisImage(self.imgDiff_Conv, ImageView.TEMPORAL)
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
        if not ImageObject._IsValidImagestack(image): return False
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
    def pims_metadata(self) -> dict | None:
        return self._pimsmetadata
    
    @property
    def nd2_metadata(self) -> dict|None:
        return self._nd2metadata
    
    
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
                                       (self._imgDiffCSpatial, self.imgDiff_ConvView(ImageView.SPATIAL)),
                                       (self._imgDiffCTemporal, self.imgDiff_ConvView(ImageView.TEMPORAL))]:
            for k in list(internalvar.keys()).copy():
                if internalvar[k] is not property:
                    del internalvar[k]

    def _IsValidImagestack(image):
        if not isinstance(image, np.ndarray):
            return False
        if len(image.shape) != 3:
            return False
        return True
    
    def SetConvolutionFunction(self, func: Callable, func_args: dict|None = None):
        self._imgDiffConvFunc = func
        self._imgDiffConvArgs = func_args if func_args is not None else {}
    
    def Conv_GaussianBlur(imgObj: Self, sigma: float) -> np.ndarray | None:
        if imgObj.imgDiff_Normal is None:
            return None
        return gaussian_filter(imgObj.imgDiff_Normal, sigma=sigma, axes=(1,2))
    
    def Conv_MeanMaxDiff(self) -> np.ndarray | None:
        if self._img is None:
            return None
        return (self.imgS - self.imgView(ImageView.SPATIAL).Mean).astype(self.imgS.dtype)
    

    def PrecomputeImage(self, calc_convoluted: bool = False, task_continue: bool = False, run_async:bool = True) -> Task:
        """ 
            Precalculate the image views to prevent stuttering during runtime.

            :param bool calc_convoluted: Controls if the convoluted function should also be precomputed
            :param bool task_continue: This function supports the continuation of an existing task (for example from opening an image file)
            :param bool async_mode: Controls if the precomputation runs in a different thread. Has no effect when task_continue is set
            :returns Task: The task object of this task
            :raises AlreadyLoading: There is already a task working on this ImageObject
        """
        if not task_continue and self._task_open_image.running:
            raise AlreadyLoadingError()

        def _Precompute(task: Task):
            _progIni = task._step if task._step is not None else 0
            task.set_step_progress(_progIni, "preparing ImgView (Spatial Mean)")
            self.imgView(ImageView.SPATIAL).Mean
            task.set_step_progress(_progIni, "preparing ImgView (Spatial Std)")
            self.imgView(ImageView.SPATIAL).Std
            gc.collect()
            task.set_step_progress(1+_progIni, "preparing imgDiff")
            self.imgDiff
            if calc_convoluted:
                task.set_step_progress(2+_progIni, "preparing imgDiff convolution")
                self.imgDiff_Conv
            gc.collect()
            task.set_step_progress(3+_progIni, "preparing ImgDiffView (Spatial Max)")
            self.imgDiffView(ImageView.SPATIAL).Max
            task.set_step_progress(3+_progIni, "preparing ImgDiffView (Spatial Std)")
            self.imgDiffView(ImageView.SPATIAL).StdNormed
            gc.collect()
            task.set_step_progress(3+_progIni, "preparing ImgDiffView (Temporal Max)")
            self.imgDiffView(ImageView.TEMPORAL).Max
            task.set_step_progress(3+_progIni, "preparing ImgDiffView (Temporal Std)")
            self.imgDiffView(ImageView.TEMPORAL).Std
            gc.collect()

        if task_continue:
            _Precompute(self._task_open_image)
        else:
            self._task_open_image.reset(function=_Precompute, name="preparing ImageObject", run_async=run_async)
            self._task_open_image.set_step_mode(4)
            self._task_open_image.start()
        return self._task_open_image
        
    def SetImagePrecompute(self, img:np.ndarray, name:str = None, calc_convoluted: bool = False, run_async:bool = True) -> Task:
        """ 
            Set a new image with a given name and run PrecomputeImage() on it.

            :param np.ndarray img: The image
            :param str name: Name of the image
            :param bool calc_convoluted: Controls if the convoluted function should also be precomputed
            :param bool task_continue: This function supports the continuation of an existing task (for example from opening an image file)
            :param bool async_mode: Controls if the precomputation runs in a different thread
            :returns Task: The task object of this task
            :raises AlreadyLoading: There is already a task working on this ImageObject
        """
        if not ImageObject._IsValidImagestack(img):
            raise UnsupportedImageError()
        self.img = img
        self.name = name
        return self.PrecomputeImage(calc_convoluted=calc_convoluted, run_async=run_async)


    def OpenFile(self, path: Path|str, precompute:bool = False, calc_convoluted:bool = False, run_async:bool = True) -> Task:
        """ 
            Open an image using a given path.

            :param Path|str path: The path to the image file
            :param bool precompute: Controls if the loaded image is also precomputed
            :param bool calc_convoluted: Has only an affect when precompute is set. Passed to PrecomputeImage() function
            :param bool run_async: Controls if the precomputation runs in a different thread
            :returns Task: The task object of this task
            :raises AlreadyLoading: There is already a task working on this ImageObject
            :raises FileNotFoundError: Can't find the file
            :raises UnsupportedImageError: The image is unsupported or has an error
            :raises ImageShapeError: The image has an invalid shape
        
        """
        if self._task_open_image.running:
            raise AlreadyLoadingError()
        
        if isinstance(path, str):
            path = Path(path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError()
        
        self.Clear()

        def _Load(task: Task):
            task.set_step_progress(0, "reading File")
            if path.suffix.lower() in [".tif", ".tiff"]:
                logger.debug(f"Opening {path.name} with tifffile")
                with tifffile.TiffFile(path) as tif:
                    self._img = tif.asarray()
                    self._tiffmetadata = tif.ome_metadata
            elif nd2.is_supported_file(path):
                logger.debug(f"Opening {path.name} with nd2")
                with nd2.ND2File(path) as ndfile:
                    self._img = ndfile.asarray()
                    self._nd2metadata = ndfile.unstructured_metadata()
            else:
                logger.debug(f"Opening {path.name} with PIMS")
                try:
                    _pimsImg = pims.open(str(path))
                except FileNotFoundError:
                    raise FileNotFoundError()
                except Exception as ex:
                    raise UnsupportedImageError(path.name, ex)
                if len(_pimsImg.shape) != 3:
                    raise ImageShapeError(_pimsImg.shape)
                task.set_step_progress(1, "converting")
                imgNP = np.zeros(shape=_pimsImg.shape, dtype=_pimsImg.dtype)
                imgNP = [_pimsImg[i] for i in range(_pimsImg.shape[0])]
                self.img = imgNP
                if getattr(_pimsImg, "get_metadata_raw", None) != None: 
                    self._pimsmetadata = collections.OrderedDict(sorted(_pimsImg.get_metadata_raw().items()))
            self._path = path
            self.name = path.stem
            

            if precompute:
                self.PrecomputeImage(calc_convoluted=calc_convoluted, task_continue=True, run_async=run_async)

        self._task_open_image.reset(function=_Load, name="open image file", run_async=run_async)
        self._task_open_image.set_step_mode(2 + 4*precompute)
        self._task_open_image.start()
        return self._task_open_image
    
class ImageView:
    """ 
        Presets for reducing the 3 dimensional ImageObject in dimensions
    
        :var tuple SPATIAL: Removes the temporal component and will create an 2D image
        :var tuple TEMPORAL: Removes the spatial component and will create an 1D time series
    """

    SPATIAL = (0)
    TEMPORAL = (1,2)


class ImageObjectError(Exception):
    """ ImageObject Error"""
    pass

class AlreadyLoadingError(ImageObjectError):
    """ Already loading an Image into an ImageObject"""
    pass

class UnsupportedImageError(ImageObjectError):
    """ The image is unsupported """
    
    def __init__(self, file_name: str, exception: Exception|None = None, *args):
        super().__init__(*args)
        self.exception = exception
        self.file_name = file_name

class ImageShapeError(ImageObjectError):
    """ The image has an invalid shape """

    def __init__(self, shape: np.ndarray|None = None, *args):
        super().__init__(*args)
        self.shape = shape