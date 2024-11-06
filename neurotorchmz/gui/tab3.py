from neurotorchmz.gui.window import Neurotorch_GUI, Tab, TabUpdateEvent
import neurotorchmz.external.trace_selector_connector as ts_con
import neurotorchmz.utils.synapse_detection_integration as detection
from neurotorchmz.utils.synapse_detection import SingleframeSynapse
from neurotorchmz.gui.components import EntryPopup, VirtualFile, Job

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
import time

class Tab3(Tab):
    def __init__(self, gui: Neurotorch_GUI):
        super().__init__(gui)
        self.tab_name = "Tab ROI Finder"
        self._gui = gui
        self.root = gui.root
        self.detectionAlgorithm = None
        self.detectionResult = detection.DetectionResult()
        self.roiPatches = {}
        self.roiPatches2 = {}
        self.treeROIs_entryPopup = None
        self.ax2Image = None

    def Init(self):
        self.tab = ttk.Frame(self._gui.tabMain)
        self._gui.tabMain.add(self.tab, text="Synapse ROI Finder")

        self.frameToolsContainer = tk.Frame(self.tab, borderwidth=10)
        self.frameToolsContainer.pack(side=tk.LEFT, fill="y", expand=True, anchor=tk.W)
        self.canvasFrameTools = tk.Canvas(self.frameToolsContainer, background="blue")
        self.scrollFrameTools = ttk.Scrollbar(self.frameToolsContainer)
        self.frameTools = tk.Frame(self.canvasFrameTools)
        self.frameTools.bind(
            "<Configure>",
            lambda e: self.canvasFrameTools.configure(
                scrollregion=self.canvasFrameTools.bbox("all")
            )
        )
        self.canvasFrameTools.create_window((0, 0), window=self.frameTools, anchor="nw")
        self.canvasFrameTools.configure(yscrollcommand=self.scrollFrameTools.set)
        self.canvasFrameTools.pack(side=tk.LEFT, fill="y", expand=True)
        self.scrollFrameTools.pack(fill="y", expand=True)

        self.frameOptions = ttk.LabelFrame(self.frameTools, text="Options")
        self.frameOptions.grid(row=0, column=0, sticky="news")
        self.lblAlgorithm = tk.Label(self.frameOptions, text="Algorithm")
        self.lblAlgorithm.grid(row=0, column=0, columnspan=2)
        self.radioAlgoVar = tk.StringVar(value="apd")
        self.radioAlgo1 = tk.Radiobutton(self.frameOptions, variable=self.radioAlgoVar, indicatoron=True, text="Threshold (Deprecated)", value="threshold", command=lambda:self.Invalidate_Algorithm())
        self.radioAlgo2 = tk.Radiobutton(self.frameOptions, variable=self.radioAlgoVar, indicatoron=True, text="Hysteresis thresholding (Polygonal)", value="apd", command=lambda:self.Invalidate_Algorithm())
        self.radioAlgo3 = tk.Radiobutton(self.frameOptions, variable=self.radioAlgoVar, indicatoron=True, text="Hysteresis thresholding (Circular)", value="apd_aprox", command=lambda:self.Invalidate_Algorithm())
        self.radioAlgo1.grid(row=1, column=0, sticky="nw")
        self.radioAlgo2.grid(row=2, column=0, sticky="nw")
        self.radioAlgo3.grid(row=3, column=0, columnspan=2, sticky="nw")
        self.btnDetect = tk.Button(self.frameOptions, text="Detect", command=self.Detect)
        self.btnDetect.grid(row=4, column=0)

        self.detectionAlgorithm = detection.IDetectionAlgorithmIntegration()
        self.frameAlgoOptions = self.detectionAlgorithm.OptionsFrame(self.frameTools, self._gui, self.Update, self._gui.GetImageObject)
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
        self.treeROIs.pack(fill="both", padx=10)

        self.frameROIsTools = tk.Frame(self.frameROIS)
        self.frameROIsTools.pack(expand=True, fill="x")
        self.btnAddROI = tk.Button(self.frameROIsTools, text="Add ROI", command=self.BtnAddROI_Click)
        self.btnAddROI.grid(row=0, column=0)
        self.btnRemoveROI = tk.Button(self.frameROIsTools, text="Remove ROI", command=self.BtnRemoveROI_Click)
        self.btnRemoveROI.grid(row=0, column=1)
        self.btnClearAllROIs = tk.Button(self.frameROIsTools, text="Clear ROIs", command=self.BtnClearAllROIs_Click)
        self.btnClearAllROIs.grid(row=0, column=2)

        self.frameBtnsExport = tk.Frame(self.frameROIS)
        self.frameBtnsExport.pack(expand=True, fill="x")
        self.btnExportROIsImageJ = tk.Button(self.frameBtnsExport, text="Export to ImageJ", command=self.ExportROIsImageJ)
        self.btnExportROIsImageJ.grid(row=0, column=0)
        self.btnExportCSVMultiM = tk.Button(self.frameBtnsExport, text="Export CSV (Multi Measure)", command=self.ExportCSVMultiM)
        self.btnExportCSVMultiM.grid(row=0, column=1)
        self.btnOpenInTraceSelector = tk.Button(self.frameBtnsExport, text="Open in Trace Selector", command=self.OpenInTraceSelector)
        self.btnOpenInTraceSelector.grid(row=1, column=0)

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
        self.canvas1.draw()

        #tk.Grid.rowconfigure(self.frameTools, 3, weight=1)

        self.treeROIInfo2 = ttk.Treeview(self.frameTools, columns=("Value"))
        #self.treeROIInfo2.grid(row=4, column=1, sticky="news")

        self.Update(["tab3_algorithmChanged"])

    def Update(self, events: list[TabUpdateEvent|str]):
        if TabUpdateEvent.NEWIMAGE in events:    
            self.detectionResult.Clear()
            self.detectionResult.modified = False
            self.Invalidate_Algorithm()
            self.ClearImagePlot()
            self.Invalidate_Image()
        elif "tab3_algorithmChanged" in events:
            self.Invalidate_Algorithm()
            self.Invalidate_Image()
        elif "tab3_replotImages" in events:
            self.Invalidate_Image()

    def Invalidate_Algorithm(self):
        match self.radioAlgoVar.get():
            case "threshold":
                if isinstance(self.detectionAlgorithm, detection.Thresholding_Integration):
                    return
                self.detectionAlgorithm = detection.Thresholding_Integration()
            case "apd":
                if type(self.detectionAlgorithm) == detection.APD_Integration:
                    self.detectionAlgorithm.OptionsFrame_Update()
                    return
                self.detectionAlgorithm = detection.APD_Integration()
            case "apd_aprox":
                if type(self.detectionAlgorithm) == detection.APD_CircleAprox_Integration:
                    self.detectionAlgorithm.OptionsFrame_Update()
                    return
                self.detectionAlgorithm = detection.APD_CircleAprox_Integration()
            case _:
                self.detectionAlgorithm = None
                return
        if (self.frameAlgoOptions is not None):
            self.frameAlgoOptions.grid_forget()
        if (self.detectionAlgorithm is not None):
            self.frameAlgoOptions = self.detectionAlgorithm.OptionsFrame(self.frameTools, self._gui, self.Update, self._gui.GetImageObject)
            self.frameAlgoOptions.grid(row=1, column=0, sticky="news")

    def ClearImagePlot(self):
        for ax in [self.ax1, self.ax2, self.ax3, self.ax4]: 
            ax.clear()
            ax.set_axis_off()
        self.ax1.xaxis.set_major_locator(MaxNLocator(integer=True))
        self.ax1.yaxis.set_major_locator(MaxNLocator(integer=True))
        self.ax2.xaxis.set_major_locator(MaxNLocator(integer=True))
        self.ax2.yaxis.set_major_locator(MaxNLocator(integer=True))
        self.ax1.set_title("Input Image (Mean)")
        self.ax2.set_title("Difference Image (Max)")

    def Invalidate_Image(self):
        imgObj = self._gui.ImageObject

        self.ax2Image = None    
        for ax in [self.ax1, self.ax2]: 
            for axImg in ax.get_images(): axImg.remove()
            ax.set_axis_off()
        
        if imgObj is None or imgObj.img is None or imgObj.imgDiff is None:
            self.Invalidate_ROIs()
            return
        
        self.ax1.imshow(imgObj.imgView(imgObj.SPATIAL).Mean, cmap="Greys_r") 
        if self.detectionAlgorithm.Img_Input() is False:
            pass
        elif self.detectionAlgorithm.Img_Input() is None:
            self.ax2Image = self.ax2.imshow(imgObj.imgDiffView(imgObj.SPATIAL).Max, cmap="inferno")
        else:
            self.ax2Image = self.ax2.imshow(self.detectionAlgorithm.Img_Input(), cmap="inferno")
        self.ax1.set_axis_on()
        self.ax2.set_axis_on()

        self.Invalidate_ROIs()


    def Invalidate_ROIs(self):
        imgObj = self._gui.ImageObject

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

        if self.detectionResult.modified:
            self.frameROIS["text"] = "ROIs*"
        else:
            self.frameROIS["text"] = "ROIs"

        if self.detectionResult.synapses is None:
            self.Invalidate_SelectedROI()
            return

        _imgReady = True
        if imgObj is None or imgObj.img is None or imgObj.imgDiff is None:
            _imgReady = False
        
        for i in range(len(self.detectionResult.synapses)):
            synapse = self.detectionResult.synapses[i]
            if not isinstance(synapse, detection.SingleframeSynapse):
                continue
            synapseROI: detection.ISynapseROI = synapse.synapse
            if isinstance(synapseROI, detection.CircularSynapseROI):
                synapseuuid = self.treeROIs.insert('', 'end', iid=synapse.uuid, text=f"ROI {i+1}", values=([synapseROI.LocationStr(), synapseROI.radius]))
                c = patches.Circle(synapseROI.location, synapseROI.radius, color="red", fill=False)
                c2 = patches.Circle(synapseROI.location, synapseROI.radius, color="green", fill=False)
            elif isinstance(synapseROI, detection.PolygonalSynapseROI):
                synapseuuid = self.treeROIs.insert('', 'end', iid=synapse.uuid, text=f"ROI {i+1}", values=([synapseROI.LocationStr(), "Polygon"]))
                c = patches.Polygon(synapseROI.polygon, color="red", fill=False)
                c2 = patches.Polygon(synapseROI.polygon, color="green", fill=False)
            else:
                synapseuuid = self.treeROIs.insert('', 'end', iid=synapse.uuid, text=f"ROI {i+1}", values=([synapseROI.LocationStr(), "Unsupported"]))
                c = patches.Circle(synapseROI.location, 3, color="red", fill=False)
                c2 = patches.Circle(synapseROI.location, 3, color="green", fill=False)
            
            if _imgReady:
                self.ax1.add_patch(c)
                if self.detectionAlgorithm.Img_Detection_Raw() is None:
                    self.ax2.add_patch(c2)
                self.roiPatches[synapseuuid] = c
                self.roiPatches2[synapseuuid] = c2

        if self.detectionAlgorithm.Img_Detection_Raw() is not None:
            self.ax2.imshow(self.detectionAlgorithm.Img_Detection_Raw()!=0, alpha=(self.detectionAlgorithm.Img_Detection_Raw() != 0).astype(int)*0.5, cmap="gist_gray")

        self.Invalidate_SelectedROI()


    def Invalidate_SelectedROI(self):
        imgObj = self._gui.ImageObject

        self.ax3.clear()
        self.ax3.set_title("Image Signal")
        self.ax3.set_ylabel("mean brightness")
        self.ax3.set_xlabel("frame")
        self.ax4.clear()
        self.ax4.set_title("Detection Signal (from imgDiff)")
        self.ax4.set_ylabel("mean brightness increase")
        self.ax4.set_xlabel("imgDiff frame")

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

        if imgObj is None or imgObj.img is None or self.detectionResult.synapses is None:
            self.ax3.set_axis_off()
            self.ax4.set_axis_off()
            self.figure1.tight_layout()
            self.canvas1.draw()
            return
       
        for i in range(len(self.detectionResult.synapses)):
            synapse = self.detectionResult.synapses[i]
            if not isinstance(synapse, detection.SingleframeSynapse):
                continue
            synapseROI: detection.ISynapseROI = synapse.synapse
            if synapse.uuid == selectionIndex:
                _slice = synapseROI.GetImageSignal(imgObj)
                if len(_slice) > 0:
                    _signal = np.mean(_slice, axis=0)
                    self.ax3.plot(_signal)
                _sliceDiff = synapseROI.GetImageDiffSignal(imgObj)
                if len(_sliceDiff) > 0:
                    _signalMaxDiff = np.max(_sliceDiff, axis=0)
                    _signalMeanDiff = np.mean(_sliceDiff, axis=0)
                    _signalMinDiff = np.min(_sliceDiff, axis=0)
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
                    self.treeROIInfo.insert('', 'end', text=f"Intensity Max", values=([f"{round(p.intensity_max, 2)}"]))
                    self.treeROIInfo.insert('', 'end', text=f"Intensity Mean", values=([f"{round(p.intensity_mean, 2)}"]))
                    self.treeROIInfo.insert('', 'end', text=f"Intensity Min", values=([f"{round(p.intensity_min, 2)}"]))
                    self.treeROIInfo.insert('', 'end', text=f"Intensity Std", values=([f"{round(p.intensity_std, 2)}"]))
                    self.treeROIInfo.insert('', 'end', text=f"Inertia X", values=([f"{round(p.inertia_tensor[0,0], 2)}"]))
                    self.treeROIInfo.insert('', 'end', text=f"Inertia Y", values=([f"{round(p.inertia_tensor[1,1], 2)}"]))
                    self.treeROIInfo.insert('', 'end', text=f"Inertia Ratio", values=([f"{round(p.inertia_tensor[0,0]/p.inertia_tensor[1,1], 2)}"]))
                    #print(p.moments_weighted_central)
        self.figure1.tight_layout()
        self.canvas1.draw()

    def Detect(self):
        if self.detectionAlgorithm is None or self._gui.ImageObject.imgDiff is None:
            self._gui.root.bell()
            return
        self.detectionResult.modified = False

        def _Detect(job: Job):
            job.SetProgress(0, "Detect ROIs")
            self.detectionResult.SetISynapses(SingleframeSynapse.ROIsToSynapses(self.detectionAlgorithm.DetectAutoParams()))
            job.SetStopped("Detecting ROIs")
            self.Invalidate_ROIs()

        job = Job(steps=1)
        self._gui.statusbar.AddJob(job)
        threading.Thread(target=_Detect, args=(job,), daemon=True).start()



    # GUI Functions

    def BtnAddROI_Click(self):
        self.detectionResult.modified = True
        self.detectionResult.AddISynapses(detection.SingleframeSynapse(detection.CircularSynapseROI().SetLocation(0,0).SetRadius(6)))
        self.Invalidate_ROIs()

    def BtnRemoveROI_Click(self):
        if self.detectionResult.synapses is None:
            self.root.bell()
            return
        if len(self.treeROIs.selection()) != 1:
            self.root.bell()
            return
        selectionIndex = self.treeROIs.selection()[0]
        self.detectionResult.modified = True
        for i in range(len(self.detectionResult.synapses)):
            synapse = self.detectionResult.synapses[i]
            if synapse.uuid == selectionIndex:
                self.detectionResult.synapses.remove(synapse)
                break
        self.Invalidate_ROIs()

    def BtnClearAllROIs_Click(self):
        if messagebox.askyesnocancel("Neurotorch", "Do you really want to clear all ROIs?"):
            self.detectionResult.Clear()
            self.detectionResult.modified = False
            self.Invalidate_ROIs()

    def ExportROIsImageJ(self):
        if self.detectionResult.synapses is None or len(self.detectionResult.synapses) == 0:
            self.root.bell()
            return
        self._gui.ijH.ExportROIs([s.synapse for s in self.detectionResult.synapses if isinstance(s, detection.SingleframeSynapse)])

    def ExportCSVMultiM(self, toStream = False):
        if self.detectionResult.synapses is None or len(self.detectionResult.synapses) == 0 or self._gui.ImageObject.img is None:
            self.root.bell()
            return None
        data = pd.DataFrame()

        for i in  range(len(self.detectionResult.synapses)):
            synapse = self.detectionResult.synapses[i]
            if not isinstance(synapse, detection.SingleframeSynapse):
                continue
            synapseROI: detection.ISynapseROI = synapse.synapse
            _slice = synapseROI.GetImageSignal(self._gui.ImageObject)
            if len(_slice) == 0:
                continue
            _signal = np.mean(_slice, axis=0)
            name = f"ROI {i+1} {synapseROI.LocationStr().replace(",","")}"
            data[name] = _signal
        data = data.round(4)
        data.index += 1
        if toStream:
            _buffer = VirtualFile()
            data.to_csv(_buffer, lineterminator="\n")
            return _buffer
        f = filedialog.asksaveasfile(mode='w', title="Save Multi Measure", filetypes=(("CSV", "*.csv"), ("All files", "*.*")), defaultextension=".csv")
        if f is None:
            return None
        data.to_csv(path_or_buf=f, lineterminator="\n")
        
    def OpenInTraceSelector(self):
        if ts_con.ts_mainWindow is None:
            messagebox.showerror("Neurotorch", "Please first start Trace Selector")
            return
        _buffer = self.ExportCSVMultiM(toStream=True)
        if (_buffer is None):
            self.root.bell()
            return
        ts_con.OpenStream(_buffer)
        
    def TreeRois_onDoubleClick(self, event):
        try: 
            self.treeROIs_entryPopup.destroy()
        except AttributeError:
            pass
        rowid = self.treeROIs.identify_row(event.y)
        column = self.treeROIs.identify_column(event.x)
        if not rowid or column not in ["#1", "#2"]:
            return
        
        # Check if synapse is circular, as others can't be edited
        for i in range(len(self.detectionResult.synapses)):
            synapse = self.detectionResult.synapses[i]
            if synapse.uuid == rowid:
                if not isinstance(synapse, detection.SingleframeSynapse):
                    self.root.bell()
                    return
                synapseROI: detection.ISynapseROI = synapse.synapse
                if not isinstance(synapseROI, detection.CircularSynapseROI):
                    self.root.bell()
                    return
        
        x,y,width,height = self.treeROIs.bbox(rowid, column)
        pady = height // 2

        if (column == "#1"):
            text = self.treeROIs.item(rowid, 'values')[0]
        elif (column == "#2"):
            text = self.treeROIs.item(rowid, 'values')[1]
        else:
            return
        self.treeROIs_entryPopup = EntryPopup(self.treeROIs, self.TreeRois_EntryChanged, rowid, column, text)
        self.treeROIs_entryPopup.place(x=x, y=y+pady, width=width, height=height, anchor=tk.W)
        
    def TreeRois_EntryChanged(self, event):
        if self.detectionResult.synapses is None:
            return
        rowID = event["RowID"]
        for i in range(len(self.detectionResult.synapses)):
            synapse = self.detectionResult.synapses[i]
            if not isinstance(synapse, detection.SingleframeSynapse):
                continue
            synapseROI: detection.ISynapseROI = synapse.synapse
            if not isinstance(synapseROI, detection.CircularSynapseROI):
                continue
            if synapse.uuid == rowID:
                if event["Column"] == "#1":
                    mval = event["NewVal"].replace("(","").replace(")","").replace(" ", "")
                    mvals = mval.split(",")
                    if len(mvals) != 2 or not mvals[0].isdigit() or not mvals[1].isdigit(): return
                    x = int(mvals[0])
                    y = int(mvals[1])
                    synapseROI.SetLocation(x,y)
                    break
                elif event["Column"] == "#2":
                    if not event["NewVal"].isdigit(): return
                    synapseROI.SetRadius(int(event["NewVal"]))
                    break
        self.detectionResult.modified = True
        self.Invalidate_ROIs()

    def _Canvas1Resize(self, event):
        if self.tab.winfo_width() > 300:
            self.figure1.tight_layout()
            self.canvas1.draw()