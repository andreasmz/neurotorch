""" Classes for describing ROIs, synapses and detection algorithms """
import numpy as np
from skimage import measure
from skimage.measure._regionprops import RegionProperties
from skimage.segmentation import expand_labels
import math
import uuid
from skimage.feature import peak_local_max
from skimage.draw import disk
from typing import Self, Annotated
from scipy.spatial.distance import pdist
from scipy.cluster.hierarchy import fcluster, ward
from typing import Callable

from .image import ImageObject

# A Synapse Fire at a specific time. Must include a location (at least a estimation) to be display in the TreeView
class ISynapseROI:
    """ 
        This abstract class defines a synapse ROI describing a specific shape in an image or image frame  
    
        Convention: The order of coordiantes is Y, X to be compatible with the shape of the image (t, row, col).
        But for any kind of displaying convert them to X, Y to not cofuse the user
    """

    CLASS_DESC = "ISynapseROI" # Every subclass defines a string representing it
    """ Every subclass defines a description string """

    # Dict used for serialization; key is property name, value is tuple of serialization name and conversion function for the given data to give at least a minimal property from 
    #_serializable_fields_dict: {"location": ("location", )} 

    # Class functions

    def __init__(self):
        self.location: tuple|None = None
        """ (Estimated or actual) center of the synapse; used for selecting it in the plot and ordering """
        self.region_props: RegionProperties|None = None 
        """ Stores skimage RegionProperties for the ROI """
        self.uuid = str(uuid.uuid4())
        """ A unique UUID to identify the synapse """
        self.frame: int|None = None
        """ The associate frame for this ROI or None if the object just defines a shape """
        self.signal_strength: float|None = None
        """ Optional parameter to determine the current signal strength of the ROI """
    
    # Serialization functions

    def serialize(self) -> dict:
        """ Serialize the object """


    def set_frame(self, frame: int|None) -> Self:
        """ Set the frame of the synapse or removes it by providing None """
        self.frame = frame
        return self
    
    def set_location(self, location:tuple[int|float, int|float] = None, y:int|float = None, x:int|float = None) -> Self:
        """ 
            Set the location of the synapse by either providing a tuple or Y and X explicitly
            
            :param tuple[int|float, int|float] location: Location tuple (Y, X)
            :param int|float y:
            :param int|float x:
        """
        # Force the user to explicitly use set_location(y=y, x=x) to prevent mixing up of x and y
        if location is not None and (x is not None or y is not None):
            raise ValueError("set_location requires either a tuple or x/y as seperate argument. You provided both")
        if location is not None:
            self.location = location
        else:
            self.location = (y, x)
        
        return self
    
    def set_region_props(self, region_props: RegionProperties|None) -> Self:
        """ Set skimage.RegionProperties for this synapse """
        self.region_props = region_props
        return self
    
    @property
    def location_string(self) -> str:
        """ Returns the location of the synapse in the format 'X, Y' or '' if the location is not set """
        if self.location is None:
            return ""
        return f"{self.location[1]}, {self.location[0]}"
    
    def get_coordinates(self, shape:tuple|None) -> tuple[np.array, np.array]:
        """ 
            Return coordinates of points inside the ROI and inside the given shape. They are returned as a tuple
            with the first parameter beeing the y coordinates and the second the x coordinates.
            
            Example output: ([Y0, Y1, Y2, ...], [X0, X1, X2, ...])
        
            :returns tuple[np.array, np.array]: The coordinates inside the ROI in the format [yy, xx]
        """
        # ISynapseROI is empty placeholder, therefore return no coordinates
        return ([], [])
    
    def get_signal_from_image(self, img: np.ndarray) -> np.ndarray:
        """ Given an 3D ImageObject (t, y, x), flatten x and y to the pixels given by get_coordinates providing a shape (t, num_image_mask_pixel) """
        yy, xx = self.get_coordinates(img.shape[-2:])
        return img[:, yy, xx]
    
    def __str__(self) -> str:
        return f"ISynapseROI ({self.location_string})" if self.location is not None else "ISynapseROI"
        
    def __repr__(self):
        return "<%s>" % str(self)
    
    # Static functions 

    def get_distance(roi1: Self, roi2: Self) -> float:
        """ Returns the distance between the locations of the ROIs or np.inf if at least one has no location """
        if roi1.location is None or roi2.location is None: 
            return np.inf
        y1, x1 = roi1.location
        y2, x2 = roi2.location
        return np.sqrt((x2-x1)**2 + (y2 - y1)**2)

