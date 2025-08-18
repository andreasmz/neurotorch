""" Classes for describing ROIs, synapses and detection algorithms """
import numpy as np
from skimage import measure
from skimage.measure._regionprops import RegionProperties
from skimage.segmentation import expand_labels
import uuid
from skimage.feature import peak_local_max
from skimage.draw import disk
from typing import Self, Callable, cast, Iterable
from collections.abc import Iterator
from scipy.spatial.distance import pdist
from scipy.cluster.hierarchy import fcluster, ward
import numbers

from ..utils.image import *

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
        self._uuid = str(uuid.uuid4())
        self._frame: int|None = None
        self._location: tuple[float, float]|None = None
        self._signal_strength: float|None = None
        self._region_props: RegionProperties|None = None 
        self._callbacks: list[Callable[[], None]] = []

    @property
    def uuid(self) -> str:
        """ Returns the unique and nopt mutable UUID of the synapse object """
        return self._uuid
    
    @property
    def frame(self) -> int|None:
        """ The associate frame for this ROI or None if the object just defines a shape """
        return self._frame
    
    @frame.setter
    def frame(self, val: int|None) -> None:
        if not (val is None or isinstance(val, int)):
            raise TypeError(f"Bad type for frame: '{type(val)}'")
        self._frame = val
        self.notify()

    @property
    def location(self) -> tuple[float, float]|None:
        """ Returns the location of the ROI (Y, X) or None """
        return self._location
    
    @location.setter
    def location(self, val: tuple[float, float]|None) -> None:
        if not (val is None or (isinstance(val, tuple) and len(val) == 2 and isinstance(val[0], numbers.Real) and isinstance(val[1], numbers.Real))):
            raise TypeError(f"Invalid location '{str(val)}'")
        self._location = val
        self.notify()

    @property
    def location_string(self) -> str:
        """ Returns the location of the synapse in the format 'X, Y' or '' if the location is not set """
        if self.location is None:
            return ""
        return f"{self.location[1]}, {self.location[0]}"
    
    @property
    def location_x(self) -> float|None:
        if self._location is None:
            return None
        return self._location[1]
    
    @property
    def location_y(self) -> float|None:
        if self._location is None:
            return None
        return self._location[0]

    @property
    def signal_strength(self) -> float|None:
        """ Optional parameter to determine the current signal strength of the ROI """
        return self._signal_strength
    
    @signal_strength.setter
    def signal_strength(self, val: float|None) -> None:
        if not (val is None or isinstance(val, numbers.Real)):
            raise TypeError(f"Bad type for signal_strength: '{type(val)}'")
        self._signal_strength = val
        self.notify()
    
    @property
    def region_props(self) -> RegionProperties|None:
        """ Stores skimage RegionProperties for the ROI """
        return self._region_props
    
    @region_props.setter
    def region_props(self, val: RegionProperties|None) -> None:
        if not (val is None or isinstance(val, RegionProperties)):
            raise TypeError(f"Bad type for region_props: '{type(val)}'")
        self._region_props = val
        self.notify()

    def get_coordinates(self, shape:tuple) -> tuple[np.ndarray|list, np.ndarray|list]:
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

    def notify(self) -> None:
        """ Notify all callbacks that some properties have changed """
        for c in self._callbacks:
            c()

    def set_frame(self, frame: int|None) -> Self:
        """ Set the frame of the synapse or removes it by providing None """
        self.frame = frame
        return self
    
    def set_location(self, *, location:tuple[int|float, int|float]|None = None, y:int|float|None = None, x:int|float|None = None) -> Self:
        """ 
            Set the location of the synapse by either providing a tuple or Y and X explicitly
            
            :param tuple[int|float, int|float] location: Location tuple (Y, X)
            :param int|float y:
            :param int|float x:
        """
        if location is not None and (x is not None or y is not None):
            raise ValueError("set_location requires either a tuple or x/y as seperate argument. You provided both")
        if location is not None:
            self.location = location
        elif x is not None and y is not None:
            self.location = (y, x)
        else:
            self.location = None
        
        return self
    
    def set_signal_strength(self, signal_strength: float|None) -> Self:
        self.signal_strength = signal_strength
        return self
    
    def set_region_props(self, region_props: RegionProperties|None) -> Self:
        """ Set skimage.RegionProperties for this synapse """
        self.region_props = region_props
        return self
    
    def register_callback(self, callback: Callable[[], None]) -> None:
        """ Register a callback. The callback is called when properties of the ISynapseROI object have been modified """
        if not callable(callback):
            raise TypeError(f"'{type(callback)}' is not callable")
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[], None]) -> None:
        """ Removes a callback """
        self._callbacks.remove(callback)
    
    def __str__(self) -> str:
        return f"ISynapseROI ({self.location_string})" if self.location is not None else "ISynapseROI"
        
    def __repr__(self):
        return "<%s>" % str(self)
    
    # Static functions 

    @staticmethod
    def get_distance_between_rois(roi1: "ISynapseROI", roi2: "ISynapseROI") -> float:
        """ Returns the distance between the locations of the ROIs or np.inf if at least one has no location """
        if roi1.location is None or roi2.location is None: 
            return np.inf
        y1, x1 = roi1.location
        y2, x2 = roi2.location
        return np.sqrt((x2-x1)**2 + (y2 - y1)**2)
    
    @staticmethod
    def get_distance(loc1: tuple[float, float]|None, loc2: tuple[float, float]|None) -> float:
        """ Returns the distance between two locations (as used in a ISynapseROI) or None if one of the locations is None """
        if loc1 is None or loc2 is None:
            return np.inf
        return np.sqrt((loc1[0]-loc2[0])**2 + (loc1[1]-loc2[1])**2)

