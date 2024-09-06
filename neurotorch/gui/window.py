import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sys, os, threading
from enum import Enum 
import pickle
import numpy as np
from PIL import Image, ImageSequence, UnidentifiedImageError
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.widgets import Slider
from matplotlib.patches import Circle
matplotlib.use('TkAgg')

import neurotorch.gui.settings as settings
from neurotorch.utils.image import Img
from neurotorch.utils.signalDetection import Signal

class Edition(Enum):
    NEUROTORCH = 1
    NEUROTORCH_LIGHT = 2

class _GUI:
    def __init__(self):
        self.root = None
        self.menubar = None
        self.IMG = Img()
        self.ij = None
        self.ijH = None
        self.signal = Signal(self.IMG)

    def GUI(self, edition:Edition=Edition.NEUROTORCH):
        import neurotorch.gui.tab1 as tab1
        import neurotorch.gui.tab2 as tab2
        import neurotorch.gui.tab3 as tab3
        self.root = tk.Tk()
        if (edition == Edition.NEUROTORCH_LIGHT):
            self.root.title("NeuroTorch Light")
        else:
            self.root.title("NeuroTorch")
        self.root.iconbitmap(os.path.join(*[settings.UserSettings.ParentPath, "media", "neurotorch_logo.ico"]))
        self.root.geometry("600x600")

        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)
        self.menuFile = tk.Menu(self.menubar,tearoff=0)
        self.menubar.add_cascade(label="File",menu=self.menuFile)
        self.menuFile.add_command(label="Open", command=self.OpenFile)
        self.menuFile.add_command(label="Open Dump", command=self._Debug_Load)

        if (edition == Edition.NEUROTORCH):
            from neurotorch.utils.pyimagej import ImageJHandler
            self.ijH = ImageJHandler(self)
            self.ijH.MenubarImageJH(self.menubar)
        

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
        self.tab1 = tab1.Tab1(self)
        self.tab2 = tab2.Tab2(self)
        self.tab3 = tab3.Tab3(self)
        self.tab4 = ttk.Frame(self.tabMain)
        self.tabMain.add(self.tab4, text="Synapse Analysis")

        self.tabMain.pack(expand=1, fill="both")


        self.root.mainloop()

    def NewImageProvided(self):
        self.signal.DetectSignal(self.tab2.radioAlgoVar.get(), self.tab2.sliderProminenceFactorVar.get())
        self.tab1.Update(True)
        self.tab2.Update(True)
        self.tab3.Update(True)

    def SignalChanged(self):
        self.tab2.Update()
        self.tab3.Update()

    def OpenFile(self):
        image_path = filedialog.askopenfilename(parent=self.root, title="Open a Image File", 
                filetypes=(("TIF File", "*.tif"), ("All files", "*.*")))
        if image_path is None or image_path == "":
            return
        try:
            img = Image.open(image_path)
        except FileNotFoundError:
            self.root.bell()
            return
        except UnidentifiedImageError:
            messagebox.showerror("Neurotorch", "The file provided is not a supported image")
            return
        imgNP = np.array([np.array(frame) for frame in ImageSequence.Iterator(img)])    
        if len(imgNP.shape) != 3:
            messagebox.showerror("Neurotorch", "The image must contain 3 dimensions: Time, Y, X. This is with your image not the case")
            return
        self.IMG.SetIMG(imgNP)
        self.NewImageProvided()

    def _Debug_Load(self):
        savePath = os.path.join(settings.UserSettings.UserPath, "img.dump")
        if not os.path.exists(savePath):
            self.root.bell()
            return
        with open(savePath, 'rb') as intp:
            self.IMG.SetIMG(pickle.load(intp))
        _size = round(sys.getsizeof(self.IMG.img)/(1024**2),2)
        self.lblImgInfo["text"] = f"Image: {self.IMG.img.shape}, dtype={self.IMG.img.dtype}, size = {_size} MB"
        self.NewImageProvided()


GUI = _GUI()