class CircularSynapseROI(ISynapseROI):
    """ Implements a circular ROI of a given radius"""

    CLASS_DESC = "Circular ROI"
    def __init__(self):
        super().__init__()
        self.radius: int|float|None = None
        """ Radius of the ROI """

    def set_radius(self, radius: int|float) -> Self:
        """ Set the radius of the ROI """
        self.radius = radius
        return self
    
    def get_coordinates(self, shape:tuple|None) -> tuple[np.array, np.array]:
        return disk(center=self.location, radius=self.radius+0.5,shape=shape)
    
    def __str__(self):
        return f"Circular ROI ({self.location_string}) r={self.radius}" if self.location is not None and self.radius is not None else "Circular ROI"
    
class PolygonalSynapseROI(ISynapseROI):
    """ Implements a polygonal synapse ROI """

    CLASS_DESC = "Polyonal ROI"
    def __init__(self):
        super().__init__()
        self.polygon: list[tuple[int, int]] = None
        """ List of polygon points in the format [(Y, X), (Y, X), ..] """
        self.coords = None
        """ List of points inside the polygon in the format [(Y, X), (Y, X), ..] """

    def set_polygon(self, polygon: list[tuple[int, int]], coords: list[tuple[int, int]], region_props: RegionProperties):
        """
            Set the polygon by providing the coordinate tuples and either a) the pixel coords or b) a RegionProperties object (from which the coords are derived)

            :param list[tuple[int, int]] polygon: The contour of the polygon in the format [(Y, X), (Y, X), ..]
            :param list[tuple[int, int]] coords: The pixel coordinates of the polygon in the format [(Y, X), (Y, X), ..]. Either it or a RegionProperties object must be given
            :param RegionPropertiers region_props: A region_props object. Either it or the coords must be given
        """
        self.polygon = polygon
        self.region_props = region_props
        if coords is not None:
            self.coords = coords
        elif region_props is not None:
            self.coords = region_props.coords_scaled
        else:
            raise ValueError("set_polygon requires requires at least coords or region props, but you did not provide either one")
        self.set_location(y=int(region_props.centroid_weighted[0]), x=int(region_props.centroid_weighted[1]))
        return self
    
    def get_coordinates(self, shape:tuple|None) -> tuple[np.array, np.array]:
        yy = np.array([ int(y) for y in self.coords[:, 0] if y >= 0 and y < shape[0]])
        xx = np.array([ int(x) for x in self.coords[:, 1] if x >= 0 and x < shape[1]])
        return (yy, xx)

    def __str__(self) -> str:
        return f"Polyonal ROI centered at ({self.location_string})"  if self.location is not None else "Polygonal ROI"

# A synapse contains multiple (MultiframeSynapse) or a single SynapseROI (SingleframeSynapse)
class ISynapse:
    """
        This abstract class defines the concept of a synapse. Currently there are two types of synapses: Singleframe and Multiframe.
    """
    def __init__(self):
        self.uuid = str(uuid.uuid4()) # Unique id
        """ Unique id of the synapse"""
        self.name: str|None = None
        """ Name of the synapse"""
        self.staged = False
        """ A synapse can be staged meaning it will not be replaced when rerunning the detection """
        self._rois: dict[str, ISynapseROI] = {}

    def __str__(self):
        return "<ISynapse Object>"
    
    def set_name(self, name: str|None) -> Self:
        """ Set the name of the synapse """
        self.name = name
        return self
    
    @property
    def location(self) -> tuple|None:
        """ Get the location of the synapse """
        return None
    
    @property
    def location_string(self) -> str:
        """ Returns the location of the synapse in the format 'X, Y' or '' if the location is not set """
        return f"{self.location[1]}, {self.location[0]}" if self.location is not None else ""
    
    @property
    def rois(self) -> list[ISynapseROI]:
        """ Returns the list of ROIS in this synapse"""
        return list(self._rois.values())
    
    @property
    def rois_dict(self) -> dict[str, ISynapseROI]:
        """ Returns the rois as dictionary with their UUID as key """
        return self._rois
    
    def get_roi_description(self) -> str:
        """ Abstract function for displaying information about the rois. Needs to be implemented by each subclass """
        return ""
    
