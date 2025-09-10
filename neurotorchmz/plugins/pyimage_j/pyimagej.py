from neurotorchmz.core.session import *
from neurotorchmz.gui import events as window_events

import numpy as np
import xarray
from pathlib import Path
import shutil
import imagej

plugin_module = plugin_manager.get_module()

class ImageJHandler:
    """
        Provides a connection between Neurotorch and Fiji/ImageJ using pyimageJ
    """

    ij = None
    OvalRoi = None # jimport('ij.gui.OvalRoi')
    PolygonRoi = None # jimport('ij.gui.PolygonRoi')
    Roi = None # ImageJHandler.Roi = jimport('ij.gui.Roi')
    RoiManager = None # ImageJHandler.RoiManager = jimport('ij.plugin.frame.RoiManager')
    RM = None # Roi Manager
    IJ_Plugin_Duplicator = None
    headless: bool = False
    ij_start_task: Task|None = None

    def __init__(self, session: Session):
        self.session = session
        window_events.WindowLoadedEvent.register(self.on_window_loaded)
        window_events.SynapseTreeviewContextMenuEvent.register(self.on_synapse_tv_context_menu_create)

    # Convinience functions
    @property
    def root(self) -> "tk.Tk | None":
        return self.session.root
    
    # Event hooks

    def on_window_loaded(self, e: "window_events.WindowLoadedEvent") -> None:
        """ Creates the GUI elements for this plugin. Is only called from WindowLoadedEvent in GUI mode """
        global tk, messagebox, filedialog, window, TabROIFinder_InvalidateEvent
        global plugin_module
        assert e.session.window is not None

        import tkinter as tk
        from tkinter import messagebox, filedialog
        from neurotorchmz.gui import window
        from neurotorchmz.gui.tab3 import TabROIFinder_InvalidateEvent

        self.plugin_menu = e.menu_plugins(plugin_module)

        self.menu_export_img = tk.Menu(e.session.window.menu_file_export, tearoff=0)
        self.menu_export_img_diff = tk.Menu(e.session.window.menu_file_export, tearoff=0)
        self.menu_settings = tk.Menu(e.session.window.menu_settings, tearoff=0)
        e.session.window.menu_file_import.add_command(label="From Fiji/ImageJ (video)", command=self.import_image, state="disabled")
        e.session.window.menu_file_import.add_command(label="From Fiji/ImageJ (ROIs)", command=self.import_rois_into_roifinder, state="disabled")

        e.session.window.menu_file_export.add_cascade(label="To Fiji/ImageJ (video)", menu=self.menu_export_img, state="disabled")
        e.session.window.menu_file_export.add_cascade(label="To Fiji/ImageJ (delta video)", menu=self.menu_export_img_diff, state="disabled")
        e.session.window.menu_file_export.add_command(label="To Fiji/ImageJ (ROIs)", command=self.export_rois_from_roifinder, state="disabled")
        
        e.session.window.menu_settings.add_cascade(label="Fiji/ImageJ bridge", menu=self.menu_settings)

        self.menu_export_img.add_command(label="As wrapper (faster loading, less memory)", command=lambda: self.export_img(asCopy=False))
        self.menu_export_img.add_command(label="As copy (faster on live measurements)", command=lambda: self.export_img(asCopy=True))
        self.menu_export_img_diff.add_command(label="As wrapper (faster loading, less memory)", command=lambda: self.export_img_diff(asCopy=False))
        self.menu_export_img_diff.add_command(label="As copy (faster on live measurements)", command=lambda: self.export_img_diff(asCopy=True))

        self.plugin_menu.add_command(label="Open ROI Manager", command=self.open_roi_manager, state="disabled")

        e.session.window.menu_run.add_command(label="Start Fiji/ImageJ", command=self.menu_start_imageJ_click)
        self.menu_settings.add_command(label="Locate installation", command=self.menu_locate_installation_click)
        self.menu_settings.add_command(label="Test installation", command=self.menu_locate_installation_click)
    
    # ImageJ bridge

    def start_imageJ(self, headless: bool = False):
        global jimport
        from scyjava import jimport
        """ Starts pyImageJ and connects to the local installation. Before start, the installation is rudimentary checked"""
        if ImageJHandler.ij is not None:
            logger.warning(f"Failed to start Fiji/ImageJ: An instance is already running")
            if self.root is not None:
                messagebox.showwarning("Neurotorch: Fiji/ImageJ bridge", "Failed to start Fiji/ImageJ: An instance is already running")
            return
    
        if not self.validate_imagej_path() and self.root is not None:
            self.ask_for_imagej_path()
        if not self.validate_imagej_path():
            logger.warning(f"Failed to start Fiji/ImageJ: The provided path seems to be invalid")
            return
                
        java_installed = self.test_for_java()
        maven_installed = self.test_for_maven()
        missing_components = []
        if not java_installed:
            missing_components.append("open-jdk")
        if not maven_installed:
            missing_components.append("apache-maven")

        if len(missing_components) > 0:
            for mc in missing_components:
                logger.warning(f"Failed to locate '{mc}'. Check if the binaries are included in PATH")
            if self.root is not None:
                messagebox.showwarning("Neurotorch: Fiji/ImageJ bridge", "To connect to Fiji/ImageJ, open-jdk and apache-maven are needed. "
                                       + "But the following components are missing on your system:\n\n"
                                       + '\n'.join(["\t- " + mc for mc in missing_components])
                                       + "\n\nYou can install them for example from https://www.microsoft.com/openjdk and https://maven.apache.org/. "
                                       + "For more details, refer to the documentation " + settings.documentation_url)
            return
        
        if ImageJHandler.ij_start_task is not None:
            logger.warning("Failed to start the Fiji/ImageJ bridge: An instance is already running")
            if self.root is not None:
                messagebox.showinfo("Neurotorch: Fiji/ImageJ bridge", "Failed to start Fiji/ImageJ: An instance is already running")
            return
        
        ImageJHandler.headless = headless

        def _start_imageJ_Thread(task: Task, path_imagej: Path):
            try:
                ImageJHandler.ij = imagej.init(path_imagej, mode=(imagej.Mode.HEADLESS if headless else imagej.Mode.INTERACTIVE), add_legacy=False)
                if not ImageJHandler.ij:
                    return
                ImageJHandler.OvalRoi = jimport('ij.gui.OvalRoi')
                ImageJHandler.PolygonRoi = jimport('ij.gui.PolygonRoi')
                ImageJHandler.Roi = jimport('ij.gui.Roi')
                ImageJHandler.RoiManager = jimport('ij.plugin.frame.RoiManager')
                ImageJHandler.IJ_Plugin_Duplicator = jimport('ij.plugin.Duplicator')
                if not headless:
                    ImageJHandler.ij.ui().showUI() # type: ignore
            except Exception as ex:
                logger.error("Failed to start Fiji/ImageJ:", exc_info=True)
                task.error = Exception("Failed to start Fiji/ImageJ")
                if self.root is not None:
                    messagebox.showerror("Neurotorch: Fiji/ImageJ bridge", f"Failed to start Fiji/ImageJ. See the logs / console output for more details")
                return
            self._imageJ_ready()
            logger.debug(f"Imported ImageJ and its dependencies")

        if self.session.window is not None:
            self.session.window.menu_run.entryconfig("Start Fiji/ImageJ", state="disabled")
        ImageJHandler.ij_start_task = Task(_start_imageJ_Thread, "starting Fiji/ImageJ").set_indeterminate().set_error_callback(self._loading_error_callback)
        ImageJHandler.ij_start_task.start(path_imagej=settings.UserSettings.IMAGEJ.imagej_path.get())

    def validate_imagej_path(self) -> bool:
        path = settings.UserSettings.IMAGEJ.imagej_path.get()
        return path is not None and path.exists() and path.is_dir() and (path / "jars").exists()
    
    def ask_for_imagej_path(self) -> None:
        if self.root is None:
            raise RuntimeError("Can not call ask_for_imagej_path() when in headless mode")
        if not self.validate_imagej_path():
            if messagebox.askyesno("Neurotorch: Fiji/ImageJ bridge", "To connect to Fiji/ImageJ, you must link Neurotorch to your local Fiji/ImageJ installation." 
                                   + " Do you want to select the path now?", icon="question", default="yes"):
                self.menu_locate_installation_click()

    def test_for_java(self) -> bool:
        java_path = shutil.which("java")
        return java_path is not None
    
    def test_for_maven(self) -> bool:
        maven_path = shutil.which("mvn")
        return maven_path is not None

    def import_image(self) -> Task|None:
        """ Load an image from ImageJ into Neurotorch """
        if ImageJHandler.ij is None:
            logger.warning(f"Attempted to import from Fiji/ImageJ before it was initialized. Run start_imageJ() first")
            if self.root is not None:
                messagebox.showerror("Neurotorch", "Fiji/ImageJ must first be started before it can be used")
            return None
        _img = ImageJHandler.ij.py.active_xarray()
        _imgIP = ImageJHandler.ij.py.active_imageplus()
        if _img is None or _imgIP is None:
            if self.root is not None:
                self.root.bell()
            return
        _name = "ImageJ Img"
        if hasattr(_imgIP, 'getTitle'):
            _name = str(_imgIP.getTitle())
        _name_without_extension = None
        if hasattr(_imgIP, 'getShortTitle'):
            _name_without_extension = str(_imgIP.getShortTitle())
        _img = np.array(_img)
        imgObj = ImageObject()
        task = imgObj.set_image_precompute(img=_img, name=_name, name_without_extension=_name_without_extension, run_async=True)
        task.add_callback(lambda: self.session.set_active_image_object(imgObj))
        if self.session.window is not None:
            task.set_error_callback(self.session.window._open_image_error_callback)
        logger.info(f"Imported '{_name}' from Fiji/ImageJ")
        return task.start()

    def export_img(self, asCopy = False) -> None:
        """ Export the active image to ImageJ """
        if ImageJHandler.ij is None:
            logger.warning(f"Attempted to export to Fiji/ImageJ before it was initialized. Run start_imageJ() first")
            if self.root is not None:
                messagebox.showerror("Neurotorch", "Fiji/ImageJ must first be started before it can be used")
            return None
        imgObj = self.session.active_image_object
        if imgObj is None or imgObj.img is None:
            if self.root is not None:
                self.root.bell()
            return
        xImg = xarray.DataArray(imgObj.img, name=f"{imgObj.name}", dims=("pln", "row", "col"))
        javaImg = ImageJHandler.ij.py.to_imageplus(xImg)
        if asCopy:
            javaImg = ImageJHandler.IJ_Plugin_Duplicator().run(javaImg) # type: ignore
        min = imgObj.img_props.minClipped
        max = imgObj.img_props.max
        if not ImageJHandler.headless:
            ImageJHandler.ij.ui().show(javaImg)  
            ImageJHandler.ij.py.run_macro(f"setMinAndMax({min}, {max});")
        logger.info(f"Exported image '{imgObj.name}' to Fiji/ImageJ")

    def export_img_diff(self, asCopy = False) -> None:
        """ Export the active imageDiff to ImageJ"""
        if ImageJHandler.ij is None:
            logger.warning(f"Attempted to export to Fiji/ImageJ before it was initialized. Run start_imageJ() first")
            if self.root is not None:
                messagebox.showerror("Neurotorch", "Fiji/ImageJ must first be started before it can be used")
            return None
        imgObj = self.session.active_image_object
        if imgObj is None or imgObj.img_diff is None:
            if self.root is not None:
                self.root.bell()
            return
        xDiffImg = xarray.DataArray(np.clip(imgObj.img_diff, a_min=0, a_max=None).astype("uint16"), name=f"{imgObj.name} (diff)", dims=("pln", "row", "col"))
        javaDiffImg = ImageJHandler.ij.py.to_imageplus(xDiffImg)
        if asCopy:
            javaDiffImg = ImageJHandler.IJ_Plugin_Duplicator().run(javaDiffImg) # type: ignore
        
        min = imgObj.img_diff_props.minClipped
        max = imgObj.img_diff_props.max
        if not ImageJHandler.headless:
            ImageJHandler.ij.ui().show(javaDiffImg)
            ImageJHandler.ij.py.run_macro(f"setMinAndMax({min}, {max});")
        logger.info(f"Exported img_diff '{imgObj.name}' to Fiji/ImageJ")

    def import_rois(self) -> list[tuple[ISynapseROI, str]]|None:
        """ Import ROIs from ImageJ """
        if ImageJHandler.ij is None:
            raise RuntimeError("Attempted to import ROIs from Fiji/ImageJ before it was initialized. Run start_imageJ() first")
        self.open_roi_manager()
        _warningFlags = []
        ij_rois = ImageJHandler.RM.getRoisAsArray()  # type: ignore
        rois: list[tuple[ISynapseROI, str]] = []
        for roi in ij_rois:
            name = str(roi.getName())
            if not isinstance(roi, ImageJHandler.OvalRoi): # type: ignore
                _warningFlags.append(f"{name}: Can't import non oval shapes and therefore skipped this ROIs")
                continue
            if (roi.getFloatHeight() - roi.getFloatWidth()) > 1e-6:
                _warningFlags.append(f"{name}: The ROI is oval, but will be imported as circular ROI")
            x,y = int(roi.getXBase()), int(roi.getYBase())
            h,w = int(roi.getFloatHeight()), int(roi.getFloatWidth())
            r = int((h+w)/4-1/2)
            center = (x + (w-1)/2, y + (h-1)/2)
            _cr =  CircularSynapseROI().set_location(x=int(round(center[0],0)), y=int(round(center[1], 0))).set_radius(r)
            rois.append((_cr, name))
        if len(_warningFlags) > 0:
            flag_str = '\n'.join(['- ' + x for x in _warningFlags])
            if self.root is not None:
                if messagebox.askyesnocancel("Neurotorch", f"Please note the following before import the ROIs:\n\n {flag_str}\n\nDo you want to proceed?"):
                    return None
            else:
                logger.warning(f"Importing ROIs from ImageJ raised the following warnings:\n{flag_str}")
        logger.info(f"Imported {len(rois)} ROIs from ImageJ")
        return rois

    def export_synapses(self, synapses: list[ISynapse]):
        """ Export ISynapses (and their ROIs) to ImageJ """
        if ImageJHandler.ij is None:
            raise RuntimeError("Attempted to import ROIs from Fiji/ImageJ before it was initialized. Run start_imageJ() first")
        self.open_roi_manager()

        if len([s for s in synapses if len(s.rois) > 1]) != 0:
            logger.warning(f"Fiji/ImageJ bridge: Tried to export incompatible ROIs")
            if self.root is not None:
                if not messagebox.askyesnocancel("Neurotorch", "Your export selection contains synapses with more than one ROI which can not be exported. Do you want to continue anyway?"):
                    return
        i_synapse = 1
        roi_count = 0
        for synapse in synapses:
            name = synapse.name
            if name is None:
                name = f"Synapse {i_synapse}"
                i_synapse += 1
            if not len(synapse.rois) == 1:
                continue
            roi = synapse.rois[0]
            if roi.location is None: continue
            name += " (" + roi.location_string.replace(",","|").replace(" ","") + ")"
            
            if isinstance(roi, CircularSynapseROI):
                if roi.radius is None: continue
                roi = ImageJHandler.OvalRoi(roi.location[1]-roi.radius, roi.location[0]-roi.radius, 2*roi.radius+1, 2*roi.radius+1) # type: ignore
                roi.setName(name)
                roi.setPosition(0)
                ImageJHandler.RM.addRoi(roi) # type: ignore
                roi_count += 1
            elif isinstance(roi, PolygonalSynapseROI):
                if roi.polygon is None: continue
                roi.polygon
                roi = roi = ImageJHandler.PolygonRoi(roi.polygon[:, 1]+0.5, roi.polygon[:, 0]+0.5, ImageJHandler.Roi.POLYGON) # type: ignore
                roi.setName(name)
                roi.setPosition(0)
                ImageJHandler.RM.addRoi(roi) # type: ignore
                roi_count += 1
            else:
                continue
        ImageJHandler.ij.py.run_macro("roiManager('Remove Slice Info');")
        logger.info(f"Exported {roi_count} ROIs to Fiji/ImageJ")

    def import_rois_into_roifinder(self):
        rois = self.import_rois()
        if rois is None or len(rois) == 0:
            if self.root is not None:
                self.root.bell()
            return
        synapses = [SingleframeSynapse(r).set_name(name) for r,name in rois]
        self.session.roifinder_detection_result.extend(synapses)

    def export_rois_from_roifinder(self) -> None:
        synapses = self.session.roifinder_detection_result.to_list()
        self.export_synapses(synapses)

    def open_roi_manager(self) -> None:
        """ Opens the ROI Manager """
        if ImageJHandler.ij is None or ImageJHandler.RoiManager is None:
            logger.warning(f"Fiji/ImageJ bridge: Attempted to open the ROI manager before ij was initialized. Run start_imageJ() first")
            if self.root is not None:
                messagebox.showerror("Neurotorch", "Fiji/ImageJ must first be started before it can be used")
            return None
        if not ImageJHandler.headless:
            ImageJHandler.ij.py.run_macro("roiManager('show all');")
        ImageJHandler.RM = ImageJHandler.RoiManager.getInstance()
        #ImageJHandler.RM = ImageJHandler.ij.RoiManager.getRoiManager()

    # GUI functions

    def menu_start_imageJ_click(self) -> None:
        """ Menu button click for starting Fiji/ImageJ """
        if self.root is None:
            raise RuntimeError("Can't call this function when in headless mode")
        if not self.validate_imagej_path():
            self.ask_for_imagej_path()
        if not self.validate_imagej_path():
            return
        self.start_imageJ()

    def menu_locate_installation_click(self):
        """ Opens a window to locate the installation. """
        if self.root is None:
            raise RuntimeError("Can't call this function when in headless mode")
        _path = settings.UserSettings.IMAGEJ.imagej_path.get()
        if _path is None or not _path.exists():
            _path = settings.platformdirs.user_desktop_path()
        elif _path.is_file():
            _path = _path.parent
        _path = filedialog.askdirectory(parent=self.root, title="Locate your Fiji/ImageJ installation by selecting the Fiji.app folder", 
                                        mustexist=True, initialdir=_path)
        if _path is None or _path == "":
            return
        _path = Path(_path)
        settings.UserSettings.IMAGEJ.imagej_path.set(_path, save=True)
        if not self.validate_imagej_path():
            if messagebox.askretrycancel("Neurotorch: Select Fiji/ImageJ path", "The provided path seems to be invalid. Do you want to retry?"):
                self.menu_locate_installation_click()

    def menu_test_installation_click(self) -> None:
        self.ask_for_imagej_path()
        if not self.validate_imagej_path():
            return
        java_installed = self.test_for_java()
        maven_installed = self.test_for_maven()
        missing_components = []
        if not java_installed:
            missing_components.append("open-jdk")
        if not maven_installed:
            missing_components.append("apache-maven")

        if len(missing_components) > 0:
            for mc in missing_components:
                logger.warning(f"Failed to locate '{mc}'. Check if the binaries are included in PATH")
            if self.root is not None:
                messagebox.showwarning("Neurotorch: Fiji/ImageJ bridge", "To connect to Fiji/ImageJ, open-jdk and apache-maven are needed. "
                                       + "But the following components are missing on your system:\n\n"
                                       + '\n'.join(["\t- " + mc for mc in missing_components])
                                       + "\n\nYou can install them for example from https://www.microsoft.com/openjdk and https://maven.apache.org/. "
                                       + "For more details, refer to the documentation " + settings.documentation_url)
        else:
            messagebox.showinfo(f"Neurotorch: Fiji/ImageJ bridge", "Fiji/ImageJ, open-jdk and apacha maven are ready")

    # Synapse Treeview

    def on_synapse_tv_context_menu_create(self, e: "window_events.SynapseTreeviewContextMenuEvent"):
        e.import_context_menu.add_command(label="Import from Fiji/ImageJ", command=self.import_rois_into_roifinder)
        e.export_context_menu.add_command(label="Export to Fiji/ImageJ", command=self.export_rois_from_roifinder)

    # Callbacks

    def _imageJ_ready(self):
        """ Internal callback triggered when ImageJ is successfully loaded """
        ImageJHandler.ij_start_task = None
        if self.session.window is None:
            return
        self.session.window.menu_file_import.entryconfig("From Fiji/ImageJ (video)", state="normal")
        self.session.window.menu_file_import.entryconfig("From Fiji/ImageJ (ROIs)", state="normal")
        self.session.window.menu_file_export.entryconfig("To Fiji/ImageJ (video)", state="normal")
        self.session.window.menu_file_export.entryconfig("To Fiji/ImageJ (delta video)", state="normal")
        self.session.window.menu_file_export.entryconfig("To Fiji/ImageJ (ROIs)", state="normal")
        self.plugin_menu.entryconfig("Open ROI Manager", state="normal")

    def _loading_error_callback(self, ex: Exception):
        """ Internal callback on an error when loading ImageJ to reset the start Button"""
        if self.session.window is not None:
            self.session.window.menu_run.entryconfig("Start Fiji/ImageJ", state="normal")
        ImageJHandler.ij_start_task = None

@SessionCreateEvent.hook
def on_session_created(e: SessionCreateEvent):
    global ijH
    ijH = ImageJHandler(e.session)