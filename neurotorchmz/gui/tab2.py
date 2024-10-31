from neurotorchmz.gui.window import Neurotorch_GUI, Tab, TabUpdateEvent
import neurotorchmz.utils.resourcemanager as rsm
from neurotorchmz.utils.signalDetection import SigDetect_DiffMax, SigDetect_DiffStd, ISignalDetectionAlgorithm
from neurotorchmz.gui.components import IntStringVar

import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.widgets as PltWidget
from matplotlib.patches import Circle

class Tab2(Tab):
    def __init__(self, gui: Neurotorch_GUI):
        super().__init__(gui)
        self.tab_name = "Tab Signal"
        self._gui = gui
        self.root = gui.root
        self.signalDetectionAlgorithms = [SigDetect_DiffMax(), SigDetect_DiffStd()]
        self.currentSigDecAlgo : ISignalDetectionAlgorithm = self.signalDetectionAlgorithms[0]

    def Init(self):
        self.tab = ttk.Frame(self._gui.tabMain)
        self._gui.tabMain.add(self.tab, text="Signal")

        self.frame = tk.Frame(self.tab)
        self.frame.pack(side=tk.LEFT, fill="both", expand=True)

        self.frameInfo = ttk.LabelFrame(self.frame, text = "Info")
        self.frameInfo.grid(row=0, column=0, sticky="news")
        self.lblTabInfo = tk.Label(self.frameInfo, text=rsm.Get("tab2_description"), wraplength=400, justify="left")
        self.lblTabInfo.pack(anchor=tk.E, expand=True, fill="x")

        self.frameOptions = ttk.LabelFrame(self.frame, text="Options")
        self.frameOptions.grid(row=1, column=0, sticky="news")
        self.frameAlgorithm = tk.Frame(self.frameOptions)
        self.frameAlgorithm.pack(anchor=tk.W)
        self.frameAlgorithmPick = tk.Frame(self.frameAlgorithm)
        self.frameAlgorithmPick.pack(anchor=tk.W)
        self.lblAlgorithm = tk.Label(self.frameAlgorithmPick, text="Algorithm:")
        self.lblAlgorithm.pack(side=tk.LEFT)
        self.radioAlgoVar = tk.StringVar(value="diffMax")
        self.radioAlgo1 = tk.Radiobutton(self.frameAlgorithmPick, variable=self.radioAlgoVar, indicatoron=False, text="DiffMax", value="diffMax", command=lambda:self.Update(["tab2_algorithmChanged"]))
        self.radioAlgo2 = tk.Radiobutton(self.frameAlgorithmPick, variable=self.radioAlgoVar, indicatoron=False, text="DiffStd", value="diffStd", command=lambda:self.Update(["tab2_algorithmChanged"]))
        self.radioAlgo1.pack(side=tk.LEFT)
        self.radioAlgo2.pack(side=tk.LEFT)
        self.lblAlgoInfo = tk.Label(self.frameAlgorithm, text=rsm.Get("tab2_algorithms").Get("DiffMax"), wraplength=400, justify="left")
        self.lblAlgoInfo.pack(anchor=tk.W)
        self.checkSnapPeaksVar = tk.IntVar(value=1)
        self.checkSnapPeaks = tk.Checkbutton(self.frameOptions, text="Snap frames to peaks", variable=self.checkSnapPeaksVar, command=lambda:self.UpdateFromSignal())
        self.checkSnapPeaks.pack(anchor=tk.W)
        self.checkNormalizeImgVar = tk.IntVar(value=1)
        self.checkNormalizeImg = tk.Checkbutton(self.frameOptions, text="Normalize", variable=self.checkNormalizeImgVar, command=lambda:self.PlotImage())
        self.checkNormalizeImg.pack(anchor=tk.W)
        self.checkShownOriginalImgVar = tk.IntVar(value=0)
        self.checkShownOriginalImg = tk.Checkbutton(self.frameOptions, text="Show original image", variable=self.checkShownOriginalImgVar, command=lambda:self.PlotImage())
        self.checkShownOriginalImg.pack(anchor=tk.W)
        self.frameProminence = tk.Frame(self.frameOptions)
        self.frameProminence.pack(anchor=tk.W)
        tk.Label(self.frameProminence, text="Peak Prominence:").pack(side=tk.LEFT)
        self.sliderProminenceFactorVar = tk.DoubleVar(value=0.5)
        self.sliderProminenceFactor = tk.Scale(self.frameProminence, from_=0.1, to=0.9, orient="horizontal", variable=self.sliderProminenceFactorVar, resolution=0.05, length=100, command=lambda _:self.Update(["tab2_refindpeaks"]))
        self.sliderProminenceFactor.pack(side=tk.LEFT)
        self.varAutoStart = tk.IntVar(value=1)
        self.checkAutoStart = tk.Checkbutton(self.frameOptions, text="Autostart Detection", variable=self.varAutoStart)
        self.checkAutoStart.pack(anchor=tk.W)

        self.framePeakWidths = tk.Frame(self.frameOptions)
        self.framePeakWidths.pack()
        self.varPeakWidthLeft = IntStringVar(self.root, tk.IntVar(value=1))
        self.varPeakWidthRight = IntStringVar(self.root, tk.IntVar(value=6))
        self.varPeakWidthLeft.SetCallback(self._UpdateSignalWidths)
        self.varPeakWidthRight.SetCallback(self._UpdateSignalWidths)
        self._UpdateSignalWidths()
        tk.Label(self.framePeakWidths, text="Peak Width Left").grid(row=0, column=0)
        tk.Label(self.framePeakWidths, text="Peak Width Right").grid(row=1, column=0)
        self.spinPeakWidthLeft = ttk.Scale(self.framePeakWidths, from_=0, to=10, variable=self.varPeakWidthLeft.IntVar)
        self.spinPeakWidthLeft.grid(row = 0, column=1)
        self.spinPeakWidthRight = ttk.Scale(self.framePeakWidths, from_=0, to=10, variable=self.varPeakWidthRight.IntVar)
        self.spinPeakWidthRight.grid(row = 1, column=1)
        self.numPeakWidthLeft = tk.Spinbox(self.framePeakWidths, width=6, textvariable=self.varPeakWidthLeft.StringVar, from_=0, to=10)
        self.numPeakWidthLeft.grid(row = 0, column=2)
        self.numPeakWidthRight = tk.Spinbox(self.framePeakWidths, width=6, textvariable=self.varPeakWidthRight.StringVar, from_=0, to=10)
        self.numPeakWidthRight.grid(row = 1, column=2)

        tk.Button(self.frameOptions, text="Detect", command=self.Detect).pack(anchor=tk.W)

        self.frameSignal = ttk.LabelFrame(self.frame, text="Image")
        self.frameSignal.grid(row=2, column=0, sticky="new")
        self.figureSignal = plt.Figure(figsize=(3.7,3.7), dpi=100)
        self.axSignal = self.figureSignal.add_subplot()  
        self.canvasSignal = FigureCanvasTkAgg(self.figureSignal, self.frameSignal)
        self.canvtoolbarSignal = NavigationToolbar2Tk(self.canvasSignal,self.frameSignal)
        self.canvtoolbarSignal.update()
        self.canvasSignal.get_tk_widget().pack(expand=True, fill="both")
        self.canvasSignal.draw()

        self.figure1 = plt.Figure(figsize=(6,6), dpi=100)
        self.ax1 = self.figure1.add_subplot()  
        self.ax1.set_axis_off()
        self.ax1_slider1 = self.figure1.add_axes([0.35, 0, 0.3, 0.03])
        self.ax1_axbtnDown = self.figure1.add_axes([0.25, 0.05, 0.05, 0.05])
        self.ax1_axbtnUp = self.figure1.add_axes([0.75, 0.05, 0.05, 0.05])
        self.ax1_slider1.set_axis_off()
        self.ax1_axbtnUp.set_axis_off()
        self.ax1_axbtnDown.set_axis_off()

        self.frameSlider = PltWidget.Slider(self.ax1_slider1, 'Frame', 0, 1, valstep=1)
        self.frameSlider.on_changed(lambda _:self.PlotImage())
        self.ax1_btnDown = PltWidget.Button(self.ax1_axbtnDown, '<-')
        self.ax1_btnUp = PltWidget.Button(self.ax1_axbtnUp, '->')
        self.ax1_btnDown.on_clicked(self.BtnDown_Click)
        self.ax1_btnUp.on_clicked(self.BtnUp_Click)
        
        self.frameCanvas1 = tk.Frame(self.frame)
        self.frameCanvas1.grid(row=0, column=1, rowspan=3, sticky="news")
        self.canvas1 = FigureCanvasTkAgg(self.figure1, self.frameCanvas1)
        #self.canvas1.get_tk_widget().grid(row=0, column=1, rowspan=2, sticky="news")
        self.canvtoolbar1 = NavigationToolbar2Tk(self.canvas1,self.frameCanvas1)
        self.canvtoolbar1.update()
        self.canvas1.get_tk_widget().pack(fill="both", expand=True)
        self.canvas1.draw()

        tk.Grid.columnconfigure(self.frame, 1, weight=1)
        tk.Grid.rowconfigure(self.frame, 2, weight=1)

    def Update(self, events: list[TabUpdateEvent|str]):
        if TabUpdateEvent.NEWIMAGE in events:    
            for algo in self.signalDetectionAlgorithms: algo.Clear()

        if "tab2_algorithmChanged" in events:
            match(self.radioAlgoVar.get()):
                case "diffMax":
                    self.currentSigDecAlgo = self.signalDetectionAlgorithms[0]
                    self.lblAlgoInfo["text"] = rsm.Get("tab2_algorithms").Get("DiffMax")
                case "diffStd":
                    self.currentSigDecAlgo = self.signalDetectionAlgorithms[1]
                    self.lblAlgoInfo["text"] = rsm.Get("tab2_algorithms").Get("DiffStd")
                case _:
                    self.currentSigDecAlgo = ISignalDetectionAlgorithm()
                    self.lblAlgoInfo["text"] = ""

        if "tab2_algorithmChanged" in events or TabUpdateEvent.NEWIMAGE in events:
            if (self.varAutoStart.get() == 1): 
                if self.Detect():
                    return
        if "tab2_refindpeaks" in events:
            self._gui.signal.DetectPeaks(self.sliderProminenceFactorVar.get())
            self._gui.SignalChanged()
            return

        if "tab2_algorithmChanged" in events or TabUpdateEvent.NEWIMAGE in events or TabUpdateEvent.NEWSIGNAL:
            self.UpdateFromSignal()
            
    def UpdateFromSignal(self):  
        imgObj = self._gui.ImageObject
        signal = self._gui.signal.signal
        peaks = self._gui.signal.peaks
        self.axSignal.clear()
        self.axSignal.set_ylabel("Strength")
        self.axSignal.set_xlabel("Frame")

        if signal is None or imgObj is None or imgObj.img is None:
            self.figureSignal.tight_layout()
            self.canvasSignal.draw()     
            self.frameSlider.valmin = 0
            self.frameSlider.valmax = 1
            self.frameSlider.valstep = 1
            self.ax1_slider1.set_xlim(self.frameSlider.valmin,self.frameSlider.valmax)
            self.frameSlider.active = False
            self.canvas1.draw()
            self.frameSlider.set_val(0)
            return

        self.axSignal.plot(range(1, len(signal)+1), signal)
        self.axSignal.scatter(peaks+1, signal[peaks], c="orange")
        _valstep = 1
        _min = 1
        if (self.checkSnapPeaksVar.get() == 1 and len(peaks) > 0):
            _valstep = peaks + 1
        if (self.checkShownOriginalImgVar.get() == 1):
            _min = 0
        self.frameSlider.valmin = _min
        self.frameSlider.valmax = imgObj.img.shape[0]-1
        self.frameSlider.valstep = _valstep
        self.ax1_slider1.set_xlim(self.frameSlider.valmin,self.frameSlider.valmax)
        self.frameSlider.active = True
        self.canvas1.draw()     
        self.figureSignal.tight_layout()
        self.canvasSignal.draw()      
        if self.frameSlider.val > self.frameSlider.valmax:
            self.frameSlider.set_val(self.frameSlider.valmax)
        elif self.frameSlider.val < self.frameSlider.valmin:
            self.frameSlider.set_val(self.frameSlider.valmin)
        else:
            self.PlotImage()

    def PlotImage(self):
        imgObj = self._gui.ImageObject
        frame = self.frameSlider.val
        for axImg in self.ax1.get_images(): axImg.remove()
        if imgObj is None or imgObj.img is None:
            self.frameSlider.valtext.set_text("")
            return
        else:
            self.frameSlider.valtext.set_text(f"{frame} / {imgObj.img.shape[0]-1}")
        if (self.checkShownOriginalImgVar.get() == 1):
            if frame < 0 or frame >= imgObj.img.shape[0]:
                _img = None
            else:
                _img = imgObj.img[frame,:,:]
            _vmin = imgObj.imgProps.min
            _vmax = imgObj.imgProps.max
            _cmap = "Greys_r"
            _title = ""
        else:
            frame -= 1
            if frame < 0 or frame >= imgObj.imgDiff.shape[0]:
                _img = None
            else:
                _img = imgObj.imgDiff[frame,:,:]
            _vmin = imgObj.imgDiffProps.minClipped
            _vmax = imgObj.imgDiffProps.max
            _cmap = "inferno"
            _title = "Difference Image"

        if (self.checkNormalizeImgVar.get() == 0):
            _vmin = None
            _vmax = None
        if _img is not None:
            self.ax1.imshow(_img, vmin=_vmin, vmax=_vmax, cmap=_cmap)
            self.ax1.set_title(_title)
        self.canvas1.draw()

    # Data functions 

    def Detect(self):
        if self._gui.ImageObject is None or self._gui.ImageObject.imgDiff is None:
            return False
        self._gui.signal.signal = self.currentSigDecAlgo.GetSignal(self._gui.ImageObject)
        self._gui.signal.DetectPeaks(self.sliderProminenceFactorVar.get())
        self._gui.SignalChanged()
        return True
    
    def _UpdateSignalWidths(self):
        self._gui.signal.SetPeakWidths(self.varPeakWidthLeft.IntVar.get(), self.varPeakWidthRight.IntVar.get())

    # GUI

    def BtnDown_Click(self, event):
        newval = min(self.frameSlider.valmax, max(self.frameSlider.valmin, self.frameSlider.val - 1))
        if self.frameSlider.active:
            self.frameSlider.set_val(newval)
    
    def BtnUp_Click(self, event):
        newval = min(self.frameSlider.valmax, max(self.frameSlider.valmin, self.frameSlider.val + 1))
        if self.frameSlider.active:
            self.frameSlider.set_val(newval)