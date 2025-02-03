from .image import ImgObj
from .synapse_detection import *
from ..gui.settings import Neurotorch_Settings as Settings
from ..gui.window import Neurotorch_GUI
from ..gui.components.general import Job


import traceback
import tkinter as tk
from tkinter import messagebox, filedialog
import os, threading
import numpy as np
import xarray

class ImageJHandler:
    def __init__(self, gui: Neurotorch_GUI):
        self._gui = gui
        self.root = gui.root
        self.ij = None
        self.job = None

        # Java imports from ImageJ
        self.OvalRoi = None # jimport('ij.gui.OvalRoi')
        self.PolygonRoi = None # jimport('ij.gui.PolygonRoi')
        self.Roi = None # self.Roi = jimport('ij.gui.Roi')
        self.IJ_Plugin_Duplicator = None

        # Image J Objects
        self.RM = None # Roi Manager

    def MenubarImageJH(self, menubar):
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
        try:
            from scyjava import jimport
            import imagej
        except ModuleNotFoundError as ex:
            print(ex)
            messagebox.showerror("Neurotorch", "It seems that pyimagej is not installed")
            return
        if Settings.GetSettings("ImageJ_Path") is None or (not os.path.exists(Settings.GetSettings("ImageJ_Path"))):
            messagebox.showerror("Neurotorch", "Can't locate your local Fiji/ImageJ installation. Please set the path to your installation via the menubar and try again")
            return
        
        if self.job is not None:
            messagebox.showerror("Neurotorch", "ImageJ has already been started")
            return

        def _StartImageJ_Thread(job: Job):
            try:
                _path = Settings.GetSettings("ImageJ_Path")
                self.ij = imagej.init(_path, mode='interactive')
                self.OvalRoi = jimport('ij.gui.OvalRoi')
                self.PolygonRoi = jimport('ij.gui.PolygonRoi')
                self.Roi = jimport('ij.gui.Roi')
                self.IJ_Plugin_Duplicator = jimport('ij.plugin.Duplicator')
            except TypeError as ex:
                messagebox.showerror("Neurotorch", f"Failed to start Fiji/ImageJ. Did you previously loaded an ND2 file (or any other Bioformat)? Then this my have crashed the Java instance. Try to restart Neurotorch and start Fiji/ImageJ BEFORE opening an ND2 file")
                self.menuImageJ.entryconfig("Start ImageJ", state="normal")
                job.SetStopped("Failed to start Fiji/ImageJ")
                return
            except Exception as ex:
                messagebox.showerror("Neurotorch", f"Failed to start Fiji/ImageJ. The error was '{ex}' and the traceback\n{traceback.format_exc()}")
                self.menuImageJ.entryconfig("Start ImageJ", state="normal")
                job.SetStopped("Failed to start Fiji/ImageJ")
                return
            self.ij.ui().showUI()
            self._ImageJReady()
            job.SetStopped("Fiji/ImageJ started")

        self.menuImageJ.entryconfig("Start ImageJ", state="disabled")
        self.job = Job(steps=0)
        self.job.SetProgress(0, "Starting Fiji/ImageJ")
        self._gui.statusbar.AddJob(self.job)
        threading.Thread(target=_StartImageJ_Thread, args=(self.job,), daemon=True, name="Neurotorch_ImageJThread").start()


    def LoadImage(self):
        if self.ij is None:
            messagebox.showerror("Neurotorch", "Please first start ImageJ")
            return
        _img = self.ij.py.active_xarray()
        _imgIP = self.ij.py.active_imageplus()
        if _img is None or _imgIP is None:
            self.root.bell()
            return
        _name = "ImageJ Img"
        if hasattr(_imgIP, 'getShortTitle'):
            _name = str(_imgIP.getShortTitle())
        _img = np.array(_img)
        ImgObj().SetImagePrecompute(img=_img, name=_name, callback=self._gui._OpenImage_Callback, errorcallback=self._gui._OpenImage_CallbackError)

    def ExportToImageJ_Img(self, asCopy = False):
        if self.ij is None:
            messagebox.showerror("Neurotorch", "Please first start ImageJ")
            return
        if self._gui.ImageObject is None or self._gui.ImageObject.img is None:
            self.root.bell()
            return
        xImg = xarray.DataArray(self._gui.ImageObject.img, name=f"{self._gui.ImageObject.name}", dims=("pln", "row", "col"))
        javaImg = self.ij.py.to_imageplus(xImg)
        if asCopy:
            javaImg = self.IJ_Plugin_Duplicator().run(javaImg)
        self.ij.ui().show(javaImg)    
        min = self._gui.ImageObject.imgProps.minClipped
        max = self._gui.ImageObject.imgProps.max
        self.ij.py.run_macro(f"setMinAndMax({min}, {max});")

    def ExportToImageJ_ImgDiff(self, asCopy = False):
        if self.ij is None:
            messagebox.showerror("Neurotorch", "Please first start ImageJ")
            return
        if self._gui.ImageObject is None or self._gui.ImageObject.imgDiff is None:
            self.root.bell()
            return
        xDiffImg = xarray.DataArray(np.clip(self._gui.ImageObject.imgDiff, a_min=0, a_max=None).astype("uint16"), name=f"{self._gui.ImageObject.name} (diff)", dims=("pln", "row", "col"))
        javaDiffImg = self.ij.py.to_imageplus(xDiffImg)
        if asCopy:
            javaDiffImg = self.IJ_Plugin_Duplicator().run(javaDiffImg)
        self.ij.ui().show(javaDiffImg)
        min = self._gui.ImageObject.imgDiffProps.minClipped
        max = self._gui.ImageObject.imgDiffProps.max
        self.ij.py.run_macro(f"setMinAndMax({min}, {max});")

    def ImportROIS(self) -> list[ISynapseROI]|None:
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
            _cr =  CircularSynapseROI().SetLocation(int(round(center[0],0)), int(round(center[1], 0))).SetRadius(r)
            rois.append(_cr)
            names.append(name)
        if len(_warningFlags) > 0:
            if not messagebox.askyesnocancel("Neurotorch", f"Please note the following before import the ROIs:\n\n {'\n'.join(["  " + x for x in _warningFlags])}\n\nDo you want to proceed?"):
                return None
        return (rois, names)

    def ExportROIs(self, synapses: list[ISynapse]):
        if self.ij is None:
            messagebox.showerror("Neurotorch", "Please first start ImageJ")
            return
        if synapses is None or len(synapses) == 0:
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
            name += " (" + roi.LocationStr().replace(",","|").replace(" ","") + ")"
            
            if isinstance(roi, CircularSynapseROI):
                if roi.radius is None: continue
                roi = self.OvalRoi(roi.location[0]-roi.radius, roi.location[1]-roi.radius, 2*roi.radius+1, 2*roi.radius+1)
                roi.setName(name)
                self.RM.addRoi(roi)
            elif isinstance(roi, PolygonalSynapseROI):
                if roi.polygon is None: continue
                roi = self.PolygonRoi(roi.polygon[:, 0]+0.5, roi.polygon[:, 1]+0.5, self._gui.ijH.Roi.POLYGON)
                roi.setName(name)
                self.RM.addRoi(roi)
            else:
                continue

    def OpenRoiManager(self):
        self.ij.py.run_macro("roiManager('show all');")
        self.RM = self.ij.RoiManager.getRoiManager()
        
    def MenuLocateInstallation_Click(self):
        _path = filedialog.askopenfilename(parent=self.root, title="Locate your local Fiji/ImageJ installation", 
                filetypes=(("ImageJ-win64.exe", "*.exe"), ))
        if _path is None or _path == "":
            return
        if _path.endswith(".exe"):
            _path = os.path.dirname(_path)
        Settings.SetSetting("ImageJ_Path", _path)

    def _ImageJReady(self):
        self.menuImageJ.entryconfig("ImageJ --> Neurotorch", state="normal")
        self.menuImageJ.entryconfig("Img --> ImageJ", state="normal")
        self.menuImageJ.entryconfig("ImgDiff --> ImageJ", state="normal")