class SingleframeSynapse(ISynapse):
    """
        Implements a synapse class which can hold exactly one ROI
    """

    def __init__(self, roi: ISynapseROI = None):
        super().__init__()
        self.set_roi(roi)

    def __str__(self):
        if self.location is not None:
            return f"<SingleframeSynapse @{self.location}>"
        return f"<SingleframeSynapse>"
    
    def set_roi(self, roi: ISynapseROI|None = None) -> Self:
        """ Set the ROI or remove it by passing None or no argument"""
        if roi is None:
            self._rois = {}
        else:
            self._rois = {roi.uuid: roi}
        return self
    
    @property
    def location(self) -> tuple|None:
        """ Get the location of the synapse accessed from the ROI """
        if len(self._rois) == 0:
            return None
        return self.rois[0].location
    
    def get_roi_description(self) -> str:
        """ Displays information about the roi by calling str(roi) """
        if len(self._rois) == 0:
            return ""
        return str(self.rois[0])


class MultiframeSynapse(ISynapse):
    """
        Implements a synapse which can hold multiple rois (one for each frame)
    """
    def __init__(self):
        super().__init__()
        self._location:tuple|None = None

    @property
    def location(self) -> tuple|None:
        """ Get the location of the synapse """
        if self._location is not None:
            return self._location
        X = [r.location[0] for r in self.rois if r.location is not None]
        Y = [r.location[1] for r in self.rois if r.location is not None]
        if len(X) != 0 and len(Y) != 0:
            return (int(np.mean(X)), int(np.mean(Y)))
        return None
    
    def set_location(self, location:tuple[int|float, int|float] = None, y:int|float = None, x:int|float = None) -> Self:
        """ 
            Set the location of the synapse by either providing a tuple or Y and X explicitly
            which is for example used for sorting them. There is no need to provide an exact center 

            :param tuple[int|float, int|float] location: Location tuple (Y, X)
            :param int|float y:
            :param int|float x:
        """
        # Force the user to explicitly use set_location(y=y, x=x) to prevent mixing up of x and y
        if location is not None and (x is not None or y is not None):
            raise ValueError("set_location requires either a tuple or x/y as seperate argument. You provided both")
        if location is not None:
            self.location = location
        else:
            self.location = (y, x)
        
        return self

    def add_roi(self, roi: ISynapseROI) -> Self:
        """ Add a ROI to the synapse"""
        self._rois[roi.uuid] = roi
        return self

    def add_rois(self, rois: list[ISynapseROI]) -> Self:
        """ Add a range of rois to the synapse """
        for r in rois:
            self.add_roi(r)
        return self

    def set_rois(self, rois: list[ISynapseROI]) -> Self:
        """ Remove all rois and append all rois in the given list """
        self._rois = {r.uuid: r for r in rois}
        return self
    
    def remove_roi(self, roi: ISynapseROI) -> Self:
        """ Remove a roi """
        del self._rois[roi.uuid]
        return self
    
    def clear_rois(self) -> Self:
        """ Remove all rois """
        self._rois = {}
        return self
    
    def get_roi_description(self) -> str:
        """ In the future return information about the rois. Currently, only the text 'Multiframe Synapse' is returned """
        return "Multiframe Synapse"
    

