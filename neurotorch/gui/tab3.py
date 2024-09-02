import neurotorch.gui.window as window
import neurotorch.utils.detection as detection

import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.widgets as PltWidget
from matplotlib.patches import Circle

class Tab3():
    def __init__(self, gui: window._GUI):
        self._gui = gui
        self.root = gui.root
        self.detection = None
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
        self.treeROIs = ttk.Treeview(self.frameROIS)
        self.treeROIs.pack(fill="both", padx=10)

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
        self.ax2 = self.figure1.add_subplot(222)  
        self.ax3 = self.figure1.add_subplot(223)  
        self.ax1.set_axis_off()
        self.ax2.set_axis_off()
        self.ax3.set_axis_off()
        self.figure1.tight_layout()

        self.ax1.plot([1,2,3,4,5,6])
        
        self.canvas1 = FigureCanvasTkAgg(self.figure1, self.tab)
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
        self.ax3.set_axis_on()
        for synapse in self.detection.synapses:
            self.treeROIs.insert('', 'end', text=synapse.LocationStr())
            color = "red"
            c = Circle(synapse.location, synapse.radius, color=color, fill=False)
            self.ax1.add_patch(c)
        self.canvas1.draw()
            
    def Detect(self):
        if self.detection is None or self._gui.IMG.imgDiff is None:
            self._gui.root.bell()
            return
        self.detection.Detect(self._gui.IMG.imgDiffMaxTime)
        self.Update()

    def AlgoChanged(self):
        print("Algo Update")
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