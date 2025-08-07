from neurotorchmz.core.session import *

import tkinter as tk
from tkinter import messagebox, filedialog
import numpy as np
import xarray
from pathlib import Path
import shutil

class ImageJHandler:
    """
        Provides a connection between Neurotorch and Fiji/ImageJ using pyimageJ
    """

    def __init__(self, session: Session):
        self.ij = None
        self.session = session
        self.task: Task|None = None

        # Java imports from ImageJ
        self.OvalRoi = None # jimport('ij.gui.OvalRoi')
        self.PolygonRoi = None # jimport('ij.gui.PolygonRoi')
        self.Roi = None # self.Roi = jimport('ij.gui.Roi')
        self.IJ_Plugin_Duplicator = None

        # Image J Objects
        self.RM = None # Roi Manager

        events.WindowLoadedEvent.register(self.on_window_loaded)

    # Convinience functions
    @property
    def root(self) -> tk.Tk | None:
        return self.session.root
    
    # Event hooks

    def on_window_loaded(self, e: events.WindowLoadedEvent) -> None:
        """ Creates the GUI elements for this plugin. Is only called from WindowLoadedEvent in GUI mode """
        assert e.session.window is not None

        self.menu_export_img = tk.Menu(e.session.window.menu_file_export, tearoff=0)
        self.menu_export_img_diff = tk.Menu(e.session.window.menu_file_export, tearoff=0)
        self.menu_settings = tk.Menu(e.session.window.menu_settings, tearoff=0)
        e.session.window.menu_file_import.add_command(label="From Fiji/ImageJ", command=self.import_image, state="disabled")
        e.session.window.menu_file_export.add_cascade(label="To Fiji/ImageJ (video)", menu=self.menu_export_img, state="disabled")
        e.session.window.menu_file_export.add_cascade(label="To Fiji/ImageJ (delta video)", menu=self.menu_export_img_diff, state="disabled")
        e.session.window.menu_settings.add_cascade(label="Fiji/ImageJ bridge", menu=self.menu_settings)

        self.menu_export_img.add_command(label="As wrapper (faster loading, less memory)", command=lambda: self.export_img(asCopy=False))
        self.menu_export_img.add_command(label="As copy (faster on live measurements)", command=lambda: self.export_img(asCopy=True))
        self.menu_export_img_diff.add_command(label="As wrapper (faster loading, less memory)", command=lambda: self.export_img_diff(asCopy=False))
        self.menu_export_img_diff.add_command(label="As copy (faster on live measurements)", command=lambda: self.export_img_diff(asCopy=True))

        e.session.window.menu_run.add_command(label="Start Fiji/ImageJ", command=self.menu_start_imageJ_click)
        self.menu_settings.add_command(label="Locate installation", command=self.menu_locate_installation_click)
    
    # ImageJ bridge

    def start_imageJ(self):
        """ Starts pyImageJ and connects to the local installation. Before start, the installation is rudimentary checked"""
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

        if self.ij is not None:
            messagebox.showwarning("Neurotorch: Fiji/ImageJ bridge", "Failed to start Fiji/ImageJ: An instance is already running")
            return

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
        
        try:
            from scyjava import jimport
            import imagej
        except ModuleNotFoundError as ex:
            logger.error("Failed to start the Fiji/ImageJ bridge: pyimagej seems to be not installed", exc_info=True)
            messagebox.showerror("Neurotorch: Fiji/ImageJ bridge", "It seems that pyimagej is not installed")
            return
        
        if self.task is not None:
            logger.warning("Failed to start the Fiji/ImageJ bridge: An instance is already running")
            messagebox.showinfo("Neurotorch: Fiji/ImageJ bridge", "Failed to start Fiji/ImageJ: An instance is already running")
            return

        def _start_imageJ_Thread(task: Task, path_imagej: Path):
            try:
                self.ij = imagej.init(path_imagej, mode='interactive', add_legacy=False)
                if not self.ij:
                    return
                self.OvalRoi = jimport('ij.gui.OvalRoi')
                self.PolygonRoi = jimport('ij.gui.PolygonRoi')
                self.Roi = jimport('ij.gui.Roi')
                self.IJ_Plugin_Duplicator = jimport('ij.plugin.Duplicator')
                self.ij.ui().showUI() # type: ignore
            except TypeError as ex:
                task.error = Exception("Failed to start Fiji/ImageJ")
                messagebox.showerror("Neurotorch", f"Failed to start Fiji/ImageJ. Did you previously loaded an ND2 file (or any other Bioformat)? Then this my have crashed the Java instance. Try to restart Neurotorch and start Fiji/ImageJ BEFORE opening an ND2 file")
                return
            self._imageJ_ready()
            logger.debug(f"Imported ImageJ and its dependencies")

        if self.session.window is not None:
            self.session.window.menu_run.entryconfig("Start Fiji/ImageJ", state="disabled")
        self.task = Task(_start_imageJ_Thread, "starting Fiji/ImageJ").set_indeterminate().set_error_callback(self._loading_error_callback)
        self.task.start(path_imagej=settings.UserSettings.IMAGEJ.imagej_path.get())

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
        assert self.session.window is not None
        if self.ij is None:
            logger.warning(f"Attempted to import from Fiji/ImageJ before it was initialized. Run start_imageJ() first")
            if self.session.window is not None:
                messagebox.showerror("Neurotorch", "Please first start ImageJ")
            return None
        _img = self.ij.py.active_xarray()
        _imgIP = self.ij.py.active_imageplus()
        if _img is None or _imgIP is None:
            if self.root is not None:
                self.root.bell()
            return
        _name = "ImageJ Img"
        if hasattr(_imgIP, 'getTitle'):
            _name = str(_imgIP.getTitle())
        _img = np.array(_img)
        imgObj = ImageObject()
        task = imgObj.SetImagePrecompute(img=_img, name=_name, run_async=True)
        task.add_callback(lambda: self.session.set_active_image_object(imgObj))
        task.set_error_callback(self.session.window._open_image_error_callback)
        logger.info(f"Imported '{_name}' from Fiji/ImageJ")
        return task.start()

    def export_img(self, asCopy = False):
        """ Export the active image to ImageJ """
        if self.ij is None:
            messagebox.showerror("Neurotorch", "Please first start ImageJ")
            return
        imgObj = self.session.active_image_object
        if imgObj is None or imgObj.img is None:
            if self.root is not None:
                self.root.bell()
            return
        xImg = xarray.DataArray(imgObj.img, name=f"{imgObj.name}", dims=("pln", "row", "col"))
        javaImg = self.ij.py.to_imageplus(xImg)
        if asCopy:
            javaImg = self.IJ_Plugin_Duplicator().run(javaImg) # type: ignore
        self.ij.ui().show(javaImg)    
        min = imgObj.imgProps.minClipped
        max = imgObj.imgProps.max
        self.ij.py.run_macro(f"setMinAndMax({min}, {max});")
        logger.info(f"Exported image '{imgObj.name}' to Fiji/ImageJ")

    def export_img_diff(self, asCopy = False):
        """ Export the active imageDiff to ImageJ"""
        if self.ij is None:
            messagebox.showerror("Neurotorch", "Please first start ImageJ")
            return
        imgObj = self.session.active_image_object
        if imgObj is None or imgObj.imgDiff is None:
            if self.root is not None:
                self.root.bell()
            return
        xDiffImg = xarray.DataArray(np.clip(imgObj.imgDiff, a_min=0, a_max=None).astype("uint16"), name=f"{imgObj.name} (diff)", dims=("pln", "row", "col"))
        javaDiffImg = self.ij.py.to_imageplus(xDiffImg)
        if asCopy:
            javaDiffImg = self.IJ_Plugin_Duplicator().run(javaDiffImg) # type: ignore
        self.ij.ui().show(javaDiffImg)
        min = imgObj.imgDiffProps.minClipped
        max = imgObj.imgDiffProps.max
        self.ij.py.run_macro(f"setMinAndMax({min}, {max});")
        logger.info(f"Exported image '{imgObj.name}' to Fiji/ImageJ")

    def import_rois(self) -> tuple[list[ISynapseROI], list[str]]|None:
        """ Import ROIs from ImageJ """
        if self.ij is None:
            messagebox.showerror("Neurotorch", "Please first start ImageJ")
            return None
        self.open_roi_manager()
        _warningFlags = []
        ij_rois = self.RM.getRoisAsArray()  # type: ignore
        rois = []
        names = []
        for roi in ij_rois:
            name = str(roi.getName())
            if not isinstance(roi, self.OvalRoi): # type: ignore
                _warningFlags.append(f"{name}: Can't import non oval shapes and therefore skipped this ROIs")
                continue
            if (roi.getFloatHeight() - roi.getFloatWidth()) > 1e-6:
                _warningFlags.append(f"{name}: The ROI is oval, but will be imported as circular ROI")
            x,y = int(roi.getXBase()), int(roi.getYBase())
            h,w = int(roi.getFloatHeight()), int(roi.getFloatWidth())
            r = int((h+w)/4-1/2)
            center = (x + (w-1)/2, y + (h-1)/2)
            _cr =  CircularSynapseROI().set_location(x=int(round(center[0],0)), y=int(round(center[1], 0))).set_radius(r)
            rois.append(_cr)
            names.append(name)
        if len(_warningFlags) > 0:
            flag_str = '\n'.join(['  ' + x for x in _warningFlags])
            if not messagebox.askyesnocancel("Neurotorch", f"Please note the following before import the ROIs:\n\n {flag_str}\n\nDo you want to proceed?"):
                return None
        return (rois, names)

    def export_rois(self, synapses: list[ISynapse]):
        """ Export ISynapses (and their ROIs) to ImageJ """
        if self.ij is None:
            messagebox.showerror("Neurotorch", "Please first start ImageJ")
            return
        if synapses is None or len(synapses) == 0:
            if self.root is not None:
                self.root.bell()
            return
        self.open_roi_manager()

        if len([s for s in synapses if len(s.rois) > 1]) != 0:
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
                roi = self.OvalRoi(roi.location[0]-roi.radius, roi.location[1]-roi.radius, 2*roi.radius+1, 2*roi.radius+1) # type: ignore
                roi.setName(name)
                self.RM.addRoi(roi) # type: ignore
                roi_count += 1
            elif isinstance(roi, PolygonalSynapseROI):
                if roi.polygon is None: continue
                roi = self.PolygonRoi(roi.polygon[:, 0]+0.5, roi.polygon[:, 1]+0.5, self.Roi.POLYGON) # type: ignore
                roi.setName(name)
                self.RM.addRoi(roi) # type: ignore
                roi_count += 1
            else:
                continue
        logger.info(f"Exported {roi_count} ROIs to Fiji/ImageJ")

    def open_roi_manager(self):
        """ Opens the ROI Manager """
        if self.ij is None:
            messagebox.showerror("Neurotorch", "Please first start ImageJ")
            return
        self.ij.py.run_macro("roiManager('show all');")
        self.RM = self.ij.RoiManager.getRoiManager()

    # GUI functions

    def menu_start_imageJ_click(self):
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

    # Callbacks

    def _imageJ_ready(self):
        """ Internal callback triggered when ImageJ is successfully loaded """
        assert self.session.window is not None
        self.session.window.menu_file_import.entryconfig("From Fiji/ImageJ", state="normal")
        self.session.window.menu_file_export.entryconfig("To Fiji/ImageJ (video)", state="normal")
        self.session.window.menu_file_export.entryconfig("To Fiji/ImageJ (delta video)", state="normal")

    def _loading_error_callback(self, ex: Exception):
        """ Internal callback on an error when loading ImageJ to reset the start Button"""
        if self.session.window is not None:
            self.session.window.menu_run.entryconfig("Start Fiji/ImageJ", state="normal")
        self.task = None

@events.SessionCreateEvent.hook
def on_session_created(e: events.SessionCreateEvent):
    global ijH
    ijH = ImageJHandler(e.session)