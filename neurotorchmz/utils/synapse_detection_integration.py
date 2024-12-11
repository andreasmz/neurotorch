import tkinter as tk
from tkinter import ttk, messagebox
from typing import Literal
from matplotlib import patches

from .image import ImageProperties
from ..gui.components import *
from ..gui.settings import Neurotorch_Resources as Resource
from .synapse_detection import *

# While synapse_detection.py provides detection algorithms, this file contains the actual implementation into Neurotorch GUI

class IDetectionAlgorithmIntegration:
    
    def __init__(self, displayMessageboxes = False):
        # The algorithm is choosing on its own what data to use. For this, an IMGObject is provided
        self.imgObj = None
        self.root = None
        self.provides_rawPlot = False

    def OptionsFrame(self, root, imgObjCallback) -> tk.LabelFrame:
        """
            This function is used to generate an frame for the algorithm options. The Integration class is responsible for this LabelFrame and
            should return in after generation. If may (!) be that this class is called multiple times, for example after changing the algorithm.
        """
        self.root = root
        self.optionsFrame = tk.LabelFrame(self.root, text="Options")
        return self.optionsFrame
    
    def OptionsFrame_Update(self, inputImageObj: ImageProperties|None):
        """
            This Update function is called, after an new image is loaded (or after other certain events that may invalidate the algorithms parameters)
            and could be for example used to update parameter estimations.
        """
        pass

    def DetectAutoParams(self, inputImageObj: ImageProperties) -> list[ISynapse]:
        """
            This function should be an wrapper for the Detect function in an DetectionAlgorithm and get the parameters from the GUI and then call
            and return the Algorithms Detect function. Only parameter frame is provided by the GUI and set to None when the mean image should be used.
        """
        pass

    def Img_DetectionOverlay(self) -> tuple[tuple[np.ndarray]|None, list[patches.Patch]|None]:
        """
            An Integration may choose to provide an custom overlay image, usually the raw data obtained in one of the first steps. 
            Also it may provide a list of matplotlib patches for this overlay
            Return None to not plot anything
        """
        pass


class Thresholding_Integration(Tresholding, IDetectionAlgorithmIntegration):

    def __init__(self):
        super().__init__()

    def OptionsFrame(self, root, imgObjCallback) -> tk.LabelFrame:
        self.root = root
        self.optionsFrame = tk.LabelFrame(self.root, text="Options")

        self.setting_threshold = GridSetting(self.optionsFrame, row=5, text="Threshold", unit="", default=50, min_=0, max_=2**15-1, scaleMin=1, scaleMax=200, tooltip=Resource.GetString("algorithms/threshold/params/threshold"))
        self.setting_radius = GridSetting(self.optionsFrame, row=6, text="Radius", unit="px", default=6, min_=0, max_=1000, scaleMin=-1, scaleMax=30, tooltip=Resource.GetString("algorithms/threshold/params/radius"))
        self.setting_minAreaPercent = GridSetting(self.optionsFrame, row=7, text="Min. converage", unit="%", default=60, min_=1, max_=100, scaleMin=1, scaleMax=100, tooltip=Resource.GetString("algorithms/threshold/params/minCoverage"))
        return self.optionsFrame
    
    def DetectAutoParams(self, inputImageObj: ImageProperties) -> list[ISynapse]:
        threshold = self.setting_threshold.Get()
        radius = self.setting_radius.Get()
        minROISize = self.setting_minAreaPercent.Get()/100
        return self.Detect(inputImageObj.img, threshold=threshold, radius=radius, minROISize=minROISize)
    
    def Img_DetectionOverlay(self) -> tuple[tuple[np.ndarray]|None, list[patches.Patch]|None]:
        return ((self.imgThresholded,), None)
    

