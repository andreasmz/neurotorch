import tkinter as tk
from tkinter import ttk, messagebox
import sys, os, threading
import pickle
from scyjava import jimport
import imagej
import numpy as np
import xarray
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.widgets import Slider
from matplotlib.patches import Circle
matplotlib.use('TkAgg')

import neurotorch.gui.settings as settings
from neurotorch.utils.image import Img
from neurotorch.utils.detection import ROIImage

class _GUI:

    def __init__(self):
        self.root = None
        self.menubar = None
        self.IMG = Img()
        self.ROI_IMG = ROIImage()
        self.ij = None

    def GUI(self):
        self.root = tk.Tk()
        self.root.title("NeuroTorch")
        self.root.iconbitmap(os.path.join(*[settings.UserSettings.ParentPath, "gui", "media", "neurotorch_logo.ico"]))
        self.root.geometry("600x600")

        self.ijH = ImageJHandler(self)

        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)
        self.menuFile = tk.Menu(self.menubar,tearoff=0)
        self.menubar.add_cascade(label="File",menu=self.menuFile)
        self.menuImageJ = tk.Menu(self.menubar,tearoff=0)
        self.menubar.add_cascade(label="ImageJ",menu=self.menuImageJ)

        self.menuFile.add_command(label="Open", state="disabled")
        self.menuFile.add_command(label="Open Dump", command=self._Debug_Load)
        self.menuImageJ.add_command(label="Start ImageJ", command=self.ijH.StartImageJ)
        self.menuImageJ.add_command(label="Read Image from ImageJ", state="disabled", command=self.ijH.LoadImage)
        self.menuImageJ.add_separator()
        self.menuImageJ.add_command(label="DiffImg --> ImageJ", state="disabled", command=self.ijH.ImageJImport_ImgDiff)

        self.statusFrame = tk.Frame(self.root)
        self.statusFrame.pack(side=tk.BOTTOM, fill="x", expand=False)
        self.varProgMain = tk.DoubleVar()
        self.progMain = ttk.Progressbar(self.statusFrame,orient="horizontal", length=200, variable=self.varProgMain)
        self.progMain.pack(side=tk.LEFT)
        self.lblProgMain = tk.Label(self.statusFrame, text="", relief=tk.SUNKEN,borderwidth=1)
        self.lblProgMain.pack(side=tk.LEFT, padx=(10,10))
        self.lblImgInfo = tk.Label(self.statusFrame, text="No image selected",borderwidth=1, relief=tk.SUNKEN)
        self.lblImgInfo.pack(side=tk.LEFT, padx=(10, 10))
        self.lblStatusInfo = tk.Label(self.statusFrame, text="", borderwidth=1, relief=tk.SUNKEN)
        self.lblStatusInfo.pack(side=tk.LEFT, padx=(10, 10))

        self.tabMain = ttk.Notebook(self.root)
        self.tab1 = Tab1(self)
        self.tab2 = Tab2(self)
        self.tab3 = ttk.Frame(self.tabMain)
        self.tabMain.add(self.tab3, text="Synapse Analysis")
        self.tabMain.pack(expand=1, fill="both")


        self.root.mainloop()

    def NewImageProvided(self):
        self.tab1.Update()

    def _Debug_Load(self):
        savePath = os.path.join(settings.UserSettings.UserPath, "img.dump")
        with open(savePath, 'rb') as intp:
            self.IMG.SetIMG(pickle.load(intp))
        _size = round(sys.getsizeof(self.IMG.img)/(1024**2),2)
        #self.lblImgInfo["text"] = f"Image: {self.IMG.img.shape}, dtype={self.IMG.img.dtype}, size = {_size} MB"
        self.tab1.Update()

class ImageJHandler:
    def __init__(self, gui: _GUI):
        self._gui = gui
        self.root = gui.root
        self.IMG = gui.IMG
        self.imageJReady = False
        self.ij_load = False
        self.OvalRoi = None

    def LoadImage(self):
        if self._gui.ij is None:
            messagebox.showerror("Glutamate Roi Finder", "Please first start ImageJ")
            return
        self._img = self._gui.ij.py.active_xarray()
        if self._img is None:
            self._gui.lblStatusInfo["text"] = "Please first select an image in ImageJ"
            return
        self._gui.lblStatusInfo["text"] = ""
        
        self._img = np.array(self._img).astype("int16")
        if not self.IMG.SetIMG(self._img):
            self._gui.lblStatusInfo["text"] = "Your image has an invalid shape"
            return

        _size = round(sys.getsizeof(self.IMG.img)/(1024**2),2)
        self._gui.lblImgInfo["text"] = f"Image: {self.IMG.img.shape}, dtype={self.IMG.img.dtype}, size = {_size} MB"
        self._gui.NewImageProvided()

    def ImageJImport_ImgDiff(self):
        if self._gui.ij is None:
            messagebox.showerror("Glutamate Roi Finder", "Please first start ImageJ")
            return
        xDiffImg = xarray.DataArray(self.IMG.imgDiff, name="diffImg", dims=("t", "y", "x"))
        javaDiffImg = self._gui.ij.py.to_java(xDiffImg)

    def StartImageJ(self):
        if (not os.path.exists(settings.UserSettings.imageJPath)):
            messagebox.showerror("Glutamate Roi Finder", "The given ImageJ path doesn't exist")
            return

        self._gui.lblProgMain["text"] = "Starting ImageJ..."
        self._gui.menuImageJ.entryconfig("Start ImageJ", state="disabled")

        self.ij_load = True
        def _ProgStartingImgJ_Step():
            self._gui.progMain.step(10)
            if self.ij_load is True:
                self.root.after(50, _ProgStartingImgJ_Step)
            else:
                self._gui.progMain.configure(mode="determinate")
                self._gui.varProgMain.set(0)
                self._gui.lblProgMain["text"] = ""

        self._gui.progMain.configure(mode="indeterminate")
        _ProgStartingImgJ_Step()
        
        self.ijthread = threading.Thread(target=self._StartImageJ)
        self.ijthread.start()

    def _StartImageJ(self):
        if (self.imageJReady or not self.ij_load):
            self.ij_load = False
            return
        self._gui.ij = imagej.init(settings.UserSettings.imageJPath, mode='interactive')
        #self.RM = jimport("ij.plugin.frame.RoiManager")
        self.OvalRoi = jimport('ij.gui.OvalRoi')
        self.ij_load = False
        self._gui.ij.ui().showUI()
        self._ImageJReady()

    def _ImageJReady(self):
        self._gui.menuImageJ.entryconfig("Read Image from ImageJ", state="normal")
        self._gui.menuImageJ.entryconfig("DiffImg --> ImageJ", state="normal")


