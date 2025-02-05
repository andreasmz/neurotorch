import numpy as np
from skimage import measure
from skimage.measure._regionprops import RegionProperties
from skimage.segmentation import expand_labels
import math
import uuid
from skimage.feature import peak_local_max
from skimage.draw import disk
from typing import Self
from scipy.spatial.distance import pdist
from scipy.cluster.hierarchy import fcluster, ward

from .image import ImgObj

# A Synapse Fire at a specific time. Must include a location (at least a estimation) to be display in the TreeView
class ISynapseROI:
    CLASS_DESC = "ISynapseROI"
    def __init__(self):
        self.location: tuple|None = None
        self.regionProps: RegionProperties|None = None
        self.uuid = str(uuid.uuid4())
        self.frame: int|None = None

    def SetFrame(self, frame: int|None):
        self.frame = frame
        return self

    def SetLocation(self, X, Y) -> Self:
        self.location = (X, Y)
        return self
    
    def SetRegionProps(self, region_props: RegionProperties|None):
        self.regionProps = region_props
        return self
    
    def LocationStr(self) -> str:
        if self.location is None:
            return ""
        return f"{self.location[0]}, {self.location[1]}"
    
    def Distance(roi1: Self, roi2: Self) -> float:
        """ Returns the distance between the locations of the ROIs or np.inf if at least one has no location """
        if roi1.location is None or roi2.location is None: 
            return np.inf
        x1, y1 = roi1.location
        x2, y2 = roi2.location
        return np.sqrt((x2-x1)**2 + (y2 - y1)**2)

    
    def GetImageMask(self, shape:tuple|None) -> tuple[np.array, np.array]:
        """ Returns list of coordinates inside the ROI in the format ([X0, X1, X2, ...], [Y0, Y1, Y2, ...])"""
        # ISynapseROI is empty placeholder, therefore return no coordinates
        return ([], [])
    
    def GetImageSignal(self, img: np.ndarray) -> np.ndarray:
        """"""
        rr, cc = self.GetImageMask(img.shape[-2:])
        return img[:, rr, cc]
    
    def ToStr(self):
        return f"ISynapseROI ({self.LocationStr()})" if self.location is not None else "ISynapseROI"

class CircularSynapseROI(ISynapseROI):
    CLASS_DESC = "Circular Synapse ROI"
    def __init__(self):
        super().__init__()
        self.radius: int|None = None

    def SetRadius(self, radius) -> Self:
        self.radius = radius
        return self
    
    def GetImageMask(self, shape:tuple|None) -> tuple[np.array, np.array]:
        """ Returns list of coordinates inside the ROI in the format ([X0, X1, X2, ...], [Y0, Y1, Y2, ...])"""
        return disk(center=(self.location[1], self.location[0]), radius=self.radius+0.5,shape=shape)
    
    def ToStr(self):
        return f"Circular ROI ({self.LocationStr()}) r={self.radius}" if self.location is not None and self.radius is not None else "Circular ROI"
    
class PolygonalSynapseROI(ISynapseROI):
    CLASS_DESC = "Polyonal Synapse ROI"
    def __init__(self):
        super().__init__()
        self.polygon = None
        self.coords_scaled = None

    def SetPolygon(self, polygon, region_props):
        # Polygon uses format [[X, Y] , [X, Y], ...]
        # region_props uses format (Y, X)
        self.polygon = polygon
        self.regionProps = region_props
        self.SetLocation(int(region_props.centroid_weighted[1]), int(region_props.centroid_weighted[0]))
        return self
    
    def GetImageMask(self, shape:tuple|None) -> tuple[np.array, np.array]:
        """ Returns list of coordinates inside the ROI in the format ([X0, X1, X2, ...], [Y0, Y1, Y2, ...])"""
        rr = np.array([ int(y) for y in self.regionProps.coords_scaled[:, 0] if y >= 0 and y < shape[0]])
        cc = np.array([ int(x) for x in self.regionProps.coords_scaled[:, 1] if x >= 0 and x < shape[1]])
        return (rr, cc)

    def ToStr(self) -> str:
        return f"Polyonal ROI centered at ({self.LocationStr()})"  if self.location is not None else "Polygonal ROI"

# A synapse contains multiple (MultiframeSynapse) or a single SynapseROI (SingleframeSynapse)
class ISynapse:
    def __init__(self):
        self.uuid = str(uuid.uuid4())
        self.name: str|None = None
        self.staged = False
        self._rois: dict[str, ISynapseROI] = {}

    def __str__(self):
        return "<ISynapse Object>"
    
    def SetName(self, name: str|None) -> Self:
        self.name = name
        return self
    
    @property
    def location(self) -> tuple|None:
        return None
    
    @property
    def locationStr(self) -> str:
        return f"{self.location[0]}, {self.location[1]}" if self.location is not None else ""
    
    @property
    def rois(self) -> list[ISynapseROI]:
        return list(self._rois.values())
    
    @property
    def rois_dict(self) -> dict[str, ISynapseROI]:
        return self._rois
    
    def ROIDescriptionStr(self) -> str:
        return ""
    