class HysteresisTh_Integration(HysteresisTh, IDetectionAlgorithmIntegration):
        
    def OptionsFrame(self, root, imgObjCallback) -> tk.LabelFrame:
        self.root = root
        self.optionsFrame = tk.LabelFrame(self.root, text="Options")


        self.lblImgStats = tk.Label(self.optionsFrame)
        self.lblImgStats.grid(row=1, column=0, columnspan=3)

        tk.Label(self.optionsFrame, text="Auto paramters").grid(row=5, column=0, sticky="ne")
        self.varAutoParams = tk.IntVar(value=1)
        self.checkAutoParams = ttk.Checkbutton(self.optionsFrame, variable=self.varAutoParams)
        self.checkAutoParams.grid(row=5, column=1, sticky="nw")

        self.setting_lowerTh = GridSetting(self.optionsFrame, row=10, text="Lower threshold", unit="", default=50, min_=0, max_=2**15-1, scaleMin=1, scaleMax=200, tooltip=Resource.GetString("algorithms/hysteresisTh/params/lowerThreshold"))
        self.setting_upperTh = GridSetting(self.optionsFrame, row=11, text="Upper threshold", unit="", default=70, min_=0, max_=2**15-1, scaleMin=1, scaleMax=200, tooltip=Resource.GetString("algorithms/hysteresisTh/params/upperThreshold"))
        self.lblPolygonalROIs = tk.Label(self.optionsFrame, text="Polygonal ROIs")
        self.lblPolygonalROIs.grid(row=12, column=0, sticky="ne")
        ToolTip(self.lblPolygonalROIs, msg=Resource.GetString("algorithms/hysteresisTh/params/polygonalROIs"), follow=True, delay=0.1)
        self.varCircularApprox = tk.IntVar(value=1)
        self.checkCircularApprox = ttk.Checkbutton(self.optionsFrame, variable=self.varCircularApprox)
        self.checkCircularApprox.grid(row=12, column=1, sticky="nw")
        self.setting_radius = GridSetting(self.optionsFrame, row=13, text="Radius", unit="px", default=6, min_=0, max_=1000, scaleMin=1, scaleMax=30, tooltip=Resource.GetString("algorithms/hysteresisTh/params/radius"))
        self.setting_radius.SetVisibility(not self.varCircularApprox.get())
        self.varCircularApprox.trace_add("write", lambda _1,_2,_3:self.setting_radius.SetVisibility(not self.varCircularApprox.get()))
        
        self.setting_minArea = GridSetting(self.optionsFrame, row=14, text="Min. Area", unit="px", default=50, min_=1, max_=10000, scaleMin=0, scaleMax=200, tooltip=Resource.GetString("algorithms/hysteresisTh/params/minArea"))
        self.setting_minArea.var.IntVar.trace_add("write", lambda _1,_2,_3: self._UpdateMinAreaText())
        self.lblMinAreaInfo = tk.Label(self.optionsFrame, text="")
        self.lblMinAreaInfo.grid(row=15, column=0, columnspan=3)
        self._UpdateMinAreaText()

        
        

        self.OptionsFrame_Update(None)
        
        return self.optionsFrame
    
    def OptionsFrame_Update(self, inputImageObj: ImageProperties|None):
        if inputImageObj is None:
            self.lblImgStats["text"] = ""
            return
        
        _t = f"Image Stats: range = [{int(inputImageObj.min)}, {int(inputImageObj.max)}], "
        _t = _t + f"{np.round(inputImageObj.mean, 2)} ± {np.round(inputImageObj.std, 2)}, "
        _t = _t + f"median = {np.round(inputImageObj.median, 2)}"
        self.lblImgStats["text"] = _t
        self.CalcAutoParams(inputImageObj)

    def CalcAutoParams(self, inputImageObj: ImageProperties):
        if self.varAutoParams.get() != 1:
            return
        lowerThreshold = int(inputImageObj.mean + 2.5*inputImageObj.std)
        upperThreshold = max(lowerThreshold, min(inputImageObj.max/2, inputImageObj.mean + 5*inputImageObj.std))
        self.setting_lowerTh.var.IntVar.set(lowerThreshold)
        self.setting_upperTh.var.IntVar.set(upperThreshold)

    def _UpdateMinAreaText(self):
        A = self.setting_minArea.Get()
        r = round(np.sqrt(A/np.pi),2)
        self.lblMinAreaInfo["text"] = f"A circle with radius {r} px has the same area" 

    def DetectAutoParams(self, inputImageObj: ImageProperties) -> list[ISynapse]:
        polygon = self.varCircularApprox.get()
        radius = self.setting_radius.Get()
        lowerThreshold = self.setting_lowerTh.Get()
        upperThreshold = self.setting_upperTh.Get()
        minArea = self.setting_minArea.Get() if polygon else 0
        

        result = self.Detect(inputImageObj.img, 
                             lowerThreshold=lowerThreshold, 
                             upperThreshold=upperThreshold, 
                             minArea=minArea, 
                             warning_callback=self._Callback)

        if polygon:
            return result
        else:
            synapses_return = []
            if result is None:
                return None
            for s in result:
                if isinstance(s, CircularSynapseROI):
                    synapses_return.append(s)
                    continue
                synapses_return.append(CircularSynapseROI().SetLocation(s.location[0], s.location[1]).SetRadius(radius))
            return synapses_return
    
    def _Callback(self, mode: Literal["ask", "info", "warning", "error"], message=""):
        if mode == "ask":
            return messagebox.askyesno("Neurotorch", message)
        elif mode == "info":
            messagebox.showinfo("Neurotorch", message)
        elif mode == "warning":
            messagebox.showwarning("Neurotorch", message)
        elif mode == "error":
            messagebox.showerror("Neurotorch", message)

            
    def Img_DetectionOverlay(self) -> tuple[tuple[np.ndarray]|None, list[patches.Patch]|None]:
        return ((self.thresholdFiltered_img, ), None)
    

