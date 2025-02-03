"""
    Main module to initialize the Neurotorch GUI.
"""
import sys, os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tktooltip import ToolTip
import threading
import pickle
from typing import Literal
import logging
import matplotlib
matplotlib.use('TkAgg')

from .components.general import Job, Statusbar
from .edition import Edition
from .settings import (Neurotorch_Settings as Settings, Neurotorch_Resources as Resource)
from ..utils.image import ImgObj
from ..utils.signalDetection import SignalObj
from ..utils.logger import logger


class Neurotorch_GUI:
    def __init__(self, version):
        self._version_ = version
        self.root = None
        self.tabs : dict[type: Tab] = {}
        self._imgObj = None
        self.signal = SignalObj(self.GetImageObject)
        self.ijH = None

    def GUI(self, edition:Edition=Edition.NEUROTORCH):
        from neurotorchmz.gui.tabWelcome import TabWelcome
        from neurotorchmz.gui.tab1 import TabImage
        from neurotorchmz.gui.tab2 import TabSignal
        from neurotorchmz.gui.tab3 import TabROIFinder
        from neurotorchmz.gui.tabAnalysis import TabAnalysis
        from ..utils.plugin_manager import PluginManager
        self.edition = edition
        self.root = tk.Tk()
        self.SetWindowTitle("")
        try:
            self.root.iconbitmap(os.path.join(*[Settings.ParentPath, "media", "neurotorch_logo.ico"]))
        except:
            pass
        self.root.geometry("600x600")
        self.root.state("zoomed")
        self.statusbar = Statusbar(self.root, self.root)

        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)
        self.menuFile = tk.Menu(self.menubar,tearoff=0)
        self.menubar.add_cascade(label="File",menu=self.menuFile)
        self.menuFile.add_command(label="Open", command=self.MenuFileOpen)
        self.menuFile.add_command(label="Open noisy image", command=lambda: self.MenuFileOpen(noisy=True))
        self.menuFile.add_command(label="Close image", command=self.MenuFileClose)

        self.menuImage = tk.Menu(self.menubar,tearoff=0)
        self.menubar.add_cascade(label="Image", menu=self.menuImage)
        self.menuDenoise = tk.Menu(self.menuImage,tearoff=0)
        self.menuImage.add_cascade(label="Denoise imgDiff", menu=self.menuDenoise)
        self.menuDenoise.add_command(label="Disable denoising", command=lambda: self.MenuImageDenoise(None, None))
        self.menuDenoise.add_command(label="Clear cache", command=self.MenuImage_ClearCache)
        self.menuDenoise.add_separator()
        self.menuDenoise.add_command(label="Gaussian kernel (σ=0.5)", command=lambda: self.MenuImageDenoise('Gaussian', (0.5,)))
        self.menuDenoise.add_command(label="Gaussian kernel (σ=0.8)", command=lambda: self.MenuImageDenoise('Gaussian', (0.8,)))
        self.menuDenoise.add_command(label="Gaussian kernel (σ=1)", command=lambda: self.MenuImageDenoise('Gaussian', (1,)))
        self.menuDenoise.add_command(label="Gaussian kernel (σ=1.5)", command=lambda: self.MenuImageDenoise('Gaussian', (1.5,)))
        self.menuDenoise.add_command(label="Gaussian kernel (σ=2, recommended)", command=lambda: self.MenuImageDenoise('Gaussian', (2,)))
        self.menuDenoise.add_command(label="Gaussian kernel (σ=2.5)", command=lambda: self.MenuImageDenoise('Gaussian', (2.5,)))
        self.menuDenoise.add_command(label="Gaussian kernel (σ=3)", command=lambda: self.MenuImageDenoise('Gaussian', (3,)))
        self.menuDenoise.add_command(label="Gaussian kernel (σ=5)", command=lambda: self.MenuImageDenoise('Gaussian', (5,)))

        self.menuFilter = tk.Menu(self.menuImage,tearoff=0)
        self.menuImage.add_cascade(label="Apply filter", menu=self.menuFilter)
        self.menuFilter.add_command(label="Disable filter", command=lambda: self.MenuImageDenoise(None, None))
        self.menuFilter.add_command(label="Clear cache", command=self.MenuImage_ClearCache)
        self.menuFilter.add_separator()
        self.menuFilter.add_command(label="Cummulative imgDiff", command=lambda: self.MenuImageDenoise('MeanMaxDiff', None))
        ToolTip(self.menuFile, msg=Resource.GetString("menubar/filters/meanMaxDiff"), follow=True, delay=0.5)

        if edition == Edition.NEUROTORCH_DEBUG:
            self.menuDenoiseImg = tk.Menu(self.menuImage,tearoff=0)
            self.menuImage.add_cascade(label="Denoise Image", menu=self.menuDenoiseImg)
            self.menuDenoiseImg.add_command(label="On", command=lambda:self.MenuImageDenoiseImg(True))
            self.menuDenoiseImg.add_command(label="Off", command=lambda:self.MenuImageDenoiseImg(False))

        if (edition != Edition.NEUROTORCH_LIGHT):
            from neurotorchmz.utils.pyimagej import ImageJHandler
            self.ijH = ImageJHandler(self)
            self.ijH.MenubarImageJH(self.menubar)

        self.menuPlugins = tk.Menu(self.menubar,tearoff=0)
        self.menubar.add_cascade(label="Plugins",menu=self.menuPlugins)
        
        self.menuNeurotorch = tk.Menu(self.menubar,tearoff=0)
        self.menubar.add_cascade(label="Neurotorch",menu=self.menuNeurotorch)
        self.menuNeurotorch.add_command(label="About", command=self.MenuNeurotorchAbout)

        self.menuDebug = tk.Menu(self.menubar,tearoff=0)
        if edition == Edition.NEUROTORCH_DEBUG:
            self.menubar.add_cascade(label="Debug", menu=self.menuDebug)
        self.menuDebug.add_command(label="Activate debugging to console", command=self.MenuDebug_EnableDebugging)    
        self.menuDebug.add_command(label="Save diffImg peak frames", command=self.MenuDebugSavePeaks)
        self.menuDebug.add_command(label="Load diffImg peak frames", command=self.MenuDebugLoadPeaks)

        self.tabMain = ttk.Notebook(self.root)
        self.tabs[TabWelcome] = TabWelcome(self)
        self.tabs[TabImage] = TabImage(self)
        self.tabs[TabSignal] = TabSignal(self)
        self.tabs[TabROIFinder] = TabROIFinder(self)
        if edition == Edition.NEUROTORCH_DEBUG:
            self.tabs[TabAnalysis] = TabAnalysis(self)
        for t in self.tabs.values(): t.Init()
        self.tabMain.select(self.tabs[TabImage].tab)

        self.plugin_mng = PluginManager(self)

        self.root.protocol("WM_DELETE_WINDOW", self.OnClosing)
        self.tabMain.pack(expand=1, fill="both")
        self.root.mainloop()

    # Image Object functions and properties
    @property
    def ImageObject(self) -> ImgObj | None:
        """
            Returns the active ImgObj or None if not ImgObj is opened or selected
        """
        return self._imgObj
    
    @ImageObject.setter
    def ImageObject(self, val: ImgObj):
        """
            Sets the active ImgObj and calls each tab to update
        """
        self._imgObj = val
        self.signal.Clear()
        self.NewImageProvided()

    def GetImageObject(self):
        """
            Sometimes it may be necessary to pass an pointer to the current image object, as the object itself may be replaced.
            For this, this function can be passed to archieve the exact same behaviour.
        """
        return self._imgObj   
    
    def NewImageProvided(self):
        def _Update(job: Job):
            job.SetProgress(0, text="Updating GUI")
            #Preload
            if self.ImageObject is not None:
                job.SetProgress(0, text="Updating GUI: Precache the image views")
                self.ImageObject.imgView(ImgObj.SPATIAL).Mean
                self.ImageObject.imgView(ImgObj.SPATIAL).Std
                job.SetProgress(1, text="Updating GUI: Precache the image views")
                self.ImageObject.imgDiffView(ImgObj.SPATIAL).Max
                self.ImageObject.imgDiffView(ImgObj.SPATIAL).StdNormed
                job.SetProgress(2, text="Updating GUI: Precache the image views")
                self.ImageObject.imgDiffView(ImgObj.TEMPORAL).Max
                self.ImageObject.imgDiffView(ImgObj.TEMPORAL).Std
                job.SetProgress(3, text="Updating GUI: Statusbar")

                self.SetWindowTitle(self.ImageObject.name or "")
                if self.ImageObject.img is not None:
                    _size = round(sys.getsizeof(self.ImageObject.img)/(1024**2),2)
                    self.statusbar.StatusText = f"Image of shape {self.ImageObject.img.shape} and size {_size} MB"
                else:
                    self.statusbar.StatusText = ""
            else:
                self.statusbar.StatusText = ""
                self.SetWindowTitle("")
            for t in self.tabs.values(): 
                job.SetProgress(4, text=f"Updating GUI: {t.tab_name}")
                t.Update(ImageChangedEvent())
            job.SetStopped("Updating GUI")

        job = Job(steps=5, showSteps=True)
        self.statusbar.AddJob(job)
        threading.Thread(target=_Update, args=(job,), daemon=True).start()

    def SignalChanged(self):
        for t in self.tabs.values(): t.Update(SignalChangedEvent())


    # General GUI functions


    def SetWindowTitle(self, text:str=""):
        if (self.edition == Edition.NEUROTORCH_LIGHT):
            self.root.title(f"NeuroTorch Light {text}")
        else:
            self.root.title(f"NeuroTorch {text}")

    def OnClosing(self):
        self.root.destroy()
        exit()

    
    # Menu Buttons Click

    def MenuFileOpen(self, noisy:bool=False):
        image_path = filedialog.askopenfilename(parent=self.root, title="Open a Image File", 
                filetypes=(("All files", "*.*"), ("TIF File", "*.tif *.tiff"), ("ND2 Files (NIS Elements)", "*.nd2")) )
        if image_path is None or image_path == "":
            return
        self.statusbar._jobs.append(ImgObj().OpenFile(image_path, callback=self._OpenImage_Callback, errorcallback=self._OpenImage_CallbackError, convolute=noisy))
        return
    
    def _OpenImage_Callback(self, imgObj: ImgObj):
        self.ImageObject = imgObj

    def _OpenImage_CallbackError(self, code, msg=""):
        match(code):
            case "FileNotFound":
                messagebox.showerror("Neurotorch", f"The given path doesn't exist or can't be opened. {msg}")
            case "AlreadyLoading":
                messagebox.showerror("Neurotorch", f"Please wait until the current image is loaded. {msg}")
            case "ImageUnsupported":
                messagebox.showerror("Neurotorch", f"The provided file is not supported. {msg}")
            case "WrongShape":
                messagebox.showerror("Neurotorch", f"The image has wrong shape ({msg}). It needs to have (t, y, x)")
            case _:
                messagebox.showerror("Neurotorch", f"An unkown error happend opening this image. {msg}") 
    
    def MenuFileClose(self):
        self.ImageObject = None
        
    def MenuImageDenoise(self, mode: None|Literal["Gaussian", "MeanMaxDiff"], args: None|tuple):
        if self.ImageObject is None or self.ImageObject.imgDiff is None:
            self.root.bell()
            return
        if mode is None:
            self.ImageObject.imgDiff_Mode = "Normal"
        elif mode == "Gaussian":
            self.ImageObject.imgDiff_Mode = "Convoluted"
            self.ImageObject.SetConvolutionFunction(self.ImageObject.Conv_GaussianBlur, args=args)
        elif mode == "MeanMaxDiff":
            self.ImageObject.imgDiff_Mode = "Convoluted" 
            self.ImageObject.SetConvolutionFunction(self.ImageObject.Conv_MeanMaxDiff, args=args)   
        else:
            raise ValueError(f"Mode parameter has an unkown value '{mode}'")
        self.NewImageProvided()

    def MenuImage_ClearCache(self):
        self.ImageObject.ClearCache()

    def MenuImageDenoiseImg(self, enable: bool):
        if self.ImageObject is None:
            self.root.bell()
            return
        self.ImageObject._imgMode = 1 if enable else 0
        self.NewImageProvided()

    def MenuNeurotorchAbout(self):
        messagebox.showinfo("Neurotorch", f"© Andreas Brilka 2024\nYou are running Neurotorch {self._version_}")


    def MenuDebugLoadPeaks(self):
        path = os.path.join(Settings.UserPath, "img_peaks.dump")
        if not os.path.exists(path):
            self.root.bell()
            return
        with open(path, 'rb') as f:
            _img = pickle.load(f)
            _name = "img_peaks.dump"
            self.statusbar._jobs.append(ImgObj().SetImagePrecompute(img=_img, name=_name, callback=self._OpenImage_Callback, errorcallback=self._OpenImage_CallbackError))

    def MenuDebugSavePeaks(self):
        if self.ImageObject is None or self.ImageObject.img is None or self.signal.peaks is None or len(self.signal.peaks) == 0:
            self.root.bell()
            return
        if not messagebox.askyesnocancel("Neurotorch", "Do you want to save the current diffImg Peak Frames in a Dump?"):
            return
        _peaksExtended = []
        for p in self.signal.peaks:
            if p != 0 and p < (self.ImageObject.img.shape[0] - 1):
                if len(_peaksExtended) == 0:
                    _peaksExtended.extend([int(p-1),int(p),int(p+1)])
                else:
                    _peaksExtended.extend([int(p),int(p+1)])
            else:
                logger.info(f"Skipped peak {p} as it is to near to the edge")
        _peaksExtended.extend([int(p+2)])
        logger.info("Exported frames", _peaksExtended)
        savePath = os.path.join(Settings.UserPath, "img_peaks.dump")
        with open(savePath, 'wb') as f:
            pickle.dump(self.ImageObject.img[_peaksExtended, :, :], f, protocol=pickle.HIGHEST_PROTOCOL)

    def MenuDebug_EnableDebugging(self):
        logger.setLevel(logging.DEBUG)
        logger.DEBUG("Neurotorch is now in debugging mode")


class TabUpdateEvent:
    pass

class ImageChangedEvent(TabUpdateEvent):
    pass

class SignalChangedEvent(TabUpdateEvent):
    pass

class Tab:

    def __init__(self, gui: Neurotorch_GUI):
        self.tab_name = None
        self.tab = None

    def Init(self):
        """
            Called by the GUI to notify the tab to generate its body
        """
        pass

    def Update(self, event:TabUpdateEvent):
        """
            Called by the GUI to notify the tab, that it may need to update. It is the resposibility of the tab to check for the events
        """
        pass
