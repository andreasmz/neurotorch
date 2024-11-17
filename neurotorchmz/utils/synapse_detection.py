import numpy as np
from skimage import measure
import math
from tkinter import messagebox
import uuid

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
    
    def GetImageSignal(self, imgObj: ImgObj) -> list[float]:
        return []
    
    def GetImageDiffSignal(self, imgObj: ImgObj) -> list[float]:
        return []
    
    def ToStr(self):
        return f"({self.LocationStr()})"

class CircularSynapseROI(ISynapseROI):
    def __init__(self):
        super().__init__()
        self.radius = None

    def SetRadius(self, radius):
        self.radius = radius
        return self
    
    def GetImageSignal(self, imgObj: ImgObj) -> list[float]:
        if imgObj.img is None:
            return
        xmax = imgObj.img.shape[2]
        ymax = imgObj.img.shape[1]
        point = self.location
        radius = self.radius
        return np.array([imgObj.img[:,y,x] for x in range(point[0]-radius,point[0]+2*radius+1) for y in range(point[1]-radius,point[1]+2*radius+1)
                     if ((x-point[0])**2+(y-point[1])**2)<radius**2+2**(1/2) and x >= 0 and y >= 0 and x < xmax and y < ymax])
    
    def GetImageDiffSignal(self, imgObj: ImgObj) -> list[float]:
        if imgObj.imgDiff is None:
            return
        xmax = imgObj.imgDiff.shape[2]
        ymax = imgObj.imgDiff.shape[1]
        point = self.location
        radius = self.radius
        return np.array([imgObj.imgDiff[:,y,x] for x in range(point[0]-radius,point[0]+2*radius+1) for y in range(point[1]-radius,point[1]+2*radius+1)
                     if ((x-point[0])**2+(y-point[1])**2)<radius**2+2**(1/2) and x >= 0 and y >= 0 and x < xmax and y < ymax])
    
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
    
    def GetImageSignal(self, imgObj: ImgObj) -> list[float]:
        if imgObj.img is None or self.regionProps is None:
            return
        return np.array([imgObj.img[:,int(y),int(x)] for (y,x) in self.regionProps.coords_scaled])
    
    def GetImageDiffSignal(self, imgObj: ImgObj) -> list[float]:
        if imgObj.imgDiff is None or self.regionProps is None:
            return
        return np.array([imgObj.imgDiff[:,int(y),int(x)] for (y,x) in self.regionProps.coords_scaled]) 

# A synapse contains multiple (MultiframeSynapse) or a single SynapseROI (SingleframeSynapse)
class ISynapse:
    def __init__(self):
        self.uuid = str(uuid.uuid4())

    def __str__(self):
        return ""
    
    def ROIsToSynapses(rois: list[ISynapseROI]):
        """
            This function should convert a list of ROIs to a list of synapses
        """
        return None
    
class SingleframeSynapse(ISynapse):
    def __init__(self):
        super().__init__()
        self.synapse = None

    def __init__(self, synapseROI: ISynapseROI):
        super().__init__()
        self.synapse = synapseROI
    
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
        self.synapses: list[ISynapse] = None # Contains ISynapse objects
        self.modified = False

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

    def Detect(self, imgObject: ImgObj, frame:int = None, **kwargs) -> list[ISynapseROI]:
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

    def Detect(self, imgObject: ImgObj, frame:int = None, **kwargs) -> list[ISynapseROI]:
        if imgObject.imgDiff is None:
            return None
        try:
            threshold = kwargs["threshold"]
            radius = kwargs["radius"]
            minROISize = kwargs["minROISize"]
        except KeyError:
            return None

        minArea = math.pi*(radius**2)*minROISize
        if frame is None:
            self.imgThresholded = (imgObject.imgDiffView(ImgObj.SPATIAL).Max >= threshold).astype(int)
        else:
            self.imgThresholded = (imgObject.imgDiff[frame] >= threshold).astype(int)
        self.imgLabeled = measure.label(self.imgThresholded, connectivity=2)
        self.imgRegProps = measure.regionprops(self.imgLabeled)
        synapses = []
        for i in range(len(self.imgRegProps)):
            props = self.imgRegProps[i]
            if(props.area >= minArea):
                s = CircularSynapseROI().SetLocation(int(round(props.centroid[1],0)), int(round(props.centroid[0],0))).SetRadius(radius)
                synapses.append(s)
        return synapses

#Advanced Polygonal Detection
class APD(DetectionAlgorithm):
    def __init__(self): 
        super().__init__()
        self.Reset()

    def Reset(self):
        self.thresholded_img = None
        self.labeled_img = None
        self.region_props = None
        self.thresholdFiltered_img = None

    def Detect(self, imgObject: ImgObj, frame = None, **kwargs) -> list[ISynapseROI]:
        try:
            mode = kwargs["imgMode"]
            lowerThreshold = kwargs["lowerThreshold"]
            upperThreshold = kwargs["upperThreshold"]
            minArea = kwargs["minArea"]
        except KeyError:
            return None
        
        if mode == "Diff":
            if frame is None:
                return None
            _img = imgObject.imgDiff[frame]
        elif mode == "DiffMax":
            _img = imgObject.imgDiffView(ImgObj.SPATIAL).Max
        elif mode == "DiffStd":
            _img = imgObject.imgDiffView(ImgObj.SPATIAL).Std
        else:
            return None

        self.thresholded_img = (_img > lowerThreshold).astype(int)
        self.thresholded_img[self.thresholded_img > 0] = 1
        self.labeled_img = measure.label(self.thresholded_img, connectivity=1)
        self.region_props = measure.regionprops(self.labeled_img, intensity_image=_img)
        self.thresholdFiltered_img = np.empty(shape=_img.shape)
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