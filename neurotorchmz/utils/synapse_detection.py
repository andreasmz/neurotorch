import numpy as np
from skimage import measure
from skimage.segmentation import expand_labels
import math
import uuid
from skimage.feature import peak_local_max
from skimage.draw import disk

from .image import ImgObj

# A Synapse Fire at a specific time. Must include a location (at least a estimation) to be display in the TreeView
class ISynapseROI:
    def __init__(self):
        self.location = None
        self.regionProps = None
        self.uuid = str(uuid.uuid4())

    def SetLocation(self, X, Y):
        self.location = (X, Y)
        return self
    
    def SetRegionProps(self, region_props):
        self.regionProps = region_props
        return self
    
    def LocationStr(self) -> str:
        if self.location is None:
            return ""
        return f"{self.location[0]}, {self.location[1]}"
    
    def GetImageMask(self, shape:tuple|None) -> tuple[np.array, np.array]:
        return ([], [])
    
    def GetImageSignal(self, img: np.ndarray) -> np.array:
        rr, cc = self.GetImageMask(img.shape[-2:])
        return img[:, rr, cc]
    
    def ToStr(self):
        return f"({self.LocationStr()})"

class CircularSynapseROI(ISynapseROI):
    def __init__(self):
        super().__init__()
        self.radius = None

    def SetRadius(self, radius):
        self.radius = radius
        return self
    
    def GetImageMask(self, shape:tuple|None) -> tuple[np.ndarray, np.ndarray]:
        return disk(center=(self.location[1], self.location[0]), radius=self.radius+0.5,shape=shape)
    
    def ToStr(self):
        return f"{self.location[0]}, {self.location[1]}, r={self.radius}"
    
class PolygonalSynapseROI(ISynapseROI):
    def __init__(self):
        super().__init__()
        self.polygon = None
        self.coords_scaled = None

    def SetPolygon(self, polygon, region_props):
        # Polygon uses format [[X, Y] , [X, Y], ...]
        self.polygon = polygon
        self.regionProps = region_props
        # region_props uses format (Y, X)
        self.SetLocation(int(region_props.centroid_weighted[1]), int(region_props.centroid_weighted[0]))
        return self
    
    def GetImageMask(self, shape:tuple|None) -> tuple[np.array, np.array]:
        rr = np.array([ int(y) for y in self.regionProps.coords_scaled[:, 0] if y >= 0 and y < shape[0]])
        cc = np.array([ int(x) for x in self.regionProps.coords_scaled[:, 1] if x >= 0 and x < shape[1]])
        return (rr, cc)
    
    """
    def GetImageSignal(self, imgObj: ImgObj) -> list[float]:
        if imgObj.img is None or self.regionProps is None:
            return
        return np.array([imgObj.img[:,int(y),int(x)] for (y,x) in self.regionProps.coords_scaled])
    
    def GetImageDiffSignal(self, imgObj: ImgObj) -> list[float]:
        if imgObj.imgDiff is None or self.regionProps is None:
            return
        return np.array([imgObj.imgDiff[:,int(y),int(x)] for (y,x) in self.regionProps.coords_scaled]) 

    """

# A synapse contains multiple (MultiframeSynapse) or a single SynapseROI (SingleframeSynapse)
class ISynapse:
    def __init__(self):
        self.uuid = str(uuid.uuid4())
        self.name: str|None = None

    def __str__(self):
        return "<ISynapse Object>"
    
    def ROIsToSynapses(rois: list[ISynapseROI]):
        """
            This function should convert a list of ROIs to a list of synapses
        """
        return None
    
    @property
    def location(self) -> tuple|None:
        return None
    
class SingleframeSynapse(ISynapse):
    def __init__(self):
        super().__init__()
        self.synapse = None

    def __init__(self, synapseROI: ISynapseROI):
        super().__init__()
        self.synapse = synapseROI

    def __str__(self):
        return f"<SingleframeSynapse @{self.location}>"
    
    def SetSynapse(self, synapseROI: ISynapseROI) -> ISynapse:
        self.synapse = synapseROI
        return self
    
    def ROIsToSynapses(rois: list[ISynapseROI]):
        synapses = []
        if rois is None:
            return None
        for r in rois:
            synapses.append(SingleframeSynapse(r))
        return synapses
    
    @property
    def location(self) -> tuple|None:
        if self.synapse is None:
            return None
        return self.synapse.location


class MultiframeSynapse(ISynapse):
    def __init__(self):
        super().__init__()
        self.subsynapses = {}

    def AddSynapse(self, frame: int, synapse: ISynapseROI) -> ISynapse:
        self.subsynapses[frame] = synapse
        return self
    
    def ClearSynapses(self):
        self.subsynapses = {}

    def ROIsToSynapses(rois: list[ISynapseROI]):
        synapses = []
        for r in rois:
            synapses.append(MultiframeSynapse().AddSynapse(r))
        return synapses
    
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