class CircularSynapseROI(ISynapseROI):
    """ Implements a circular ROI of a given radius"""

    CLASS_DESC = "Circular ROI"
    def __init__(self):
        super().__init__()
        self._radius: float|None = None
        """ Radius of the ROI """

    @property
    def radius(self) -> float|None:
        return self._radius
    
    @radius.setter
    def radius(self, val: float|None):
        if not (val is None or isinstance(val, numbers.Real)):
            raise TypeError(f"Bad type for radius: '{type(val)}'")
        self._radius = val
        self.notify()

    def set_radius(self, radius: int|float|None) -> Self:
        """ Set the radius of the ROI """
        self.radius = radius
        return self
    
    def get_coordinates(self, shape:tuple) -> tuple[np.ndarray|list, np.ndarray|list]:
        if self.radius is None:
            return ([], [])
        return disk(center=self.location, radius=self.radius+0.5,shape=shape)
    
    def __str__(self):
        return f"Circular ROI ({self.location_string}) r={self.radius}" if self.location is not None and self.radius is not None else "Circular ROI"
    
class PolygonalSynapseROI(ISynapseROI):
    """ Implements a polygonal synapse ROI """

    CLASS_DESC = "Polyonal ROI"

    def __init__(self):
        super().__init__()
        self._coords: list[tuple[int, int]]|None = None
        self._polygon: list[tuple[int, int]]|None = None

    @property
    def coords(self) -> list[tuple[int, int]]|None:
        """ List of points inside the polygon in the format [(Y, X), (Y, X), ..] """
        return self._coords
    
    @coords.setter
    def coords(self, val: list[tuple[int, int]]|None) -> None:
        self._coords = val
        self.notify()

    @property
    def polygon(self) -> list[tuple[int, int]]|None:
        """ List of polygon points in the format [(Y, X), (Y, X), ..] """
        return self._polygon
    
    @polygon.setter
    def polygon(self, val: list[tuple[int, int]]|None) -> None:
        self._polygon = val
        self.notify()

    def set_polygon(self, polygon: list[tuple[int, int]], coords: list[tuple[int, int]]|None = None, region_props: RegionProperties|None = None):
        """
            Set the polygon by providing the coordinate tuples and either a) the pixel coords or b) a RegionProperties object (from which the coords are derived)

            :param list[tuple[int, int]] polygon: The contour of the polygon in the format [(Y, X), (Y, X), ..]
            :param list[tuple[int, int]] coords: The pixel coordinates of the polygon in the format [(Y, X), (Y, X), ..]. Either it or a RegionProperties object must be given
            :param RegionPropertiers region_props: A region_props object. Either it or the coords must be given
        """
        self._polygon = polygon
        self._region_props = region_props
        if coords is not None:
            self._coords = coords
            self.notify()
        elif region_props is not None:
            self._coords = [(int(yx[0]), int(yx[1])) for yx in region_props.coords_scaled]
            self.set_location(y=int(region_props.centroid_weighted[0]), x=int(region_props.centroid_weighted[1])) 
            # Set location does already call self.notify()
        else:
            raise ValueError("set_polygon requires requires at least coords or region props, but you did not provide either one")
        
        return self
    
    def get_coordinates(self, shape:tuple) -> tuple[np.ndarray|list, np.ndarray|list]:
        if self.coords is None:
            return ([], [])
        yy = np.array([ int(yx[0]) for yx in self.coords if yx[0] >= 0 and yx[0] < shape[0]])
        xx = np.array([ int(yx[1]) for yx in self.coords if yx[1] >= 0 and yx[1] < shape[1]])
        return (yy, xx)

    def __str__(self) -> str:
        return f"Polyonal ROI centered at ({self.location_string})"  if self.location is not None else "Polygonal ROI"
    
