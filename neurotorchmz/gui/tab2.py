from .window import *
from ..utils.signalDetection import SigDetect_DiffMax, SigDetect_DiffStd, ISignalDetectionAlgorithm
from ..gui.settings import Neurotorch_Resources as Resource
from .components.general import *

import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.widgets as PltWidget
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
import numpy as np

class TabSignal_AlgorithmChangedEvent(TabUpdateEvent):
    pass

class TabSignal_RefindPeaksEvent(TabUpdateEvent):
    pass

class TabSignal(Tab):
    def __init__(self, gui: Neurotorch_GUI):
        super().__init__(gui)
        self.tab_name = "Tab Signal"
        self._gui = gui
        self.root = gui.root
        self.signalDetectionAlgorithms = [SigDetect_DiffMax(), SigDetect_DiffStd()]
        self.currentSigDecAlgo : ISignalDetectionAlgorithm = self.signalDetectionAlgorithms[0]
        self.ax1Image = None
        self.colorbar = None

    def Init(self):
        self.tab = ttk.Frame(self._gui.tabMain)
        self._gui.tabMain.add(self.tab, text="Signal")

        self.frame = tk.Frame(self.tab)
        self.frame.pack(side=tk.LEFT, fill="both", expand=True)

        self.frameInfo = ttk.LabelFrame(self.frame, text = "Info")
        self.frameInfo.grid(row=0, column=0, sticky="news")
        self.lblTabInfo = tk.Label(self.frameInfo, text=Resource.GetString("tab2/description"), wraplength=350, justify="left")
        self.lblTabInfo.pack(anchor=tk.E, expand=True, fill="x")

        self.frameOptions = ttk.LabelFrame(self.frame, text="Options")
        self.frameOptions.grid(row=1, column=0, sticky="news")
        self.frameAlgorithm = tk.Frame(self.frameOptions)
        self.frameAlgorithm.grid(row=0, column=0, columnspan=4)
        self.lblAlgorithm = tk.Label(self.frameAlgorithm, text="Algorithm:")
        self.lblAlgorithm.pack(side=tk.LEFT)
        self.radioAlgoVar = tk.StringVar(value="diffMax")
        self.radioAlgo1 = tk.Radiobutton(self.frameAlgorithm, variable=self.radioAlgoVar, indicatoron=False, text="DiffMax", value="diffMax", command=lambda:self.Update(TabSignal_AlgorithmChangedEvent()))
        self.radioAlgo2 = tk.Radiobutton(self.frameAlgorithm, variable=self.radioAlgoVar, indicatoron=False, text="DiffStd", value="diffStd", command=lambda:self.Update(TabSignal_AlgorithmChangedEvent()))
        self.radioAlgo1.pack(side=tk.LEFT)
        self.radioAlgo2.pack(side=tk.LEFT)
        ToolTip(self.radioAlgo1, msg=Resource.GetString("tab2/algorithms/diffMax"), follow=True, delay=0.1)
        ToolTip(self.radioAlgo2, msg=Resource.GetString("tab2/algorithms/diffStd"), follow=True, delay=0.1)

        self.setting_snapFrames = GridSetting(self.frameOptions, row=10, type_="Checkbox", text="Snap frames to peaks", unit="", default=1, tooltip="")
        self.setting_snapFrames.var.IntVar.trace_add("write", lambda _1,_2,_3: self.UpdateFromSignal())
        self.setting_normalize = GridSetting(self.frameOptions, row=11, type_="Checkbox", text="Normalize", unit="", default=1, tooltip="")
        self.setting_normalize.var.IntVar.trace_add("write", lambda _1,_2,_3: self.PlotImage())
        self.setting_originalImage = GridSetting(self.frameOptions, row=12, type_="Checkbox", text="Show original image", default=0)
        self.setting_originalImage.var.IntVar.trace_add("write", lambda _1,_2,_3: self.PlotImage())
        self.setting_peakProminence = GridSetting(self.frameOptions, row=13, text="Peak Prominence", unit="%", default=50, min_=1, max_=100, scaleMin=1, scaleMax=100, tooltip=Resource.GetString("tab2/peakProminence"))
        self.setting_peakProminence.var.IntVar.trace_add("write", lambda _1,_2,_3: self.Update(TabSignal_RefindPeaksEvent()))
        self.setting_colorbarUpdate = GridSetting(self.frameOptions, row=14, type_="Checkbox", text="Colorbar Update", unit="", default=1, tooltip=Resource.GetString("tab2/checkColorbar"))
        self.setting_autostart = GridSetting(self.frameOptions, row=20, type_="Checkbox", text="Autostart Detection", default=1)
        tk.Button(self.frameOptions, text="Detect", command=self.Detect).grid(row=21, column=0)

        self.frameSignal = ttk.LabelFrame(self.frame, text="Signal")
        self.frameSignal.grid(row=2, column=0, sticky="new")
        self.setting_peakWidthLeft = GridSetting(self.frameSignal, row=5, text="Peak Width Left", default=3, min_=0, max_=50, scaleMin=0, scaleMax=20, tooltip=Resource.GetString("tab2/peakWidth"))
        self.setting_peakWidthRight = GridSetting(self.frameSignal, row=6, text="Peak Width Right", default=10, min_=0, max_=50, scaleMin=0, scaleMax=20, tooltip=Resource.GetString("tab2/peakWidth"))
        self.setting_peakWidthLeft.var.IntVar.trace_add("write", lambda _1,_2,_3: self._UpdateSignalWidths())
        self.setting_peakWidthRight.var.IntVar.trace_add("write", lambda _1,_2,_3: self._UpdateSignalWidths())

        self.frameSignalPlot = tk.Frame(self.frameSignal)
        self.frameSignalPlot.grid(row=10, column=0, columnspan=4, sticky="news")
        self.figureSignal = plt.Figure(figsize=(3.7,3.7), dpi=100)
        self.axSignal = self.figureSignal.add_subplot()  
        self.canvasSignal = FigureCanvasTkAgg(self.figureSignal, self.frameSignalPlot)
        self.canvtoolbarSignal = NavigationToolbar2Tk(self.canvasSignal,self.frameSignalPlot)
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
        self.canvtoolbar1 = NavigationToolbar2Tk(self.canvas1,self.frameCanvas1)
        self.canvtoolbar1.update()
        self.canvas1.get_tk_widget().pack(fill="both", expand=True)
        self.canvas1.draw()

        tk.Grid.columnconfigure(self.frame, 1, weight=1)
        tk.Grid.rowconfigure(self.frame, 2, weight=1)

    def Update(self, event: TabUpdateEvent):
        if isinstance(event, ImageChangedEvent):
            for algo in self.signalDetectionAlgorithms: algo.Clear()
            if (self.setting_autostart.Get() == 1): 
                self.Detect()
            else:
                self.UpdateFromSignal()
        elif isinstance(event, TabSignal_AlgorithmChangedEvent):
            match(self.radioAlgoVar.get()):
                case "diffMax":
                    self.currentSigDecAlgo = self.signalDetectionAlgorithms[0]
                case "diffStd":
                    self.currentSigDecAlgo = self.signalDetectionAlgorithms[1]
                case _:
                    self.currentSigDecAlgo = ISignalDetectionAlgorithm()
            if (self.setting_autostart.Get() == 1): self.Detect()
        elif isinstance(event, TabSignal_RefindPeaksEvent):
            self._gui.signal.DetectPeaks(self.setting_peakProminence.Get()/100)
            self._gui.SignalChanged()
        elif isinstance(event, SignalChangedEvent):
            self.UpdateFromSignal()

            
    def UpdateFromSignal(self):  
        imgObj = self._gui.ImageObject
        signal = self._gui.signal.signal
        peaks = np.array(self._gui.signal.peaks)
        self.axSignal.clear()
        self.axSignal.set_ylabel("Strength")
        self.axSignal.set_xlabel("Frame")
        self.axSignal.set_title("Signal")

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
        if (self.setting_snapFrames.Get() == 1 and len(peaks) > 0):
            _valstep = peaks + 1
        if (self.setting_originalImage.Get() == 1):
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

        _oldnorm = None
        if self.ax1Image is not None and self.ax1Image.colorbar is not None:
            _oldnorm = self.ax1Image.colorbar.norm
        if self.colorbar is not None:
            self.colorbar.remove()
            self.colorbar = None
    
        for axImg in self.ax1.get_images(): axImg.remove()
        if imgObj is None or imgObj.img is None:
            self.frameSlider.valtext.set_text("")
            return
        else:
            self.frameSlider.valtext.set_text(f"{frame} / {imgObj.img.shape[0]-1}")
        if (self.setting_originalImage.Get() == 1):
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

        if (self.setting_normalize.Get() == 0):
            _vmin = None
            _vmax = None
        if _img is not None:
            self.ax1Image = self.ax1.imshow(_img, vmin=_vmin, vmax=_vmax, cmap=_cmap)
            self.ax1.set_title(_title)
            self.colorbar = self.figure1.colorbar(self.ax1Image, ax=self.ax1)
            if self.setting_colorbarUpdate.Get() == 0:
                self.ax1Image.set_norm(_oldnorm)
        self.canvas1.draw()

    # Data functions 

    def Detect(self):
        if self._gui.ImageObject is None or self._gui.ImageObject.imgDiff is None:
            return False
        self._gui.signal.signal = self.currentSigDecAlgo.GetSignal(self._gui.ImageObject)
        self.Update(TabSignal_RefindPeaksEvent())
    
    def _UpdateSignalWidths(self):
        self._gui.signal.SetPeakWidths(self.setting_peakWidthLeft.Get(), self.setting_peakWidthRight.Get())

    # GUI

    def BtnDown_Click(self, event):
        newval = min(self.frameSlider.valmax, max(self.frameSlider.valmin, self.frameSlider.val - 1))
        if self.frameSlider.active:
            self.frameSlider.set_val(newval)
    
    def BtnUp_Click(self, event):
        newval = min(self.frameSlider.valmax, max(self.frameSlider.valmin, self.frameSlider.val + 1))
        if self.frameSlider.active:
            self.frameSlider.set_val(newval)