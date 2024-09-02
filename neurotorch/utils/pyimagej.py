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
        if not self.IMG.SetIMG(self._img):
            self._gui.lblStatusInfo["text"] = "Your image has an invalid shape"
            return

        _size = round(sys.getsizeof(self.IMG)/(1024**2),2)
        self._gui.lblImgInfo["text"] = f"Image: {self.IMG.img.shape}, dtype={self.IMG.img.dtype}, size = {_size} MB"
        self._gui.NewImageProvided()

    def ImageJImport_ImgDiff(self):
        if self._gui.ij is None:
            messagebox.showerror("Glutamate Roi Finder", "Please first start ImageJ")
            return
        xDiffImg = xarray.DataArray(self.IMG.imgDiff, name="diffImg", dims=("t", "y", "x"))
        javaDiffImg = self._gui.ij.py.to_java(xDiffImg)

    def StartImageJ(self):
        if (not os.path.exists(settings.UserSettings.imageJPath)):
            messagebox.showerror("Glutamate Roi Finder", "The given ImageJ path doesn't exist")
            return

        self._gui.lblProgMain["text"] = "Starting ImageJ..."
        self._gui.menuImageJ.entryconfig("Start ImageJ", state="disabled")

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
        if self.RM is None:
            self.RM = self._gui.ij.RoiManager.getRoiManager()
        #if (self.RM is None):
        #    messagebox.showwarning("Neurotorch", "Attention: Is the ROI Manager in ImageJ opened? If not, open it now or ImageJ will prompt out an error message refusing to open the ROIManager until restart of Neurotorch")

    def _StartImageJ(self):
        if (self.imageJReady or not self.ij_load):
            self.ij_load = False
            return
        self._gui.ij = imagej.init(settings.UserSettings.imageJPath, mode='interactive')
        #self.RM = jimport("ij.plugin.frame.RoiManager")
        self.OvalRoi = jimport('ij.gui.OvalRoi')
        self.ij_load = False
        self._gui.ij.ui().showUI()
        self._ImageJReady()

    def _ImageJReady(self):
        self._gui.menuImageJ.entryconfig("Read Image from ImageJ", state="normal")
        self._gui.menuImageJ.entryconfig("DiffImg --> ImageJ", state="normal")