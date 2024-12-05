from .window import *
from .components import *
from ..utils import synapse_detection_integration as detection
from ..utils.image import *
from ..utils.synapse_detection import *


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

class SynapseResult:
    DETECTION_RESULT = "DETECTION_RESULT"
    KEEP_RESULT = "KEEP_RESULT"

    def __init__(self):
        self.detectionResult = detection.DetectionResult()
        self.keepResult = detection.DetectionResult()
        self.modified = False

    def ClearAll(self):
        self.detectionResult.Clear()
        self.keepResult.Clear()
        self.modified = False

    def Clear(self):
        self.detectionResult.Clear()
        self.modified = False

    def GetSynapses(self) -> list[tuple[ISynapse, str]]:
        ret = []
        if self.keepResult.synapses is not None:
            ret.extend([(s, SynapseResult.KEEP_RESULT) for s in self.keepResult.synapses])
        if self.detectionResult.synapses is not None:
            ret.extend([(s, SynapseResult.DETECTION_RESULT) for s in self.detectionResult.synapses])
        return ret
    
    def GetSynapseByUUID(self, uuid=None) -> ISynapse|None:
        for synapse, synapse_source in self.GetSynapses():
            if synapse.uuid == uuid:
                return synapse
        return None
    
    def RemoveSynapse(self, synapse=None):
        if self.detectionResult.synapses is not None and synapse in self.detectionResult.synapses:
            self.detectionResult.synapses.remove(synapse)
        if self.keepResult.synapses is not None and synapse in self.keepResult.synapses:
            self.keepResult.synapses.remove(synapse)



