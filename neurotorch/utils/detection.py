import numpy as np
from skimage import measure
import math
import tkinter as tk
from tkinter import ttk, messagebox
import uuid

from neurotorch.utils.image import Img as IMGObject
from neurotorch.gui.components import IntStringVar

# A Synapse Fire at a specific time. Must include a location (at least a estimation) to be display in the TreeView
class ISynapseROI:
    def __init__(self):
        self.location = None
        self.uuid = str(uuid.uuid4())

    def SetLocation(self, X, Y):
        self.location = (X, Y)
        return self
    
    def LocationStr(self) -> str:
        if self.location is None:
            return ""
        return f"{self.location[0]}, {self.location[1]}"
    
    def GetImageSignal(self, imgObj: IMGObject) -> list[float]:
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
    
    def GetImageSignal(self, imgObj: IMGObject) -> list[float]:
        if imgObj.img is None:
            return
        xmax = imgObj.img.shape[2]
        ymax = imgObj.img.shape[1]
        point = self.location
        radius = self.radius
        return np.array([imgObj.img[:,y,x] for x in range(point[0]-radius,point[0]+2*radius+1) for y in range(point[1]-radius,point[1]+2*radius+1)
                     if ((x-point[0])**2+(y-point[1])**2)<radius**2+2**(1/2) and x >= 0 and y >= 0 and x < xmax and y < ymax])
    
    def ToStr(self):
        return f"{self.location[0]}, {self.location[1]}, r={self.radius}"
    
class PolygonalSynapseROI(ISynapseROI):
    def __init__(self):
        super().__init__()
        self.polygon = None
        self.regionProps = None
        self.coords_scaled = None

    def SetPolygon(self, polygon, region_props):
        self.polygon = polygon
        self.regionProps = region_props
        # region_props uses format (Y, X)
        self.SetLocation(int(region_props.centroid_weighted[1]), int(region_props.centroid_weighted[0]))
        return self
    
    def GetImageSignal(self, imgObj: IMGObject) -> list[float]:
        if imgObj.img is None or self.regionProps is None:
            return
        return np.array([imgObj.img[:,int(y),int(x)] for (y,x) in self.regionProps.coords_scaled])

# A synapse contains multiple (MultiframeSynapse) or a single SynapseROI (SingleframeSynapse)
class ISynapse:
    def __init__(self):
        self.uuid = str(uuid.uuid4())

    def __str__(self):
        return ""
    
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

class MultiframeSynapse(ISynapse):
    def __init__(self):
        super().__init__()
        self.subsynapses = {}

    def AddSynapse(self, frame: int, synapse: ISynapseROI) -> ISynapse:
        self.subsynapses[frame] = synapse
        return self
    
    def ClearSynapses(self):
        self.subsynapses = {}
    
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
        if len(isynapses) == 0:
            return
        self.synapses = isynapses
    
    def Clear(self):
        self.synapses = None

class DetectionAlgorithm:

    def __init__(self):
        self.ax2Title = ""

    def Detect(self, imgObject: IMGObject, frame:int = None) -> list[ISynapse]:
        return None

    def OptionsFrame(self, master, imgObj: IMGObject):
        self.optionsFrame = tk.LabelFrame(master, text="Options")
        return self.optionsFrame
    
    def OptionsFrame_Update(self):
        pass

    def Reset(self):
        pass
    
    def AX2Image(self):
        return None


