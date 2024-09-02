import numpy as np
import skimage as ski
import math
import tkinter as tk

from neurotorch.utils.image import Img

class Synapse:
    def __init__(self):
        self.location = None
        self.radius = None
        self.frames = []

    def SetLocation(self, X, Y):
        self.location = (X, Y)
        return self
    
    def SetFrames(self, frames):
        self.frames = frames
        return self
    
    def SetRadius(self, radius):
        self.radius = radius
        return self
    
    def LocationStr(self):
        return f"({self.location[0]}, {self.location[1]})"
    
    def FramesStr(self):
        if self.frames is None:
            return ""
        return ','.join(self.frames)


    def GetUniqueName(self):
        return f"({self.LocationStr()}, r={self.radius}, f={self.FramesStr}"

class DetectionAlgorithm:

    def __init__(self):
        self.synapses = None

    def Detect(self, IMG: Img):
        pass

    def OptionsFrame(self, master):
        self.optionsFrame = tk.LabelFrame(master, text="Options")
        return self.optionsFrame

class Tresholding(DetectionAlgorithm):

    def __init__(self): 
        super().__init__()

    def Detect(self, IMG: Img):
        self.synapses = [Synapse().SetLocation(100,100).SetRadius(6)]
        return True

    def OptionsFrame(self, master):
        self.master = master
        self.optionsFrame = tk.LabelFrame(master, text="Options")
        self.lblScaleDiffInfo = tk.Label(self.optionsFrame, text="threshold")
        self.lblScaleDiffInfo.grid(row=0, column=0, columnspan=2)
        self.varDiff = tk.IntVar(value=20)
        self.intDiff = tk.Spinbox(self.optionsFrame, from_=1, to=200, textvariable=self.varDiff,width=5)
        self.intDiff.grid(row=1, column=0)
        self.scaleDiff = tk.Scale(self.optionsFrame, variable=self.varDiff, from_=1, to=200, orient="horizontal", showvalue=False)
        self.scaleDiff.grid(row=1, column=1)
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

#Advanced Maximum Mask
class AMM(DetectionAlgorithm):
    def __init__(self): 
        super().__init__()

    def Detect(self, IMG: Img):
        self.synapses = [Synapse().SetLocation(100,100).SetRadius(6)]

class ROIImage:

    # Convention: self.rois (X, Y)

    def __init__(self):
        self.imgThresholded = None
        self.imgLabeled = None
        self.imgRegProps = None
        self.rois = None

    def EstimateParameters(self, img: np.ndarray):
        median = np.median(img.flatten())
        std = np.std(img.flatten())
        max = np.max(img)
        threshold = math.ceil(median+2*std)
        if (std <= 2*median):
            threshold = math.ceil(0.3*max)
        return {"Threshold": threshold}

    def SetImg(self, img: np.ndarray, threshold):
        if (img is None or len(img.shape) != 2): return
        self.imgThresholded = (img >= threshold).astype(int)


    def LabelImg(self, radius: int, minROISize: float):
        self.imgLabeled = ski.measure.label(self.imgThresholded, connectivity=2)
        self.imgRegProps = ski.measure.regionprops(self.imgLabeled)
        self.rois = []
        for i in range(len(self.imgRegProps)):
            if(self.imgRegProps[i].area >= math.pi*(radius**2)*minROISize):
                self.rois.append((int(round(self.imgRegProps[i].centroid[1],0)), int(round(self.imgRegProps[i].centroid[0],0))))
