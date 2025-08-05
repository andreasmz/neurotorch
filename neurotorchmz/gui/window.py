"""
    Main module to initialize the Neurotorch GUI.
"""
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tktooltip import ToolTip
import pickle
from typing import Literal
import matplotlib
from pathlib import Path
import platform
import subprocess
import os
from collections import deque
matplotlib.use('TkAgg')

from .components.general import Statusbar
from ..core.session import *
from ..core.session import __version__
from ..core.task_system import Task
from ..utils.plugin_manager import Plugin, PluginManager

class TabUpdateEvent:
    pass

class ImageChangedEvent(TabUpdateEvent):
    pass

class SignalChangedEvent(TabUpdateEvent):
    pass

class Neurotorch_GUI:
    def __init__(self, session: Session):
        self.session = session
        self.tabs : dict[type, Tab] = {}
        self._pending_updates: deque[tuple[Tab, TabUpdateEvent]] = deque()

    def launch(self, edition:Edition=Edition.NEUROTORCH):
        self.edition = edition
        self.root = tk.Tk()
        self.set_window_title("")
        self.root.iconbitmap(default=(settings.resource_path / "neurotorch_logo.ico"))
        self.root.geometry("900x600")
        self.root.state("zoomed")
        self.statusbar = Statusbar(self.root, self.root)

        self._update_task = self._update_task = Task(self._update_loop, name="updating GUI", run_async=True, keep_alive=True)

        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)
        self.menuFile = tk.Menu(self.menubar,tearoff=0)
        self.menubar.add_cascade(label="File",menu=self.menuFile)
        self.menuFile.add_command(label="Open", command=self.menuFile_open_click)
        self.menuFile.add_command(label="Open noisy image", command=lambda: self.menuFile_open_click(noisy=True))
        self.menuFile.add_command(label="Close image", command=self.menuFile_close_click)

        self.menuImage = tk.Menu(self.menubar,tearoff=0)
        self.menubar.add_cascade(label="Image", menu=self.menuImage)
        self.menuDenoise = tk.Menu(self.menuImage,tearoff=0)
        self.menuImage.add_cascade(label="Denoise imgDiff", menu=self.menuDenoise)
        self.menuDenoise.add_command(label="Disable denoising", command=lambda: self.menuImage_denoise_click(None, None))
        self.menuDenoise.add_command(label="Clear cache", command=self.menuImage_clear_cache_click)
        self.menuDenoise.add_separator()
        self.menuDenoise.add_command(label=f"Gaussian kernel (σ=0.5)", command=lambda: self.menuImage_denoise_click(denoising.gaussian_blur, {"sigma": 0.5}))
        self.menuDenoise.add_command(label=f"Gaussian kernel (σ=0.8)", command=lambda: self.menuImage_denoise_click(denoising.gaussian_blur, {"sigma": 0.8}))
        self.menuDenoise.add_command(label=f"Gaussian kernel (σ=1)", command=lambda: self.menuImage_denoise_click(denoising.gaussian_blur, {"sigma": 1}))
        self.menuDenoise.add_command(label=f"Gaussian kernel (σ=1.5)", command=lambda: self.menuImage_denoise_click(denoising.gaussian_blur, {"sigma": 1.5}))
        self.menuDenoise.add_command(label=f"Gaussian kernel (σ=2, recommended)", command=lambda: self.menuImage_denoise_click(denoising.gaussian_blur, {"sigma": 2}))
        self.menuDenoise.add_command(label=f"Gaussian kernel (σ=2.5)", command=lambda: self.menuImage_denoise_click(denoising.gaussian_blur, {"sigma": 2.5}))
        self.menuDenoise.add_command(label=f"Gaussian kernel (σ=3)", command=lambda: self.menuImage_denoise_click(denoising.gaussian_blur, {"sigma": 3}))
        self.menuDenoise.add_command(label=f"Gaussian kernel (σ=5)", command=lambda: self.menuImage_denoise_click(denoising.gaussian_blur, {"sigma": 5}))

        self.menuFilter = tk.Menu(self.menuImage,tearoff=0)
        self.menuImage.add_cascade(label="Apply filter", menu=self.menuFilter)
        self.menuFilter.add_command(label="Disable filter", command=lambda: self.menuImage_denoise_click(None, None))
        self.menuFilter.add_command(label="Clear cache", command=self.menuImage_clear_cache_click)
        self.menuFilter.add_separator()
        self.menuFilter.add_command(label="Cummulative imgDiff", command=lambda: self.menuImage_denoise_click(denoising.mean_diff, None))
        ToolTip(self.menuFile, msg=resources.get_string("menubar/filters/meanMaxDiff"), follow=True, delay=0.5)

        if edition == Edition.NEUROTORCH_DEBUG:
            self.menuDenoiseImg = tk.Menu(self.menuImage,tearoff=0)
            self.menuImage.add_cascade(label="Denoise Image", menu=self.menuDenoiseImg)
            self.menuDenoiseImg.add_command(label="On", command=lambda:self.menuImage_denoise_image_click(True))
            self.menuDenoiseImg.add_command(label="Off", command=lambda:self.menuImage_denoise_image_click(False))

        if (edition != Edition.NEUROTORCH_LIGHT):
            self.session.import_ijh()
            self.session.ijH.MenubarImageJH(self.menubar) # type: ignore

        self.menuPlugins = tk.Menu(self.menubar,tearoff=0)
        self.menubar.add_cascade(label="Plugins",menu=self.menuPlugins)
        
        self.menuNeurotorch = tk.Menu(self.menubar,tearoff=0)
        self.menubar.add_cascade(label="Neurotorch",menu=self.menuNeurotorch)
        self.menuNeurotorch.add_command(label="About", command=self.menuNeurotorch_about_click)
        self.menuNeurotorch.add_command(label="Open logs", command=self.menuNeurotorch_logs_click)

        self.menuDebug = tk.Menu(self.menubar,tearoff=0)
        if edition == Edition.NEUROTORCH_DEBUG:
            self.menubar.add_cascade(label="Debug", menu=self.menuDebug)
        self.menuDebug.add_command(label="Activate debugging to console", command=self.menuDebug_enable_debugging_click)    
        self.menuDebug.add_command(label="Save diffImg peak frames", command=self.menuDebug_save_peaks_click)
        self.menuDebug.add_command(label="Load diffImg peak frames", command=self.menuDebug_load_peaks_click)

        self.tabMain = ttk.Notebook(self.root)
        self.tabs[TabWelcome] = TabWelcome(self.session, self.root, self.tabMain)
        self.tabs[TabImage] = TabImage(self.session, self.root, self.tabMain)
        #self.tabs[TabSignal] = TabSignal(self.session, self.root, self.tabMain)
        #self.tabs[TabROIFinder] = TabROIFinder(self.session, self.root, self.tabMain)
        #self.tabs[TabAnalysis] = TabAnalysis(self.session, self.root, self.tabMain)
        for t in self.tabs.values(): t.init()
        self.tabMain.select(self.tabs[TabImage].tab)

        self.plugin_manager = PluginManager(self.session)

        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.tabMain.pack(expand=1, fill="both")
        self.root.mainloop()

    # Update handling

    def invoke_tab_update_event(self, event: TabUpdateEvent) -> Task:
        """ Notify each tab about the given TabUpdateEvent """
        if isinstance(event, ImageChangedEvent):
            imgObj =  self.session.active_image_object
            if imgObj is not None and imgObj.img is not None:
                self.set_window_title(imgObj.name or "")
                _size = round(sys.getsizeof(imgObj.img)/(1024**2),2)
                self.statusbar.StatusText = f"Image of shape {imgObj.img.shape} and size {_size} MB"
            else:
                self.statusbar.StatusText = ""
        for t in self.tabs.values():
            self.invoke_tab_about_update(t, event)
        return self._update_task

    def invoke_tab_about_update(self, tab: 'Tab', event: TabUpdateEvent) -> Task:
        """ Add a UpdateEvent to the queue and start the update loop if not already running """
        self._pending_updates.append((tab, event))
        self._update_task.start()
        return self._update_task

    def _update_loop(self, task: Task, **kwargs):
        """ Process the update queue as long as items are contained """
        #num_total_updates = len(self._pending_updates) # Used to set the progress bar
        #num_pending_updates = len(self._pending_updates) # Cache pending updates count
        #update_index = 0
        task.set_indeterminate()
        while len(self._pending_updates) != 0:
            #num_total_updates += len(self._pending_updates) - num_pending_updates # Add number of updates which had been previous while loop not in the Queue
            #task.set_step_mode(step_count=num_total_updates)
            tab, event = self._pending_updates.pop()
            num_pending_updates = len(self._pending_updates)
            task.set_message(" %s %s" % (tab.tab_name, f'({num_pending_updates} more updates queued)' if num_pending_updates > 0 else ''))
            tab.update_tab(event)
            #update_index += 1


    # General GUI functions

    def set_window_title(self, text:str=""):
        if (self.edition == Edition.NEUROTORCH_LIGHT):
            self.root.title(f"NeuroTorch Light {text}")
        elif self.edition == Edition.NEUROTORCH_DEBUG:
            self.root.title(f"Neurotorch {text} (DEBUG mode)")
        else:
            self.root.title(f"NeuroTorch {text}")

    def _on_closing(self):
        self.root.destroy()
        #exit()

    # ImageObject handling

    def _open_image_error_callback(self, ex: Exception):
        if isinstance(ex, FileNotFoundError):
            logger.warning(f"[ImageObject OpenFile] The given path is invalid")
            messagebox.showerror("Neurotorch", f"The given path is invalid")
        elif isinstance(ex, AlreadyLoadingError):
            logger.warning(f"[ImageObject OpenFile] Image already loading error")
            messagebox.showerror("Neurotorch", f"Please wait until the current image is loaded")
        elif isinstance(ex, UnsupportedImageError):
            logger.warning(f"[ImageObject OpenFile] Unsupported image: {str(ex.exception)}")
            messagebox.showerror("Neurotorch", f"The provided file {ex.file_name} is not supported")
        elif isinstance(ex, ImageShapeError):
            logger.warning(f"[ImageObject OpenFile] Invalid shape {ex.shape}")
            messagebox.showerror("Neurotorch", f"The image has shape {ex.shape}, which is incompatible as it must have (t, y, x)")
        else:
            logger.exception("[OpenImageObject] An unkown error happened", exc_info=(type(ex), ex, ex.__traceback__))
            messagebox.showerror("Neurotorch", f"An unkown error happened oppening this image: {str(ex)}")

    
    # Menu Buttons Click

    def menuFile_open_click(self, noisy:bool=False):
        image_path = filedialog.askopenfilename(parent=self.root, title="Open a Image File", 
                filetypes=(("All files", "*.*"), ("TIF File", "*.tif *.tiff"), ("ND2 Files (NIS Elements)", "*.nd2")) )
        if image_path is None or image_path == "":
            return
        imgObj = ImageObject()
        self.session.set_active_image_object(imgObj)
        task = imgObj.OpenFile(Path(image_path), precompute=True, calc_convoluted=noisy, run_async=True)
        task.add_callback(self.session.notify_image_object_change)
        task.set_error_callback(self._open_image_error_callback)
    
    def menuFile_close_click(self):
        self.session.set_active_image_object(None)
        
    def menuImage_denoise_click(self, func: Callable[..., np.ndarray]|None, func_args: dict|None):
        imgObj = self.session.active_image_object
        if imgObj is None or imgObj.imgDiff is None:
            self.root.bell()
            return
        imgObj.set_diff_conv_func(func, func_args)
        imgObj.PrecomputeImage().add_callback(lambda: self.invoke_tab_update_event(ImageChangedEvent()))

    def menuImage_clear_cache_click(self):
        if self.session.active_image_object is None:
            self.root.bell()
            return    
        self.session.active_image_object.clear_cache()
        logger.debug("Cleared ImageObject cache")

    def menuImage_denoise_image_click(self, enable: bool):
        if self.session.active_image_object is None:
            self.root.bell()
            return
        if self.session.active_image_object._img_conv_func is None:
            self.session.active_image_object.set_conv_func(denoising.cumsum_denoise, func_args=None)
        else:
            self.session.active_image_object.set_conv_func(None, None)
        self.session.active_image_object.PrecomputeImage().add_callback(lambda: self.invoke_tab_update_event(ImageChangedEvent()))

    def menuNeurotorch_about_click(self):
        messagebox.showinfo("Neurotorch", f"© Andreas Brilka 2025\nYou are running Neurotorch {__version__}")

    def menuNeurotorch_logs_click(self):
        if platform.system() == 'Darwin':       # macOS
            subprocess.call(('open', settings.log_path))
        elif platform.system() == 'Windows':    # Windows
            os.startfile(settings.log_path)
        else:                                   # linux variants
            subprocess.call(('xdg-open', settings.log_path))

    def menuDebug_load_peaks_click(self):
        path = settings.app_data_path / "img_peaks.dump"
        if not path.exists() or not path.is_file():
            self.root.bell()
            return
        
        with open(path, 'rb') as f:
            _img = pickle.load(f)
            _name = "img_peaks.dump"
            imgObj = ImageObject()
            task = Task(lambda task, **kwargs: imgObj.SetImagePrecompute(**kwargs), name="Open image", run_async=True)
            task.add_callback(lambda: self.session.set_active_image_object(imgObj))
            task.set_error_callback(self._open_image_error_callback)
            task.start(img=_img, name=_name, run_async=False)

    def menuDebug_save_peaks_click(self):
        imgObj = self.session.active_image_object
        signalObj = self.session.active_image_signal
        if imgObj is None or imgObj.img is None or signalObj is None or signalObj.peaks is None or len(signalObj.peaks) == 0:
            self.root.bell()
            return
        if not messagebox.askyesnocancel("Neurotorch", "Do you want to save the current diffImg Peak Frames in a Dump?"):
            return
        _peaksExtended = []
        for p in signalObj.peaks:
            if p != 0 and p < (imgObj.img.shape[0] - 1):
                if len(_peaksExtended) == 0:
                    _peaksExtended.extend([int(p-1),int(p),int(p+1)])
                else:
                    _peaksExtended.extend([int(p),int(p+1)])
            else:
                logger.info(f"Skipped peak {p} as it is to near to the edge")
        _peaksExtended.extend([int(max(signalObj.peaks) + 2)])
        logger.info("Exported frames", _peaksExtended)
        savePath = settings.app_data_path / "img_peaks.dump"
        with open(savePath, 'wb') as f:
            pickle.dump(imgObj.img[_peaksExtended, :, :], f, protocol=pickle.HIGHEST_PROTOCOL)

    def menuDebug_enable_debugging_click(self):
        logs.start_debugging()