class DetectionResult:
    """
        Class to store the result of synapse detections
    """
    def __init__(self):
        self.clear()

    def clear(self):
        self._synapses: dict[str, ISynapse] = {}

    def add_synapse(self, s: ISynapse):
        self._synapses[s.uuid] = s

    @property
    def synapses(self) -> list[ISynapse]:
        """ The current list of synapses in this tab. If you modify values inside this list, make sure to call tvSynapses.SyncSynapses() to reflect the changes in the TreeView. """
        return list(self._synapses.values())
    
    @synapses.setter
    def synapses(self, val: list[ISynapse]):
        if not isinstance(val, list) or not all(isinstance(v, ISynapse) for v in val):
            raise ValueError("The synapse property expects a list of ISynapse")
        self._synapses = {s.uuid:s for s in val}

    @property
    def synapses_dict(self) -> dict[str, ISynapse]:
        """ 
            The current list of synapses in this tab presented as dict with the UUID as key. 
            If you modify values inside this list, make sure to call tvSynapses.SyncSynapses() to reflect the changes in the TreeView. 
        """
        return self._synapses
    
    @synapses_dict.setter
    def synapses_dict(self, val: dict[str, ISynapse]):
        if not isinstance(val, dict) or not all(isinstance(k, str) and isinstance(v, ISynapse) for k, v in val.items()):
            raise ValueError("The synapse property expects a dictionary of ISynapses with their UUID as key")
        self._synapses = val

        
class IDetectionAlgorithm:
    """ Abstract base class for a detection algorithm implementation """

    def __init__(self):
        pass
    
    def detect(self, img: np.ndarray, **kwargs) -> list[ISynapseROI]:
        """
            Given an input image as 2D np.ndarray and algorithm dependend arbitary arguments,
            return a list of ISynapseROI.

            :param np.ndarray img: The input image as 2D array
        """
        pass
    
    def reset(self):
        """ 
            Abstract funtion which must be overwritten by a subclass to reset internal variables and states
        """
        pass

class DetectionError(Exception):
    """
        Error thrown by calling detect() on a IDetectionAlgorithm object indicating something went wrong in the
        detection process.
    """
    pass


class Thresholding(IDetectionAlgorithm):
    """ 
        Implementation of the thresholding detection algorithm. For details see the documentation    
    """

    def __init__(self): 
        super().__init__()
        self.reset()

    def reset(self):
        self.imgThresholded: np.ndarray|None = None
        """ Internal variable; The image after it is thresholded """
        self.imgLabeled: np.ndarray|None = None
        """ Internal variable; The thresholded image with assigned labels"""
        self.imgRegProps = None
        """ Internal variable; Holding the region properties of each detected label """

    def detect(self, 
               img:np.ndarray, 
               threshold: int|float, 
               radius: int|float|None, 
               minArea: int|float
            ) -> list[ISynapseROI]:
        """
            Find ROIs in a given image. For details see the documentation

            :param np.ndarray img: The image as 2D numpy array
            :param int|float threshold: Detection is performed on a thresholded image
            :param int|float|None radius: Returns circular ROIs if radius >= 0 and polygonal ROIs if radius is None. Raises exception otherwise
            :param int|float minArea: Consider only ROIs with a pixel area greater than the provided value
        """
        if len(img.shape) != 2:
            raise ValueError("img must be a 2D numpy array")
        if radius is not None and radius < 0:
            raise ValueError("Radius must be positive or None")
        self.imgThresholded = (img >= threshold).astype(int)
        self.imgLabeled = measure.label(self.imgThresholded, connectivity=2)
        self.imgRegProps = measure.regionprops(self.imgLabeled)
        synapses = []
        for i in range(len(self.imgRegProps)):
            props = self.imgRegProps[i]
            if(props.area >= minArea):
                s = CircularSynapseROI().set_location(y=int(round(props.centroid[0],0)), x=int(round(props.centroid[1],0))).set_radius(radius).set_region_props(props)
                synapses.append(s)
        return synapses

