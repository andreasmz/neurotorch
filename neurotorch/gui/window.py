import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sys, os, threading
from enum import Enum 
import pickle
import numpy as np
from PIL import Image, ImageSequence, UnidentifiedImageError
import pims
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.widgets import Slider
from matplotlib.patches import Circle
matplotlib.use('TkAgg')
import time

import neurotorch.gui.settings as settings
from neurotorch.utils.image import Img, ImgObj
from neurotorch.utils.signalDetection import Signal
import neurotorch.utils.update as Update
from neurotorch.gui.components import Statusbar
import neurotorch.external.trace_selector_connector as ts_con

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
        self._imgObj = ImgObj()
        self.signal = Signal()
        self.edition = None
        self.pimsObj = None

    def GUI(self, edition:Edition=Edition.NEUROTORCH):
        import neurotorch.gui.tabWelcome as tabWelcome
        import neurotorch.gui.tab1 as tab1
        import neurotorch.gui.tab2 as tab2
        import neurotorch.gui.tab3 as tab3
        self.edition = edition
        self.root = tk.Tk()
        self.SetWindowTitle("")
        self.root.iconbitmap(os.path.join(*[settings.UserSettings.ParentPath, "media", "neurotorch_logo.ico"]))
        #self.root.geometry("600x600")
        self.root.state("zoomed")

        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)
        self.menuFile = tk.Menu(self.menubar,tearoff=0)
        self.menubar.add_cascade(label="File",menu=self.menuFile)
        self.menuFile.add_command(label="Open", command=self.OpenFile)
        self.menuFile.add_command(label="Open noisy image", command=self._OpenFile_DenoiseClick)

        self.menuImage = tk.Menu(self.menubar,tearoff=0)
        self.menubar.add_cascade(label="Image", menu=self.menuImage)
        self.menuImage.add_command(label="Diff Gaussian Filter σ=2", command=self.DiffGaussianFilter)
        self.menuImage.add_command(label="Start Trace Selector", command=self.StartTraceSelector_Click)

        if (edition == Edition.NEUROTORCH):
            from neurotorch.utils.pyimagej import ImageJHandler
            self.ijH = ImageJHandler(self)
            self.ijH.MenubarImageJH(self.menubar)
        
        self.menuNeurotorch = tk.Menu(self.menubar,tearoff=0)
        self.menubar.add_cascade(label="Neurotorch",menu=self.menuNeurotorch)
        self.menuNeurotorch.add_command(label="About", command=self.MenuNeurotorchAbout_Click)
        self.menuNeurotorch.add_command(label="Update", command=self.MenuNeurotorchUpdate_Click)

        self.menuDebug = tk.Menu(self.menubar,tearoff=0)
        self.menubar.add_cascade(label="Debug", menu=self.menuDebug)
        self.menuDebug.add_command(label="Save diffImg peak frames", command=self._Debug_Save_ImgPeaks)
        self.menuDebug.add_command(label="Load diffImg peak frames", command=self._Debug_Load_ImgPeaks)

        """
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
        """
        self.statusbar = Statusbar(self.root, self.root)

        self.tabMain = ttk.Notebook(self.root)
        self.tabWelcome = tabWelcome.TabWelcome(self)
        self.tab1 = tab1.Tab1(self)
        self.tab2 = tab2.Tab2(self)
        self.tab3 = tab3.Tab3(self)
        self.tab4 = ttk.Frame(self.tabMain)
        self.tabMain.add(self.tab4, text="Synapse Analysis")
        self.tabMain.select(self.tab1.tab)

        self.tabMain.pack(expand=1, fill="both")


        self.root.mainloop()

    def GetActiveImageObject(self):
        return self._imgObj
    
    @property
    def ActiveImageObject(self):
        return self._imgObj
    
    @ActiveImageObject.setter
    def ActiveImageObject(self, val: ImgObj):
        self._imgObj = val

    def NewImageProvided(self):
        self.SetWindowTitle(self.IMG.name)
        if self.IMG.img is not None:
            _size = round(sys.getsizeof(self.IMG.img)/(1024**2),2)
            self.lblImgInfo["text"] = f"Image: {self.IMG.img.shape}, dtype={self.IMG.img.dtype}, size = {_size} MB"
        else:
            self.lblImgInfo["text"] = "No image selected"
        self.signal.Clear()
        self.tab1.Update(True)
        self.tab2.Update(True)
        self.tab3.Update(True)

    def SignalChanged(self):
        self.tab2.Update()
        self.tab3.Update()

    def SetWindowTitle(self, text:str=""):
        if (self.edition == Edition.NEUROTORCH_LIGHT):
            self.root.title(f"NeuroTorch Light {text}")
        else:
            self.root.title(f"NeuroTorch {text}")

    def OpenFile(self, denoise=False):
        image_path = filedialog.askopenfilename(parent=self.root, title="Open a Image File", 
                filetypes=(("All compatible files", "*.tif *.tiff *.nd2"), ("TIF File", "*.tif *.tiff"), ("ND2 Files (NIS Elements)", "*.nd2"), ("All files", "*.*")) )
        file_name = os.path.splitext(os.path.basename(image_path))[0]
        if image_path is None or image_path == "":
            return
        """if image_path.lower().endswith(".tif") or image_path.lower().endswith(".tiff"):
            try:
                img = Image.open(image_path)
            except FileNotFoundError:
                self.root.bell()
                return
            except UnidentifiedImageError:
                messagebox.showerror("Neurotorch", "The file provided is not a supported image")
                return
            imgNP = np.array([np.array(frame) for frame in ImageSequence.Iterator(img)])    
        elif image_path.lower().endswith(".nd2"):
            try:
                pimsImg = pims.open(image_path)
            except FileNotFoundError:
                self.root.bell()
                return
            except Exception:
                messagebox.showerror("Neurotorch", "The nd2 file can't be opened")
                return
            imgNP = np.array(pimsImg)"""
        _time = time.time()
        print("Start opening Image")
        try:
            _pimsImg = pims.open(image_path)
        except FileNotFoundError:
            self.root.bell()
            return
        except Exception:
            messagebox.showerror("Neurotorch", "The given image file is not supported")
            return
        print(round(time.time() - _time, 3), "s", "PIMS opening")
        imgNP = np.array([np.array(_pimsImg[i]) for i in range(_pimsImg.shape[0])])    
        print(round(time.time() - _time, 3), "s", "NP array")
        if len(imgNP.shape) != 3:
            messagebox.showerror("Neurotorch", "The image must contain 3 dimensions: Time, Y, X. This is with your image not the case")
            return
        self.pimsObj = _pimsImg
        self.IMG.SetIMG(imgNP, file_name, denoise)
        print(round(time.time() - _time, 3), "s", "Set image")
        self.NewImageProvided()
        print(round(time.time() - _time, 3), "s", "Finished")

    def DiffGaussianFilter(self):
        if self.IMG.img is None:
            self.root.bell()
            return
        self.IMG.CalcDiff(denoise=True)
        self.IMG.CalcDiffMax()
        self.NewImageProvided()

    def MenuNeurotorchAbout_Click(self):
        Update.Updater.CheckForUpdate()
        _strUpdate = ""
        _github_version = Update.Updater.version_github
        _local_version = Update.Updater.version
        if _github_version is not None:
            if _local_version == _github_version:
                _strUpdate = " (newest version)"
            else:
                _strUpdate = f" (version {_github_version} available for download)"
        messagebox.showinfo("Neurotorch", f"© Andreas Brilka 2024\nYou are running Neurotorch {_local_version}{_strUpdate}")

    def MenuNeurotorchUpdate_Click(self):
        Update.Updater.CheckForUpdate()
        _github_version = Update.Updater.version_github
        _local_version = Update.Updater.version
        if _github_version is None:
            messagebox.showerror("Neurotorch", f"The server can't be contacted to check for an update. Please try again later")
            return
        if _local_version == _github_version:
            messagebox.showinfo("Neurotorch", f"You are running the newest version")
            return
        if not messagebox.askyesno("Neurotorch", f"Version {_github_version} is available for download (You have {_local_version}). Do you want to update?"):
            return
        Update.Updater.DownloadUpdate()

    def StartTraceSelector_Click(self):
        if messagebox.askokcancel("Neurotorch", "This is currently an experimental feature. Are you sure you want to continue?"):
            ts_con.StartTraceSelector()

    def _OpenFile_DenoiseClick(self):
        self.OpenFile(denoise=True)

    def _Debug_Load_Img(self):
        savePath = os.path.join(settings.UserSettings.UserPath, "img.dump")
        if not os.path.exists(savePath):
            self.root.bell()
            return
        with open(savePath, 'rb') as intp:
            self.IMG.SetIMG(pickle.load(intp), name= "img.dump")
        self.NewImageProvided()

    def _Debug_Load_ImgPeaks(self):
   
        savePath = os.path.join(settings.UserSettings.UserPath, "img_peaks.dump")
        if not os.path.exists(savePath):
            self.root.bell()
            return
        with open(savePath, 'rb') as intp:
            _img = pickle.load(intp)
            self.IMG.SetIMG(_img, name= "img_peaks.dump")
            self.ActiveImageObject = ImgObj()
            self.ActiveImageObject.SetImage_Precompute(_img)
        self.NewImageProvided()

    def _Debug_Save_ImgPeaks(self):
        if self.IMG.img is None or self.IMG.imgDiff is None or self.signal.peaks is None or len(self.signal.peaks) == 0:
            self.root.bell()
            return
        _peaksExtended = []
        for p in self.signal.peaks:
            if p != 0 and p < (self.IMG.img.shape[0] - 1):
                if len(_peaksExtended) == 0:
                    _peaksExtended.extend([int(p-1),int(p),int(p+1)])
                else:
                    _peaksExtended.extend([int(p),int(p+1)])
            else:
                print(f"Skipped peak {p} as it is to near to the edge")
        _peaksExtended.extend([int(p+2)])
        if not messagebox.askyesnocancel("Neurotorch", "Do you want to save the current diffImg Peak Frames in a Dump?"):
            return
        print("Exported frames", _peaksExtended)
        savePath = os.path.join(settings.UserSettings.UserPath, "img_peaks.dump")
        with open(savePath, 'wb') as intp:
            pickle.dump(self.IMG.img[_peaksExtended, :, :], intp, protocol=pickle.HIGHEST_PROTOCOL)


GUI = _GUI()