class Tab1():
    def __init__(self, gui: _GUI):
        self._gui = gui
        self.root = gui.root
        self.imshow = None
        self.Init()

    def Init(self):
        self.tab = ttk.Frame(self._gui.tabMain)
        self._gui.tabMain.add(self.tab, text="Image")

        self.frameDisplay = tk.Frame(self.tab)
        self.radioDisplayVar = tk.StringVar(value="img")
        self.radioDisplay1 = tk.Radiobutton(self.frameDisplay, variable=self.radioDisplayVar, indicatoron=False, command=self.Update, text="Image", value="img")
        self.radioDisplay2 = tk.Radiobutton(self.frameDisplay, variable=self.radioDisplayVar, indicatoron=False, command=self.Update, text="Derivative Maximum", value="diffMax")
        self.radioDisplay3 = tk.Radiobutton(self.frameDisplay, variable=self.radioDisplayVar, indicatoron=False, command=self.Update, text="Derivative Maximum 3D", value="diffMax3D")
        self.radioDisplay1.grid(row=0, column=0)
        self.radioDisplay2.grid(row=0, column=1)
        self.radioDisplay3.grid(row=0, column=2)
        self.frameDisplay.pack()

        self.figure1 = plt.Figure(figsize=(6,6), dpi=100)
        self.figure1.tight_layout()
        self.ax = self.figure1.add_subplot()  
        self.ax.set_axis_off()
        #self.ax3D = self.figure1.add_subplot(projection="3d")
        #self.ax3D.set_visible(False)
        
        self.canvas = FigureCanvasTkAgg(self.figure1, self.tab)
        self.canvtoolbar = NavigationToolbar2Tk(self.canvas,self.tab)
        self.canvtoolbar.update()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self.canvas.draw()

    def Update(self):
        _selected = self.radioDisplayVar.get()
        if (_selected == "img"):
            self.ax.set_visible(True)
            #self.ax3D.set_visible(False)
            if self._gui.IMG.img is not None:
                self.ax.set_axis_on()
                if (self.imshow is not None):
                    self.imshow.remove()
                    self.imshow = None
                self.imshow = self.ax.imshow(self._gui.IMG.img[0,:,:])
            else:
                self.ax.set_axis_off()
        elif (_selected == "diffMax"):
            self.ax.set_visible(True)
            #self.ax3D.set_visible(False)
            if self._gui.IMG.imgDiffMaxTime is not None:
                self.ax.set_axis_on()
                if (self.imshow is not None):
                    self.imshow.remove()
                    self.imshow = None
                self.imshow = self.ax.imshow(self._gui.IMG.imgDiffMaxTime)
            else:
                self.ax.set_axis_off()
        elif (_selected == "diffMax3D"):
            return
            self.ax.set_visible(False)
            self.ax3D.set_visible(True)
            if self._gui.IMG.imgDiffMaxTime is not None:
                X = np.arange(0,self._gui.IMG.imgDiffMaxTime.shape[0])
                Y = np.arange(0,self._gui.IMG.imgDiffMaxTime.shape[1])
                X, Y = np.meshgrid(X, Y)
                self.ax3D.plot_surface(X,Y, self._gui.IMG.imgDiffMaxTime, cmap=cm.coolwarm)

            else:
                self.ax.set_axis_off()
        else:
            self.ax.set_axis_off()
        self.canvas.draw()

class Tab2():
    def __init__(self, gui: _GUI):
        self._gui = gui
        self.root = gui.root
        self.Init()

    def Init(self):
        self.tab = ttk.Frame(self._gui.tabMain)
        self._gui.tabMain.add(self.tab, text="Synapse ROI Finder")

        self.figure1 = plt.Figure(figsize=(6,6), dpi=100)
        self.figure1.tight_layout()
        self.ax = self.figure1.add_subplot()  
        self.ax.set_axis_off()
        
        self.canvas = FigureCanvasTkAgg(self.figure1, self.tab)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self.canvas.draw()

    def Update():
        pass

GUI = _GUI()