class HysteresisTh(IDetectionAlgorithm):
    def __init__(self): 
        super().__init__()
        self.reset()

    def reset(self):
        self.thresholded_img = None
        self.labeled_img = None
        self.region_props = None
        self.thresholdFiltered_img = None

    def detect(self, 
               img:np.ndarray, 
               lowerThreshold: int|float, 
               upperThreshold: int|float, 
               minArea: int|float
        ) -> list[ISynapseROI]:
        """
            Find ROIs in a given image. For details see the documentation

            :param np.ndarray img: The image as 2D numpy array
            :param int|float lowerThreshold: lower threshold for detection
            :param int|float upperThreshold: upper threshold for detection
            :param int|float minArea: Consider only ROIs with a pixel area greater than the given value
        """
        self.thresholded_img = (img > lowerThreshold).astype(int)
        self.thresholded_img[self.thresholded_img > 0] = 1
        self.labeled_img = measure.label(self.thresholded_img, connectivity=1)
        self.region_props = measure.regionprops(self.labeled_img, intensity_image=img)
        self.thresholdFiltered_img = np.zeros(shape=img.shape)
        labels_ok = []

        rois = []
        for i in range(len(self.region_props)):
            region = self.region_props[i]
            if region.area >= minArea and region.intensity_max >= upperThreshold:
                labels_ok.append(region.label)
                contours = measure.find_contours(np.pad(region.image_filled, 1, constant_values=0), 0.9)
                if len(contours) != 1:
                    print(f"Error while Detecting using Advanced Polygonal Detection in label {i+1}; len(contour) = {len(contours)}, lowerThreshold = {lowerThreshold}, upperThreshold = {upperThreshold}, minArea = {minArea}")
                    raise DetectionError("While detecting ROIs, an unkown error happened (region with contour length greater than 1). Please refer to the log for help and provide the current image")
                contour = contours[0][:, ::-1] # contours has shape ((Y, X), (Y, X), ...). Switch it to ((X, Y),...) 
                startX = region.bbox[1] - 1 #bbox has shape (Y1, X1, Y2, X2)
                startY = region.bbox[0] - 1 # -1 As correction for the padding
                contour[:, 0] = contour[:, 0] + startX
                contour[:, 1] = contour[:, 1] + startY
                synapse = PolygonalSynapseROI().set_polygon(polygon=contour, region_props=region)
                rois.append(synapse)

                self.thresholdFiltered_img[region.bbox[0]:region.bbox[2], region.bbox[1]:region.bbox[3]] += region.image_filled*(i+1)
        
        return rois
    