class ROIList:
    """ Implements a list of ROIS, but allows to access them via their UUID as in a dict. Also, a callback system is implemented """

    def __init__(self) -> None:
        self._rois: dict[str, ISynapseROI] = {}
        self._rois_callbacks: dict[str, Callable[[], None]] = {}
        self._callbacks: list[Callable[[list[ISynapseROI], list[ISynapseROI], list[ISynapseROI]], None]] = []

    def __getitem__(self, key: str|int):
        if isinstance(key, str) and key in self._rois:
            return self._rois[key]
        elif isinstance(key, int) and key < len(self):
            return self.to_list()[key]
        raise KeyError(f"Invalid key '{key}'")
    
    def __setitem__(self, key: str, value: ISynapseROI):
        if not isinstance(key, str):
            raise KeyError(f"Invalid key '{key}'")
        if not isinstance(value, ISynapseROI):
            raise TypeError(f"'{type(value)}' is not allowed")
        if key != value.uuid:
            raise ValueError(f"Invalid value: The key must match the UUID of the value")
        self._rois[key] = value
        self._rois_callbacks[key] = lambda: self.notify(modified=[value])
        value.register_callback(self._rois_callbacks[key])
        self.notify(added=[value])

    def __delitem__(self, key: str) -> None:
        if not isinstance(key, str) or not key in self._rois:
            raise KeyError(f"Invalid key '{key}'")
        s = self._rois[key]
        s.remove_callback(self._rois_callbacks[key])
        del self._rois[key]
        del self._rois_callbacks[key]
        self.notify(removed=[s])

    def __contains__(self, key: ISynapseROI|str) -> bool:
        if isinstance(key, str):
            return key in self._rois
        elif isinstance(key, ISynapseROI):
            return key in self._rois.values()
        return False
    
    def __iter__(self) -> Iterator[ISynapseROI]:
        return iter(self._rois.values())

    def __len__(self) -> int:
        return len(self._rois)
    
    def __del__(self) -> None:
        for r in self._rois.values():
            r.remove_callback(self._rois_callbacks[r.uuid])

    def __repr__(self) -> str:
        return f"<ROIList of {len(self)} ROIs>"

    def append(self, synapse: ISynapseROI, /) -> None:
        if not isinstance(synapse, ISynapseROI):
            raise TypeError(f"Can not append object of type '{type(synapse)}'")
        if synapse.uuid in self:
            raise KeyError(f"Duplicate key '{synapse.uuid}'")
        self[synapse.uuid] = synapse

    def as_dict(self) -> dict[str, ISynapseROI]:
        return self._rois

    def clear(self) -> None:
        self.clear_where(lambda s: True)

    def clear_where(self, fn: Callable[[ISynapseROI], bool]) -> None:
        deleted = []
        for r in self.to_list():
            if fn(r):
                deleted.append(r)
                r.remove_callback(self._rois_callbacks[r.uuid])
                del self._rois_callbacks[r.uuid]
                del self._rois_callbacks[r.uuid]
        self.notify(removed=deleted)

    def extend(self, rois: Iterable[ISynapseROI], /) -> None:
        if not isinstance(rois, Iterable):
            raise TypeError(f"{type(rois)} is not iterable")
        for r in rois:
            if not isinstance(r, ISynapseROI):
                raise TypeError(f"'{type(r)}' is not allowed")
            if r in self._rois:
                raise KeyError(f"Duplicate key '{str(r)}'")
        for r in rois:
            self._rois[r.uuid] = r
            self._rois_callbacks[r.uuid] = lambda: self.notify(modified=[r])
            r.register_callback(self._rois_callbacks[r.uuid])
        self.notify(added=list(rois))
            
    def notify(self, added: list[ISynapseROI] = [], removed: list[ISynapseROI] = [], modified: list[ISynapseROI] = []) -> None:
        """ Notify all registered callbacks"""
        for c in self._callbacks:
            c(added, removed, modified)

    def to_list(self) -> list[ISynapseROI]:
        return list(self._rois.values())
    
    def register_callback(self, callback: Callable[[list[ISynapseROI], list[ISynapseROI], list[ISynapseROI]], None]) -> None:
        """
        Register a callback on this results object. The callback must accept three lists of ISynapseROI (added, removed and modified) and will be called
        whenever the result changes
        """
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[list[ISynapseROI], list[ISynapseROI], list[ISynapseROI]], None]) -> None:
        """ Remove a callback """
        self._callbacks.remove(callback)

    def remove(self, roi: ISynapseROI) -> None:
        del self[roi.uuid]