class Tresholding(DetectionAlgorithm):

    def __init__(self): 
        self.imgThresholded = None
        self.imgLabeled = None
        self.imgRegProps = None
        super().__init__()
        self.ax2Title = "Thresholded Image"

    def Reset(self):
        self.__init__()

    def Detect(self, imgObject: IMGObject, frame:int = None) -> list[SingleframeSynapse]:
        if frame is None and imgObject.imgDiffMaxTime is None:
            return None
        if frame is not None and imgObject.imgDiff is None:
            return None
        threshold = self.varThreshold.get()
        radius = self.varROIRadius.get()
        minROISize = self.varROIMinSize.get()/100
        minArea = math.pi*(radius**2)*minROISize
        if frame is None:
            self.imgThresholded = (imgObject.imgDiffMaxTime >= threshold).astype(int)
        else:
            self.imgThresholded = (imgObject.imgDiff[frame] >= threshold).astype(int)
        self.imgLabeled = measure.label(self.imgThresholded, connectivity=2)
        self.imgRegProps = measure.regionprops(self.imgLabeled)
        synapses = []
        for i in range(len(self.imgRegProps)):
            if(self.imgRegProps[i].area >= minArea):
                s = SingleframeSynapse(CircularSynapseROI().SetLocation(int(round(self.imgRegProps[i].centroid[1],0)), int(round(self.imgRegProps[i].centroid[0],0))).SetRadius(radius))
                synapses.append(s)
        return synapses
    
    def AX2Image(self):
        return self.imgLabeled

    def OptionsFrame(self, master, imgObj: IMGObject):
        self.master = master
        self.optionsFrame = tk.LabelFrame(master, text="Options")
        self.lblScaleDiffInfo = tk.Label(self.optionsFrame, text="threshold")
        self.lblScaleDiffInfo.grid(row=0, column=0, columnspan=2)
        self.varThreshold = tk.IntVar(value=20)
        self.intThreshold = tk.Spinbox(self.optionsFrame, from_=1, to=200, textvariable=self.varThreshold,width=5)
        self.intThreshold.grid(row=1, column=0)
        self.scaleThreshold = tk.Scale(self.optionsFrame, variable=self.varThreshold, from_=1, to=200, orient="horizontal", showvalue=False)
        self.scaleThreshold.grid(row=1, column=1)
        tk.Label(self.optionsFrame, text="ROI radius").grid(row=2, column=0)
        self.varROIRadius = tk.IntVar(value=6)
        self.intROIRadius = tk.Spinbox(self.optionsFrame, from_=1, to=50, textvariable=self.varROIRadius, width=5)
        self.intROIRadius.grid(row=2, column=1)
        tk.Label(self.optionsFrame, text="px").grid(row=2, column=2)
        self.lblROIMinSize = tk.Label(self.optionsFrame, text="Minimum coverage")
        self.lblROIMinSize.grid(row=3, column=0)
        self.varROIMinSize = tk.IntVar(value=60)
        self.intROIMinSize = tk.Spinbox(self.optionsFrame, from_=0, to=100, textvariable=self.varROIMinSize, width=5)
        self.intROIMinSize.grid(row=3,column=1)
        tk.Label(self.optionsFrame, text="%").grid(row=3, column=2)   

        return self.optionsFrame

