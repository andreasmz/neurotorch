import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Literal

from .image import ImgObj, ImageProperties
from ..gui.components import IntStringVar
from ..gui.window import Neurotorch_GUI, TabUpdateEvent
from .synapse_detection import *

# While synapse_detection.py provides detection algorithms, this file contains the actual implementation into Neurotorch GUI

class IDetectionAlgorithmIntegration:
    
    def __init__(self, displayMessageboxes = False):
        # The algorithm is choosing on its own what data to use. For this, an IMGObject is provided
        self.imgObj = None
        self.root = None

    def OptionsFrame(self, root, gui:Neurotorch_GUI, updateCallback, imgObj_Callable: Callable) -> tk.LabelFrame:
        """
            This function is used to generate an frame for the algorithm options. The Integration class is responsible for this LabelFrame and
            should return in after generation. If may (!) be that this class is called multiple times, for example after changing the algorithm.
        """
        self.root = root
        self.gui = gui
        self.optionsFrame = tk.LabelFrame(self.root, text="Options")
        self.updatecallback = updateCallback
        return self.optionsFrame
    
    def OptionsFrame_Update(self):
        """
            This Update function is called, after an new image is loaded (or after other certain events that may invalidate the algorithms parameters)
            and could be for example used to update parameter estimations.
        """
        pass

    def DetectAutoParams(self, frame: int = None) -> list[ISynapse]:
        """
            This function should be an wrapper for the Detect function in an DetectionAlgorithm and get the parameters from the GUI and then call
            and return the Algorithms Detect function. Only parameter frame is provided by the GUI and set to None when the mean image should be used.
        """
        pass

    def Img_Detection_Raw(self) -> np.ndarray | None:
        """
            An Integration may choose to provide an custom overlay image, usually the raw data obtained in one of the first steps. 
            Return None to let the GUI decide.
        """
        return None
    
    def Img_Input(self) -> np.ndarray | None:
        """
            An Integration may offer to user other sources than imgDiffMaxTime. Use this function to return this image.
            Return None to let the GUI decide.
        """
        return None



class Thresholding_Integration(Tresholding, IDetectionAlgorithmIntegration):

    def __init__(self):
        super().__init__()

    def OptionsFrame(self, root, gui:Neurotorch_GUI, updateCallback, imgObj_Callable: Callable):
        self.root = root
        self.imgObjCallback = imgObj_Callable
        self.updatecallback = updateCallback
        self.optionsFrame = tk.LabelFrame(self.root, text="Options")
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
    
    def DetectAutoParams(self, frame: int = None) -> list[ISynapse]:
        threshold = self.varThreshold.get()
        radius = self.varROIRadius.get()
        minROISize = self.varROIMinSize.get()/100
        return self.Detect(self.imgObjCallback(), frame=frame, threshold=threshold, radius=radius, minROISize=minROISize)
    
    def Img_Detection_Raw(self):
        return self.imgThresholded
    

