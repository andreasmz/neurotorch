import neurotorch.gui.window as window

import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib import cm
import numpy as np

class Tab1():
    def __init__(self, gui: window._GUI):
        self._gui = gui
        self.root = gui.root
        self.imshow2D = None
        self.imshow3D = None
        self.Init()

    def Init(self):
        self.tab = ttk.Frame(self._gui.tabMain)
        self._gui.tabMain.add(self.tab, text="Image")

        self.frameRadioImageMode = tk.Frame(self.tab)
        self.radioDisplayVar = tk.StringVar(value="imgMean")
        self.radioDisplay1 = tk.Radiobutton(self.frameRadioImageMode, variable=self.radioDisplayVar, indicatoron=False, command=self.Update, text="Image mean (imgMean)", value="imgMean")
        self.radioDisplay1b = tk.Radiobutton(self.frameRadioImageMode, variable=self.radioDisplayVar, indicatoron=False, command=self.Update, text="Image standard deviation (imgStd)", value="imgStd")
        self.radioDisplay2 = tk.Radiobutton(self.frameRadioImageMode, variable=self.radioDisplayVar, indicatoron=False, command=self.Update, text="Difference Image Maximum (diffImgMax)", value="diffMax")
        self.radioDisplay3 = tk.Radiobutton(self.frameRadioImageMode, variable=self.radioDisplayVar, indicatoron=False, command=self.Update, text="Difference Image Std (diffImgStd)", value="diffStd")
        #self.radioDisplay4 = tk.Radiobutton(self.frameRadioImageMode, variable=self.radioDisplayVar, indicatoron=False, command=self.Update, text="2nd Derivative Maximum", value="diff2Max")
        #self.radioDisplay5 = tk.Radiobutton(self.frameRadioImageMode, variable=self.radioDisplayVar, indicatoron=False, command=self.Update, text="2nd Derivative Std", value="diff2Std")
        self.radioDisplay1.grid(row=0, column=0)
        self.radioDisplay1b.grid(row=0, column=1)
        self.radioDisplay2.grid(row=0, column=2)
        self.radioDisplay3.grid(row=0, column=3)
        #self.radioDisplay4.grid(row=0, column=4)
        #self.radioDisplay5.grid(row=0, column=5)
        self.frameRadioImageMode.pack()

        self.frameMainDisplay = tk.Frame(self.tab)
        self.frameMainDisplay.pack(expand=True, fill="both")
        self.frameMetadata = tk.LabelFrame(self.frameMainDisplay,  text="Metadata")
        self.frameMetadata.pack(side=tk.LEFT, fill="y", padx=10)
        self.treeMetadata = ttk.Treeview(self.frameMetadata, columns=("Value"))
        self.treeMetadata.pack(expand=True, fill="y", padx=2)
        self.treeMetadata.heading('#0', text="Property")
        self.treeMetadata.heading('Value', text='Value')
        self.treeMetadata.column("#0", minwidth=0, width=120)
        self.treeMetadata.column("Value", minwidth=0, width=200)

        self.notebookPlots = ttk.Notebook(self.frameMainDisplay)
        self.notebookPlots.bind('<<NotebookTabChanged>>',self.Update)
        self.tab2D = ttk.Frame(self.notebookPlots)
        self.tab3D = ttk.Frame(self.notebookPlots)
        self.notebookPlots.add(self.tab2D, text="2D")
        self.notebookPlots.add(self.tab3D, text="3D")
        self.notebookPlots.pack(side=tk.LEFT, expand=True, fill="both")

        self.figure2D = plt.Figure(figsize=(6,6), dpi=100)
        self.figure2D.tight_layout()
        self.ax2D = self.figure2D.add_subplot()  
        self.ax2D.set_axis_off()
        self.canvas2D = FigureCanvasTkAgg(self.figure2D, self.tab2D)
        self.canvtoolbar2D = NavigationToolbar2Tk(self.canvas2D,self.tab2D)
        self.canvtoolbar2D.update()
        self.canvas2D.get_tk_widget().pack(fill="both", expand=True)
        self.canvas2D.draw()

        self.figure3D = plt.Figure(figsize=(6,6), dpi=100)
        self.figure3D.tight_layout()
        self.ax3D = self.figure3D.add_subplot(projection='3d')  
        self.canvas3D = FigureCanvasTkAgg(self.figure3D, self.tab3D)
        self.canvtoolbar3D = NavigationToolbar2Tk(self.canvas3D,self.tab3D)
        self.canvtoolbar3D.update()
        self.canvas3D.get_tk_widget().pack(fill="both", expand=True)
        self.canvas3D.draw()

    def Update(self, newImage=False):
        if newImage:
            self.ax2D.clear()
            self.ax3D.clear()
            self.ax2D.set_axis_off()
            self.imshow2D = None
            self.imshow3D = None
            self.treeMetadata.delete(*self.treeMetadata.get_children())
            if self._gui.pimsObj is not None:
                if hasattr(self._gui.pimsObj, "metadata"):
                    try:
                        for propFunc in dir(self._gui.pimsObj.metadata):
                            k = propFunc
                            v = ""
                            try:
                                v = getattr(self._gui.pimsObj.metadata, propFunc)(0)
                            except Exception as exx:
                                pass
                            try:
                                v = getattr(self._gui.pimsObj.metadata, propFunc)(0, 0)
                            except Exception as exx:
                                pass
                            self.treeMetadata.insert('', 'end', text=k, values=([v]))
                    except Exception as ex:
                        print(ex)
                else:
                    print("Image has not metdata") 
        _selected = self.radioDisplayVar.get()
        if self.imshow2D is not None:
            self.imshow2D.remove()
            self.imshow2D = None
        if self.imshow3D is not None:
            self.imshow3D.remove()
            self.imshow3D = None

        if (self._gui.IMG.img is None):
            self.canvas2D.draw()
            self.canvas3D.draw()
            return
        match (_selected):
            case "imgMean":
                self.ax2D.set_axis_on()
                self.imshow2D = self.ax2D.imshow(self._gui.IMG.imgMean, cmap="Greys_r")
            case "imgStd":
                self.ax2D.set_axis_on()
                self.imshow2D = self.ax2D.imshow(self._gui.IMG.imgStd, cmap="Greys_r")
            case "diffMax":
                self.ax2D.set_axis_on()
                self.imshow2D = self.ax2D.imshow(self._gui.IMG.imgDiffMaxTime, cmap="inferno")
            case "diffStd":
                self.ax2D.set_axis_on()
                self.imshow2D = self.ax2D.imshow(self._gui.IMG.imgDiffStdTime, cmap="inferno")
            case "diff2Max":
                self.ax2D.set_axis_on()
                self.imshow2D = self.ax2D.imshow(self._gui.IMG.imgDiff2MaxTime, cmap="inferno")
            case "diff2Std":
                self.ax2D.set_axis_on()
                self.imshow2D = self.ax2D.imshow(self._gui.IMG.imgDiff2StdTime, cmap="inferno")
            case _:
                self.ax2D.set_axis_off()

        if (self.notebookPlots.tab(self.notebookPlots.select(), "text") == "2D"):
            self.canvas2D.draw()
            return
        if self.notebookPlots.tab(self.notebookPlots.select(), "text") != "3D":
            print("Assertion Error: The tabMain value is not 2D or 3D")

        X = np.arange(0,self._gui.IMG.imgDiff.shape[2])
        Y = np.arange(0,self._gui.IMG.imgDiff.shape[1])
        X, Y = np.meshgrid(X, Y)
        match (_selected):
            case "imgMean":
                self.imshow3D = self.ax3D.plot_surface(X,Y, self._gui.IMG.imgMean, cmap="Greys_r")
            case "imgStd":
                self.imshow3D = self.ax3D.plot_surface(X,Y, self._gui.IMG.imgStd, cmap="Greys_r")
            case "diffMax":
                self.imshow3D = self.ax3D.plot_surface(X,Y, self._gui.IMG.imgDiffMaxTime, cmap="inferno")
            case "diffStd":
                self.imshow3D = self.ax3D.plot_surface(X,Y, self._gui.IMG.imgDiffStdTime, cmap="inferno")
            case "diff2Max":
                self.imshow3D = self.ax3D.plot_surface(X,Y, self._gui.IMG.imgDiff2MaxTime, cmap="inferno")
            case "diff2Std":
                self.imshow3D = self.ax3D.plot_surface(X,Y, self._gui.IMG.imgDiff2StdTime, cmap="inferno")
            case _:
                pass
        
        self.canvas2D.draw()
        self.canvas3D.draw()
