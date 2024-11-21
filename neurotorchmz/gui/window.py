import sys, os
import tkinter as tk
import threading
import pickle
import matplotlib
from tkinter import ttk, messagebox, filedialog
from enum import Enum
from typing import Literal
import logging

matplotlib.use('TkAgg')

from .. import __version__
from .components import Job, Statusbar
from .settings import Neurotorch_Settings as Settings
from ..utils.image import ImgObj
from ..utils.signalDetection import SignalObj
from ..utils.plugin_manager import PluginManager



class Edition(Enum):
    NEUROTORCH = 1
    NEUROTORCH_LIGHT = 2

class Neurotorch_GUI:
    def __init__(self):
        self.root = None
        self.tabs : dict[str: Tab] = {}
        self._imgObj = None
        self.signal = SignalObj(self.GetImageObject)
        self.ijH = None

    def GUI(self, edition:Edition=Edition.NEUROTORCH):
        import neurotorchmz.gui.tabWelcome as tabWelcome
        from neurotorchmz.gui.tab1 import Tab1
        from neurotorchmz.gui.tab2 import Tab2
        from neurotorchmz.gui.tab3 import Tab3
        from neurotorchmz.gui.tabAnalysis import TabAnalysis
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
        self.menuDenoise.add_command(label="Gaussian kernel (σ=2, recommended)", command=lambda: self.MenuImageDenoise('Gaussian', (2,)))
        self.menuDenoise.add_separator()
        self.menuDenoise.add_command(label="Clear cache", command=self.MenuImage_ClearCache)
        self.menuDenoise.add_command(label="Gaussian kernel (σ=0.5)", command=lambda: self.MenuImageDenoise('Gaussian', (0.5,)))
        self.menuDenoise.add_command(label="Gaussian kernel (σ=0.8)", command=lambda: self.MenuImageDenoise('Gaussian', (0.8,)))
        self.menuDenoise.add_command(label="Gaussian kernel (σ=1)", command=lambda: self.MenuImageDenoise('Gaussian', (1,)))
        self.menuDenoise.add_command(label="Gaussian kernel (σ=1.5)", command=lambda: self.MenuImageDenoise('Gaussian', (1.5,)))
        self.menuDenoise.add_command(label="Gaussian kernel (σ=2)", command=lambda: self.MenuImageDenoise('Gaussian', (2,)))
        self.menuDenoise.add_command(label="Gaussian kernel (σ=2.5)", command=lambda: self.MenuImageDenoise('Gaussian', (2.5,)))
        self.menuDenoise.add_command(label="Gaussian kernel (σ=3)", command=lambda: self.MenuImageDenoise('Gaussian', (3,)))
        self.menuDenoise.add_command(label="Gaussian kernel (σ=5)", command=lambda: self.MenuImageDenoise('Gaussian', (5,)))
        self.menuDenoiseImg = tk.Menu(self.menuImage,tearoff=0)
        self.menuImage.add_cascade(label="Denoise Image", menu=self.menuDenoiseImg)
        self.menuDenoiseImg.add_command(label="On", command=lambda:self.MenuImageDenoiseImg(True))
        self.menuDenoiseImg.add_command(label="Off", command=lambda:self.MenuImageDenoiseImg(False))
        self.menuImage.add_command(label="Start Trace Selector", command=self.MenuImageTraceSelector)

        if (edition == Edition.NEUROTORCH):
            from neurotorchmz.utils.pyimagej import ImageJHandler
            self.ijH = ImageJHandler(self)
            self.ijH.MenubarImageJH(self.menubar)
        
        self.menuNeurotorch = tk.Menu(self.menubar,tearoff=0)
        self.menubar.add_cascade(label="Neurotorch",menu=self.menuNeurotorch)
        self.menuNeurotorch.add_command(label="About", command=self.MenuNeurotorchAbout)
        self.menuNeurotorch.add_command(label="Update", command=self.MenuNeurotorchUpdate)

        self.menuDebug = tk.Menu(self.menubar,tearoff=0)
        self.menubar.add_cascade(label="Debug", menu=self.menuDebug)
        self.menuDebug.add_command(label="Save diffImg peak frames", command=self.MenuDebugSavePeaks)
        self.menuDebug.add_command(label="Load diffImg peak frames", command=self.MenuDebugLoadPeaks)
        self.menuDebug.add_separator()
        self.menuDebug.add_command(label="Activate debugging to console", command=self.MenuDebug_EnableDebugging)
        self.menuDebug.add_command(label="Dump memory usage", command=self.MenuDebug_MemoryDump)
        self.menuDebug.add_command(label="Print all imported modules", command=self.MenuDebug_ImportedModules)

        self.tabMain = ttk.Notebook(self.root)
        self.tabWelcome = tabWelcome.TabWelcome(self)
        self.tabs["Tab1"] = Tab1(self)
        self.tabs["Tab2"] = Tab2(self)
        self.tabs["Tab3"] = Tab3(self)
        #self.tabs["TabAnalysis"] = TabAnalysis(self)
        for t in self.tabs.values(): t.Init()
        self.tabMain.select(self.tabs["Tab1"].tab)

        self.plugin_mng = PluginManager()

        self.tabMain.pack(expand=1, fill="both")

        # Debug
        self.root.protocol("WM_DELETE_WINDOW", self.OnClosing)

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
            #Preload
            job.SetProgress(0, text="Calculating image preview")
            if self.ImageObject is not None and self.ImageObject.imgDiff is not None:
                self.ImageObject.imgView(ImgObj.SPATIAL).Mean
                job.SetProgress(1, text="Calculating imgDiff")
                self.ImageObject.imgDiff
                job.SetProgress(2, text="Calculating imgDiff previews")
                self.ImageObject.imgView(ImgObj.SPATIAL).Mean
                self.ImageObject.imgView(ImgObj.SPATIAL).Std
                self.ImageObject.imgDiffView(ImgObj.SPATIAL).Max
                self.ImageObject.imgDiffView(ImgObj.SPATIAL).Std
            job.SetProgress(3, text="Updating GUI (Statusbar)")

            if self.ImageObject is not None:
                if self.ImageObject.img is not None:
                    _size = round(sys.getsizeof(self.ImageObject.img)/(1024**2),2)
                    self.statusbar.StatusText = f"Image of shape {self.ImageObject.img.shape} and size {_size} MB"
                self.SetWindowTitle(self.ImageObject.name)
            else:
                self.statusbar.StatusText = ""
                self.SetWindowTitle("")
            for t in self.tabs.values(): 
                job.SetProgress(3, text=f"Updating GUI ({t.tab_name})")
                t.Update([TabUpdateEvent.NEWIMAGE, TabUpdateEvent.NEWSIGNAL])
            job.SetStopped("Updating GUI")

        job = Job(steps=4)
        self.statusbar.AddJob(job)
        threading.Thread(target=_Update, args=(job,), daemon=True).start()

    def SignalChanged(self):
        for t in self.tabs.values(): t.Update([TabUpdateEvent.NEWSIGNAL])


    # General GUI functions


    def SetWindowTitle(self, text:str=""):
        if (self.edition == Edition.NEUROTORCH_LIGHT):
            self.root.title(f"NeuroTorch Light {text}")
        else:
            self.root.title(f"NeuroTorch {text}")

    def OnClosing(self):
        print("Running threads: ", end="")
        for thread in threading.enumerate(): 
            print(thread.name, end="")
        print("\nClosing")
        self.root.destroy()
        print("Exit Neurotorch")
        exit()

    
    # Menu Buttons Click

    def MenuFileOpen(self, noisy:bool=False):
        image_path = filedialog.askopenfilename(parent=self.root, title="Open a Image File", 
                filetypes=(("All compatible files", "*.tif *.tiff *.nd2"), ("TIF File", "*.tif *.tiff"), ("ND2 Files (NIS Elements)", "*.nd2"), ("All files", "*.*")) )
        if image_path is None or image_path == "":
            return
        self.statusbar._jobs.append(ImgObj().OpenFile(image_path, callback=self._OpenImage_Callback, errorcallback=self._OpenImage_CallbackError, convolute=noisy))
        return
    
    def _OpenImage_Callback(self, imgObj: ImgObj):
        self.ImageObject = imgObj

    def _OpenImage_CallbackError(self, code, msg=""):
        match(code):
            case "FileNotFound":
                messagebox.showerror("Neurotorch", f"The given path doesn't exist or can't be opened {msg}")
            case "AlreadyLoading":
                messagebox.showerror("Neurotorch", f"Please wait until the current image is loaded {msg}")
            case "ImageUnsupported":
                messagebox.showerror("Neurotorch", f"The provided file is not supported {msg}")
            case _:
                messagebox.showerror("Neurotorch", f"An unkown error happend opening this image {msg}") 
    
    def MenuFileClose(self):
        self.ImageObject = None
        
    def MenuImageDenoise(self, mode: None|Literal["Gaussian"], args: None|tuple):
        if self.ImageObject is None or self.ImageObject.imgDiff is None:
            self.root.bell()
            return
        if mode is None:
            self.ImageObject.imgDiff_Mode = "Normal"
        elif mode == "Gaussian":
            self.ImageObject.imgDiff_Mode = "Convoluted"
            self.ImageObject.SetConvolutionFunction(self.ImageObject.Conv_GaussianBlur, args=args)
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
        

    def MenuImageTraceSelector(self):
        if messagebox.askokcancel("Neurotorch", "This is currently an experimental feature. Are you sure you want to continue?"):
            pass

    def MenuNeurotorchAbout(self):
        messagebox.showinfo("Neurotorch", f"© Andreas Brilka 2024\nYou are running Neurotorch {__version__}")

    def MenuNeurotorchUpdate(self):
        Updater.CheckForUpdate()
        _github_version = Updater.version_github
        _local_version = Updater.version
        if _github_version is None:
            messagebox.showerror("Neurotorch", f"The server can't be contacted to check for an update. Please try again later")
            return
        if _local_version == _github_version:
            messagebox.showinfo("Neurotorch", f"You are running the newest version")
            return
        if not messagebox.askyesno("Neurotorch", f"Version {_github_version} is available for download (You have {_local_version}). Do you want to update?"):
            return
        Updater.DownloadUpdate()


    def MenuDebugLoadPeaks(self):
        path = os.path.join(Settings.UserPath, "img_peaks.dump")
        if not os.path.exists(path):
            self.root.bell()
            return
        with open(path, 'rb') as f:
            _img = pickle.load(f)
            self.statusbar._jobs.append(ImgObj().SetImage_Precompute(_img, name="img_peaks.dump", callback=self._OpenImage_Callback, errorcallback=self._OpenImage_CallbackError))

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
                logging.info(f"Skipped peak {p} as it is to near to the edge")
        _peaksExtended.extend([int(p+2)])
        logging.info("Exported frames", _peaksExtended)
        savePath = os.path.join(Settings.UserPath, "img_peaks.dump")
        with open(savePath, 'wb') as f:
            pickle.dump(self.ImageObject.img[_peaksExtended, :, :], f, protocol=pickle.HIGHEST_PROTOCOL)

    def MenuDebug_EnableDebugging(self):
        logging.getLogger().setLevel(logging.DEBUG)
        logging.info("Activated Debugging")

    def MenuDebug_MemoryDump(self):
        logging.debug("Dump ImageObject Sizes")
        if self._imgObj is None:
            self.root.bell()
            logging.debug("ImageObject is None")
            return
        for name, obj in {"img": self._imgObj._img, 
                          "imgDiff": self._imgObj._imgDiff, 
                          "imgSpatial": self._imgObj._imgSpatial}.items():
            _size = sys.getsizeof(obj)
            if _size < 1024:
                _sizeFormatted = f"{_size} Bytes"
            elif _size < 1024**2:
                _sizeFormatted = f"{round(_size/1024, 3)} KB"
            elif _size < 1024**3:
                _sizeFormatted = f"{round(_size/1024**2, 3)} MB"
            else:
                _sizeFormatted = f"{round(_size/1024**3, 3)} GB"
            logging.debug(f"{name}: {_sizeFormatted}")

    def MenuDebug_ImportedModules(self):
        print([k for k in sys.modules.keys() if "imagej" in k])

class TabUpdateEvent(Enum):
    NEWIMAGE = "newimage"
    NEWSIGNAL = "newsignal"
    #Customs Event should have the syntax tabName_eventName for its value

class Tab:

    def __init__(self, gui: Neurotorch_GUI):
        self.tab_name = None
        self.tab = None

    def Init(self):
        """
            Called by the GUI to notify the tab to generate its body
        """
        pass

    def Update(self, event : list[TabUpdateEvent]):
        """
            Called by the GUI to notify the tab, that it may need to update. It is the resposibility of the tab to check for the events
            Note that the values in the Enum TabUpdatEvent may be added dynamically during tab creation.
        """
        pass