# A synapse contains multiple (MultiframeSynapse) or a single SynapseROI (SingleframeSynapse)
class ISynapse:
    """
        This abstract class defines the concept of a synapse. Currently there are two types of synapses: Singleframe and Multiframe.
    """
    def __init__(self):
        self._uuid = str(uuid.uuid4()) # Unique id
        self._name: str|None = None
        self._staged: bool = False
        self.rois = ROIList()
        self._rois_callback = lambda _1,_2,_3: self.notify()
        self.rois.register_callback(self._rois_callback)

        self._callbacks: list[Callable[[], None]] = []

    @property
    def uuid(self) -> str:
        """ Returns the unique and nopt mutable UUID of the synapse object """
        return self._uuid
    
    @property
    def location(self) -> tuple[float, float]|None:
        """ Returns the location of the synapse (Y, X) or None """
        return None
    
    @property
    def location_x(self) -> float|None:
        if self.location is None:
            return None
        return self.location[1]
    
    @property
    def location_y(self) -> float|None:
        if self.location is None:
            return None
        return self.location[0]
    
    @property
    def location_string(self) -> str:
        """ Returns the location of the synapse in the format 'X, Y' or '' if the location is not set """
        return f"{self.location[1]}, {self.location[0]}" if self.location is not None else ""
    
    @property
    def name(self) -> str|None:
        """ Returns the name of the synapse or None """
        return self._name
    
    @name.setter
    def name(self, val: str|None) -> None:
        if not (val is None or isinstance(val, str)):
            raise TypeError(f"'{type(val)}' is not a valid name")
        self._name = val
        self.notify()

    def set_name(self, name: str|None) -> Self:
        self.name = name
        return self

    @property
    def staged(self) -> bool:
        """ A synapse can be staged meaning it will not be replaced when rerunning the detection """
        return self._staged
    
    @staged.setter
    def staged(self, val: bool) -> None:
        if not isinstance(val, bool):
            raise TypeError(f"bad type for staged: '{type(val)}'")
        self._staged = val
        self.notify()

    def get_roi_description(self) -> str:
        """ Abstract function for displaying information about the rois. Needs to be implemented by each subclass """
        return ""    

    def notify(self) -> None:
        """ Notify all callbacks that some properties have changed """
        for c in self._callbacks:
            c()    
    
    def register_callback(self, callback: Callable[[], None]) -> None:
        """ Register a callback. The callback is called when properties of the ISynapse object have been modified """
        if not callable(callback):
            raise TypeError(f"'{type(callback)}' is not callable")
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[], None]) -> None:
        """ Removes a callback """
        self._callbacks.remove(callback)

    def _format(self, append_str: str) -> str:
        append_str = " " + append_str
        return self.__class__.__name__ + (f" '{self.name}'" if self.name is not None else "") + f" of {len(self.rois)} ROIS" + append_str + (" staged" if self.staged else "")
    
    def __str__(self) -> str:
        return self._format("")
    
    def __repr__(self):
        return "<%s>" % str(self)
    
    def __del__(self) -> None:
        self.rois.remove_callback(self._rois_callback)
    