class Tab:

    def __init__(self, session: Session, root:tk.Tk, notebook: ttk.Notebook, _tab_name: str|None = None):
        self.session = session
        """ The current session object """
        self.root = root
        """ The tkinter root object """
        self.notebook = notebook
        """ The current notebook frame """
        self.tab = ttk.Frame(self.notebook)
        self.tab_name: str|None = _tab_name

    def init(self):
        """
            Called by the GUI to notify the tab to generate its body
        """
        pass

    def update_tab(self, event:TabUpdateEvent):
        """
            Called by the GUI to notify the tab, that it may need to update. It is the resposibility of the tab to check for the events
        """
        pass

    def invoke_update(self, event: TabUpdateEvent):
        """ Invoke an update on the tab """
        if self.session.window is None:
            raise RuntimeError(f"Can't invoke a tab update in headleass mode")
        self.session.window.invoke_tab_about_update(tab=self, event=event)

    @property
    def window(self) -> Neurotorch_GUI:
        """ Convience function to get the window faster """
        if self.session.window is None:
            raise RuntimeError(f"Can't invoke a tab update in headleass mode")
        return self.session.window
    
    @property
    def active_image_object(self) -> ImageObject|None:
        """ Convinience function for the currently active session image object """
        return self.session.active_image_object


from ..gui.tabWelcome import TabWelcome
from neurotorchmz.gui.tab1 import TabImage
# from neurotorchmz.gui.tab2 import TabSignal
# from neurotorchmz.gui.tab3 import TabROIFinder
# from neurotorchmz.gui.tabAnalysis import TabAnalysis
#from ..utils.plugin_manager import PluginManager
