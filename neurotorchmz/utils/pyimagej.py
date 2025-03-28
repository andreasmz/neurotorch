from ..core.session import *
from ..core.task_system import Task
from .synapse_detection import *

import tkinter as tk
from tkinter import messagebox, filedialog
import os
import numpy as np
import xarray
from pathlib import Path

class ImageJHandler:
    """
        Provides a connection between Neurotorch and Fiji/ImageJ using pyimageJ
    """

    def __init__(self, session: Session):
        self.ij = None
        self.session = session
        self.task: Task|None = None
        self.root: tk.Tk|None = self.session.root

        # Java imports from ImageJ
        self.OvalRoi = None # jimport('ij.gui.OvalRoi')
        self.PolygonRoi = None # jimport('ij.gui.PolygonRoi')
        self.Roi = None # self.Roi = jimport('ij.gui.Roi')
        self.IJ_Plugin_Duplicator = None

        # Image J Objects
        self.RM = None # Roi Manager

    def MenubarImageJH(self, menubar: tk.Menu):
        """ Creates a menu with ImageJ commands in the supplied menubar by the GUI """
        self.menubar = menubar
        self.menuImageJ = tk.Menu(self.menubar,tearoff=0)
        self.menubar.add_cascade(label="ImageJ",menu=self.menuImageJ)
        self.menuImageJ.add_command(label="Start ImageJ", state="normal", command=self.StartImageJ)
        self.menuImageJ.add_separator()
        self.menuImageJ.add_command(label="ImageJ --> Neurotorch", state="disabled", command=self.LoadImage)
        self.menuExportImg = tk.Menu(self.menuImageJ,tearoff=0)
        self.menuImageJ.add_cascade(label="Img --> ImageJ", menu=self.menuExportImg, state="disabled")
        self.menuExportImg.add_command(label="As Wrapper (faster loading, less memory)", command=lambda: self.ExportToImageJ_Img(asCopy=False))
        self.menuExportImg.add_command(label="As Copy (faster on live measurements)", command=lambda: self.ExportToImageJ_Img(asCopy=True))
        self.menuExportImgDiff = tk.Menu(self.menuImageJ,tearoff=0)
        self.menuImageJ.add_cascade(label="ImgDiff --> ImageJ", menu=self.menuExportImgDiff, state="disabled")
        self.menuExportImgDiff.add_command(label="As Wrapper (faster loading, less memory)", command=lambda: self.ExportToImageJ_ImgDiff(asCopy=False))
        self.menuExportImgDiff.add_command(label="As Copy (faster on live measurements)", command=lambda: self.ExportToImageJ_ImgDiff(asCopy=True))

        self.menuImageJ.add_separator()
        self.menuImageJ.add_command(label="Locate Installation", state="normal", command=self.MenuLocateInstallation_Click)

    def StartImageJ(self):
        """ Starts ImageJ """
        try:
            from scyjava import jimport
            import imagej
        except ModuleNotFoundError as ex:
            log_exception_debug(ex, "ModuleImport Error trying to import ImageJ")
            messagebox.showerror("Neurotorch", "It seems that pyimagej is not installed")
            return
        if (path_imagej := Settings.GetSettings("ImageJ_Path")) is None or not (path_imagej := Path(Settings.GetSettings("ImageJ_Path"))).exists() or not path_imagej.is_dir():
            logger.warning(f"Failed to locate ImageJ at {path_imagej}")
            messagebox.showerror("Neurotorch", "Can't locate your local Fiji/ImageJ installation. Please set the path to your installation via the menubar and try again")
            return
        
        if self.task is not None:
            logger.debug("ImageJ is already running")
            messagebox.showerror("Neurotorch", "ImageJ has already been started")
            return

        def _StartImageJ_Thread(task: Task, path_imagej: Path):
            try:
                self.ij = imagej.init(path_imagej, mode='interactive')
                self.OvalRoi = jimport('ij.gui.OvalRoi')
                self.PolygonRoi = jimport('ij.gui.PolygonRoi')
                self.Roi = jimport('ij.gui.Roi')
                self.IJ_Plugin_Duplicator = jimport('ij.plugin.Duplicator')
                self.ij.ui().showUI()
            except TypeError as ex:
                task.error = True
                log_exception_debug(ex, "TypeError trying to start Fiji/ImageJ")
                messagebox.showerror("Neurotorch", f"Failed to start Fiji/ImageJ. Did you previously loaded an ND2 file (or any other Bioformat)? Then this my have crashed the Java instance. Try to restart Neurotorch and start Fiji/ImageJ BEFORE opening an ND2 file")
                return
            self._ImageJReady()
            logger.debug(f"Imported ImageJ and its dependencies")

        self.menuImageJ.entryconfig("Start ImageJ", state="disabled")
        self.task = Task(_StartImageJ_Thread, "starting Fiji/ImageJ").set_indeterminate().set_error_callback(self._LoadingErrorCallback)
        self.task.start(path_imagej=path_imagej)

    def _LoadingErrorCallback(self, ex: Exception):
        self.menuImageJ.entryconfig("Start ImageJ", state="normal")
        self.task = None
        if isinstance(ex, Exception):
            log_exception_debug(ex, "Failed to start ImageJ")
            messagebox.showerror("Neurotorch", f"Failed to start Fiji/ImageJ. See the logs for more details")

    def LoadImage(self) -> Task:
        """ Load an image from ImageJ into Neurotorch """
        if self.ij is None:
            messagebox.showerror("Neurotorch", "Please first start ImageJ")
            return
        _img = self.ij.py.active_xarray()
        _imgIP = self.ij.py.active_imageplus()
        if _img is None or _imgIP is None:
            if self.root is not None:
                self.root.bell()
            return
        _name = "ImageJ Img"
        if hasattr(_imgIP, 'getShortTitle'):
            _name = str(_imgIP.getShortTitle())
        _img = np.array(_img)
        imgObj = ImageObject()
        task = imgObj.SetImagePrecompute(img=_img, name=_name, run_async=True)
        task.add_callback(lambda: self.session.set_active_image_object(imgObj))
        task.set_error_callback(self.session.window._open_image_error_callback)
        return task.start()

    def ExportToImageJ_Img(self, asCopy = False):
        """ Export the active image to ImageJ """
        if self.ij is None:
            messagebox.showerror("Neurotorch", "Please first start ImageJ")
            return
        if self.session.active_image_object is None or self.session.active_image_object.img is None:
            if self.root is not None:
                self.root.bell()
            return
        xImg = xarray.DataArray(self.session.active_image_object.img, name=f"{self.session.active_image_object.name}", dims=("pln", "row", "col"))
        javaImg = self.ij.py.to_imageplus(xImg)
        if asCopy:
            javaImg = self.IJ_Plugin_Duplicator().run(javaImg)
        self.ij.ui().show(javaImg)    
        min = self.session.active_image_object.imgProps.minClipped
        max = self.session.active_image_object.imgProps.max
        self.ij.py.run_macro(f"setMinAndMax({min}, {max});")

    def ExportToImageJ_ImgDiff(self, asCopy = False):
        """ Export the active imageDiff to ImageJ"""
        if self.ij is None:
            messagebox.showerror("Neurotorch", "Please first start ImageJ")
            return
        if self.session.active_image_object is None or self.session.active_image_object.imgDiff is None:
            if self.root is not None:
                self.root.bell()
            return
        xDiffImg = xarray.DataArray(np.clip(self.session.active_image_object.imgDiff, a_min=0, a_max=None).astype("uint16"), name=f"{self.session.active_image_object.name} (diff)", dims=("pln", "row", "col"))
        javaDiffImg = self.ij.py.to_imageplus(xDiffImg)
        if asCopy:
            javaDiffImg = self.IJ_Plugin_Duplicator().run(javaDiffImg)
        self.ij.ui().show(javaDiffImg)
        min = self.session.active_image_object.imgDiffProps.minClipped
        max = self.session.active_image_object.imgDiffProps.max
        self.ij.py.run_macro(f"setMinAndMax({min}, {max});")

    def ImportROIS(self) -> tuple[list[ISynapseROI], list[str]]|None:
        """ Import ROIs from ImageJ """
        if self.ij is None:
            messagebox.showerror("Neurotorch", "Please first start ImageJ")
            return None
        self.OpenRoiManager()
        _warningFlags = []
        ij_rois = self.RM.getRoisAsArray() 
        rois = []
        names = []
        for roi in ij_rois:
            name = str(roi.getName())
            if not isinstance(roi, self.OvalRoi):
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
            if not messagebox.askyesnocancel("Neurotorch", f"Please note the following before import the ROIs:\n\n {'\n'.join(["  " + x for x in _warningFlags])}\n\nDo you want to proceed?"):
                return None
        return (rois, names)

    def ExportROIs(self, synapses: list[ISynapse]):
        """ Export ISynapses (and their ROIs) to ImageJ """
        if self.ij is None:
            messagebox.showerror("Neurotorch", "Please first start ImageJ")
            return
        if synapses is None or len(synapses) == 0:
            if self.root is not None:
                self.root.bell()
            return
        self.OpenRoiManager()

        if len([s for s in synapses if len(s.rois) > 1]) != 0:
            if not messagebox.askyesnocancel("Neurotorch", "Your export selection contains synapses with more than one ROI which can not be exported. Do you want to continue anyway?"):
                return
        i_synapse = 1
        for synapse in synapses:
            name = synapse.name
            if synapse.name is None:
                name = f"Synapse {i_synapse}"
                i_synapse += 1
            if not len(synapse.rois) == 1:
                continue
            roi = synapse.rois[0]
            if roi.location is None: continue
            name += " (" + roi.location_string.replace(",","|").replace(" ","") + ")"
            
            if isinstance(roi, CircularSynapseROI):
                if roi.radius is None: continue
                roi = self.OvalRoi(roi.location[0]-roi.radius, roi.location[1]-roi.radius, 2*roi.radius+1, 2*roi.radius+1)
                roi.setName(name)
                self.RM.addRoi(roi)
            elif isinstance(roi, PolygonalSynapseROI):
                if roi.polygon is None: continue
                roi = self.PolygonRoi(roi.polygon[:, 0]+0.5, roi.polygon[:, 1]+0.5, self.Roi.POLYGON)
                roi.setName(name)
                self.RM.addRoi(roi)
            else:
                continue

    def OpenRoiManager(self):
        """ Opens the ROI Manager """
        if self.ij is None:
            messagebox.showerror("Neurotorch", "Please first start ImageJ")
            return
        self.ij.py.run_macro("roiManager('show all');")
        self.RM = self.ij.RoiManager.getRoiManager()
        
    def MenuLocateInstallation_Click(self):
        """ Opens a window to locate the installation. """
        if self.root is None:
            raise RuntimeError("Can't call this function when in headless mode")
        _path = filedialog.askopenfilename(parent=self.root, title="Locate your local Fiji/ImageJ installation", 
                filetypes=(("ImageJ-win64.exe (Windows)", "*.exe"), ("Fiji.app (MacOS)", "*.app")))
        if _path is None or _path == "":
            return
        _path = Path(_path)
        if _path.suffix == ".exe":
            _path = _path.parent
        Settings.SetSetting("ImageJ_Path", str(_path))

    def _ImageJReady(self):
        """ Internal function. Called, when ImageJ is successfully loaded """
        self.menuImageJ.entryconfig("ImageJ --> Neurotorch", state="normal")
        self.menuImageJ.entryconfig("Img --> ImageJ", state="normal")
        self.menuImageJ.entryconfig("ImgDiff --> ImageJ", state="normal")