class LocalMax_Integration(LocalMax, IDetectionAlgorithmIntegration):

    def __init__(self):
        super().__init__()

    def OptionsFrame(self, root, imgObjCallback) -> tk.LabelFrame:
        self.root = root
        self.imgObjCallback = imgObjCallback
        self.optionsFrame = tk.LabelFrame(self.root, text="Options")

        self.lblImgStats = tk.Label(self.optionsFrame)
        self.lblImgStats.grid(row=1, column=0, columnspan=3)

        tk.Label(self.optionsFrame, text="Auto paramters").grid(row=5, column=0, sticky="ne")
        self.varAutoParams = tk.IntVar(value=1)
        self.checkAutoParams = ttk.Checkbutton(self.optionsFrame, variable=self.varAutoParams)
        self.checkAutoParams.grid(row=5, column=1, sticky="nw")

        self.setting_radius = GridSetting(self.optionsFrame, row=10, text="Radius", unit="px", default=6, min_=-1, max_=1000, scaleMin=-1, scaleMax=30, tooltip=Resource.GetString("algorithms/localMax/params/radius"))
        self.setting_lowerTh = GridSetting(self.optionsFrame, row=11, text="Lower threshold", unit="", default=50, min_=0, max_=2**15-1, scaleMin=1, scaleMax=400, tooltip=Resource.GetString("algorithms/localMax/params/lowerThreshold"))
        self.setting_upperTh = GridSetting(self.optionsFrame, row=12, text="Upper threshold", unit="", default=70, min_=0, max_=2**15-1, scaleMin=1, scaleMax=400, tooltip=Resource.GetString("algorithms/localMax/params/upperThreshold"))
        self.setting_sortBySignal = GridSetting(self.optionsFrame, row=13, text="Sort by signal strength", type_="Checkbox", default=1, min_=0, tooltip=Resource.GetString("algorithms/localMax/params/sortBySignal"))
        
        tk.Label(self.optionsFrame, text="Advanced settings").grid(row=20, column=0, columnspan=4, sticky="nw")
        self.setting_maxPeakCount = GridSetting(self.optionsFrame, row=21, text="Max. Peak Count", unit="", default=0, min_=0, max_=200, scaleMin=0, scaleMax=100, tooltip=Resource.GetString("algorithms/localMax/params/maxPeakCount"))
        self.setting_minDistance = GridSetting(self.optionsFrame, row=22, text="Min. Distance", unit="px", default=20, min_=1, max_=1000, scaleMin=1, scaleMax=100, tooltip=Resource.GetString("algorithms/localMax/params/minDistance"))
        self.setting_expandSize = GridSetting(self.optionsFrame, row=23, text="Expand size", unit="px", default=6, min_=0, max_=200, scaleMin=0, scaleMax=50, tooltip=Resource.GetString("algorithms/localMax/params/expandSize"))
        self.setting_minSignal = GridSetting(self.optionsFrame, row=24, text="Minimum Signal", unit="", default=0, min_=0, max_=2**15-1, scaleMin=0, scaleMax=400, tooltip=Resource.GetString("algorithms/localMax/params/minSignal"))
        self.setting_minArea = GridSetting(self.optionsFrame, row=25, text="Min. Area", unit="px", default=50, min_=1, max_=10000, scaleMin=0, scaleMax=200, tooltip=Resource.GetString("algorithms/localMax/params/minArea"))
        self.setting_minArea.var.IntVar.trace_add("write", lambda _1,_2,_3: self._UpdateMinAreaText())
        self.lblMinAreaInfo = tk.Label(self.optionsFrame, text="")
        self.lblMinAreaInfo.grid(row=26, column=0, columnspan=3)
        self._UpdateMinAreaText()
        

        self.OptionsFrame_Update(None)

        return self.optionsFrame
    
    def OptionsFrame_Update(self, inputImageObj: ImageProperties|None):
        if inputImageObj is None:
            self.lblImgStats["text"] = ""
            return
        
        _t = f"Image Stats: range = [{int(inputImageObj.min)}, {int(inputImageObj.max)}], "
        _t = _t + f"{np.round(inputImageObj.mean, 2)} ± {np.round(inputImageObj.std, 2)}, "
        _t = _t + f"median = {np.round(inputImageObj.median, 2)}"
        self.lblImgStats["text"] = _t
        self.CalcAutoParams(inputImageObj)

    def CalcAutoParams(self, inputImageObj: ImageProperties):
        if self.varAutoParams.get() != 1:
            return
        lowerThreshold = int(inputImageObj.mean + 2.5*inputImageObj.std)
        upperThreshold = max(lowerThreshold, min(inputImageObj.max/2, inputImageObj.mean + 5*inputImageObj.std))
        self.setting_lowerTh.var.IntVar.set(lowerThreshold)
        self.setting_upperTh.var.IntVar.set(upperThreshold)

    def _UpdateMinAreaText(self):
        A = self.setting_minArea.Get()
        r = round(np.sqrt(A/np.pi),2)
        self.lblMinAreaInfo["text"] = f"A circle with radius {r} px has the same area" 

    
    def DetectAutoParams(self, inputImageObj: ImageProperties) -> list[ISynapse]:
        lowerThreshold = self.setting_lowerTh.Get()
        upperThreshold = self.setting_upperTh.Get()
        sortBySignal = self.setting_sortBySignal.Get()
        expandSize = self.setting_expandSize.Get()
        maxPeakCount = self.setting_maxPeakCount.Get()
        minArea = self.setting_minArea.Get()
        minDistance = self.setting_minDistance.Get()
        minSignal = self.setting_minSignal.Get()
        radius = self.setting_radius.Get()
        return self.Detect(inputImageObj.img,
                           lowerThreshold=lowerThreshold, 
                           upperThreshold=upperThreshold, 
                           sortBySignal=sortBySignal,
                           expandSize=expandSize,
                           maxPeakCount=maxPeakCount,
                           minArea=minArea,
                           minDistance=minDistance, 
                           minSignal=minSignal,
                           radius=radius,
                           ImgObj=self.imgObjCallback(),
                           warning_callback=self._Callback)
    
    def _Callback(self, mode: Literal["ask", "info", "warning", "error"], message=""):
        if mode == "ask":
            return messagebox.askyesno("Neurotorch", message)
        elif mode == "info":
            messagebox.showinfo("Neurotorch", message)
        elif mode == "warning":
            messagebox.showwarning("Neurotorch", message)
        elif mode == "error":
            messagebox.showerror("Neurotorch", message)

            
    def Img_DetectionOverlay(self) -> tuple[tuple[np.ndarray]|None, list[patches.Patch]|None]:
        if self.maxima is None:
            return (None, None)
        _patches = []
        for i in range(self.maxima.shape[0]):
            x, y = self.maxima[i, 1], self.maxima[i, 0]
            label = self.labeledImage[y,x]
            for region in self.region_props:
                if region.label == label:
                    y2, x2 = region.centroid_weighted
                    p = patches.Arrow(x,y, (x2-x), (y2-y))
                    _patches.append(p)
                    break
        return ((self.maxima_labeled_expanded, self.labeledImage), _patches)