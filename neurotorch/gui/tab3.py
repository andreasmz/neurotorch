import neurotorch.gui.window as window
import neurotorch.utils.detection as detection

import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.widgets as PltWidget
from matplotlib.patches import Circle
import numpy as np

class Tab3():
    def __init__(self, gui: window._GUI):
        self._gui = gui
        self.root = gui.root
        self.detection = None
        self.roiPatches = {}
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
        self.radioAlgoVar = tk.StringVar(value="threshold")
        self.radioAlgo1 = tk.Radiobutton(self.frameOptions, variable=self.radioAlgoVar, indicatoron=False, text="Threshold", value="threshold", command=self.AlgoChanged)
        self.radioAlgo2 = tk.Radiobutton(self.frameOptions, variable=self.radioAlgoVar, indicatoron=False, text="Advanced Maximum Mask", value="amm", command=self.AlgoChanged)
        self.radioAlgo1.grid(row=1, column=0)
        self.radioAlgo2.grid(row=1, column=1)
        self.btnDetect = tk.Button(self.frameOptions, text="Detect", command=self.Detect)
        self.btnDetect.grid(row=2, column=0)

        self.detection = detection.DetectionAlgorithm()
        self.frameAlgoOptions = self.detection.OptionsFrame(self.frame)
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
        self.treeROIs.pack(fill="both", padx=10)
        self.btnExportROIsImageJ = tk.Button(self.frameROIS, text="Export to ImageJ", command=self.ExportROIsImageJ)
        self.btnExportROIsImageJ.pack(anchor=tk.E)

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

        tk.Grid.rowconfigure(self.frame, 2, weight=1)

        self.AlgoChanged()

    def Update(self, newImage=False):
        if newImage:
            self.AlgoChanged()
            return
        self.axImg.clear()    
        self.axImg.set_title("Img Mean")
        self.axImg.set_axis_off()
        if self._gui.IMG.imgMean is not None:
            self.axImg.imshow(self._gui.IMG.imgMean)
        self.canvasImg.draw()

        self.ax1.clear()
        self.ax2.clear()
        self.ax3.clear()
        self.ax1.set_axis_off()
        self.ax2.set_axis_off()
        self.ax3.set_axis_off()
        self.roiPatches = {}
        self.treeROIs.delete(*self.treeROIs.get_children())
        if (self._gui.IMG.imgDiff is None):
            self.canvas1.draw()
            return
        self.ax1.imshow(self._gui.IMG.imgDiffMaxTime)
        if self.detection.synapses is None:
            self.canvas1.draw()
            return
        self.ax1.set_axis_on()
        self.ax2.set_axis_on()
        self.ax3.set_axis_off()
        for i in range(len(self.detection.synapses)):
            synapse = self.detection.synapses[i]
            synapse.tvindex = self.treeROIs.insert('', 'end', text=f"ROI {i+1}", values=([synapse.LocationStr(), synapse.radius]))
            color = "red"
            c = Circle(synapse.location, synapse.radius, color=color, fill=False)
            self.ax1.add_patch(c)
            self.roiPatches[synapse.tvindex] = c
        if self.detection.AX2Image() is not None:
            self.ax2.set_title(self.detection.ax2Title)
            self.ax2.imshow(self.detection.AX2Image())
        #self.figure1.tight_layout()
        self.canvas1.draw()
            
    def Detect(self):
        if self.detection is None or self._gui.IMG.imgDiff is None:
            self._gui.root.bell()
            return
        self.detection.Detect(self._gui.IMG.imgDiffMaxTime)
        self.Update()

    def AlgoChanged(self):
        if (self.frameAlgoOptions is not None):
            self.frameAlgoOptions.grid_forget()
        match self.radioAlgoVar.get():
            case "threshold":
                self.detection = detection.Tresholding()
            case "amm":
                self.detection = detection.AMM()
            case _:
                self.detection = None
                return
        if (self.detection is not None):
            self.frameAlgoOptions = self.detection.OptionsFrame(self.frame)
            self.frameAlgoOptions.grid(row=1, column=0, sticky="news")
        self.Update()

    def TreeViewClick(self, event):
        if self.detection.synapses is None:
            return
        if len(self.treeROIs.selection()) != 1:
            return
        selection = self.treeROIs.selection()[0]

        self.ax3.clear()
        self.ax3.set_ylabel("mean brightness")
        self.ax3.set_xlabel("frame")
        for i in range(len(self.detection.synapses)):
            synapse = self.detection.synapses[i]
            if synapse.tvindex == selection:
                _imgmask, _n = self._gui.IMG.GetImgConv_At(synapse.location, synapse.radius)
                _signal = np.sum(_imgmask, axis=(1,2))/_n
                self.ax3.plot(_signal)
        for name,c in self.roiPatches.items():
            if name == selection:
                c.set_color("yellow")
            else:
                c.set_color("red")
        self.canvas1.draw()

    def ExportROIsImageJ(self):
        if self._gui.ij is None:
            messagebox.showerror("Neurotorch", "Please first start ImageJ")
            return
        if self.detection.synapses is None or len(self.detection.synapses) == 0:
            self.root.bell()
            return
        self._gui.ijH.OpenRoiManager()
        for i in  range(len(self.detection.synapses)):
            synapse = self.detection.synapses[i]
            roi = self._gui.ijH.OvalRoi(synapse.location[0]-synapse.radius, synapse.location[1]-synapse.radius, 2*synapse.radius, 2*synapse.radius)
            roi.setName(f"ROI {i+1} {synapse.LocationStr()}")
            self._gui.ijH.RM.addRoi(roi)