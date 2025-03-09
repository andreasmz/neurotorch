from .window import *
from .components.general import *
from .components.treeview import SynapseTreeview
from ..utils import synapse_detection_integration as detection
from ..utils.image import *
from ..utils.synapse_detection import *
from ..utils.logger import logger


import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.widgets as PltWidget
import matplotlib.patches as patches
from matplotlib.ticker import MaxNLocator
import numpy as np
import pandas as pd

class TabROIFinder_AlgorithmChangedEvent(TabUpdateEvent):
    pass

class TabROIFinder(Tab):

    def __init__(self, gui: Neurotorch_GUI):
        super().__init__(gui)
        self.tab_name = "Tab ROI Finder"
        self._gui = gui
        self.root = gui.root
        self.detectionAlgorithm = None
        self.roiPatches = {}
        self.roiPatches2 = {}
        self.treeROIs_entryPopup = None
        self.ax1Image = None
        self.ax2Image = None
        self.ax1_colorbar = None
        self.ax2_colorbar = None

        self._synapses: dict[str, ISynapse] = {}

    def Init(self):
        self.tab = ttk.Frame(self._gui.tabMain)
        self._gui.tabMain.add(self.tab, text="Synapse ROI Finder")
        self.frameToolsContainer = ScrolledFrame(self.tab)
        self.frameToolsContainer.pack(side=tk.LEFT, fill="y", anchor=tk.NW)
        self.frameTools = self.frameToolsContainer.frame

        self.frameOptions = ttk.LabelFrame(self.frameTools, text="Algorithm and image")
        self.frameOptions.grid(row=0, column=0, sticky="news")
        self.lblAlgorithm = tk.Label(self.frameOptions, text="Algorithm")
        self.lblAlgorithm.grid(row=0, column=0, columnspan=2, sticky="nw")
        self.radioAlgoVar = tk.StringVar(value="local_max")
        self.radioAlgo1 = tk.Radiobutton(self.frameOptions, variable=self.radioAlgoVar, indicatoron=True, text="Threshold (Deprecated)", value="threshold", command=lambda:self.Invalidate_Algorithm())
        self.radioAlgo2 = tk.Radiobutton(self.frameOptions, variable=self.radioAlgoVar, indicatoron=True, text="Hysteresis thresholding", value="hysteresis", command=lambda:self.Invalidate_Algorithm())
        self.radioAlgo3 = tk.Radiobutton(self.frameOptions, variable=self.radioAlgoVar, indicatoron=True, text="Local Max", value="local_max", command=lambda:self.Invalidate_Algorithm())
        ToolTip(self.radioAlgo1, msg=Resource.GetString("algorithms/threshold/description"), follow=True, delay=0.1)
        ToolTip(self.radioAlgo2, msg=Resource.GetString("algorithms/hysteresisTh/description"), follow=True, delay=0.1)
        ToolTip(self.radioAlgo3, msg=Resource.GetString("algorithms/localMax/description"), follow=True, delay=0.1)
        self.radioAlgo1.grid(row=1, column=0, sticky="nw", columnspan=3)
        self.radioAlgo2.grid(row=2, column=0, sticky="nw", columnspan=3)
        self.radioAlgo3.grid(row=3, column=0, sticky="nw", columnspan=3)

        self.lblFrameOptions = tk.Label(self.frameOptions, text="Image Source")
        self.lblFrameOptions.grid(row=10, column=0, sticky="ne")
        ToolTip(self.lblFrameOptions, msg=Resource.GetString("tab3/imageSource"), follow=True, delay=0.1)
        self.varImage = tk.StringVar(value="DiffMax")
        self.varImage.trace_add("write", lambda _1,_2,_3: self.ComboImage_Changed())
        self.comboImage = ttk.Combobox(self.frameOptions, textvariable=self.varImage, state="readonly")
        self.comboImage['values'] = ["Diff", "DiffMax", "DiffStd", "DiffMax without Signal"]
        self.comboImage.grid(row=10, column=1, sticky="news")
        self.varImageFrame = tk.StringVar()
        self.varImageFrame.trace_add("write", lambda _1,_2,_3: self.ComboImage_Changed())
        self.comboFrame = ttk.Combobox(self.frameOptions, textvariable=self.varImageFrame, state="disabled", width=5)
        self.comboFrame.grid(row=10, column=2, sticky="news")
        tk.Label(self.frameOptions, text="Diff. Img Overlay").grid(row=11, column=0)
        self.setting_plotOverlay = GridSetting(self.frameOptions, row=11, type_="Checkbox", text="Plot raw algorithm output", default=0, tooltip=Resource.GetString("tab3/rawAlgorithmOutput"))
        self.setting_plotOverlay.var.IntVar.trace_add("write", lambda _1,_2,_3: self.Invalidate_ROIs())
        self.setting_plotPixels = GridSetting(self.frameOptions, row=12, type_="Checkbox", text="Plot ROIs pixels", default=0, tooltip=Resource.GetString("tab3/plotROIPixels"))
        self.setting_plotPixels.var.IntVar.trace_add("write", lambda _1,_2,_3: self.Invalidate_ROIs())

        self.btnDetect = tk.Button(self.frameOptions, text="Detect", command=self.Detect)
        self.btnDetect.grid(row=15, column=0)

        self.detectionAlgorithm = detection.IDetectionAlgorithmIntegration()
        self.frameAlgoOptions = self.detectionAlgorithm.OptionsFrame(self.frameTools, self._gui.GetImageObject)
        self.frameAlgoOptions.grid(row=1, column=0, sticky="news")

        self.frameROIS = tk.LabelFrame(self.frameTools, text="ROIs")
        self.frameROIS.grid(row=2, column=0, sticky="news")

        self.tvSynapses = SynapseTreeview(self.frameROIS, self._gui, synapseCallback=self.Synapses,selectCallback=self.InvalidateSelectedROI, updateCallback=self.Invalidate_ROIs, allowSingleframe=True)
        self.tvSynapses.pack(fill="both")

        self.figure1 = plt.Figure(figsize=(20,10), dpi=100)
        self.ax1 = self.figure1.add_subplot(221)  
        self.ax2 = self.figure1.add_subplot(222, sharex=self.ax1, sharey=self.ax1)  
        self.ax3 = self.figure1.add_subplot(223)  
        self.ax4 = self.figure1.add_subplot(224, sharex=self.ax3)  
        self.ClearImagePlot()
        self.canvas1 = FigureCanvasTkAgg(self.figure1, self.tab)
        self.canvtoolbar1 = NavigationToolbar2Tk(self.canvas1,self.tab)
        self.canvtoolbar1.update()
        self.canvas1.get_tk_widget().pack(expand=True, fill="both", side=tk.LEFT)
        self.canvas1.mpl_connect('resize_event', self._Canvas1Resize)
        self.canvas1.mpl_connect('button_press_event', self.Canvas1ClickEvent)
        self.canvas1.draw()

        #tk.Grid.rowconfigure(self.frameTools, 3, weight=1)

        self.tvSynapses.SyncSynapses()
        self.Update(TabROIFinder_AlgorithmChangedEvent())


    # Public functions

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

    def Synapses(self, newval: dict[str, ISynapse]|None = None) -> dict[str, ISynapse]:
        """ Python does not provide a pointer concept. Therefore use this helper function combining a Getter/Setter"""
        if newval is not None:
            self._synapses = newval
        return self._synapses

    # Update and Invalidation functions

    def Update(self, event: TabUpdateEvent):
        """ The main function to update this tab. """
        if isinstance(event, ImageChangedEvent):
            self.tvSynapses.ClearSynapses('non_staged')
            self.tvSynapses.SyncSynapses()
            self.ClearImagePlot()
            self.ComboImage_Changed()
        elif isinstance(event, TabROIFinder_AlgorithmChangedEvent):
            self.Invalidate_Algorithm()
            self.Invalidate_Image()

    def ComboImage_Changed(self):
        if self.varImage.get() != "Diff" or self._gui.signal.peaks is None:
            self.comboFrame['values'] = []
            self.comboFrame["state"] = "disabled"
            self.varImageFrame.set("")
        else:
            self.comboFrame['values'] = [str(f+1) for f in list(self._gui.signal.peaks)]
            self.comboFrame["state"] = "normal"
        self.Invalidate_Algorithm()
        self.Invalidate_Image()

    def Invalidate_Algorithm(self):
        match self.radioAlgoVar.get():
            case "threshold":
                if isinstance(self.detectionAlgorithm, detection.Thresholding_Integration):
                    self.detectionAlgorithm.OptionsFrame_Update(self.GetCurrentDetectionSource()[1])
                    return
                self.detectionAlgorithm = detection.Thresholding_Integration()
            case "hysteresis":
                if type(self.detectionAlgorithm) == detection.HysteresisTh_Integration:
                    self.detectionAlgorithm.OptionsFrame_Update(self.GetCurrentDetectionSource()[1])
                    return
                self.detectionAlgorithm = detection.HysteresisTh_Integration()
            case "local_max":
                if type(self.detectionAlgorithm) == detection.LocalMax_Integration:
                    self.detectionAlgorithm.OptionsFrame_Update(self.GetCurrentDetectionSource()[1])
                    return
                self.detectionAlgorithm = detection.LocalMax_Integration()
            case _:
                self.detectionAlgorithm = None
                return
        if (self.frameAlgoOptions is not None):
            self.frameAlgoOptions.grid_forget()
        self.frameAlgoOptions = self.detectionAlgorithm.OptionsFrame(self.frameTools, self._gui.GetImageObject)
        self.detectionAlgorithm.OptionsFrame_Update(self.GetCurrentDetectionSource()[1])
        self.frameAlgoOptions.grid(row=1, column=0, sticky="news")

    def ClearImagePlot(self):
        if self.ax1_colorbar is not None:
            self.ax1_colorbar.remove()
            self.ax1_colorbar = None
        if self.ax2_colorbar is not None:
            self.ax2_colorbar.remove()
            self.ax2_colorbar = None
        for ax in [self.ax1, self.ax2, self.ax3, self.ax4]: 
            ax.clear()
            ax.set_axis_off()
            ax.xaxis.set_major_locator(MaxNLocator(integer=True))
            if ax == self.ax1 or ax == self.ax2:
                ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        self.ax1.set_title("Image (Mean)")
        self.ax2.set_title("Diff Image")

    def Invalidate_Image(self):
        imgObj = self._gui.ImageObject

        self.ax2.set_title("Diff Image")
        self.ax1Image = None
        self.ax2Image = None    
        if self.ax1_colorbar is not None:
            self.ax1_colorbar.remove()
            self.ax1_colorbar = None
        if self.ax2_colorbar is not None:
            self.ax2_colorbar.remove()
            self.ax2_colorbar = None
        for ax in [self.ax1, self.ax2]: 
            for axImg in ax.get_images(): 
                axImg.remove()
            ax.set_axis_off()
        
        if imgObj is None or imgObj.img is None or imgObj.imgDiff is None:
            self.Invalidate_ROIs()
            return
        
        self.ax1Image = self.ax1.imshow(imgObj.imgView(imgObj.SPATIAL).Mean, cmap="Greys_r") 
        self.ax1.set_axis_on()
        self.ax1_colorbar = self.figure1.colorbar(self.ax1Image, ax=self.ax1)

        _ax2Title, ax2_ImgProp = self.GetCurrentDetectionSource()
        self.ax2.set_title(_ax2Title)
        if ax2_ImgProp is not None:
            self.ax2Image = self.ax2.imshow(ax2_ImgProp.img, cmap="inferno")
            self.ax2_colorbar = self.figure1.colorbar(self.ax2Image, ax=self.ax2)
            self.ax2.set_axis_on()

        self.Invalidate_ROIs()


    def Invalidate_ROIs(self):
        for axImg in self.ax1.get_images():
            if axImg != self.ax1Image: axImg.remove()
        for axImg in self.ax2.get_images():
            if axImg != self.ax2Image: axImg.remove()
        for p in reversed(self.ax1.patches): p.remove()
        for p in reversed(self.ax2.patches): p.remove()
        self.roiPatches = {}
        self.roiPatches2 = {}

        if self.tvSynapses.modified:
            self.frameROIS["text"] = "ROIs*"
        else:
            self.frameROIS["text"] = "ROIs"

        _ax1HasImage = len(self.ax1.get_images()) > 0
        _ax2HasImage = len(self.ax2.get_images()) > 0
        
        # Plotting the ROIs
        for synapse in self.synapses:
            for roi in synapse.rois:
                if isinstance(roi, detection.CircularSynapseROI):
                    c = patches.Circle(roi.location, roi.radius+0.5, color="red", fill=False)
                    c2 = patches.Circle(roi.location, roi.radius+0.5, color="green", fill=False)
                elif isinstance(roi, detection.PolygonalSynapseROI):
                    c = patches.Polygon(roi.polygon, color="red", fill=False)
                    c2 = patches.Polygon(roi.polygon, color="green", fill=False)
                else:
                    continue
                if _ax1HasImage:
                    self.ax1.add_patch(c)
                    self.roiPatches[roi.uuid] = c
                if _ax2HasImage:
                    self.ax2.add_patch(c2)
                    self.roiPatches2[roi.uuid] = c2

        # Plotting the overlays
        if self.GetCurrentDetectionSource()[1] is not None:
            _currentSource = self.GetCurrentDetectionSource()[1].img
            if self.setting_plotPixels.Get() == 1 and _ax1HasImage and _currentSource is not None:
                _overlay = np.zeros(shape=_currentSource.shape, dtype=_currentSource.dtype)
                for synapse in self.synapses:
                    for roi in synapse.rois:
                        _overlay[roi.GetImageMask(_currentSource.shape)] = 1
                self.ax1.imshow(_overlay, alpha=_overlay*0.5, cmap="viridis")

            if self.setting_plotOverlay.Get() == 1 and _ax2HasImage:
                _overlays, _patches = self.detectionAlgorithm.Img_DetectionOverlay()
                if _overlays is not None:
                    for _overlay in _overlays:
                        self.ax2.imshow(_overlay!=0, alpha=(_overlay != 0).astype(int)*0.5, cmap="gist_gray")
                if _patches is not None:
                    for p in _patches:
                        self.ax2.add_patch(p)

        self.figure1.tight_layout()
        self.canvas1.draw()

        self.tvSynapses.selection_clear()

    def InvalidateSelectedROI(self, synapse: ISynapse|None=None, roi: ISynapseROI|None=None):
        """ Called by self.tvSynapses when a item is selected. If root item is selected, synapse and roi are None. If a ISynapse is selected, roi is None """
        imgObj = self._gui.ImageObject
        self.ax3.clear()
        self.ax3.set_title("Image Signal")
        self.ax3.set_ylabel("mean brightness")
        self.ax3.set_xlabel("frame")
        self.ax3.set_axis_off()
        self.ax4.clear()
        self.ax4.set_title("Detection Signal (from imgDiff)")
        self.ax4.set_ylabel("mean brightness increase")
        self.ax4.set_xlabel("imgDiff frame")
        self.ax4.set_axis_off()

        if synapse is not None and roi is None:
            roi_uuids = list(synapse.rois_dict.keys())
        elif synapse is not None and roi is not None:
            roi_uuids = [roi.uuid]
        else:
            roi_uuids = []
        for patch_name, patch in self.roiPatches.items():
            if patch_name in roi_uuids:
                patch.set_color("yellow")
            else:
                patch.set_color("red")
        for patch_name, patch in self.roiPatches2.items():
            if patch_name in roi_uuids:
                patch.set_color("yellow")
            else:
                patch.set_color("green")
    
        if synapse is not None and len(synapse.rois) == 1 and self._gui.ImageObject is not None and self._gui.ImageObject.img is not None:
            self.ax3.set_axis_on()
            self.ax4.set_axis_on()

            roi = synapse.rois[0]
            signal = roi.GetImageSignal(imgObj.img)
            signalDiff = roi.GetImageSignal(imgObj.imgDiff)
            if signal.shape[0] > 0:
                self.ax3.plot(np.mean(signal, axis=1))
            if signalDiff.shape[0] > 0:
                self.ax4.plot(range(1, signalDiff.shape[0]+1), np.max(signalDiff, axis=1), label="Max", c="blue")
                self.ax4.plot(range(1, signalDiff.shape[0]+1), np.mean(signalDiff, axis=1), label="Mean", c="red")
                self.ax4.plot(range(1, signalDiff.shape[0]+1), np.min(signalDiff, axis=1), label="Min", c="darkorchid")
                self.ax4.legend()
        self.figure1.tight_layout()
        self.canvas1.draw()

        
    def Detect(self, waitCompletion:bool=False):
        if self.detectionAlgorithm is None or self._gui.ImageObject is None:
            self._gui.root.bell()
            return
        if self.GetCurrentDetectionSource()[1] is None:
            self._gui.root.bell()
            return 

        def _Detect(job: Job):
            self.tvSynapses.ClearSynapses('non_staged')
            self.tvSynapses.SyncSynapses()
            job.SetProgress(0, "Detecting ROIs")
            rois = self.detectionAlgorithm.DetectAutoParams(self.GetCurrentDetectionSource()[1])
            for r in rois:
                s = SingleframeSynapse(r)
                self._synapses[s.uuid] = s
            self.tvSynapses.SyncSynapses()
            job.SetStopped("Detecting ROIs")
            self.Invalidate_ROIs()

        job = Job(steps=1)
        self._gui.statusbar.AddJob(job)
        _thread = threading.Thread(target=_Detect, args=(job,), daemon=True)
        _thread.start()
        if waitCompletion:
            _thread.join()

    # Helper function

    def GetCurrentDetectionSource(self) -> tuple[str, ImageProperties|None]:
        imgObj = self._gui.ImageObject
        signal = self._gui.signal
        if imgObj is None or imgObj.img is None or imgObj.imgDiff is None:
            return ("Diff. Image", None)
        
        match(self.varImage.get()):
            case "Diff":
                if self.varImageFrame.get() == "":
                    return("INVALID FRAME",  None)
                _frame = int(self.varImageFrame.get()) - 1
                if _frame < 0 or _frame >= imgObj.imgDiff.shape[0]:
                    return("INVALID FRAME",  None)
                return (f"Diff. Image (Frame {_frame + 1})", imgObj.imgDiff_FrameProps(_frame))
            case "DiffMax":
                return ("Diff. Image (Max.)", imgObj.imgDiffView(ImgObj.SPATIAL).MaxProps)
            case "DiffStd":
                return ("Diff. Image (Std.)", imgObj.imgDiffView(ImgObj.SPATIAL).StdNormedProps)
            case "DiffMax without Signal":
                if signal.imgObj_Sliced is None:
                    return("NO SIGNAL", None)  
                elif signal.imgObj_Sliced is False:
                    return("SIGNAL SLICED ALL FRAMES", None)  
                return ("Diff. Image (Max) without signal", signal.imgObj_Sliced.imgDiffView(ImgObj.SPATIAL).MaxProps)
            case _:
                return ("UNEXPECTED IMAGE SOURCE", None)

    
    def Canvas1ClickEvent(self, event):
        if not event.dblclick or event.inaxes is None:
            return
        if (event.inaxes != self.ax1 and event.inaxes != self.ax2):
            return
        x, y = event.xdata, event.ydata
        rois = [(s, r) for s in self.synapses for r in s.rois]
        if len(rois) == 0: return
        rois.sort(key=lambda v: (v[1].location[0]-x)**2+(v[1].location[1]-y)**2 if v[1].location is not None else np.inf)
        synapse, roi = rois[0]
        d = ((roi.location[0]-x)**2+(roi.location[1]-y)**2)**0.5 if roi.location is not None else np.inf
        if d <= 40:
            self.tvSynapses.Select(synapse=synapse, roi=roi)

    def _Canvas1Resize(self, event):
        if self.tab.winfo_width() > 300:
            self.figure1.tight_layout()
            self.canvas1.draw()