class SingleframeSynapse(ISynapse):
    """
        Implements a synapse class which can hold exactly one ROI
    """

    def __init__(self, roi: ISynapseROI|None = None):
        super().__init__()
        if roi is not None:
            self.rois.append(roi)

    def __str__(self) -> str:
        if self.location is not None:
            return self._format(f"@{self.location_string}")
        return self._format("")
    
    def set_roi(self, roi: ISynapseROI|None = None) -> Self:
        """ Set the ROI or remove it by passing None or no argument"""
        self.rois.clear()
        if roi is not None:
            self.rois.append(roi)
        return self
    
    @property
    def location(self) -> tuple[float, float]|None:
        if len(self.rois) == 0:
            return None
        return self.rois[0].location
    
    def get_roi_description(self) -> str:
        """ Displays information about the roi by calling str(roi) """
        if len(self.rois) == 0:
            return ""
        return str(self.rois[0])


class MultiframeSynapse(ISynapse):
    """
        Implements a synapse which can hold multiple rois (one for each frame)
    """
    def __init__(self):
        super().__init__()
        self._location:tuple[float, float]|None = None

    @property
    def location(self) -> tuple[float, float]|None:
        if self._location is not None:
            return self._location
        X = [r.location_x for r in self.rois if r.location_x is not None]
        Y = [r.location_y for r in self.rois if r.location_y is not None]
        if len(X) != 0 and len(Y) != 0:
            return (int(np.mean(X)), int(np.mean(Y)))
        return None
    
    def set_location(self, *, location:tuple[float, float]|None = None, y:float|None = None, x:float|None = None) -> Self:
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
            self._location = location
        elif x is not None and y is not None:
            self._location = (y, x)
        else:
            self._location = None
        
        return self
    
    def set_rois(self, rois: list[ISynapseROI]) -> Self:
        """ Add a range of rois to the synapse """
        self.rois.clear()
        self.rois.extend(rois)
        return self

    def extend_rois(self, rois: list[ISynapseROI]) -> Self:
        """ Add a range of rois to the synapse """
        self.rois.extend(rois)
        return self

    def get_roi_description(self) -> str:
        """ In the future return information about the rois. Currently, only the text 'Multiframe Synapse' is returned """
        return "Multiframe Synapse"
    
    def __str__(self) -> str:
        if self.location is not None:
            return self._format(f"@{self.location_string}")
        return self._format("")
    
