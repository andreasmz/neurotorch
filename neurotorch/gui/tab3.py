import neurotorch.gui.window as window
import neurotorch.utils.detection as detection
from neurotorch.gui.components import EntryPopup, VirtualFile, IntStringVar
import neurotorch.external.trace_selector_connector as ts_con

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.widgets as PltWidget
import matplotlib.patches as patches
import numpy as np
import pandas as pd
from io import StringIO

class Tab3():
    def __init__(self, gui: window._GUI):
        self._gui = gui
        self.root = gui.root
        self.detectionAlgorithm = None
        self.detectionResult = detection.DetectionResult()
        self.roiPatches = {}
        self.treeROIs_entryPopup = None
        self.Init()

    def Init(self):
        self.tab = ttk.Frame(self._gui.tabMain)
        self._gui.tabMain.add(self.tab, text="Synapse ROI Finder")

        self.frame = tk.Frame(self.tab)
        self.frame.pack(side=tk.LEFT, fill="y", expand=True, anchor=tk.W)
        self.frameOptions = ttk.LabelFrame(self.frame, text="Options")
        self.frameOptions.grid(row=0, column=0, sticky="news")
        self.lblAlgorithm = tk.Label(self.frameOptions, text="Algorithm")
        self.lblAlgorithm.grid(row=0, column=0, columnspan=2)
        self.radioAlgoVar = tk.StringVar(value="apd")
        self.radioAlgo1 = tk.Radiobutton(self.frameOptions, variable=self.radioAlgoVar, indicatoron=False, text="Threshold (Deprecated)", value="threshold", command=self.AlgoChanged)
        self.radioAlgo2 = tk.Radiobutton(self.frameOptions, variable=self.radioAlgoVar, indicatoron=False, text="Advanced Polygonal Detection", value="apd", command=self.AlgoChanged)
        self.radioAlgo1.grid(row=1, column=0)
        self.radioAlgo2.grid(row=1, column=1)
        self.btnDetect = tk.Button(self.frameOptions, text="Detect", command=self.Detect)
        self.btnDetect.grid(row=2, column=0)

        self.detectionAlgorithm = detection.DetectionAlgorithm()
        self.frameAlgoOptions = self.detectionAlgorithm.OptionsFrame(self.frame, self._gui.IMG)
        self.frameAlgoOptions.grid(row=1, column=0, sticky="news")

        self.frameROIS = tk.LabelFrame(self.frame, text="ROIs")
        self.frameROIS.grid(row=2, column=0, sticky="news")
        self.treeROIs = ttk.Treeview(self.frameROIS, columns=("Location", "Radius"))
        self.treeROIs.heading('Location', text="Center (X,Y)")
        self.treeROIs.heading('Radius', text='Radius [px]')
        self.treeROIs.column("#0", minwidth=0, width=50)
        self.treeROIs.column("Location", minwidth=0, width=50)
        self.treeROIs.column("Radius", minwidth=0, width=50)
        self.treeROIs.bind("<<TreeviewSelect>>", self.TreeViewClick)
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

        self.frameImg = ttk.LabelFrame(self.frame, text="Image")
        self.frameImg.grid(row=3, column=0, sticky="new")
        self.figureImg = plt.Figure(figsize=(3,3), dpi=100)
        self.axImg = self.figureImg.add_subplot()  
        self.axImg.set_title("Img Mean")
        self.axImg.set_axis_off()
        self.figureImg.tight_layout()
        self.canvasImg = FigureCanvasTkAgg(self.figureImg, self.frameImg)
        self.canvasImg.get_tk_widget().pack(expand=True, fill="both")
        self.canvasImg.draw()

        self.figure1 = plt.Figure(figsize=(20,10), dpi=100)
        self.ax1 = self.figure1.add_subplot(221)  
        self.ax2 = self.figure1.add_subplot(222, sharex=self.ax1, sharey=self.ax1)  
        self.ax3 = self.figure1.add_subplot(223)  
        self.ax1.set_axis_off()
        self.ax2.set_axis_off()
        self.ax3.set_axis_off()
        self.canvas1 = FigureCanvasTkAgg(self.figure1, self.tab)
        self.canvtoolbar1 = NavigationToolbar2Tk(self.canvas1,self.tab)
        self.canvtoolbar1.update()
        self.canvas1.get_tk_widget().pack(expand=True, fill="both", side=tk.LEFT)
        self.canvas1.draw()

        tk.Grid.rowconfigure(self.frame, 3, weight=1)

        self.AlgoChanged()

    def Update(self, newImage=False):
        if newImage:
            self.detectionResult.Clear()
            self.detectionResult.modified = False
            self.detectionAlgorithm.Reset()
        self.axImg.clear()    
        self.axImg.set_title("Img Mean")
        self.axImg.set_axis_off()
        if self._gui.IMG.imgMean is not None:
            self.axImg.imshow(self._gui.IMG.imgMean, cmap="Greys_r")
        self.canvasImg.draw()

        self.ax1.clear()
        self.ax2.clear()
        self.ax3.clear()
        self.ax1.set_axis_off()
        self.ax2.set_axis_off()
        self.ax3.set_axis_off()
        self.roiPatches = {}
        self.treeROIs.delete(*self.treeROIs.get_children())
        self.frameROIS["text"] = "ROIs"
        try: 
            self.treeROIs_entryPopup.destroy()
        except AttributeError:
            pass
        if (self._gui.IMG.imgDiff is None):
            self.canvas1.draw()
            return
        self.ax1.imshow(self._gui.IMG.imgDiffMaxTime, cmap="inferno")
        self.ax1.set_axis_on()
        if self.detectionResult.synapses is None:
            self.canvas1.draw()
            return
        self.ax2.set_axis_on()
        self.ax3.set_axis_off()
        self.UpdateROIs(draw = False)
        if self.detectionAlgorithm.AX2Image() is not None:
            self.ax2.set_title(self.detectionAlgorithm.ax2Title)
            self.ax2.imshow(self.detectionAlgorithm.AX2Image())
        #self.figure1.tight_layout()
        self.canvas1.draw()

    def UpdateROIs(self, draw = True):
        [p.remove() for p in reversed(self.ax1.patches)]
        self.roiPatches = {}
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
            if draw: self.canvas1.draw()
            return
        
        for i in range(len(self.detectionResult.synapses)):
            synapse = self.detectionResult.synapses[i]
            if not isinstance(synapse, detection.SingleframeSynapse):
                continue
            synapseROI: detection.ISynapseROI = synapse.synapse
            if isinstance(synapseROI, detection.CircularSynapseROI):
                synapseuuid = self.treeROIs.insert('', 'end', iid=synapse.uuid, text=f"ROI {i+1}", values=([synapseROI.LocationStr(), synapseROI.radius]))
                c = patches.Circle(synapseROI.location, synapseROI.radius, color="red", fill=False)
            elif isinstance(synapseROI, detection.PolygonalSynapseROI):
                synapseuuid = self.treeROIs.insert('', 'end', iid=synapse.uuid, text=f"ROI {i+1}", values=([synapseROI.LocationStr(), 0]))
                c = patches.Polygon(synapseROI.polygon, color="red", fill=False)
            else:
                synapseuuid = self.treeROIs.insert('', 'end', iid=synapse.uuid, text=f"ROI {i+1}", values=([synapseROI.LocationStr(), 3]))
                c = patches.Circle(synapseROI.location, 3, color="red", fill=False)
            self.ax1.add_patch(c)
            self.roiPatches[synapseuuid] = c
        if draw: self.canvas1.draw()
            
    def Detect(self):
        if self.detectionAlgorithm is None or self._gui.IMG.imgDiffMaxTime is None:
            self._gui.root.bell()
            return
        self.detectionResult.modified = False
        self.detectionResult.SetISynapses(self.detectionAlgorithm.Detect(self._gui.IMG))
        self.Update()

    def AlgoChanged(self):
        match self.radioAlgoVar.get():
            case "threshold":
                if isinstance(self.detectionAlgorithm, detection.Tresholding):
                    self.detectionAlgorithm.OptionsFrame_Update()
                    return
                self.detectionAlgorithm = detection.Tresholding()
            case "apd":
                if isinstance(self.detectionAlgorithm, detection.APD):
                    self.detectionAlgorithm.OptionsFrame_Update()
                    return
                self.detectionAlgorithm = detection.APD()
            case _:
                self.detectionAlgorithm = None
                return
        if (self.frameAlgoOptions is not None):
            self.frameAlgoOptions.grid_forget()
        if (self.detectionAlgorithm is not None):
            self.frameAlgoOptions = self.detectionAlgorithm.OptionsFrame(self.frame, self._gui.IMG)
            self.frameAlgoOptions.grid(row=1, column=0, sticky="news")
        self.Update()

    def BtnAddROI_Click(self):
        self.detectionResult.modified = True
        self.detectionResult.AddISynapses(detection.SingleframeSynapse(detection.CircularSynapseROI().SetLocation(0,0).SetRadius(6)))
        #self.detectionResult.synapses.append(detection.Synapse().SetLocation(0,0).SetRadius(6))
        self.UpdateROIs()

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
        self.UpdateROIs()

    def BtnClearAllROIs_Click(self):
        if messagebox.askyesnocancel("Neurotorch", "Do you really want to clear all ROIs?"):
            self.detectionResult.Clear()
            self.detectionResult.modified = False
            self.UpdateROIs()

    def TreeViewClick(self, event):
        if (self._gui.IMG.img is None):
            return
        if self.detectionResult.synapses is None:
            return
        if len(self.treeROIs.selection()) != 1:
            return
        selectionIndex = self.treeROIs.selection()[0]

        self.ax3.clear()
        self.ax3.set_ylabel("mean brightness")
        self.ax3.set_xlabel("frame")
        for i in range(len(self.detectionResult.synapses)):
            synapse = self.detectionResult.synapses[i]
            if not isinstance(synapse, detection.SingleframeSynapse):
                continue
            synapseROI: detection.ISynapseROI = synapse.synapse
            if synapse.uuid == selectionIndex:
                if isinstance(synapseROI, detection.CircularSynapseROI):
                    _slice = synapseROI.GetImageSignal(self._gui.IMG)
                    if len(_slice) > 0:
                        _signal = np.mean(_slice, axis=0)
                    else:
                        _signal = []
                elif isinstance(synapseROI, detection.PolygonalSynapseROI):
                    _slice = synapseROI.GetImageSignal(self._gui.IMG)
                    if len(_slice) > 0:
                        _signal = np.mean(_slice, axis=0)
                    else:
                        _signal = []
                else:
                    _signal = []
                self.ax3.plot(_signal)
        for name,c in self.roiPatches.items():
            if name == selectionIndex:
                c.set_color("yellow")
            else:
                c.set_color("red")
        self.canvas1.draw()

    def ExportROIsImageJ(self):
        if self._gui.ij is None:
            messagebox.showerror("Neurotorch", "Please first start ImageJ")
            return
        if self.detectionResult.synapses is None or len(self.detectionResult.synapses) == 0:
            self.root.bell()
            return
        self._gui.ijH.OpenRoiManager()
        for i in  range(len(self.detectionResult.synapses)):
            synapse = self.detectionResult.synapses[i]
            if not isinstance(synapse, detection.SingleframeSynapse):
                continue
            synapseROI: detection.ISynapseROI = synapse.synapse
            if isinstance(synapseROI, detection.CircularSynapseROI):
                roi = self._gui.ijH.OvalRoi(synapseROI.location[0]-synapseROI.radius, synapseROI.location[1]-synapseROI.radius, 2*synapseROI.radius, 2*synapseROI.radius)
                roi.setName(f"ROI {i+1} {synapseROI.LocationStr()}")
                self._gui.ijH.RM.addRoi(roi)
            else:
                continue

    def ExportCSVMultiM(self, toStream = False):
        if self.detectionResult.synapses is None or len(self.detectionResult.synapses) == 0 or self._gui.IMG.img is None:
            self.root.bell()
            return None
        data = pd.DataFrame()

        for i in  range(len(self.detectionResult.synapses)):
            synapse = self.detectionResult.synapses[i]
            if not isinstance(synapse, detection.SingleframeSynapse):
                continue
            synapseROI: detection.ISynapseROI = synapse.synapse
            if isinstance(synapseROI, detection.CircularSynapseROI):
                _signal = np.mean(self._gui.IMG.GetImgROIAt(synapseROI.location, synapseROI.radius), axis=0)
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
        self.UpdateROIs()