class SingleframeSynapse(ISynapse):

    def __init__(self, roi: ISynapseROI = None):
        super().__init__()
        self.SetROI(roi)

    def __str__(self):
        if self.location is not None:
            return f"<SingleframeSynapse @{self.location}>"
        return f"<SingleframeSynapse>"
    
    def SetROI(self, roi: ISynapseROI|None = None) -> Self:
        """ Set the ROI or remove it by passing None or no argument"""
        if roi is None:
            self._rois = {}
        else:
            self._rois = {roi.uuid: roi}
        return self
    
    @property
    def location(self) -> tuple|None:
        if len(self._rois) == 0:
            return None
        return self.rois[0].location
    
    def ROIDescriptionStr(self) -> str:
        if len(self._rois) == 0:
            return ""
        return self.rois[0].ToStr()


class MultiframeSynapse(ISynapse):
    def __init__(self):
        super().__init__()
        self._location:tuple|None = None

    @property
    def location(self) -> tuple|None:
        if self._location is not None:
            return self._location
        X = [r.location[0] for r in self.rois if r.location is not None]
        Y = [r.location[1] for r in self.rois if r.location is not None]
        if len(X) != 0 and len(Y) != 0:
            return (int(np.mean(X)), int(np.mean(Y)))
        return None
    
    def SetLocation(self, X:int, Y:int) -> Self:
        self._location = (X, Y)
        return self
    
    def RemoveExplicitLocation(self) -> Self:
        self._location = None
        return self

    def AddROI(self, roi: ISynapseROI) -> Self:
        self._rois[roi.uuid] = roi
        return self

    def AddROIs(self, rois: list[ISynapseROI]) -> Self:
        for r in rois:
            self.AddROI(r)
        return self

    def SetROIs(self, rois: list[ISynapseROI]) -> Self:
        self._rois = {r.uuid: r for r in rois}
        return self
    
    def RemoveROI(self, roi: ISynapseROI) -> Self:
        del self._rois[roi.uuid]
        return self
    
    def ClearROIs(self) -> Self:
        self._rois = {}
        return self

    def AddSynapse(self, frame: int, synapse: ISynapseROI) -> ISynapse:
        self.AddROI(synapse.SetFrame(frame))
        return self
    
    def ROIDescriptionStr(self) -> str:
        return "Multiframe Synapse"
    

class DetectionResult:
    def __init__(self):
        self.synapses: list[ISynapse] = None

    def AddISynapses(self, isynapses: list[ISynapse]):
        if isynapses is None:
            return
        if not isinstance(isynapses, list):
            isynapses = [isynapses]
        if len(isynapses) == 0:
            return
        if self.synapses is None:
            self.synapses = []
        self.synapses.extend(isynapses)

    def SetISynapses(self, isynapses: list[ISynapse]):
        if isynapses is None:
            return
        if not isinstance(isynapses, list):
            isynapses = [isynapses]
        self.synapses = isynapses
    
    def Clear(self):
        self.synapses = None
        
class DetectionAlgorithm:

    def Detect(self, img: np.ndarray, **kwargs) -> list[ISynapseROI]:
        return None
    
    def Reset(self):
        pass


class Tresholding(DetectionAlgorithm):

    def __init__(self): 
        super().__init__()
        self.Reset()

    def Reset(self):
        self.imgThresholded = None
        self.imgLabeled = None
        self.imgRegProps = None

    def Detect(self, img:np.ndarray, **kwargs) -> list[ISynapseROI]:
        try:
            threshold = kwargs["threshold"]
            radius = kwargs["radius"]
            minROISize = kwargs["minROISize"]
        except KeyError:
            return None

        minArea = math.pi*(radius**2)*minROISize
        self.imgThresholded = (img >= threshold).astype(int)
        self.imgLabeled = measure.label(self.imgThresholded, connectivity=2)
        self.imgRegProps = measure.regionprops(self.imgLabeled)
        synapses = []
        for i in range(len(self.imgRegProps)):
            props = self.imgRegProps[i]
            if(props.area >= minArea):
                s = CircularSynapseROI().SetLocation(int(round(props.centroid[1],0)), int(round(props.centroid[0],0))).SetRadius(radius)
                synapses.append(s)
        return synapses