class DetectionResult:
    """
        Class to store the result of synapse detections
    """

    def __init__(self) -> None:
        self._synapses: dict[str, ISynapse] = {}
        self._synapses_callbacks: dict[str, Callable[[], None]] = {}
        self._callbacks: list[Callable[[list[ISynapse], list[ISynapse], list[ISynapse]], None]] = []

    def __getitem__(self, key: str|int):
        if isinstance(key, str) and key in self._synapses:
            return self._synapses[key]
        elif isinstance(key, int) and key < len(self):
            return self.to_list()[key]
        raise KeyError(f"Invalid key '{key}'")
    
    def __setitem__(self, key: str, value: ISynapse):
        if not isinstance(key, str):
            raise KeyError(f"Invalid key '{key}'")
        if not isinstance(value, ISynapse):
            raise TypeError(f"'{type(value)}' is not allowed")
        if key != value.uuid:
            raise ValueError(f"Invalid value: The key must match the UUID of the value")
        self._synapses[key] = value
        self._synapses_callbacks[key] = lambda: self.notify(modified=[value])
        value.register_callback(self._synapses_callbacks[key])
        self.notify(added=[value])

    def __delitem__(self, key: str) -> None:
        if not isinstance(key, str) or not key in self._synapses:
            raise KeyError(f"Invalid key '{key}'")
        s = self._synapses[key]
        s.remove_callback(self._synapses_callbacks[key])
        del self._synapses_callbacks[key]
        del self._synapses[key]
        self.notify(removed=[s])

    def __contains__(self, key: ISynapse|str) -> bool:
        if isinstance(key, str):
            return key in self._synapses
        elif isinstance(key, ISynapse):
            return key in self._synapses.values()
        return False
    
    def __iter__(self) -> Iterator[ISynapse]:
        return iter(self._synapses.values())

    def __len__(self) -> int:
        return len(self._synapses)
    
    def __del__(self) -> None:
        for s in self._synapses.values():
            s.remove_callback(self._synapses_callbacks[s.uuid])

    def __repr__(self) -> str:
        return f"<DetectionResult holding {len(self)} Synapses>"

    def append(self, synapse: ISynapse, /) -> None:
        if not isinstance(synapse, ISynapse):
            raise TypeError(f"Can not append object of type '{type(synapse)}'")
        if synapse.uuid in self:
            raise KeyError(f"Duplicate key '{synapse.uuid}'")
        self[synapse.uuid] = synapse

    def as_dict(self) -> dict[str, ISynapse]:
        return self._synapses
    
    def clear(self) -> None:
        self.clear_where(lambda s: True)

    def clear_where(self, fn: Callable[[ISynapse], bool]) -> None:
        deleted = []
        for s in self.to_list():
            if fn(s):
                deleted.append(s)
                s.remove_callback(self._synapses_callbacks[s.uuid])
                del self._synapses_callbacks[s.uuid]
                del self._synapses[s.uuid]
        self.notify(removed=deleted)
        
    def extend(self, synapses: Iterable[ISynapse], /) -> None:
        if not isinstance(synapses, Iterable):
            raise TypeError(f"{type(synapses)} is not iterable")
        for s in synapses:
            if not isinstance(s, ISynapse):
                raise TypeError(f"'{type(s)}' is not allowed")
            if s in self._synapses:
                raise KeyError(f"Duplicate key '{str(s)}'")
        for s in synapses:
            self._synapses[s.uuid] = s
            self._synapses_callbacks[s.uuid] = lambda: self.notify(modified=[s])
            s.register_callback(self._synapses_callbacks[s.uuid])
        self.notify(added=list(synapses))
            
    def notify(self, added: list[ISynapse] = [], removed: list[ISynapse] = [], modified: list[ISynapse] = []) -> None:
        """ Notify all registered callbacks"""
        for c in self._callbacks:
            c(added, removed, modified)

    def to_list(self) -> list[ISynapse]:
        return list(self._synapses.values())
    
    def register_callback(self, callback: Callable[[list[ISynapse], list[ISynapse], list[ISynapse]], None]) -> None:
        """
        Register a callback on this results object. The callback must accept three lists of ISynapse (added, removed and modified) and will be called
        whenever the result changes
        """
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[list[ISynapse], list[ISynapse], list[ISynapse]], None]) -> None:
        """ Remove a callback """
        self._callbacks.remove(callback)

    def remove(self, synapse: ISynapse) -> None:
        del self[synapse.uuid]

        
