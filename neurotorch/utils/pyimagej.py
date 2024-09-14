import neurotorch.gui.settings as settings
import neurotorch.gui.window as window

import tkinter as tk
from tkinter import ttk, messagebox
import sys, os, threading
import numpy as np
import xarray
from scyjava import jimport
import imagej

class ImageJHandler:
    def __init__(self, gui: window._GUI):
        self._gui = gui
        self.root = gui.root
        self.IMG = gui.IMG
        self.imageJReady = False
        self.ij_load = False
        self.OvalRoi = None
        self.RM = None
        self.menubar = None

    def MenubarImageJH(self, menubar):
        self.menubar = menubar
        self.menuImageJ = tk.Menu(self.menubar,tearoff=0)
        self.menubar.add_cascade(label="ImageJ",menu=self.menuImageJ)
        self.menuImageJ.add_command(label="Start ImageJ", state="normal", command=self.StartImageJ)
        self.menuImageJ.add_command(label="Read Image from ImageJ", state="disabled", command=self.LoadImage)
        self.menuImageJ.add_separator()
        self.menuImageJ.add_command(label="Img --> ImageJ", state="disabled", command=self.ExportToImageJ_Img)
        self.menuImageJ.add_command(label="DiffImg --> ImageJ", state="disabled", command=self.ExportToImageJ_ImgDiff)

    def LoadImage(self):
        if self._gui.ij is None:
            messagebox.showerror("Glutamate Roi Finder", "Please first start ImageJ")
            return
        self._img = self._gui.ij.py.active_xarray()
        if self._img is None:
            self._gui.lblStatusInfo["text"] = "Please first select an image in ImageJ"
            return
        self._gui.lblStatusInfo["text"] = ""
        
        self._img = np.array(self._img).astype("int16")
        _name = self._img.name if hasattr(self._img, 'name') else "ImageJ Img"
        if not self.IMG.SetIMG(self._img, _name):
            self._gui.lblStatusInfo["text"] = "Your image has an invalid shape"
            return

        _size = round(sys.getsizeof(self.IMG.img)/(1024**2),2)
        self._gui.lblImgInfo["text"] = f"Image: {self.IMG.img.shape}, dtype={self.IMG.img.dtype}, size = {_size} MB"
        self._gui.NewImageProvided()

    def ExportToImageJ_Img(self):
        if self._gui.ij is None:
            messagebox.showerror("Glutamate Roi Finder", "Please first start ImageJ")
            return
        if self._gui.IMG.img is None:
            self.root.bell()
            return
        xImg = xarray.DataArray(np.clip(self._gui.IMG.img, a_min=0, a_max=None).astype("uint16"), name=f"{self._gui.IMG.name}", dims=("pln", "row", "col"))
        javaImg = self._gui.ij.py.to_java(xImg)
        self._gui.ij.ui().show(javaImg)

    def ExportToImageJ_ImgDiff(self):
        if self._gui.ij is None:
            messagebox.showerror("Glutamate Roi Finder", "Please first start ImageJ")
            return
        if self._gui.IMG.imgDiff is None:
            self.root.bell()
            return
        xDiffImg = xarray.DataArray(np.clip(self._gui.IMG.imgDiff, a_min=0, a_max=None).astype("uint16"), name=f"{self._gui.IMG.name} (diff)", dims=("pln", "row", "col"))
        javaDiffImg = self._gui.ij.py.to_java(xDiffImg)
        self._gui.ij.ui().show(javaDiffImg)
        min = self._gui.IMG.imgDiff_Stats["AbsMin"]
        max = self._gui.IMG.imgDiff_Stats["Max"]
        self._gui.ij.py.run_macro(f"setMinAndMax({min}, {max});")

    def StartImageJ(self):
        if (not os.path.exists(settings.UserSettings.imageJPath)):
            messagebox.showerror("Glutamate Roi Finder", "The given ImageJ path doesn't exist")
            return

        self._gui.lblProgMain["text"] = "Starting ImageJ..."
        self.menuImageJ.entryconfig("Start ImageJ", state="disabled")

        self.ij_load = True
        def _ProgStartingImgJ_Step():
            self._gui.progMain.step(10)
            if self.ij_load is True:
                self.root.after(50, _ProgStartingImgJ_Step)
            else:
                self._gui.progMain.configure(mode="determinate")
                self._gui.varProgMain.set(0)
                self._gui.lblProgMain["text"] = ""

        self._gui.progMain.configure(mode="indeterminate")
        _ProgStartingImgJ_Step()
        
        self.ijthread = threading.Thread(target=self._StartImageJ)
        self.ijthread.start()

    def OpenRoiManager(self):
        self._gui.ij.py.run_macro("roiManager('show all');")
        self.RM = self._gui.ij.RoiManager.getRoiManager()
        #if (self.RM is None):
        #    messagebox.showwarning("Neurotorch", "Attention: Is the ROI Manager in ImageJ opened? If not, open it now or ImageJ will prompt out an error message refusing to open the ROIManager until restart of Neurotorch")

    def _StartImageJ(self):
        if (self.imageJReady or not self.ij_load):
            self.ij_load = False
            return
        try:
            self._gui.ij = imagej.init(settings.UserSettings.imageJPath, mode='interactive')
            self.OvalRoi = jimport('ij.gui.OvalRoi')
        except:
            messagebox.showerror("Neurotorch", "Failed to start ImageJ. Did you specifed the right path in user/settings.json?")
            self.ij_load = False
            self.menuImageJ.entryconfig("Start ImageJ", state="normal")
            return
        #self.RM = jimport("ij.plugin.frame.RoiManager")
        
        self.ij_load = False
        self._gui.ij.ui().showUI()
        self._ImageJReady()

    def _ImageJReady(self):
        self.menuImageJ.entryconfig("Read Image from ImageJ", state="normal")
        self.menuImageJ.entryconfig("Img --> ImageJ", state="normal")
        self.menuImageJ.entryconfig("DiffImg --> ImageJ", state="normal")