class HysteresisTh(DetectionAlgorithm):
    def __init__(self): 
        super().__init__()
        self.Reset()

    def Reset(self):
        self.thresholded_img = None
        self.labeled_img = None
        self.region_props = None
        self.thresholdFiltered_img = None

    def Detect(self, img:np.ndarray, **kwargs) -> list[ISynapseROI]:
        try:
            lowerThreshold = kwargs["lowerThreshold"]
            upperThreshold = kwargs["upperThreshold"]
            minArea = kwargs["minArea"]
        except KeyError:
            return None

        self.thresholded_img = (img > lowerThreshold).astype(int)
        self.thresholded_img[self.thresholded_img > 0] = 1
        self.labeled_img = measure.label(self.thresholded_img, connectivity=1)
        self.region_props = measure.regionprops(self.labeled_img, intensity_image=img)
        self.thresholdFiltered_img = np.zeros(shape=img.shape)
        labels_ok = []

        synapses = []
        for i in range(len(self.region_props)):
            region = self.region_props[i]
            if region.area >= minArea and region.intensity_max >= upperThreshold:
                labels_ok.append(region.label)
                if (len(labels_ok) == 50):
                    if "warning_callback" in kwargs and not kwargs["warning_callback"](mode="ask", message="Your settings found more than 50 ROIs. Do you really want to continue?"):
                        return None
                contours = measure.find_contours(np.pad(region.image_filled, 1, constant_values=0), 0.9)
                if len(contours) != 1:
                    print(f"Error while Detecting using Advanced Polygonal Detection in label {i+1}; len(contour) = {len(contours)}, lowerThreshold = {lowerThreshold}, upperThreshold = {upperThreshold}, minArea = {minArea}")
                    if "warning_callback" in kwargs:
                        kwargs["warning_callback"](mode="error", message="While detecting ROIs, an unkown error happened (region with contour length greater than 1). Please refer to the log for help and provide the current image")
                    return None
                contour = contours[0][:, ::-1] # contours has shape ((Y, X), (Y, X), ...). Switch it to ((X, Y),...) 
                startX = region.bbox[1] - 1 #bbox has shape (Y1, X1, Y2, X2)
                startY = region.bbox[0] - 1 # -1 As correction for the padding
                contour[:, 0] = contour[:, 0] + startX
                contour[:, 1] = contour[:, 1] + startY
                synapse = PolygonalSynapseROI().SetPolygon(contour, region)
                synapses.append(synapse)

                self.thresholdFiltered_img[region.bbox[0]:region.bbox[2], region.bbox[1]:region.bbox[3]] += region.image_filled*(i+1)
        
        return synapses
    



class LocalMax(DetectionAlgorithm):
    def __init__(self): 
        super().__init__()
        self.Reset()

    def Reset(self):
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

    def Detect(self, img:np.ndarray, **kwargs) -> list[ISynapseROI]:
        self.Reset()
        warningCallback = None if "warning_callback" not in kwargs else kwargs["warning_callback"]
        try:
            lowerThreshold = kwargs["lowerThreshold"]
            upperThreshold = kwargs["upperThreshold"]
            expandSize = kwargs["expandSize"]
            maxPeakCount = kwargs["maxPeakCount"]
            minArea = kwargs["minArea"]
            minDistance = kwargs["minDistance"]
            minSignal = kwargs["minSignal"]
            radius = kwargs["radius"]
            sortBySignal = kwargs["sortBySignal"]
            imgObj = kwargs["ImgObj"]
        except KeyError:
            if warningCallback is not None:
                warningCallback(mode="error", message="There was internal error in passing the algorithms parameters")           
            return None

        
        if lowerThreshold >= upperThreshold:
            upperThreshold = lowerThreshold

        self.imgThresholded = (img >= lowerThreshold)
        self.imgThresholded_labeled = measure.label(self.imgThresholded, connectivity=1)
        #_numpeaks = maxPeakCount if maxPeakCount > 0 else np.inf
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
        
        synapses = []
        for i in range(len(self.region_props)):
            region = self.region_props[i]
            if radius < 0:
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
                synapse = PolygonalSynapseROI().SetPolygon(contour, region)
            else:
                y, x = region.centroid_weighted
                x, y = int(round(x,0)), int(round(y,0))
                synapse = CircularSynapseROI().SetLocation(x, y).SetRadius(radius)
                _imgSynapse = np.zeros(shape=img.shape, dtype=img.dtype)
                _imgSynapse[synapse.GetImageMask(img.shape)] = 1
                _regProp = measure.regionprops(_imgSynapse, intensity_image=img)
                synapse.SetRegionProps(_regProp[0])
            synapse.strength = np.max(np.mean(synapse.GetImageSignal(imgObj.imgDiff), axis=1))
            if minSignal <= 0 or synapse.strength >= minSignal:
                synapses.append(synapse)
        if sortBySignal or maxPeakCount > 0:
            synapses.sort(key=lambda x: x.strength, reverse=True)
        if maxPeakCount > 0:
            synapses = synapses[:maxPeakCount]
        if not sortBySignal:
            synapses.sort(key=lambda x: (x.location[1], x.location[0]))
            
        return synapses 
    



class SynapseClusteringAlgorithm:
    """
        A synapse clustering algorithm merges a list of ROIs detected from a defined list of frames to 
        a new list of synapses.
    """

    def Cluster(rois: list[ISynapseROI]) -> list[ISynapse]:
        pass

class SimpleCustering(SynapseClusteringAlgorithm):

    def Cluster(rois: list[ISynapseROI]) -> list[ISynapse]:
        locations = [r.location for r in rois]
        distances = pdist(locations)
        wardmatrix = ward(distances)
        cluster = fcluster(wardmatrix, criterion='distance', t=20)

        synapses: dict[int, MultiframeSynapse] = {}
        for label in set(cluster):
            synapses[label] = MultiframeSynapse()

        for i,r in enumerate(rois):
            label = cluster[i]
            synapses[label].AddROI(r)

        return list(synapses.values())