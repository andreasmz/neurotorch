import neurotorch.gui.window as window

import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.widgets as PltWidget
from matplotlib.patches import Circle

class Tab2():
    def __init__(self, gui: window._GUI):
        self._gui = gui
        self.root = gui.root
        self.frameSlider = None
        self.ax1_imshow = None
        self.Init()

    def Init(self):
        self.tab = ttk.Frame(self._gui.tabMain)
        self._gui.tabMain.add(self.tab, text="Signal")

        self.frame = tk.Frame(self.tab)
        self.frame.pack(side=tk.LEFT, fill="both", expand=True)
        self.frameOptions = ttk.LabelFrame(self.frame, text="Options")
        self.frameOptions.grid(row=0, column=0, sticky="news")
        self.frameAlgorithm = tk.Frame(self.frameOptions)
        self.frameAlgorithm.pack(anchor=tk.W)
        self.lblAlgorithm = tk.Label(self.frameAlgorithm, text="Algorithm:")
        self.lblAlgorithm.pack(side=tk.LEFT)
        self.radioAlgoVar = tk.StringVar(value="diffMax")
        self.radioAlgo1 = tk.Radiobutton(self.frameAlgorithm, variable=self.radioAlgoVar, indicatoron=False, text="DiffMax", value="diffMax", command=self._AlgoChanged)
        self.radioAlgo2 = tk.Radiobutton(self.frameAlgorithm, variable=self.radioAlgoVar, indicatoron=False, text="DiffStd", value="diffStd", command=self._AlgoChanged)
        self.radioAlgo1.pack(side=tk.LEFT)
        self.radioAlgo2.pack(side=tk.LEFT)
        self.checkSnapPeaksVar = tk.IntVar(value=1)
        self.checkSnapPeaks = tk.Checkbutton(self.frameOptions, text="Snap frames to peaks", variable=self.checkSnapPeaksVar, command=self._IntSliderChanged)
        self.checkSnapPeaks.pack(anchor=tk.W)
        self.checkNormalizeImgVar = tk.IntVar(value=1)
        self.checkNormalizeImg = tk.Checkbutton(self.frameOptions, text="Normalize", variable=self.checkNormalizeImgVar, command=self._IntSliderChanged)
        self.checkNormalizeImg.pack(anchor=tk.W)
        self.checkShownOriginalImgVar = tk.IntVar(value=0)
        self.checkShownOriginalImg = tk.Checkbutton(self.frameOptions, text="Show originmal image", variable=self.checkShownOriginalImgVar, command=self._IntSliderChanged)
        self.checkShownOriginalImg.pack(anchor=tk.W)
        self.frameProminence = tk.Frame(self.frameOptions)
        self.frameProminence.pack(anchor=tk.W)
        tk.Label(self.frameProminence, text="Peak Prominence:").pack(side=tk.LEFT)
        self.sliderProminenceFactorVar = tk.DoubleVar(value=0.5)
        self.sliderProminenceFactor = tk.Scale(self.frameProminence, from_=0.1, to=0.9, orient="horizontal", variable=self.sliderProminenceFactorVar, resolution=0.05, length=100, command=self._AlgoChanged)
        self.sliderProminenceFactor.pack(side=tk.LEFT)

        self.frameSignal = ttk.LabelFrame(self.frame, text="Image")
        self.frameSignal.grid(row=1, column=0, sticky="new")
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
        
        self.frameCanvas1 = tk.Frame(self.frame)
        self.frameCanvas1.grid(row=0, column=1, rowspan=2, sticky="news")
        self.canvas1 = FigureCanvasTkAgg(self.figure1, self.frameCanvas1)
        #self.canvas1.get_tk_widget().grid(row=0, column=1, rowspan=2, sticky="news")
        self.canvtoolbar1 = NavigationToolbar2Tk(self.canvas1,self.frameCanvas1)
        self.canvtoolbar1.update()
        self.canvas1.get_tk_widget().pack(fill="both", expand=True)
        self.canvas1.draw()


        tk.Grid.columnconfigure(self.frame, 1, weight=1)
        tk.Grid.rowconfigure(self.frame, 1, weight=1)

        self.Update()

    def Update(self, newImage=False):
        if newImage:
            self.ax1.clear()
            self.ax1_imshow = None
        self.axSignal.clear()
        self.axSignal.set_ylabel("Strength")
        self.axSignal.set_xlabel("Frame")
        self.figureSignal.tight_layout()

        self.ax1_slider1.clear()
        self.ax1_slider1.set_axis_off()

        if self._gui.signal.signal is not None:
            self.axSignal.plot(self._gui.signal.signal)
            self.axSignal.scatter(self._gui.signal.peaks, self._gui.signal.signal[self._gui.signal.peaks], c="orange")
            _valstep = 1
            _min = 1
            if (self.checkSnapPeaksVar.get() == 1 and len(self._gui.signal.peaks) > 0):
                _valstep =self._gui.signal.peaks + 1
            if (self.checkShownOriginalImgVar.get() == 1):
                _min = 0

            self.frameSlider = PltWidget.Slider(self.ax1_slider1, 'Frame', _min, self._gui.IMG.img.shape[0]-1, valstep=_valstep)
            self.frameSlider.on_changed(self._UpdateFrameSlider)
            self.ax1_btnDown = PltWidget.Button(self.ax1_axbtnDown, '<-')
            self.ax1_btnUp = PltWidget.Button(self.ax1_axbtnUp, '->')
            self.ax1_btnDown.on_clicked(self._BtnDown)
            self.ax1_btnUp.on_clicked(self._BtnUp)
            self._UpdateFrameSlider(self.frameSlider.val)
        else:
            self.frameSlider = None
            self.canvas1.draw()
        self.canvasSignal.draw()

    def _UpdateFrameSlider(self, val):
        if (self.ax1_imshow is not None):
            self.ax1_imshow.remove()
            self.ax1_imshow = None
        if self.frameSlider is None or self._gui.IMG.imgDiff is None:
            return
        frame = self.frameSlider.val
        self.frameSlider.valtext.set_text(f"{frame} / {self._gui.IMG.img.shape[0]-1}")
        if (self.checkShownOriginalImgVar.get() == 1):
            _img = self._gui.IMG.img[frame,:,:]
            _vmin = self._gui.IMG.img_Stats["ClipMin"]
            _vmax = self._gui.IMG.img_Stats["Max"]
            _cmap = "Greys_r"
            _title = ""
        else:
            frame -= 1
            _img = self._gui.IMG.imgDiff[frame,:,:]
            _vmin = self._gui.IMG.imgDiff_Stats["ClipMin"]
            _vmax = self._gui.IMG.imgDiff_Stats["Max"]
            _cmap = "inferno"
            _title = "Diff Image"

        if (self.checkNormalizeImgVar.get() == 0):
            _vmin = None
            _vmax = None
        self.ax1_imshow = self.ax1.imshow(_img, vmin=_vmin, vmax=_vmax, cmap=_cmap)
        self.ax1.set_title(_title)
        self.canvas1.draw()

        #if (self.checkNormalizeImgVar.get() == 1):
        #    self.ax1_imshow = self.ax1.imshow(self._gui.IMG.imgDiff[frame,:,:], vmin=self._gui.IMG.imgDiff_Stats["ClipMin"], vmax=self._gui.IMG.imgDiff_Stats["Max"], cmap="Greys_r")
        #else:
        #    self.ax1_imshow = self.ax1.imshow(self._gui.IMG.imgDiff[frame,:,:])  

    def _AlgoChanged(self, val=0):
        if (self._gui.IMG.imgDiff is None):
            return
        self._gui.signal.DetectSignal(self.radioAlgoVar.get(), self.sliderProminenceFactorVar.get())
        self._gui.SignalChanged()


    def _IntSliderChanged(self):
        self.Update()

    def _BtnDown(self, event):
        newval = min(self.frameSlider.valmax, max(self.frameSlider.valmin, self.frameSlider.val - 1))
        self.frameSlider.set_val(newval)
    
    def _BtnUp(self, event):
        newval = min(self.frameSlider.valmax, max(self.frameSlider.valmin, self.frameSlider.val + 1))
        self.frameSlider.set_val(newval)