class TabROIFinder(Tab):

    TO_STREAM = "TO_STREAM"

    def __init__(self, gui: Neurotorch_GUI):
        super().__init__(gui)
        self.tab_name = "Tab ROI Finder"
        self._gui = gui
        self.root = gui.root
        self.detectionAlgorithm = None
        self.synapseResult = SynapseResult()
        self.roiPatches = {}
        self.roiPatches2 = {}
        self.treeROIs_entryPopup = None
        self.ax1Image = None
        self.ax2Image = None
        self.ax1_colorbar = None
        self.ax2_colorbar = None

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
        self.radioAlgo1.grid(row=1, column=0, sticky="nw", columnspan=3)
        self.radioAlgo2.grid(row=2, column=0, sticky="nw", columnspan=3)
        self.radioAlgo3.grid(row=3, column=0, sticky="nw", columnspan=3)

        tk.Label(self.frameOptions, text="Image Source").grid(row=10, column=0, sticky="ne")
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
        self.setting_plotOverlay = GridSetting(self.frameOptions, row=11, type_="Checkbox", text="Plot raw algorithm output", default=0)
        self.setting_plotOverlay.var.IntVar.trace_add("write", lambda _1,_2,_3: self.Invalidate_ROIs())
        self.setting_plotPixels = GridSetting(self.frameOptions, row=12, type_="Checkbox", text="Plot ROIs pixels", default=0)
        self.setting_plotPixels.var.IntVar.trace_add("write", lambda _1,_2,_3: self.Invalidate_ROIs())

        self.btnDetect = tk.Button(self.frameOptions, text="Detect", command=self.Detect)
        self.btnDetect.grid(row=15, column=0)

        self.detectionAlgorithm = detection.IDetectionAlgorithmIntegration()
        self.frameAlgoOptions = self.detectionAlgorithm.OptionsFrame(self.frameTools, self._gui.GetImageObject)
        self.frameAlgoOptions.grid(row=1, column=0, sticky="news")

        self.frameROIS = tk.LabelFrame(self.frameTools, text="ROIs")
        self.frameROIS.grid(row=2, column=0, sticky="news")
        self.treeROIs = ttk.Treeview(self.frameROIS, columns=("Location", "Radius"))
        self.treeROIs.heading('Location', text="Center (X,Y)")
        self.treeROIs.heading('Radius', text='Radius [px]')
        self.treeROIs.column("#0", minwidth=0, width=50)
        self.treeROIs.column("Location", minwidth=0, width=50)
        self.treeROIs.column("Radius", minwidth=0, width=50)
        self.treeROIs.bind("<<TreeviewSelect>>", lambda _: self.Invalidate_SelectedROI())
        self.treeROIs.bind("<Double-1>", self.TreeRois_onDoubleClick)
        self.treeROIs.tag_configure("keep_synapse", foreground="#9416a6")
        self.treeROIs.pack(fill="both", padx=10)

        self.frameROIsTools1 = tk.Frame(self.frameROIS)
        self.frameROIsTools1.pack(expand=True)
        self.btnAddROI = tk.Button(self.frameROIsTools1, text="Add", command=self.BtnAddROI_Click)
        self.btnAddROI.pack(side=tk.LEFT, padx=(0,5))
        self.btnRemoveROI = tk.Button(self.frameROIsTools1, text="Remove", command=self.BtnRemoveROI_Click)
        self.btnRemoveROI.pack(side=tk.LEFT, padx=(0,5))
        self.btnResetNameROI = tk.Button(self.frameROIsTools1, text="Reset Name", command=self.BtnResetNameROI_Click)
        self.btnResetNameROI.pack(side=tk.LEFT, padx=(0,5))

        self.btnClearROIs = tk.Button(self.frameROIsTools1, text="Clear ROIs", command=self.BtnClearROIs_Click)
        self.btnClearROIs.pack(side=tk.LEFT, padx=(0,5))
        self.btnClearAllROIs = tk.Button(self.frameROIsTools1, text="Clear All ROIs", command=self.BtnClearAllROIs_Click)
        self.btnClearAllROIs.pack(side=tk.LEFT)


        self.frameROIsTools2 = tk.Frame(self.frameROIS)
        self.frameROIsTools2.pack(expand=True)
        self.btnToogleStage = tk.Button(self.frameROIsTools2, text="Toogle stage", command=self.BtnToogleStage)
        self.btnToogleStage.pack(side=tk.LEFT, padx=(0,5))
        self.btnMoveAllToKeep = tk.Button(self.frameROIsTools2, text="All to stage", command=self.BtnMoveAllToKeep)
        self.btnMoveAllToKeep.pack(side=tk.LEFT, padx=(0,5))
        self.btnMoveAllFromKeep = tk.Button(self.frameROIsTools2, text="All from stage", command=self.BtnMoveAllFromKeep)
        self.btnMoveAllFromKeep.pack(side=tk.LEFT)

        self.frameBtnsExportEx = tk.Frame(self.frameROIS)
        self.frameBtnsExportEx.pack(expand=True)
        self.btnImportROIsImageJ = tk.Button(self.frameBtnsExportEx, text="Import ROIs from ImageJ", command=self.ImportROIsImageJ)
        self.btnImportROIsImageJ.pack(side=tk.LEFT, padx=(0,5))
        self.btnExportROIsImageJ = tk.Button(self.frameBtnsExportEx, text="Export ROIs to ImageJ", command=self.ExportROIsImageJ)
        self.btnExportROIsImageJ.pack(side=tk.LEFT, padx=(0,5))

        self.frameBtnsExport = tk.Frame(self.frameROIS)
        self.frameBtnsExport.pack(expand=True)
        self.btnExportCSVMultiM = tk.Button(self.frameBtnsExport, text="Export Multi Measure (CSV)", command=self.ExportCSVMultiM)
        self.btnExportCSVMultiM.pack(side=tk.LEFT, padx=(0,5))


        self.frameROIProperties = tk.LabelFrame(self.frameTools, text="ROI Properties")
        self.frameROIProperties.grid(row=3, column=0, sticky="news")
        self.treeROIInfo = ttk.Treeview(self.frameROIProperties, columns=("Value"))
        self.treeROIInfo.heading('#0', text='Name')
        self.treeROIInfo.heading('Value', text='Value')
        self.treeROIInfo.column("#0", minwidth=0, width=50)
        self.treeROIInfo.column("Value", minwidth=0, width=100)
        #self.treeROIInfo.bind("<<TreeviewSelect>>", FUNCTION)
        #self.treeROIInfo.bind("<Double-1>", FUNCTION)
        self.treeROIInfo.pack(fill="both", padx=10)


        self.figure1 = plt.Figure(figsize=(20,10), dpi=100)
        self.ax1 = self.figure1.add_subplot(221)  
        self.ax2 = self.figure1.add_subplot(222, sharex=self.ax1, sharey=self.ax1)  
        self.ax3 = self.figure1.add_subplot(223)  
        self.ax4 = self.figure1.add_subplot(224)  
        self.ClearImagePlot()
        self.canvas1 = FigureCanvasTkAgg(self.figure1, self.tab)
        self.canvtoolbar1 = NavigationToolbar2Tk(self.canvas1,self.tab)
        self.canvtoolbar1.update()
        self.canvas1.get_tk_widget().pack(expand=True, fill="both", side=tk.LEFT)
        self.canvas1.mpl_connect('resize_event', self._Canvas1Resize)
        self.canvas1.mpl_connect('button_press_event', self.Canvas1ClickEvent)
        self.canvas1.draw()

        #tk.Grid.rowconfigure(self.frameTools, 3, weight=1)

        self.Update(TabROIFinder_AlgorithmChangedEvent())

    def Update(self, event: TabUpdateEvent):
        if isinstance(event, ImageChangedEvent):
            self.synapseResult.Clear()
            self.ComboImage_Changed()
            self.Invalidate_Algorithm()
            self.ClearImagePlot()
            self.Invalidate_Image()
        elif isinstance(event, TabROIFinder_AlgorithmChangedEvent):
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
        self.ax1.xaxis.set_major_locator(MaxNLocator(integer=True))
        self.ax1.yaxis.set_major_locator(MaxNLocator(integer=True))
        self.ax2.xaxis.set_major_locator(MaxNLocator(integer=True))
        self.ax2.yaxis.set_major_locator(MaxNLocator(integer=True))
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
        self.treeROIs.delete(*self.treeROIs.get_children())
        try: 
            self.treeROIs_entryPopup.destroy()
        except AttributeError:
            pass

        if self.synapseResult.modified:
            self.frameROIS["text"] = "ROIs*"
        else:
            self.frameROIS["text"] = "ROIs"

        _ax1HasImage = len(self.ax1.get_images()) > 0
        _ax2HasImage = len(self.ax2.get_images()) > 0
        
        i = 0
        for synapse, synapse_source in self.synapseResult.GetSynapses():
            match synapse_source:
                case SynapseResult.KEEP_RESULT:
                    tv_tags = ("keep_synapse",)
                case _:
                    tv_tags = ()
            if not isinstance(synapse, detection.SingleframeSynapse):
                continue
            synapseROI: detection.ISynapseROI = synapse.synapse

            if synapse.name is not None:
                name = synapse.name
            else:
                name = f"ROI {i+1}"
                i += 1

            if isinstance(synapseROI, detection.CircularSynapseROI):
                synapseuuid = self.treeROIs.insert('', 'end', iid=synapse.uuid, text=name, values=([synapseROI.LocationStr(), synapseROI.radius]), tags=tv_tags)
                c = patches.Circle(synapseROI.location, synapseROI.radius+0.5, color="red", fill=False)
                c2 = patches.Circle(synapseROI.location, synapseROI.radius+0.5, color="green", fill=False)
            elif isinstance(synapseROI, detection.PolygonalSynapseROI):
                synapseuuid = self.treeROIs.insert('', 'end', iid=synapse.uuid, text=name, values=([synapseROI.LocationStr(), "Polygon"]), tags=tv_tags)
                c = patches.Polygon(synapseROI.polygon, color="red", fill=False)
                c2 = patches.Polygon(synapseROI.polygon, color="green", fill=False)
            else:
                synapseuuid = self.treeROIs.insert('', 'end', iid=synapse.uuid, text=name, values=([synapseROI.LocationStr(), "Unsupported"]), tags=tv_tags)
                c = patches.Circle(synapseROI.location, 3, color="red", fill=False)
                c2 = patches.Circle(synapseROI.location, 3, color="green", fill=False)
            
            if _ax1HasImage:
                self.ax1.add_patch(c)
                self.roiPatches[synapseuuid] = c
            if _ax2HasImage:
                self.ax2.add_patch(c2)
                self.roiPatches2[synapseuuid] = c2

        if self.GetCurrentDetectionSource()[1] is not None:
            _currentSource = self.GetCurrentDetectionSource()[1].img
            if self.setting_plotPixels.Get() == 1 and _ax1HasImage and _currentSource is not None:
                _overlay = np.zeros(shape=_currentSource.shape, dtype=_currentSource.dtype)
                for synapse, synapse_source in self.synapseResult.GetSynapses():
                    if not isinstance(synapse, detection.SingleframeSynapse):
                        continue
                    synapseROI: detection.ISynapseROI = synapse.synapse
                    _overlay[synapseROI.GetImageMask(_currentSource.shape)] = 1
                self.ax1.imshow(_overlay, alpha=_overlay*0.5, cmap="viridis")

            if self.setting_plotOverlay.Get() == 1 and _ax2HasImage:
                _overlays, _patches = self.detectionAlgorithm.Img_DetectionOverlay()
                if _overlays is not None:
                    for _overlay in _overlays:
                        self.ax2.imshow(_overlay!=0, alpha=(_overlay != 0).astype(int)*0.5, cmap="gist_gray")
                if _patches is not None:
                    for p in _patches:
                        self.ax2.add_patch(p)

        self.Invalidate_SelectedROI()


    def Invalidate_SelectedROI(self):
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

        self.treeROIInfo.delete(*self.treeROIInfo.get_children())
        
        selectionIndex = None
        if len(self.treeROIs.selection()) == 1:
            selectionIndex = self.treeROIs.selection()[0]

        for name,c in self.roiPatches.items():
            if name == selectionIndex:
                c.set_color("yellow")
            else:
                c.set_color("red")
        for name,c in self.roiPatches2.items():
            if name == selectionIndex:
                c.set_color("yellow")
            else:
                c.set_color("green")
       
        if self._gui.ImageObject is not None and self._gui.ImageObject.img is not None:
            for synapse, synapse_source in self.synapseResult.GetSynapses():
                if not isinstance(synapse, detection.SingleframeSynapse):
                    continue
                self.ax3.set_axis_on()
                self.ax4.set_axis_on()
                synapseROI: detection.ISynapseROI = synapse.synapse
                if synapse.uuid == selectionIndex:
                    _slice = synapseROI.GetImageSignal(imgObj.img)
                    if len(_slice) > 0:
                        _signal = np.mean(_slice, axis=1)
                        self.ax3.plot(_signal)
                    _sliceDiff = synapseROI.GetImageSignal(imgObj.imgDiff)
                    if len(_sliceDiff) > 0:
                        _signalMaxDiff = np.max(_sliceDiff, axis=1)
                        _signalMeanDiff = np.mean(_sliceDiff, axis=1)
                        _signalMinDiff = np.min(_sliceDiff, axis=1)
                        self.ax4.plot(_signalMaxDiff, label="Max", c="blue")
                        self.ax4.plot(_signalMeanDiff, label="Mean", c="red")
                        self.ax4.plot(_signalMinDiff, label="Min", c="darkorchid")

                        self.ax4.legend()
                    if synapseROI.regionProps is not None:
                        p = synapseROI.regionProps
                        self.treeROIInfo.insert('', 'end', text=f"Area [px]", values=([p.area]))
                        self.treeROIInfo.insert('', 'end', text=f"Center of mass (X,Y)", values=([f"({round(p.centroid_weighted[1], 3)}, {round(p.centroid_weighted[0], 3)})"]))
                        self.treeROIInfo.insert('', 'end', text=f"Radius of circle with same size [px]", values=([f"{round(p.equivalent_diameter_area/2, 2)}"]))
                        self.treeROIInfo.insert('', 'end', text=f"Eccentricity [0,1)", values=([f"{round(p.eccentricity, 3)}"]))
                        self.treeROIInfo.insert('', 'end', text=f"Signal Max", values=([f"{round(p.intensity_max, 2)}"]))
                        self.treeROIInfo.insert('', 'end', text=f"Inertia X", values=([f"{round(p.inertia_tensor[0,0], 2)}"]))
                        self.treeROIInfo.insert('', 'end', text=f"Inertia Y", values=([f"{round(p.inertia_tensor[1,1], 2)}"]))
                        self.treeROIInfo.insert('', 'end', text=f"Inertia Ratio", values=([f"{round(p.inertia_tensor[0,0]/p.inertia_tensor[1,1], 2)}"]))
                        #print(p.moments_weighted_central)
                    if hasattr(synapseROI, "strength"):
                        self.treeROIInfo.insert('', 'end', text=f"Signal Strength", values=([f"{round(synapseROI.strength, 3)}"]))
        self.figure1.tight_layout()
        self.canvas1.draw()

    def Detect(self, waitCompletion:bool=False):
        if self.detectionAlgorithm is None or self._gui.ImageObject is None:
            self._gui.root.bell()
            return
        if self.GetCurrentDetectionSource()[1] is None:
            self._gui.root.bell()
            return 

        self.synapseResult.modified = False

        def _Detect(job: Job):
            job.SetProgress(0, "Detect ROIs")
            self.synapseResult.detectionResult.SetISynapses(SingleframeSynapse.ROIsToSynapses(self.detectionAlgorithm.DetectAutoParams(self.GetCurrentDetectionSource()[1])))
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


    # GUI Functions

    def BtnAddROI_Click(self):
        self.synapseResult.modified = True
        self.synapseResult.detectionResult.AddISynapses(detection.SingleframeSynapse(detection.CircularSynapseROI().SetLocation(0,0).SetRadius(6)))
        self.Invalidate_ROIs()

    def BtnRemoveROI_Click(self):
        if len(self.treeROIs.selection()) != 1:
            self.root.bell()
            return
        selectionIndex = self.treeROIs.selection()[0]
        self.synapseResult.modified = True
        self.synapseResult.RemoveSynapse(self.synapseResult.GetSynapseByUUID(selectionIndex))
        self.Invalidate_ROIs()
    
    def BtnResetNameROI_Click(self):
        if len(self.treeROIs.selection()) != 1:
            self.root.bell()
            return
        selectionIndex = self.treeROIs.selection()[0]
        self.synapseResult.GetSynapseByUUID(selectionIndex).name = None
        self.Invalidate_ROIs()


    def BtnClearROIs_Click(self):
        if messagebox.askyesnocancel("Neurotorch", "Do you really want to clear the ROIs?"):
            self.synapseResult.Clear()
            self.Invalidate_ROIs()

    def BtnClearAllROIs_Click(self):
        if messagebox.askyesnocancel("Neurotorch", "Do you really want to clear all ROIs?"):
            self.synapseResult.ClearAll()
            self.Invalidate_ROIs()

    def BtnToogleStage(self):
        if len(self.treeROIs.selection()) != 1:
            self.root.bell()
            return
        selectionIndex = self.treeROIs.selection()[0]
        s = self.synapseResult.GetSynapseByUUID(selectionIndex)
        if self.synapseResult.detectionResult.synapses is not None and s in self.synapseResult.detectionResult.synapses:
            if self.synapseResult.keepResult.synapses is None:
                self.synapseResult.keepResult.synapses = []
            self.synapseResult.keepResult.synapses.append(s)
            self.synapseResult.detectionResult.synapses.remove(s)
        elif self.synapseResult.keepResult.synapses is not None and s in self.synapseResult.keepResult.synapses:
            if self.synapseResult.detectionResult.synapses is None:
                self.synapseResult.detectionResult.synapses = []
            self.synapseResult.detectionResult.synapses.append(s)
            self.synapseResult.keepResult.synapses.remove(s)
        self.Invalidate_ROIs()

    def BtnMoveAllToKeep(self):
        if self.synapseResult.detectionResult.synapses is None:
            return
        if self.synapseResult.keepResult.synapses is None:
            self.synapseResult.keepResult.synapses = []
        self.synapseResult.keepResult.synapses.extend(self.synapseResult.detectionResult.synapses)
        self.synapseResult.detectionResult.Clear()
        self.Invalidate_ROIs()

    def BtnMoveAllFromKeep(self):
        if self.synapseResult.keepResult.synapses is None:
            return
        if self.synapseResult.detectionResult.synapses is None:
            self.synapseResult.detectionResult.synapses = []
        self.synapseResult.detectionResult.synapses.extend(self.synapseResult.keepResult.synapses)
        self.synapseResult.keepResult.Clear()
        self.Invalidate_ROIs()

    def ImportROIsImageJ(self):
        res = self._gui.ijH.ImportROIS()
        if res is None:
            self.root.bell()
            return
        rois, names = res[0], res[1]
        if len(rois) == 0:
            self.root.bell()
            return
        self.synapseResult.detectionResult.synapses = []
        for i in range(len(rois)):
            roi = rois[i]
            name = names[i]
            s = SingleframeSynapse(roi)
            s.name = name
            self.synapseResult.detectionResult.synapses.append(s)
        self.Invalidate_ROIs()

    def ExportROIsImageJ(self):
        self._gui.ijH.ExportROIs([synapse for synapse,_source in self.synapseResult.GetSynapses()])

    def ExportCSVMultiM(self, path:str|None = None, dropFrame=False) -> bool|None:
        if len(self.synapseResult.GetSynapses()) == 0 or self._gui.ImageObject is None or self._gui.ImageObject.img is None:
            self.root.bell()
            return None
        data = pd.DataFrame()

        i = 0
        for synapse, synapse_source in self.synapseResult.GetSynapses():
            if not isinstance(synapse, detection.SingleframeSynapse):
                continue
            synapseROI: detection.ISynapseROI = synapse.synapse
            _slice = synapseROI.GetImageSignal(self._gui.ImageObject.img)
            if len(_slice) == 0:
                continue
            _signal = np.mean(_slice, axis=1)
            if synapse.name is not None:
                name = synapse.name
            else:
                name = f"ROI {i+1} {synapseROI.LocationStr().replace(",","")}"
                i += 1
            if name in list(data.columns.values):
                for i in range(2, 10):
                    if f"{name} ({i})" not in list(data.columns.values):
                        name = f"{name} ({i})"
                        break
            data[name] = _signal
        data = data.round(4)
        data.index += 1

        if path == TabROIFinder.TO_STREAM:
            return data.to_csv(lineterminator="\n",index=(not dropFrame))
        if path is None:
            path = filedialog.asksaveasfilename(title="Save Multi Measure", filetypes=(("CSV", "*.csv"), ("All files", "*.*")), defaultextension=".csv")
        if path is None or path == "":
            return None
        data.to_csv(path_or_buf=path, lineterminator="\n", mode="w", index=(not dropFrame))
        return True

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
        
    def TreeRois_onDoubleClick(self, event):
        try: 
            self.treeROIs_entryPopup.destroy()
        except AttributeError:
            pass
        rowid = self.treeROIs.identify_row(event.y)
        column = self.treeROIs.identify_column(event.x)
        if not rowid or column not in ["#0", "#1", "#2"]:
            return
        
        # Check if synapse is circular, as others can't be edited
        synapse = self.synapseResult.GetSynapseByUUID(rowid)
        if synapse is None or not isinstance(synapse, detection.SingleframeSynapse):
            self.root.bell()
            return
        synapseROI: detection.ISynapseROI = synapse.synapse
        if not isinstance(synapseROI, detection.CircularSynapseROI):
            self.root.bell()
            return
        
        x,y,width,height = self.treeROIs.bbox(rowid, column)
        pady = height // 2

        if (column == "#0"):
            text = self.treeROIs.item(rowid)["text"]
        elif (column == "#1"):
            text = self.treeROIs.item(rowid, 'values')[0]
        elif (column == "#2"):
            text = self.treeROIs.item(rowid, 'values')[1]
        else:
            return
        self.treeROIs_entryPopup = EntryPopup(self.treeROIs, self.TreeRois_EntryChanged, rowid, column, text)
        self.treeROIs_entryPopup.place(x=x, y=y+pady, width=width, height=height, anchor=tk.W)
        
    def TreeRois_EntryChanged(self, event):
        rowID = event["RowID"]
        synapse = self.synapseResult.GetSynapseByUUID(rowID)
        if synapse is None:
            self.root.bell()
            return
        if not isinstance(synapse, detection.SingleframeSynapse):
            return
        synapseROI: detection.ISynapseROI = synapse.synapse
        if not isinstance(synapseROI, detection.CircularSynapseROI):
            return
        if event["Column"] == "#0":
            if len(event["NewVal"]) <= 2:
                return
            synapse.name = event["NewVal"]
        elif event["Column"] == "#1":
            mval = event["NewVal"].replace("(","").replace(")","").replace(" ", "")
            mvals = mval.split(",")
            if len(mvals) != 2 or not mvals[0].isdigit() or not mvals[1].isdigit(): return
            x = int(mvals[0])
            y = int(mvals[1])
            synapseROI.SetLocation(x,y)
        elif event["Column"] == "#2":
            if not event["NewVal"].isdigit(): return
            synapseROI.SetRadius(int(event["NewVal"]))
        self.synapseResult.modified = True
        self.Invalidate_ROIs()

    def Canvas1ClickEvent(self, event):
        if not event.dblclick or event.inaxes is None:
            return
        if len(self.synapseResult.GetSynapses()) == 0:
            return
        if (event.inaxes != self.ax1 and event.inaxes != self.ax2):
            return
        x, y = event.xdata, event.ydata
        _synapses = sorted(self.synapseResult.GetSynapses(), key=lambda v: (v[0].location[0]-x)**2+(v[0].location[1]-y)**2)
        s = _synapses[0][0]
        d = ((s.location[0]-x)**2+(s.location[1]-y)**2)**0.5
        if d > 40:
            return
        if s.uuid in self.treeROIs.get_children():
            self.treeROIs.selection_set(s.uuid)

    def _Canvas1Resize(self, event):
        if self.tab.winfo_width() > 300:
            self.figure1.tight_layout()
            self.canvas1.draw()