class IDetectionAlgorithm():
    """ Abstract base class for a detection algorithm implementation """

    def __init__(self):
        pass
    
    def detect(self, img: np.ndarray, **kwargs) -> list[ISynapseROI]:
        """
            Given an input image as 2D np.ndarray and algorithm dependend arbitary arguments,
            return a list of ISynapseROI.

            :param np.ndarray img: The input image as 2D array
        """
        raise NotImplementedError()
    
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

    def detect(self,  # pyright: ignore[reportIncompatibleMethodOverride]
               img:np.ndarray,
               threshold: int|float, 
               radius: int|float|None, 
               minArea: int|float|None,
               **kwargs
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
        imgLabeled = measure.label(self.imgThresholded, connectivity=2)
        if not isinstance(imgLabeled, np.ndarray):
            raise RuntimeError(f"skimage.measure.label returned an unexpected result of type '{type(imgLabeled)}'")
        self.imgLabeled = imgLabeled
        self.imgRegProps = measure.regionprops(self.imgLabeled)
        synapses = []
        for i in range(len(self.imgRegProps)):
            props = self.imgRegProps[i]
            if minArea is None or (props.area >= minArea):
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

    def detect(self,  # pyright: ignore[reportIncompatibleMethodOverride]
               img:np.ndarray, 
               lowerThreshold: int|float, 
               upperThreshold: int|float, 
               minArea: int|float,
               **kwargs
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
        if not isinstance(self.labeled_img, np.ndarray):
            raise RuntimeError(f"skimage.measure.label returned an unexpected result of type '{type(self.labeled_img)}'")
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
                contour = [(yx[0], yx[1]) for yx in contour]
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
        self.imgThresholded: np.ndarray|None = None
        self.imgThresholded_labeled = None
        self.imgMaximumFiltered = None
        self.maxima_mask = None
        self.maxima_labeled = None
        self.maxima_labeled_expanded: np.ndarray|None = None
        self.maxima_labeled_expaned_adjusted = None
        self.maxima = None
        self.combined_labeled = None
        self.region_props: list[RegionProperties]|None = None
        self.labeledImage = None

    def detect(self, # pyright: ignore[reportIncompatibleMethodOverride]
               img:np.ndarray, 
               lowerThreshold: int|float,
               upperThreshold: int|float,
               expandSize: int,
               minArea: int,
               minDistance: int,
               radius: int|float|None,
               **kwargs
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
        if not isinstance(self.imgThresholded_labeled, np.ndarray):
            raise RuntimeError(f"skimage.measure.label returned an unexpected result of type '{type(self.imgThresholded_labeled)}'")
        self.maxima = peak_local_max(img, min_distance=minDistance, threshold_abs=upperThreshold) # ((Y, X), ..)
        self.maxima_labeled = np.zeros(shape=img.shape, dtype=int)
        for i in range(self.maxima.shape[0]):
            y,x = self.maxima[i, 0], self.maxima[i, 1]
            self.maxima_labeled[y,x] = i+1
        self.maxima_labeled_expanded = cast(np.ndarray, expand_labels(self.maxima_labeled, distance=expandSize))
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
                assert region.image_filled is not None
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
                contour = [(yx[0], yx[1]) for yx in contour]
                synapse = PolygonalSynapseROI().set_polygon(polygon=contour, region_props=region)
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

    @staticmethod
    def cluster(rois: list[ISynapseROI]) -> list[ISynapse]:
        raise NotImplementedError()

class SimpleCustering(SynapseClusteringAlgorithm):

    @staticmethod
    def cluster(rois: list[ISynapseROI]) -> list[ISynapse]:
        locations = [r.location for r in rois]
        # TODO
        distances = pdist(locations) # type: ignore
        wardmatrix = ward(distances)
        cluster = fcluster(wardmatrix, criterion='distance', t=20)

        synapses: dict[int, MultiframeSynapse] = {}
        for label in set(cluster):
            synapses[label] = MultiframeSynapse()

        for i,r in enumerate(rois):
            label = cluster[i]
            synapses[label].rois.append(r)

        return list(synapses.values())