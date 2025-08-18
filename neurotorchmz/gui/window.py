"""
    Main module to initialize the Neurotorch GUI.
"""
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tktooltip import ToolTip
import pickle
import matplotlib
matplotlib.use('TkAgg')

from pathlib import Path
import subprocess
import os
import platformdirs
from collections import deque
from types import ModuleType

from .components.general import Statusbar
from ..gui import events as window_events
from ..core.session import *
from ..core.session import __version__

class TabUpdateEvent:
    pass

class ImageChangedEvent(TabUpdateEvent):
    pass

class SignalChangedEvent(TabUpdateEvent):
    pass

class PeaksChangedEvent(TabUpdateEvent):
    pass

class UpdateRoiFinderDetectionResultEvent(TabUpdateEvent):
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
        self.menu_file = tk.Menu(self.menubar, tearoff=0)
        self.menu_edit = tk.Menu(self.menubar, tearoff=0)
        self.menu_run = tk.Menu(self.menubar, tearoff=0)
        self.menu_settings = tk.Menu(self.menubar, tearoff=0)
        self.menu_plugins = tk.Menu(self.menubar, tearoff=0)
        self.menu_debug = tk.Menu(self.menubar, tearoff=0)
        self.menu_about = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File",menu=self.menu_file)
        self.menubar.add_cascade(label="Edit",menu=self.menu_edit)
        self.menubar.add_cascade(label="Run",menu=self.menu_run)
        self.menubar.add_cascade(label="Settings",menu=self.menu_settings)
        self.menubar.add_cascade(label="Plugins",menu=self.menu_plugins)
        if self.edition == Edition.NEUROTORCH_DEBUG:
            self.menubar.add_cascade(label="Debug",menu=self.menu_debug)
        self.menubar.add_cascade(label="Neurotorch",menu=self.menu_about)

        # File menu
        self.menu_file.add_command(label="Open file", command=self.menu_file_open_click)
        self.menu_file.add_separator()
        self.menu_file_import = tk.Menu(self.menu_file, tearoff=0)
        self.menu_file.add_cascade(label="Import", menu=self.menu_file_import)
        self.menu_file_export = tk.Menu(self.menu_file, tearoff=0)
        self.menu_file.add_cascade(label="Export", menu=self.menu_file_export)
        self.menu_file.add_separator()
        self.menu_file.add_command(label="Close file", command=self.menu_file_close_click)

        self.menu_file_export_file = tk.Menu(self.menu_file_export, tearoff=0)
        self.menu_file_export.add_cascade(label="As file (video)", menu=self.menu_file_export_file)
        self.menu_file_export_file.add_command(label="export", command=lambda: self.menu_export_click("img"))
        self.menu_file_export_file.add_separator()
        self.menu_file_export_file.add_command(label="... without stimulation", command=lambda: self.menu_export_click("img_without_signal"))
        self.menu_file_export_file.add_command(label="... including only stimulation", command=lambda: self.menu_export_click("img_only_signal"))
        self.menu_file_export.add_command(label="As file (delta video)", command=lambda: self.menu_export_click("img_diff"))
        

        # Edit menu
        self.menu_denoise = tk.Menu(self.menu_edit,tearoff=0)
        self.menu_edit.add_cascade(label="Denoise delta video", menu=self.menu_denoise)
        self.menu_denoise.add_command(label="Disable denoising", command=lambda: self.set_img_diff_convolution_xy(None))
        self.menu_denoise.add_command(label="Clear cache", command=self.menu_image_clear_cache_click)
        self.menu_denoise.add_separator()
        self.menu_denoise.add_command(label=f"Gaussian kernel (σ=0.5)", command=lambda: self.set_img_diff_convolution_xy(denoising.gaussian_xy_kernel, {"sigma":0.5}))
        self.menu_denoise.add_command(label=f"Gaussian kernel (σ=0.8)", command=lambda: self.set_img_diff_convolution_xy(denoising.gaussian_xy_kernel, {"sigma":0.8}))
        self.menu_denoise.add_command(label=f"Gaussian kernel (σ=1)", command=lambda: self.set_img_diff_convolution_xy(denoising.gaussian_xy_kernel, {"sigma":1}))
        self.menu_denoise.add_command(label=f"Gaussian kernel (σ=1.5)", command=lambda: self.set_img_diff_convolution_xy(denoising.gaussian_xy_kernel, {"sigma":1.5}))
        self.menu_denoise.add_command(label=f"Gaussian kernel (σ=2, recommended)", command=lambda: self.set_img_diff_convolution_xy(denoising.gaussian_xy_kernel, {"sigma":2}))
        self.menu_denoise.add_command(label=f"Gaussian kernel (σ=2.5)", command=lambda: self.set_img_diff_convolution_xy(denoising.gaussian_xy_kernel, {"sigma":2.5}))
        self.menu_denoise.add_command(label=f"Gaussian kernel (σ=3)", command=lambda: self.set_img_diff_convolution_xy(denoising.gaussian_xy_kernel, {"sigma":3}))
        self.menu_denoise.add_command(label=f"Gaussian kernel (σ=5)", command=lambda: self.set_img_diff_convolution_xy(denoising.gaussian_xy_kernel, {"sigma":5}))
        self.menu_denoise.add_command(label=f"Gaussian kernel (σ=7.5)", command=lambda: self.set_img_diff_convolution_xy(denoising.gaussian_xy_kernel, {"sigma":7.5}))
        self.menu_denoise.add_command(label=f"Gaussian kernel (σ=10)", command=lambda: self.set_img_diff_convolution_xy(denoising.gaussian_xy_kernel, {"sigma":10}))
        self.menu_trigger = tk.Menu(self.menu_edit, tearoff=0)
        self.menu_edit.add_cascade(label="Trigger", menu=self.menu_trigger)
        self.menu_trigger.add_command(label="Transient peak", command=lambda: self.set_img_diff_convolution_t(None))
        self.menu_trigger.add_command(label="Transient drop", command=lambda: self.set_img_diff_convolution_t(denoising.reverse_t_kernel))
        self.menu_trigger.add_command(label="Fast peak", command=lambda: self.set_img_diff_convolution_t(denoising.cumsum, {"frames": 3}))
        self.menu_trigger.add_command(label="Fast drop", command=lambda: self.set_img_diff_convolution_t(denoising.cumsum, {"frames": 3, "negate": True}))
        self.menu_trigger.add_command(label="Fast gaussian peak", command=lambda: self.set_img_diff_convolution_t(denoising.gaussian_t_kernel, {"sigma": 3}))
        self.menu_trigger.add_command(label="Fast gaussian drop", command=lambda: self.set_img_diff_convolution_t(denoising.gaussian_t_kernel, {"sigma": 3, "negate": True}))
        self.menu_trigger.add_command(label="Fast leap gaussian peak", command=lambda: self.set_img_diff_convolution_t(denoising.gaussian_t_kernel, {"sigma": 3}))
        self.menu_trigger.add_command(label="Fast leap gaussian drop", command=lambda: self.set_img_diff_convolution_t(denoising.gaussian_t_kernel, {"sigma": 3, "negate": True}))
        self.menu_trigger.add_command(label="Enable std norm", command=lambda: self.set_img_diff_std_norm(True))
        self.menu_trigger.add_command(label="Disable std norm", command=lambda: self.set_img_diff_std_norm(False))
        self.menu_trigger.add_separator()
        self.menu_trigger.add_command(label="Fast increase", command=lambda: self.set_img_diff_convolution_t(denoising.gaussian_t_kernel, {"sigma": 2}))
        self.menu_trigger.add_command(label="Normal increase", command=lambda: self.set_img_diff_convolution_t(denoising.gaussian_t_kernel, {"sigma": 5}))
        self.menu_trigger.add_command(label="Slow increase", command=lambda: self.set_img_diff_convolution_t(denoising.gaussian_t_kernel, {"sigma": 10}))
        self.menu_trigger.add_command(label="Fast drop", command=lambda: self.set_img_diff_convolution_t(denoising.gaussian_t_kernel, {"sigma": 2, "negate": True}))
        self.menu_trigger.add_command(label="Normal drop", command=lambda: self.set_img_diff_convolution_t(denoising.gaussian_t_kernel, {"sigma": 5, "negate": True}))
        self.menu_trigger.add_command(label="Slow drop", command=lambda: self.set_img_diff_convolution_t(denoising.gaussian_t_kernel, {"sigma": 10, "negate": True}))
        # Run menu

        # Settings menu

        # Plugins menu
        self.plugin_menus: dict[ModuleType, tk.Menu] = {}
        for p in plugin_manager.plugins:
            name = str(p.__plugin_name__)
            plugin_menu = tk.Menu(self.menu_plugins, tearoff=0)
            self.menu_plugins.add_cascade(label=name, menu=plugin_menu)
            if not p.__package__:
                logger.error(f"It seems like '{p.__plugin_name__}' is not a package")
            self.plugin_menus[p] = plugin_menu
            ToolTip(plugin_menu, msg=p.__plugin_desc__, follow=True, delay=0.5)

        # About menu
        self.menu_about.add_command(label="About", command=self.menu_neurotorch_about_click)
        self.menu_about.add_command(label="Open logs", command=self.menu_neurotorch_logs_click)

        # Debug menu
        self.menu_debug.add_command(label="Activate debugging to console", command=self.menu_debug_enable_debugging_click)    
        self.menu_debug.add_command(label="Save diffImg peak frames", command=self.menu_debug_save_peaks_click)
        self.menu_debug.add_command(label="Load diffImg peak frames", command=self.menu_debug_load_peaks_click)
        self.menu_debug.add_command(label="Test", command=self.menu_debug_test)

        # Register tabs
        self.tabMain = ttk.Notebook(self.root)
        self.tabs[TabWelcome] = TabWelcome(self.session, self.root, self.tabMain)
        self.tabs[TabImage] = TabImage(self.session, self.root, self.tabMain)
        self.tabs[TabSignal] = TabSignal(self.session, self.root, self.tabMain)
        self.tabs[TabROIFinder] = TabROIFinder(self.session, self.root, self.tabMain)
        #self.tabs[TabAnalysis] = TabAnalysis(self.session, self.root, self.tabMain)
        for t in self.tabs.values(): t.init()
        self.tabMain.select(self.tabs[TabImage].tab)
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.tabMain.pack(expand=1, fill="both")

        # Events and main loop
        window_events.WindowLoadedEvent(session=self.session)
        self.root.after(1000, lambda: window_events.WindowTKReadyEvent(session=self.session))
        self.root.mainloop()

    # Update handling

    def invoke_tab_update_event(self, event: TabUpdateEvent) -> Task:
        """ Notify each tab about the given TabUpdateEvent """
        if isinstance(event, ImageChangedEvent):
            imgObj =  self.session.active_image_object
            if imgObj is not None and imgObj.img is not None:
                self.set_window_title(imgObj.name or "")
                _size = round(sys.getsizeof(imgObj.img_raw)/(1024**2),2)
                self.statusbar.status_text = f"Image of shape {imgObj.img.shape} and size {_size} MB"
            else:
                self.statusbar.status_text = ""
            self.update_menu()
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

    def update_menu(self):
        if self.session.active_image_object is None:
            return

        if self.session.active_image_object._img_diff_conv_func != denoising.combined_diff_convolution:
            return
        


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
        self.session.window = None
        logger.debug(f"Closed the Neurotorch GUI")
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

    def menu_file_open_click(self, noisy:bool=False):
        image_path = filedialog.askopenfilename(parent=self.root, title="Open a Image File", 
                filetypes=(("All files", "*.*"), ("TIF File", "*.tif *.tiff"), ("ND2 Files (NIS Elements)", "*.nd2")) )
        if image_path is None or image_path == "":
            return
        imgObj = ImageObject()
        task = imgObj.open_file(Path(image_path), precompute=True, run_async=True)
        task.add_callback(lambda: self.session.set_active_image_object(imgObj))
        task.set_error_callback(self._open_image_error_callback)
    
    def menu_file_close_click(self):
        self.session.set_active_image_object(None)

    def menu_export_click(self, what: Literal["img", "img_diff", "img_only_signal", "img_without_signal"]):
        if self.session.active_image_object is None:
            messagebox.showwarning("Neurotorch", "You must open a file before you can export the video")
            return
        if what == "img" and self.session.active_image_object.img is None:
            messagebox.showwarning("Neurotorch", "You must open a file before you can export the video")
            return
        elif what == "img_diff" and self.session.active_image_object.img_diff is None:
            messagebox.showwarning("Neurotorch", "You must open a file before you can export the video")
            return
        elif what == "img_only_signal" and self.session.active_image_object.signal_obj.img_props_only_signal.img is None:
            messagebox.showwarning("Neurotorch", "The video without signal would be empty. Try to adjust the signal settings")
            return
        elif what == "img_without_signal" and self.session.active_image_object.signal_obj.img_props_without_signal.img is None:
            messagebox.showwarning("Neurotorch", "The video including only the signal would be empty. Try to adjust the signal settings")
            return
        ini_dir = self.session.active_image_object.path.parent if self.session.active_image_object.path is not None else platformdirs.user_downloads_path()
        ini_file = self.session.active_image_object.name_without_extension if self.session.active_image_object.name_without_extension is not None else "export"
        if what == "img_diff":
            ini_file += "_delta"
        elif what == "img_only_signal":
            ini_file += "_only_stimulation"
        elif what == "img_without_signal":
            ini_file += "_without_stimulation"
        elif what != "img":
            raise RuntimeError(f"Invalid parameter '{what}'")
        
        path = filedialog.asksaveasfilename(title="Neurotorch: Export video", initialdir=ini_dir, initialfile=ini_file, filetypes=ImageObject.SUPPORTED_EXPORT_EXTENSIONS, defaultextension="*.tiff")
        if not path:
            return
        path = Path(path)
        try:
            if what == "img":
                self.session.active_image_object.export_img(path)
            elif what == "img_diff":
                self.session.active_image_object.export_img_diff(path)
            elif what == "img_only_signal":
                self.session.active_image_object.signal_obj.export_img_only_signal(path)
            elif what == "img_without_signal":
                self.session.active_image_object.signal_obj.export_img_without_signal(path)
        except UnsupportedExtensionError:
            messagebox.showerror("Neurotorch: Export video", f"Failed to export the video: The file type '{path.suffix}' is not supported")
        except Exception:
            logger.error("Failed to export the video:", exc_info=True)
            messagebox.showerror("Neurotorch: Export video", f"Failed to export the video. For details see the logs")
        else:
            messagebox.showinfo("Neurotorch: Export video", f"Successfully exported video '{path.name}'")

    def set_img_diff_convolution_xy(self, func: Callable|None, args: dict = {}):
        imgObj = self.session.active_image_object
        if imgObj is None or imgObj.img_diff is None:
            self.root.bell()
            return
        
        if imgObj._img_diff_conv_func != denoising.combined_diff_convolution:
            imgObj.set_diff_conv_func(denoising.combined_diff_convolution, 
                                      func_args={"xy_kernel_fn": None, "xy_kernel_args": {}, 
                                                 "t_kernel_fn": None, "t_kernel_args": {},
                                                 "std_norm": True})

        imgObj.update_diff_conv_args(xy_kernel_fn = func, xy_kernel_args = args)
        imgObj.precompute_image().add_callback(lambda: self.invoke_tab_update_event(ImageChangedEvent()))

    def set_img_diff_convolution_t(self, func: Callable|None, args: dict = {}):
        imgObj = self.session.active_image_object
        if imgObj is None or imgObj.img_diff is None:
            self.root.bell()
            return
        
        if imgObj._img_diff_conv_func != denoising.combined_diff_convolution:
            imgObj.set_diff_conv_func(denoising.combined_diff_convolution, 
                                      func_args={"xy_kernel_fn": None, "xy_kernel_args": {}, 
                                                 "t_kernel_fn": None, "t_kernel_args": {},
                                                 "std_norm": True})

        imgObj.update_diff_conv_args(t_kernel_fn = func, t_kernel_args = args)
        imgObj.precompute_image().add_callback(lambda: self.invoke_tab_update_event(ImageChangedEvent()))

    def set_img_diff_std_norm(self, std_norm: bool) -> None:
        imgObj = self.session.active_image_object
        if imgObj is None or imgObj.img_diff is None:
            self.root.bell()
            return
        
        if imgObj._img_diff_conv_func != denoising.combined_diff_convolution:
            imgObj.set_diff_conv_func(denoising.combined_diff_convolution, 
                                      func_args={"xy_kernel_fn": None, "xy_kernel_args": {}, 
                                                 "t_kernel_fn": None, "t_kernel_args": {},
                                                 "std_norm": True})

        imgObj.update_diff_conv_args(std_norm= std_norm)
        imgObj.precompute_image().add_callback(lambda: self.invoke_tab_update_event(ImageChangedEvent()))

    def menu_image_clear_cache_click(self):
        if self.session.active_image_object is None:
            self.root.bell()
            return    
        self.session.active_image_object.clear_cache(full_clear=True)
        logger.debug("Cleared ImageObject cache")

    def menu_image_denoise_image_click(self, enable: bool):
        if self.session.active_image_object is None:
            self.root.bell()
            return
        self.root.bell()
        # if self.session.active_image_object._img_conv_func is None:
        #     self.session.active_image_object.set_conv_func(denoising.cumsum_denoise, func_args=None)
        # else:
        #     self.session.active_image_object.set_conv_func(None, None)
        # self.session.active_image_object.precompute_image().add_callback(lambda: self.invoke_tab_update_event(ImageChangedEvent()))

    def menu_neurotorch_about_click(self):
        messagebox.showinfo("Neurotorch", f"© Andreas Brilka 2025\nYou are running Neurotorch {__version__}")

    def menu_neurotorch_logs_click(self):
        if sys.platform.startswith('darwin'):  # macOS
            subprocess.Popen(['open', settings.log_path], start_new_session=True)
        elif os.name == 'nt':  # Windows
            os.startfile(settings.log_path)
        elif os.name == 'posix':  # Linux / Unix-Systeme
            subprocess.Popen(['xdg-open', filepath], start_new_session=True)

    def menu_debug_load_peaks_click(self):
        path = settings.app_data_path / "img_peaks.dump"
        if not path.exists() or not path.is_file():
            if self.root is not None:
                self.root.bell()
            else:
                logger.warning(f"Failed to load '{path.name}': The path does not exist")
            return
        
        with open(path, 'rb') as f:
            _img = pickle.load(f)
            _name = "img_peaks.dump"
            imgObj = ImageObject()
            task = imgObj.set_image_precompute(img=_img, name=_name, run_async=False)
            task.add_callback(lambda: self.session.set_active_image_object(imgObj))
            task.set_error_callback(self._open_image_error_callback)

    def menu_debug_save_peaks_click(self):
        if self.session.active_image_object is None:
            if self.root is not None:
                self.root.bell()
            else:
                logger.warning(f"Can't save the current dump as no video is opened")
            return
        _img = self.session.active_image_object.signal_obj.img_props_only_signal.img
        if _img is None:
            if self.root is not None:
                messagebox.showwarning(f"Can't save the current dump of peak frames as it would be empty. Check if you have peak frames")
            else:
                logger.warning(f"Can't save the current dump as the signal slice would be empty")
            return
        if self.root is not None and not messagebox.askyesnocancel("Neurotorch", f"Do you want to save the current video as a dump containing only the peak frames?"):
            return
        savePath = settings.app_data_path / "img_peaks.dump"
        with open(savePath, 'wb') as f:
            pickle.dump(_img, f, protocol=pickle.HIGHEST_PROTOCOL)
        logger.info(f"Saved the delta video dump to APPDATA/img_peaks.dump")

    def menu_debug_enable_debugging_click(self):
        logs.start_debugging()

    def menu_debug_test(self):
        def test(self):
            print(1/0)
        t = threading.Thread(target=test)
        t.start()


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
from neurotorchmz.gui.tab2 import TabSignal
from neurotorchmz.gui.tab3 import TabROIFinder
# from neurotorchmz.gui.tabAnalysis import TabAnalysis