#Advanced Polygonal Detection
class APD(DetectionAlgorithm):
    def __init__(self): 
        super().__init__()
        self.thresholded_img = None
        self.labeled_img = None
        self.region_props = None
        self.thresholdFiltered_img = None
        self.imgObj = None

    def Reset(self):
        self.__init__()

    def Detect(self, imgObject: IMGObject, frame = None) -> list[SingleframeSynapse]:
        if frame is None and imgObject.imgDiffMaxTime is None:
            return None
        if frame is not None and imgObject.imgDiff is None:
            return None
        lowerThreshold = self.varLowerThreshold.IntVar.get()
        upperThreshold = self.varUpperThreshold.IntVar.get()
        minArea = self.varMinArea.IntVar.get()

        if frame is None:
            _img = imgObject.imgDiffMaxTime
        else:
            _img = imgObject.imgDiff[frame]

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
                    if not messagebox.askyesno("Neurotorch", "Your settings found more than 50 ROIs. Do you really want to continue?"):
                        return None
                contours = measure.find_contours(np.pad(region.image_filled, 1, constant_values=0), 0.9)
                if len(contours) != 1:
                    print(f"Error while Detecting using Advanced Polygonal Detection in label {i+1}; len(contour) = {len(contours)}, lowerThreshold = {lowerThreshold}, upperThreshold = {upperThreshold}, minArea = {minArea}")
                    messagebox.showerror("Neurotorch", "While detecting ROIs, an unkown error happened (region with contour length greater than 1). Please refer to the log for help and provide the current image")
                    return None
                contour = contours[0][:, ::-1] 
                startX = region.bbox[1] - 1 
                startY = region.bbox[0] - 1
                contour[:, 0] = contour[:, 0] + startX
                contour[:, 1] = contour[:, 1] + startY
                _roi = PolygonalSynapseROI().SetPolygon(contour, region)
                synapse = SingleframeSynapse(_roi)
                synapses.append(synapse)

        for l in labels_ok:
            self.thresholdFiltered_img = np.max([self.thresholdFiltered_img, self.labeled_img == l], axis=0)
        
        return synapses
        
    def AX2Image(self):
        return self.thresholdFiltered_img
        
    def OptionsFrame(self, master, imgObj: IMGObject):
        self.master = master
        self.imgObj = imgObj
        self.optionsFrame = tk.LabelFrame(master, text="Options")

        tk.Label(self.optionsFrame, text="Lower Threshold").grid(row=1, column=0)
        tk.Label(self.optionsFrame, text="Upper Threshold").grid(row=2, column=0)
        tk.Label(self.optionsFrame, text="Min. Area").grid(row=3, column=0)
        self.lblMinAreaInfo = tk.Label(self.optionsFrame, text="")
        self.lblMinAreaInfo.grid(row=4, column=0, columnspan=3)

        self.varLowerThreshold = IntStringVar(master, tk.IntVar(value=10)).SetStringVarBounds(0,1000)
        self.varUpperThreshold = IntStringVar(master, tk.IntVar(value=40)).SetStringVarBounds(0,1000)
        self.varMinArea = IntStringVar(master, tk.IntVar(value=20)).SetStringVarBounds(0,1000)
        self.varMinArea.SetCallback(self._UpdateMinAreaText)
        self.scaleLowerThreshold = ttk.Scale(self.optionsFrame, from_=1, to=100, variable=self.varLowerThreshold.IntVar)
        self.scaleUpperThreshold = ttk.Scale(self.optionsFrame, from_=1, to=100, variable=self.varUpperThreshold.IntVar)
        self.scaleMinArea = ttk.Scale(self.optionsFrame, from_=0, to=500, variable=self.varMinArea.IntVar)
        self.numLowerThreshold = tk.Spinbox(self.optionsFrame, width=6, textvariable=self.varLowerThreshold.StringVar, from_=0, to=1000)
        self.numUpperThreshold = tk.Spinbox(self.optionsFrame, width=6, textvariable=self.varUpperThreshold.StringVar, from_=0, to=1000)
        self.numMinArea = tk.Spinbox(self.optionsFrame, width=6, textvariable=self.varMinArea.StringVar, from_=0, to=1000)
        self.scaleLowerThreshold.grid(row=1, column=1, sticky="news")
        self.scaleUpperThreshold.grid(row=2, column=1, sticky="news")
        self.scaleMinArea.grid(row=3, column=1, sticky="news")
        self.numLowerThreshold.grid(row=1, column=2)
        self.numUpperThreshold.grid(row=2, column=2)
        self.numMinArea.grid(row=3, column=2)

        self._UpdateMinAreaText()
        self.OptionsFrame_Update()
        
        return self.optionsFrame
    
    def OptionsFrame_Update(self):
        if self.imgObj is None:
            return
        if self.imgObj.imgDiffMaxTime is not None:
            self.lblImgStats = tk.Label(self.optionsFrame, text=f"DiffImage Stats: range = [{np.min(self.imgObj.imgDiffMaxTime)}, {np.max(self.imgObj.imgDiffMaxTime)}], std = {np.round(np.std(self.imgObj.imgDiffMaxTime), 2)}")
            self.lblImgStats.grid(row=0, column=0, columnspan=3)
    
    def _UpdateMinAreaText(self):
        A = self.varMinArea.IntVar.get()
        r = round(np.sqrt(A/np.pi),2)
        self.lblMinAreaInfo["text"] = f"A circle with radius {r} px has the same area"