from ..core.task_system import Task  
from ..core.serialize import Serializable, DeserializeError, SerializeError
from ..core.logs import logger
from ..core.settings import UserSettings

import collections
from enum import Enum
from typing import Callable, Literal, Self, Any, cast, Protocol
import numpy as np
import pims
import tifffile
import nd2
from pathlib import Path
import gc
from scipy.signal import find_peaks

class ImageProperties:
    """
        A class that supports lazy loading and caching of image properties like mean, median, std, min, max and clippedMin (=np.min(0, self.min))
        Returns scalars (except for the img property, where it returns the image used to initializate this object.
    """
    def __init__(self, img: np.ndarray|None):
        self._img = img
        self._mean = None
        self._std = None
        self._median = None
        self._min = None
        self._max = None


    @property
    def mean(self) -> np.floating|None:
        if self._img is None:
            return None
        if self._mean is None:
            self._mean = np.mean(self._img)
        return self._mean
    
    @property
    def median(self) -> np.floating|None:
        if self._img is None:
            return None
        if self._median is None:
            self._median = np.median(self._img)
        return self._median
    
    @property
    def std(self) -> np.floating|None:
        if self._img is None:
            return None
        if self._std is None:
            self._std = np.std(self._img)
        return self._std
    
    @property
    def min(self) -> np.floating|None:
        if self._img is None:
            return None
        if self._min is None:
            self._min = np.min(self._img)
        return self._min
    
    @property
    def max(self) -> np.floating|None:
        if self._img is None:
            return None
        if self._max is None:
            self._max = np.max(self._img)
        return self._max

    @property
    def minClipped(self) -> np.floating|None:
        if self.min is None:
            return None
        return np.max(np.array([0, self.min]))
    
    @property
    def img(self) -> np.ndarray|None:
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

    def __init__(self, img: np.ndarray|None, axis:tuple, name: str|None = None):
        self._img = img
        self._axis = axis
        self._name = name
        self._mean = None
        self._mean_normed = None
        self._std = None
        self._std_normed = None
        self._median = None
        self._min = None
        self._max = None

    @property
    def Mean(self) -> np.ndarray|None:
        """ Mean image over the specified axis """
        return self.MeanProps.img

    @property
    def MeanNormed(self) -> np.ndarray|None:
        """ Normalized Mean image (max value is garanter to be 255 or 0) over the specified axis """
        return self.MeanNormedProps.img
    
    @property
    def Median(self) -> np.ndarray|None:
        """ Median image over the specified axis """
        return self.MedianProps.img
    
    @property
    def Std(self) -> np.ndarray|None:
        """ Std image over the specified axis """
        return self.StdProps.img
    
    @property
    def StdNormed(self) -> np.ndarray|None:
        """ Normalized Std image (max value is garanter to be 255 or 0) over the specified axis """
        return self.StdNormedProps.img
    
    @property
    def Min(self) -> np.ndarray|None:
        """ Minimum image over the specified axis """
        return self.MinProps.img
    
    @property
    def Max(self) -> np.ndarray|None:
        """ Maximum image over the specified axis """
        return self.MaxProps.img

    @property
    def MeanProps(self) -> ImageProperties:
        if self._mean is None:
            if self._img is None:
                self._mean = ImageProperties(None)
            else:
                logger.debug(f"Calculating mean view for AxisImage '{self._name if self._name is not None else ''}' on axis '{self._axis}'")
                self._mean = ImageProperties(np.mean(self._img, axis=self._axis, dtype="float32").astype("float64")) # Use float32 for calculations (!) to lower peak memory usage
        return self._mean
    
    @property
    def MeanNormedProps(self) -> ImageProperties:
        if self._mean_normed is None:
            if self._img is None or self.Mean is None:
                self._mean_normed = ImageProperties(None)
            else:
                self._mean_normed = ImageProperties((self.Mean*255/self.MeanProps.max).astype(self._img.dtype))
        return self._mean_normed
    
    @property
    def MedianProps(self) -> ImageProperties:
        if self._median is None:
            if self._img is None:
                self._median = ImageProperties(None)
            else:
                logger.debug(f"Calculating median view for AxisImage '{self._name if self._name is not None else ''}' on axis '{self._axis}'")
                self._median = ImageProperties(np.median(self._img, axis=self._axis))
        return self._median
    
    @property
    def StdProps(self) -> ImageProperties:
        if self._std is None:
            if self._img is None:
                self._std = ImageProperties(None)
            else:
                logger.debug(f"Calculating std view for AxisImage '{self._name if self._name is not None else ''}' on axis '{self._axis}'")
                self._std = ImageProperties(np.std(self._img, axis=self._axis, dtype="float32").astype("float64")) # Use float32 for calculations (!) to lower peak memory usage
        return self._std
    
    @property
    def StdNormedProps(self) -> ImageProperties:
        if self._std_normed is None:
            if self._img is None or self.Std is None:
                self._std_normed = ImageProperties(None)
            else:
                self._std_normed = ImageProperties((self.Std*255/self.StdProps.max).astype(self._img.dtype))
        return self._std_normed
    
    @property
    def MinProps(self) -> ImageProperties:
        if self._min is None:
            if self._img is None:
                self._min = ImageProperties(None)
            else:
                logger.debug(f"Calculating min view for AxisImage '{self._name if self._name is not None else ''}' on axis '{self._axis}'")
                self._min = ImageProperties(np.min(self._img, axis=self._axis))
        return self._min
    
    @property
    def MaxProps(self) -> ImageProperties:
        if self._max is None:
            if self._img is None:
                self._max = ImageProperties(None)
            else:
                logger.debug(f"Calculating max view for AxisImage '{self._name if self._name is not None else ''}' on axis '{self._axis}'")
                self._max = ImageProperties(np.max(self._img, axis=self._axis))
        return self._max
    
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
    
    def __init__(self, conv_cache_size: int = 1, diff_conv_cache_size: int = 3):
        global SignalObject
        from .signal_detection import SignalObject
        self._task_open_image = Task(lambda task, **kwargs: None, "ImageObject", run_async=True, keep_alive=False)
        self.conv_cache_size = conv_cache_size
        self.diff_conv_cache_size = diff_conv_cache_size
        self.clear()

    def clear(self):
        """ Resets the ImageObject and clears all stored images and metadata """
        self._name: str|None = None
        self._path: Path|None = None
        self._metdata: dict|None = None

        self._img: np.ndarray|None = None
        self._img_props: dict[str, ImageProperties] = {}
        self._img_views: dict[str, dict[ImageView, AxisImage]] = {"default" : {}}
        self._img_conv_func: Callable[..., np.ndarray]|None = None
        self._img_conv_args: dict|None = None

        self._img_diff: np.ndarray|None = None
        self._img_diff_props: dict[str, ImageProperties] = {}
        self._img_diff_views: dict[str, dict[ImageView, AxisImage]] = {"default" : {}}
        self._img_diff_conv_func: Callable[..., np.ndarray]|None = None
        self._img_diff_conv_args: dict|None = None

        self._signal_obj: SignalObject = SignalObject(self)

    def serialize(self, **kwargs) -> dict:
        r: dict[str, Any] = {
            "name": self._name
        }
        if self._path is not None:
            r["path"] = self._path
        else:
            raise SerializeError("Can not serialize an ImageObject without a path")
        return r
    
    @classmethod
    def deserialize(cls, serialize_dict: dict, **kwargs) -> Self:
        imgObj = cls()
        if "path" not in serialize_dict.keys():
            raise DeserializeError("Can not deserialize an ImageObject without a path") 
        task = imgObj.OpenFile(serialize_dict["path"], precompute=True)
        task.join()
        return imgObj

    @property
    def name(self) -> str:
        """ Get or set the name of the ImageObject """
        if self._name is None:
            return ""
        return self._name
    
    @name.setter
    def name(self, val):
        if val is None or isinstance(val, str):
            self._name = val

    @property
    def path(self) -> Path|None:
        """ Returns the path of the current ImageObject or None if not originating from a file """
        return self._path
    
    @property
    def metadata(self) -> dict[str, Any]|None:
        return self._metdata
    
    # Img and ImageDiff properties

    @property
    def img(self) -> np.ndarray | None:
        """
            Get or set the image. Note that setting to a new value will remove the old diff image

            :raises UnsupportedImageError: The image is not a valid image stack
        """
        return self.imgProps.img
    
    @img.setter
    def img(self, image: np.ndarray):
        if not ImageObject._is_valid_image_stack(image): raise UnsupportedImageError()
        self.clear()
        self._img = image
    
    @property
    def imgDiff(self) -> np.ndarray | None:
        """ 
            Get or set the diff image. Note that setting to a new value will remove the old image

            :raises UnsupportedImageError: The image is not a valid image stack
        """
        return self.imgDiffProps.img

    @imgDiff.setter
    def imgDiff(self, image: np.ndarray):
        if not ImageObject._is_valid_image_stack(image): raise UnsupportedImageError()
        self.clear()
        self._img_diff = image

    @property
    def imgS(self) -> np.ndarray | None:
        """
            Returns a numpy view with a signed datatype (e.g. for calculating the diffImage). 
        """
        if self._img is None:
            return None
        match (self._img.dtype):
            case "uint8":
                return self._img.view("int8")
            case "uint16":
                return self._img.view("int16")
            case "uint32":
                return self._img.view("int32")
            case "uint64":
                return self._img.view("int64")
            case _:
                return self._img

    # ImageProperties
    
    @property
    def imgProps(self) -> ImageProperties:
        """ Returns the image properties (e.g. median, mean or maximum) """
        if self._img is None:
            return ImageProperties(None)
        if self._conv_func_identifier not in self._img_props.keys():
            if self._img_conv_func is not None and self._img_conv_args is not None:
                self._img_props[self._conv_func_identifier] = ImageProperties(self._img_conv_func(self, *self._img_conv_args))
            else:
                self._img_props["default"] = ImageProperties(self._img)
        self._gc_cache()
        return self._img_props[self._conv_func_identifier]
    

    @property
    def imgDiffProps(self) -> ImageProperties:
        """ Returns the diff image properties (e.g. median, mean or maximum) """
        # Generate img_diff first
        if self._img_diff is None:
            if self.imgS is None:
                return ImageProperties(None)
            self._img_diff = np.diff(self.imgS, axis=0)

        if self._diff_conv_func_identifier not in self._img_diff_props.keys():
            if self._img_diff_conv_func is not None and self._img_diff_conv_args is not None:
                self._img_diff_props[self._diff_conv_func_identifier] = ImageProperties(self._img_diff_conv_func(self, *self._img_diff_conv_args))
            else:
                self._img_diff_props["default"] = ImageProperties(self._img_diff)
        self._gc_cache()
        return self._img_diff_props[self._diff_conv_func_identifier]
    
    def img_FrameProps(self, frame:int) -> ImageProperties:
        """ Returns the image properties for a given frame """
        # Edge case, do not use caching
        if self.img is None or frame < 0 or frame >= self.img.shape[0]:
            return ImageProperties(None)
        return ImageProperties(self.img[frame])
    
    def imgDiff_FrameProps(self, frame:int) -> ImageProperties:
        """ Returns the image diff properties for a given frame """
        # Edge case, do not use caching
        if self.imgDiff is None or frame < 0 or frame >= self.imgDiff.shape[0]:
            return ImageProperties(None)
        return ImageProperties(self.imgDiff[frame])
    
    # Image View

    def imgView(self, mode: "ImageView") -> AxisImage:
        """ Returns a view of the current image given an ImageView mode """
        if mode not in self._img_views[self._conv_func_identifier].keys():
            self._img_views[self._conv_func_identifier][mode] = AxisImage(self.img, axis=mode.value, name=self.name)
        return self._img_views[self._conv_func_identifier][mode]
    
    def imgDiffView(self, mode) -> AxisImage:
        """ Returns a view of the current diff image given an ImageView mode """
        if mode not in self._img_diff_views[self._diff_conv_func_identifier].keys():
            self._img_diff_views[self._diff_conv_func_identifier][mode] = AxisImage(self.imgDiff, axis=mode.value, name=self.name)
        return self._img_diff_views[self._diff_conv_func_identifier][mode]
    
    # Signal

    @property
    def signal_obj(self) -> "SignalObject":
        return self._signal_obj
    
    # Convolution functions

    def set_conv_func(self, func: Callable[..., np.ndarray]|None = None, func_args: dict[str, Any]|None = None) -> None:
        self._img_conv_func = func
        self._img_conv_args = func_args

    def set_diff_conv_func(self, func: Callable[..., np.ndarray]|None = None, func_args: dict[str, Any]|None = None) -> None:
        self._img_diff_conv_func = func
        self._img_diff_conv_args = func_args

    @property
    def _conv_func_identifier(self) -> str:
        if self._img_conv_func is None:
            return "default"
        return self._img_conv_func.__name__ + repr(self._img_conv_args) # type: ignore
    
    @property
    def _diff_conv_func_identifier(self) -> str:
        if self._img_diff_conv_func is None:
            return "default"
        return self._img_diff_conv_func.__name__ + repr(self._img_diff_conv_args) # type: ignore
    
    def _gc_cache(self) -> None:
        """ Garbage collect the convolution caches """
        while len(self._img_props) > self.conv_cache_size:
            del self._img_props[list(self._img_props.keys())[0]]
        while len(self._img_views) > self.conv_cache_size:
            del self._img_views[list(self._img_views.keys())[0]]   

        while len(self._img_diff_props) > self.diff_conv_cache_size:
            del self._img_diff_props[list(self._img_diff_props.keys())[0]]
        while len(self._img_diff_views) > self.diff_conv_cache_size:
            del self._img_diff_views[list(self._img_diff_views.keys())[0]]   

    def clear_cache(self) -> None:
        """Clears caches of unsused convolutions """
        k, v = self._img_props.popitem()
        self._img_props = {k: v}
        k, v = self._img_views.popitem()
        self._img_views = {k: v}

        k, v = self._img_diff_props.popitem()
        self._img_diff_props = {k: v}
        k, v = self._img_diff_views.popitem()
        self._img_diff_views = {k: v}

    # Image loading
    
    def PrecomputeImage(self, task_continue: bool = False, run_async:bool = True) -> Task:
        """ 
            Precalculate the image views to prevent stuttering during runtime.

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
            gc.collect()
            task.set_step_progress(2+_progIni, "preparing ImgDiffView (Spatial Max)")
            self.imgDiffView(ImageView.SPATIAL).Max
            task.set_step_progress(2+_progIni, "preparing ImgDiffView (Spatial Std)")
            self.imgDiffView(ImageView.SPATIAL).StdNormed
            gc.collect()
            task.set_step_progress(2+_progIni, "preparing ImgDiffView (Temporal Max)")
            self.imgDiffView(ImageView.TEMPORAL).Max
            task.set_step_progress(2+_progIni, "preparing ImgDiffView (Temporal Std)")
            self.imgDiffView(ImageView.TEMPORAL).Std
            gc.collect()

        if task_continue:
            _Precompute(self._task_open_image)
        else:
            self._task_open_image.reset(function=_Precompute, name="preparing ImageObject", run_async=run_async)
            self._task_open_image.set_step_mode(3)
            self._task_open_image.start()
        return self._task_open_image
        
    def SetImagePrecompute(self, img:np.ndarray, name:str|None = None, run_async:bool = True) -> Task:
        """ 
            Set a new image with a given name and run PrecomputeImage() on it.

            :param np.ndarray img: The image
            :param str name: Name of the image
            :param bool async_mode: Controls if the precomputation runs in a different thread
            :returns Task: The task object of this task
            :raises AlreadyLoading: There is already a task working on this ImageObject
        """
        if not ImageObject._is_valid_image_stack(img):
            raise UnsupportedImageError()
        self.img = img
        self.name = name
        return self.PrecomputeImage(run_async=run_async)


    def OpenFile(self, path: Path|str, precompute:bool = False, calc_convoluted:bool = False, run_async:bool = True) -> Task:
        """ 
            Open an image using a given path.

            :param Path|str path: The path to the image file
            :param bool precompute: Controls if the loaded image is also precomputed
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
        
        self.clear()

        def _Load(task: Task):
            task.set_step_progress(0, "reading File")
            if path.suffix.lower() in [".tif", ".tiff"]:
                logger.debug(f"Opening '{path.name}' with tifffile")
                with tifffile.TiffFile(path) as tif:
                    self._img = tif.asarray()
                    self._metdata = tif.metaseries_metadata
            elif nd2.is_supported_file(path):
                logger.debug(f"Opening '{path.name}' with nd2")
                with nd2.ND2File(path) as ndfile:
                    self.img = ndfile.asarray()
                    self._metdata = ndfile.unstructured_metadata()
            else:
                logger.debug(f"Opening '{path.name}' with PIMS")
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
                self.img = np.array(imgNP)
                if getattr(_pimsImg, "get_metadata_raw", None) != None: 
                    self._metdata = collections.OrderedDict(sorted(_pimsImg.get_metadata_raw().items()))
            self._path = path
            self.name = path.stem
            
            if precompute:
                self.PrecomputeImage(task_continue=True, run_async=run_async)

        self._task_open_image.reset(function=_Load, name="open image file", run_async=run_async)
        self._task_open_image.set_step_mode(2 + 4*precompute)
        self._task_open_image.start()
        return self._task_open_image
    
    # Static functions

    @staticmethod
    def _is_valid_image_stack(image: Any) -> bool:
        if not isinstance(image, np.ndarray):
            return False
        if len(image.shape) != 3:
            return False
        return True
    
class ImageView(Enum):
    """ 
        Collapse a 3D image (t, y, x) into a smaller dimension
    """

    SPATIAL = (0,)
    """ SPATIAL: Removes the temporal component and creates a 2D image """
    TEMPORAL = (1,2)
    """ TEMPORAL: Removes the spatial component and creates an 1D time series """

class ImageObjectError(Exception):
    """ ImageObject Error"""
    pass

class AlreadyLoadingError(ImageObjectError):
    """ Already loading an Image into an ImageObject"""
    pass

class UnsupportedImageError(ImageObjectError):
    """ The image is unsupported """
    
    def __init__(self, file_name: str|None = None, exception: Exception|None = None, *args):
        super().__init__(*args)
        self.exception = exception
        self.file_name = file_name

class ImageShapeError(ImageObjectError):
    """ The image has an invalid shape """

    def __init__(self, shape: np.ndarray|None = None, *args):
        super().__init__(*args)
        self.shape = shape