class LocalMax(IDetectionAlgorithm):
    """ 
        Implementation of the LocalMax algorithm for ROI detection. For details see the documentation
    """

    def __init__(self): 
        super().__init__()
        self.reset()

    def reset(self):
        self.imgThresholded = None
        self.imgThresholded_labeled = None
        self.imgMaximumFiltered = None
        self.maxima_mask = None
        self.maxima_labeled = None
        self.maxima_labeled_expanded = None
        self.maxima_labeled_expaned_adjusted = None
        self.maxima = None
        self.combined_labeled = None
        self.region_props = None
        self.labeledImage = None

    def detect(self, 
               img:np.ndarray, 
               lowerThreshold: int|float,
               upperThreshold: int|float,
               expandSize: int,
               minArea: int,
               minDistance: int,
               radius: int|float|None
               ) -> list[ISynapseROI]:
        """
            Detect ROIs in the given 2D image. For details see the documentation

            Find ROIs in a given image. For details see the documentation

            :param np.ndarray img: The image as 2D numpy array
            :param int|float lowerThreshold: The lower threshold
            :param int|float upperThreshold: The upper threshold
            :param int expandSize: Pixel to expand the peak search into
            :param int minArea: Minimum area of a ROI
            :param int minDistance: Mimum distance between two ROIs
            :param int|float|None radius: Returns circular ROIs if radius >= 0 and polygonal ROIs if radius is None. Raises exception otherwise

        """
        if len(img.shape) != 2:
            raise ValueError("img must be a 2D numpy array")
        if radius is not None and radius < 0:
            raise ValueError("Radius must be positive or None")
        if lowerThreshold >= upperThreshold:
            upperThreshold = lowerThreshold
        
        self.reset()

        self.imgThresholded = (img >= lowerThreshold)
        self.imgThresholded_labeled = measure.label(self.imgThresholded, connectivity=1)
        self.maxima = peak_local_max(img, min_distance=minDistance, threshold_abs=upperThreshold) # ((Y, X), ..)
        self.maxima_labeled = np.zeros(shape=img.shape, dtype=int)
        for i in range(self.maxima.shape[0]):
            y,x = self.maxima[i, 0], self.maxima[i, 1]
            self.maxima_labeled[y,x] = i+1
        self.maxima_labeled_expanded = expand_labels(self.maxima_labeled, distance=expandSize)
        self.labeledImage = np.zeros(shape=img.shape, dtype=int)

        self.maxima_labeled_expaned_adjusted = np.zeros(shape=img.shape, dtype=int)

        for i in range(self.maxima.shape[0]):
            y,x = self.maxima[i]
            th_label = self.imgThresholded_labeled[y,x]
            maxima_label = self.maxima_labeled_expanded[y,x]
            assert th_label != 0
            assert maxima_label != 0
            _slice = np.logical_and((self.maxima_labeled_expanded == maxima_label), (self.imgThresholded_labeled == th_label))
            if np.count_nonzero(_slice) >= minArea:
                self.labeledImage += _slice*(i+1)
                self.maxima_labeled_expaned_adjusted += (self.maxima_labeled_expanded == maxima_label)*maxima_label

        self.region_props = measure.regionprops(self.labeledImage, intensity_image=img)
        
        rois = []
        for i in range(len(self.region_props)):
            region = self.region_props[i]
            if radius is None:
                contours = measure.find_contours(np.pad(region.image_filled, 1, constant_values=0), 0.9)
                contour = contours[0]
                for c in contours: # Find the biggest contour and assume its the one wanted
                    if c.shape[0] > contour.shape[0]:
                        contour = c

                contour = contour[:, ::-1] # contours has shape ((Y, X), (Y, X), ...). Switch it to ((X, Y),...) 
                startX = region.bbox[1] - 1 #bbox has shape (Y1, X1, Y2, X2)
                startY = region.bbox[0] - 1 # -1 As correction for the padding
                contour[:, 0] = contour[:, 0] + startX
                contour[:, 1] = contour[:, 1] + startY
                synapse = PolygonalSynapseROI()(polygon=contour, region_props=region)
            else:
                y, x = region.centroid_weighted
                x, y = int(round(x,0)), int(round(y,0))
                synapse = CircularSynapseROI().set_location(y=y, x=x).set_radius(radius)
                _imgSynapse = np.zeros(shape=img.shape, dtype=img.dtype)
                _imgSynapse[synapse.get_coordinates(img.shape)] = 1
                _regProp = measure.regionprops(_imgSynapse, intensity_image=img)
                synapse.set_region_props(_regProp[0])
            rois.append(synapse)
            
        return rois 
    



class SynapseClusteringAlgorithm:
    """
        A synapse clustering algorithm merges a list of ROIs detected from a defined list of frames to 
        a new list of synapses.
    """

    def cluster(rois: list[ISynapseROI]) -> list[ISynapse]:
        pass

class SimpleCustering(SynapseClusteringAlgorithm):

    def cluster(rois: list[ISynapseROI]) -> list[ISynapse]:
        locations = [r.location for r in rois]
        distances = pdist(locations)
        wardmatrix = ward(distances)
        cluster = fcluster(wardmatrix, criterion='distance', t=20)

        synapses: dict[int, MultiframeSynapse] = {}
        for label in set(cluster):
            synapses[label] = MultiframeSynapse()

        for i,r in enumerate(rois):
            label = cluster[i]
            synapses[label].add_roi(r)

        return list(synapses.values())