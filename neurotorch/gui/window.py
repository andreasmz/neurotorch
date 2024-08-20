import tkinter as tk
from tkinter import ttk
import sys, os
import pickle
import numpy as np
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

    def GUI(self):
        self.root = tk.Tk()
        self.root.title("NeuroTorch")
        self.root.iconbitmap(os.path.join(*[settings.UserSettings.ParentPath, "gui", "media", "neurotorch_logo.ico"]))
        self.root.geometry("600x600")

        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)
        self.menuFile = tk.Menu(self.menubar,tearoff=0)
        self.menubar.add_cascade(label="File",menu=self.menuFile)

        self.menuFile.add_command(label="Open")
        self.menuFile.add_command(label="Open Dump", command=self._Debug_Load)

        self.tabMain = ttk.Notebook(self.root)
        self.tab1 = Tab1(self)
        self.tab2 = ttk.Frame(self.tabMain)
        self.tab3 = ttk.Frame(self.tabMain)
        self.tabMain.add(self.tab2, text="Synapse ROI Finder")
        self.tabMain.add(self.tab3, text="Synapse Analysis")
        self.tabMain.pack(expand=1, fill="both")

        self.root.mainloop()


    def _Debug_Load(self):
        savePath = os.path.join(settings.UserSettings.UserPath, "img.dump")
        with open(savePath, 'rb') as intp:
            self.IMG.img = pickle.load(intp)
            self.IMG.ImgProvided()
        _size = round(sys.getsizeof(self.IMG.img)/(1024**2),2)
        #self.lblImgInfo["text"] = f"Image: {self.IMG.img.shape}, dtype={self.IMG.img.dtype}, size = {_size} MB"
        self.tab1.Update()

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
        self.radioDisplay1.grid(row=0, column=0)
        self.radioDisplay2.grid(row=0, column=1)
        self.frameDisplay.pack()

        self.figure1 = plt.Figure(figsize=(6,6), dpi=100)
        self.figure1.tight_layout()
        self.ax = self.figure1.add_subplot()  
        self.ax.set_axis_off()
        
        self.canvas = FigureCanvasTkAgg(self.figure1, self.tab)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self.canvtoolbar = NavigationToolbar2Tk(self.canvas,self.root)
        self.canvtoolbar.update()
        self.canvas.draw()

    def Update(self):
        if (self.radioDisplayVar.get() == "img"):
            if self._gui.IMG.CheckImg():
                self.ax.set_axis_on()
                if (self.imshow is not None):
                    self.imshow.remove()
                    self.imshow = None
                self.imshow = self.ax.imshow(self._gui.IMG.img[0,:,:])
            else:
                self.ax.set_axis_off()
        elif (self.radioDisplayVar.get() == "diffMax"):
            if self._gui.IMG.CheckImgDiff():
                self.ax.set_axis_on()
                if (self.imshow is not None):
                    self.imshow.remove()
                    self.imshow = None
                self.imshow = self.ax.imshow(self._gui.IMG.imgDiffMaxTime)
            else:
                self.ax.set_axis_off()
        else:
            self.ax.set_axis_off()
        self.canvas.draw()

GUI = _GUI()