class APD_Integration(APD, IDetectionAlgorithmIntegration):
    
    def __init__(self):
        super().__init__()
        self.lblImgStats = None
        self.imgStats = None
        self._currentImgObj_Callback = None
        
    def OptionsFrame(self, root, gui:Neurotorch_GUI, updateCallback, imgObj_Callable: Callable):
        self.root = root
        self.gui = gui
        self.imgObjCallback = imgObj_Callable
        self.updatecallback = updateCallback
        self.optionsFrame = tk.LabelFrame(self.root, text="Options")

        tk.Label(self.optionsFrame, text="Auto paramters").grid(row=2, column=0, sticky="ne")
        tk.Label(self.optionsFrame, text="Image Source").grid(row=3, column=0, sticky="ne")
        tk.Label(self.optionsFrame, text="Lower Threshold").grid(row=4, column=0, sticky="ne")
        tk.Label(self.optionsFrame, text="Upper Threshold").grid(row=5, column=0, sticky="ne")
        tk.Label(self.optionsFrame, text="Min. Area").grid(row=6, column=0, sticky="ne")
        tk.Label(self.optionsFrame, text="px").grid(row=6, column=3, sticky="nw")
        self.lblMinAreaInfo = tk.Label(self.optionsFrame, text="")
        self.lblMinAreaInfo.grid(row=7, column=0, columnspan=3)

        self.varAutoParams = tk.IntVar(value=1)
        self.checkAutoParams = tk.Checkbutton(self.optionsFrame, variable=self.varAutoParams)
        self.checkAutoParams.grid(row=2, column=1, sticky="nw")
        self.comboImageVar = tk.StringVar(value="DiffMax")
        self.comboImageVar.trace_add("write", self._ComboImage_Changed)
        self.comboImage = ttk.Combobox(self.optionsFrame, textvariable=self.comboImageVar, state="readonly")
        self.comboImage['values'] = ["Diff", "DiffMax", "DiffStd", "DiffMax without Signal"]
        self.comboImage.grid(row=3, column=1, sticky="news")
        self.comboFrameVar = tk.StringVar()
        self.comboFrameVar.trace_add("write", self._ComboImage_Changed)
        self.comboFrame = ttk.Combobox(self.optionsFrame, textvariable=self.comboFrameVar, state="disabled", width=5)
        self.comboFrame.grid(row=3, column=2, sticky="news")
        self.varLowerThreshold = IntStringVar(self.root, tk.IntVar(value=10)).SetStringVarBounds(0,1000)
        self.varUpperThreshold = IntStringVar(self.root, tk.IntVar(value=40)).SetStringVarBounds(0,1000)
        self.varMinArea = IntStringVar(self.root, tk.IntVar(value=20)).SetStringVarBounds(0,1000)
        self.varMinArea.SetCallback(self._UpdateMinAreaText)
        self.scaleLowerThreshold = ttk.Scale(self.optionsFrame, from_=1, to=200, variable=self.varLowerThreshold.IntVar)
        self.scaleUpperThreshold = ttk.Scale(self.optionsFrame, from_=1, to=200, variable=self.varUpperThreshold.IntVar)
        self.scaleMinArea = ttk.Scale(self.optionsFrame, from_=0, to=500, variable=self.varMinArea.IntVar)
        self.numLowerThreshold = tk.Spinbox(self.optionsFrame, width=6, textvariable=self.varLowerThreshold.StringVar, from_=0, to=1000)
        self.numUpperThreshold = tk.Spinbox(self.optionsFrame, width=6, textvariable=self.varUpperThreshold.StringVar, from_=0, to=1000)
        self.numMinArea = tk.Spinbox(self.optionsFrame, width=6, textvariable=self.varMinArea.StringVar, from_=0, to=1000)
        self.scaleLowerThreshold.grid(row=4, column=1, sticky="news")
        self.scaleUpperThreshold.grid(row=5, column=1, sticky="news")
        self.scaleMinArea.grid(row=6, column=1, sticky="news")
        self.numLowerThreshold.grid(row=4, column=2)
        self.numUpperThreshold.grid(row=5, column=2)
        self.numMinArea.grid(row=6, column=2)

        tk.Label(self.optionsFrame, text="Overlay diffImage").grid(row=8, column=0, sticky="ne")
        self.radioAx2Frame = tk.Frame(self.optionsFrame)
        self.radioAx2Frame.grid(row=8, column=1, columnspan=2, sticky="news")
        self.radioAx2Var = tk.IntVar(value=0)
        self.radioAx2Var.trace_add("write", self._varChanged_Update)
        self.radioAx2Patches = tk.Radiobutton(self.radioAx2Frame, text="Polygon", value=0, variable=self.radioAx2Var)
        self.radioAx2Polygon = tk.Radiobutton(self.radioAx2Frame, text="Shape", value=1, variable=self.radioAx2Var)
        self.radioAx2Patches.pack(side=tk.LEFT)
        self.radioAx2Polygon.pack(side=tk.LEFT)

        self._UpdateMinAreaText()
        self.OptionsFrame_Update()
        
        return self.optionsFrame
    
    def OptionsFrame_Update(self):
        if self.lblImgStats is None:
            self.lblImgStats = tk.Label(self.optionsFrame)
            self.lblImgStats.grid(row=0, column=0, columnspan=3)
        if self.comboImageVar.get() != "Diff" or self.gui.signal is  None or self.gui.signal.peaks is None or len(self.gui.signal.peaks) == 0:
            self.comboFrame['values'] = []
            self.comboFrame["state"] = "disabled"
            if self.comboFrame.get() != "":
                self.comboFrame.set("")
        else:
            self.comboFrame['values'] = list(self.gui.signal.peaks.astype(str))
            self.comboFrame["state"] = "normal"

        imgObj: ImgObj = self.imgObjCallback()

        if imgObj is None or imgObj.imgDiff is None:
            self.lblImgStats["text"] = ""
            return
        
        self._currentImgObj_Callback = self.imgObjCallback
        if self.comboImageVar.get() == "Diff" and self.comboFrameVar.get() != "":
            self._currentImgObj_Callback = self.imgObjCallback
            _frame = int(self.comboFrameVar.get())
            if _frame < 0 or _frame >= imgObj.imgDiff.shape[0]:
                self.lblImgStats["text"] = ""
                return
            self.imgStats = ImageProperties(imgObj.imgDiff[_frame])
        elif self.comboImageVar.get() == "DiffMax":
            self._currentImgObj_Callback = self.imgObjCallback
            self.imgStats = imgObj.imgDiffView(ImgObj.SPATIAL).MaxProps
        elif self.comboImageVar.get() == "DiffStd":
            self._currentImgObj_Callback = self.imgObjCallback
            self.imgStats = imgObj.imgDiffView(ImgObj.SPATIAL).StdProps
        elif self.comboImageVar.get() == "DiffMax without Signal":
            self._currentImgObj_Callback = lambda: self.gui.signal.imgObj_Sliced
            if self.gui.signal.imgObj_Sliced is None or self.gui.signal.imgObj_Sliced.imgDiff is None:
                self.lblImgStats["text"] = "imgDiff or Signal not ready"
                self.imgStats = None
                return
            self.imgStats = self.gui.signal.imgObj_Sliced.imgDiffView(ImgObj.SPATIAL).MaxProps
            
        else:
            self.lblImgStats["text"] = ""
            self.imgStats = None
            return
        _t = f"Image Stats: range = [{int(self.imgStats.min)}, {int(self.imgStats.max)}], "
        _t = _t + f"{np.round(self.imgStats.mean, 2)} ± {np.round(self.imgStats.std, 2)}, "
        _t = _t + f"median = {np.round(self.imgStats.median, 2)}"
        self.lblImgStats["text"] = _t
        self.CalcAutoParams()

    def CalcAutoParams(self):
        if self.varAutoParams.get() != 1:
            return
        if self.imgStats is None:
            return
        lowerThreshold = int(self.imgStats.mean + 2.5*self.imgStats.std)
        upperThreshold = max(lowerThreshold, min(self.imgStats.max/2, self.imgStats.mean + 5*self.imgStats.std))
        self.varLowerThreshold.IntVar.set(lowerThreshold)
        self.varUpperThreshold.IntVar.set(upperThreshold)

    def _UpdateMinAreaText(self):
        A = self.varMinArea.IntVar.get()
        r = round(np.sqrt(A/np.pi),2)
        self.lblMinAreaInfo["text"] = f"A circle with radius {r} px has the same area" 

    def _ComboImage_Changed(self, val1, val2, val3):
        self.OptionsFrame_Update()
        self.updatecallback(["tab3_replotImages"])

    def _varChanged_Update(self, val1, val2, val3):
        self.updatecallback(["tab3_replotImages"])

    def DetectAutoParams(self, frame: int = None) -> list[ISynapseROI]:
        lowerThreshold = self.varLowerThreshold.IntVar.get()
        upperThreshold = self.varUpperThreshold.IntVar.get()
        minArea = self.varMinArea.IntVar.get()
        mode = self.comboImageVar.get()
        if mode == "DiffMax without Signal":
            mode = "DiffMax"
        imgObj = self._currentImgObj_Callback()
        if frame is None and mode == "Diff":
            _frame = self.comboFrameVar.get()
            if _frame.isdigit(): 
                _frame = int(self.comboFrameVar.get())
                if _frame >= 0 and _frame < imgObj.imgDiff.shape[0]:
                    frame = _frame
        return self.Detect(imgObj, frame, imgMode=mode, lowerThreshold=lowerThreshold, upperThreshold=upperThreshold, minArea=minArea, warning_callback=self._Callback)

    def _Callback(self, mode: Literal["ask", "info", "warning", "error"], message=""):
        if mode == "ask":
            return messagebox.askyesno("Neurotorch", message)
        elif mode == "info":
            messagebox.showinfo("Neurotorch", message)
        elif mode == "warning":
            messagebox.showwarning("Neurotorch", message)
        elif mode == "error":
            messagebox.showerror("Neurotorch", message)

    def Img_Input(self) -> np.ndarray | None:
        imgObj: ImgObj = self._currentImgObj_Callback()
        if imgObj is None or imgObj.imgDiff is None:
            return False
        match(self.comboImageVar.get()):
            case "DiffMax" | "DiffMax without Signal":
                return imgObj.imgDiffView(ImgObj.SPATIAL).Max
            case "DiffStd":
                return imgObj.imgDiffView(ImgObj.SPATIAL).Std
            case "Diff":
                if not self.comboFrameVar.get().isdigit():
                    return False
                _frame = int(self.comboFrameVar.get())
                if _frame < 0 or _frame > imgObj.imgDiff.shape[0]:
                    return False
                return imgObj.imgDiff[_frame]
            case _:
                return None
            
    def Img_Detection_Raw(self):
        if self.radioAx2Var.get() == 1:
            return self.thresholdFiltered_img
        return None
    

class APD_CircleAprox_Integration(APD_Integration):

    def OptionsFrame(self, root, gui:Neurotorch_GUI, updateCallback, imgObj_Callable: Callable):
        super().OptionsFrame(root, gui, updateCallback, imgObj_Callable)
        self.varCircApproxR = IntStringVar(self.root, tk.IntVar(value=6))
        self.numCircApproxR = tk.Spinbox(self.optionsFrame, width=6, textvariable=self.varCircApproxR.StringVar, from_=0, to=100)
        self.numCircApproxR.grid(row = 9, column=2)
        tk.Label(self.optionsFrame, text="Approx. Circle Radius").grid(row=9, column=0, columnspan=2)
        return self.optionsFrame

    def DetectAutoParams(self, frame: int = None) -> list[ISynapse]:
        radius = self.varCircApproxR.IntVar.get()
        synapseROIs = super().DetectAutoParams(frame)
        synapses_return = []
        if synapseROIs is None:
            return None
        for s in synapseROIs:
            if isinstance(s, CircularSynapseROI):
                synapses_return.append(s)
                continue
            synapses_return.append(CircularSynapseROI().SetLocation(s.location[0], s.location[1]).SetRadius(radius))
        return synapses_return