from .window import *

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends._backend_tk import NavigationToolbar2Tk
from mpl_toolkits.mplot3d.axes3d import Axes3D
import numpy as np
from typing import cast

class TabImage_ViewChangedEvent(TabUpdateEvent):
    pass

class TabImage(Tab):

    def __init__(self, session: Session, root:tk.Tk, notebook: ttk.Notebook):
        super().__init__(session, root, notebook, _tab_name="Tab Image")
        self.imshow2D = None
        self.imshow3D = None
        self.colorbar = None

    def init(self):
        self.notebook.add(self.tab, text="Image")
        #ToolTip(self.tab, msg=self.__doc__, follow=True, delay=0.1)

        self.frameRadioImageMode = tk.Frame(self.tab)
        self.radioDisplayVar = tk.StringVar(value="imgMean")
        self.radioDisplay1 = tk.Radiobutton(self.frameRadioImageMode, variable=self.radioDisplayVar, indicatoron=False, command=lambda:self.invoke_update(TabImage_ViewChangedEvent()), text="Original (mean)", value="imgMean")
        self.radioDisplay1b = tk.Radiobutton(self.frameRadioImageMode, variable=self.radioDisplayVar, indicatoron=False, command=lambda:self.invoke_update(TabImage_ViewChangedEvent()), text="Original (standard deviation)", value="imgStd")
        self.radioDisplay2 = tk.Radiobutton(self.frameRadioImageMode, variable=self.radioDisplayVar, indicatoron=False, command=lambda:self.invoke_update(TabImage_ViewChangedEvent()), text="Delta (maximum)", value="diffMax")
        self.radioDisplay3 = tk.Radiobutton(self.frameRadioImageMode, variable=self.radioDisplayVar, indicatoron=False, command=lambda:self.invoke_update(TabImage_ViewChangedEvent()), text="Delta (standard deviation)", value="diffStd")
        self.radioDisplay4 = tk.Radiobutton(self.frameRadioImageMode, variable=self.radioDisplayVar, indicatoron=False, command=lambda:self.invoke_update(TabImage_ViewChangedEvent()), text="Delta (maximum), signal frames removed", value="diffMaxWithoutSignal")
        self.radioDisplay1.grid(row=0, column=0)
        self.radioDisplay1b.grid(row=0, column=1)
        self.radioDisplay2.grid(row=0, column=2)
        self.radioDisplay3.grid(row=0, column=3)
        self.radioDisplay4.grid(row=0, column=4)
        self.frameRadioImageMode.pack()

        self.frameMainDisplay = tk.Frame(self.tab)
        self.frameMainDisplay.pack(expand=True, fill="both")
        self.frameMetadata = tk.LabelFrame(self.frameMainDisplay,  text="Metadata")
        self.frameMetadata.pack(side=tk.LEFT, fill="y")
        self.frameMetadataTop = tk.Frame(self.frameMetadata)
        self.frameMetadataTop.pack(expand=True, fill="both", padx=10)
        self.treeMetadata = ttk.Treeview(self.frameMetadataTop, columns=("Value"))
        self.treeMetadata.pack(expand=True, fill="y", padx=2, side=tk.LEFT)
        self.treeMetadata.heading('#0', text="Property")
        self.treeMetadata.heading('Value', text='Value')
        self.treeMetadata.column("#0", minwidth=0, width=200)
        self.treeMetadata.column("Value", minwidth=0, width=120)
        self.scrollTreeMetadata = ttk.Scrollbar(self.frameMetadataTop, orient="vertical", command=self.treeMetadata.yview)
        self.scrollTreeMetadata.pack(side=tk.LEFT, expand=True, fill="y")
        self.scrollXTreeMetadata = ttk.Scrollbar(self.frameMetadata, orient="horizontal", command=self.treeMetadata.xview)
        self.scrollXTreeMetadata.pack(fill="x")
        
        self.treeMetadata.configure(yscrollcommand=self.scrollTreeMetadata.set)
        self.treeMetadata.configure(xscrollcommand=self.scrollXTreeMetadata.set)


        self.notebookPlots = ttk.Notebook(self.frameMainDisplay)
        self.notebookPlots.bind('<<NotebookTabChanged>>',lambda _:self.invoke_update(TabImage_ViewChangedEvent()))
        self.tab2D = ttk.Frame(self.notebookPlots)
        self.tab3D = ttk.Frame(self.notebookPlots)
        self.notebookPlots.add(self.tab2D, text="2D")
        self.notebookPlots.add(self.tab3D, text="3D")
        self.notebookPlots.pack(side=tk.LEFT, expand=True, fill="both")

        self.figure2D = Figure(figsize=(6,6), dpi=100)
        self.figure2D.tight_layout()
        self.ax2D = self.figure2D.add_subplot()  
        self.ax2D.set_axis_off()
        self.canvas2D = FigureCanvasTkAgg(self.figure2D, self.tab2D)
        self.canvtoolbar2D = NavigationToolbar2Tk(self.canvas2D,self.tab2D)
        self.canvtoolbar2D.update()
        self.canvas2D.get_tk_widget().pack(fill="both", expand=True)
        self.canvas2D.draw()

        self.figure3D = Figure(figsize=(6,6), dpi=100)
        self.figure3D.tight_layout()
        self.ax3D = cast(Axes3D, self.figure3D.add_subplot(projection='3d'))
        self.canvas3D = FigureCanvasTkAgg(self.figure3D, self.tab3D)
        self.canvtoolbar3D = NavigationToolbar2Tk(self.canvas3D,self.tab3D)
        self.canvtoolbar3D.update()
        self.canvas3D.get_tk_widget().pack(fill="both", expand=True)
        self.canvas3D.draw()

    def update_tab(self, event: TabUpdateEvent):
        imgObj = self.session.active_image_object
        if not (isinstance(event, ImageChangedEvent) or isinstance(event, TabImage_ViewChangedEvent)):
            return
        if isinstance(event, ImageChangedEvent):
            if self.colorbar is not None:
                self.colorbar.remove()
                self.colorbar = None
            self.ax2D.clear()
            self.ax3D.clear()
            self.ax2D.set_axis_off()
            self.imshow2D = None
            self.imshow3D = None    
            self.treeMetadata.delete(*self.treeMetadata.get_children())
            if imgObj is not None:
                if imgObj.name is not None:
                    self.treeMetadata.insert('', 'end', text="Name", values=([imgObj.name]))
                if imgObj.path is not None:
                    self.treeMetadata.insert('', 'end', text="Path", values=([imgObj.path]))
                if imgObj.img is not None and imgObj.imgProps is not None:
                    self.treeMetadata.insert('', 'end', iid="providedImageData", text="Image Properties", open=True)
                    self.treeMetadata.insert('providedImageData', 'end', text="Frames", values=([imgObj.img.shape[0]]))
                    self.treeMetadata.insert('providedImageData', 'end', text="Width [px]", values=([imgObj.img.shape[2]]))
                    self.treeMetadata.insert('providedImageData', 'end', text="Height [px]", values=([imgObj.img.shape[1]]))
                    self.treeMetadata.insert('providedImageData', 'end', text="Numpy dtype", values=([imgObj.img.dtype]))
                    self.treeMetadata.insert('providedImageData', 'end', text="Maximum", values=([imgObj.imgProps.max]))
                    self.treeMetadata.insert('providedImageData', 'end', text="Minimum", values=([imgObj.imgProps.min]))
                    
                if imgObj.metadata is not None:
                    self.treeMetadata.insert('', 'end', iid="metadata", text="ND2 metadata", open=True)
                    self._insert_dict_into_tree(parent_node="metadata", d=imgObj.metadata, max_level_open=2)
                # if imgObj.pims_metadata is not None:
                #     self.treeMetadata.insert('', 'end', iid="pims_metadata", text="Metadata", open=False)
                #     for k,v in imgObj.pims_metadata.items():
                #         if "#" in k:
                #             continue
                #         self.treeMetadata.insert('pims_metadata', 'end', text=k, values=([v]))

        _selected = self.radioDisplayVar.get()
        if self.colorbar is not None:
            self.colorbar.remove()
            self.colorbar = None
        if self.imshow2D is not None:
            self.imshow2D.remove()
            self.imshow2D = None
        if self.imshow3D is not None:
            self.imshow3D.remove()
            self.imshow3D = None
        
        if imgObj is None or imgObj.img is None or imgObj.imgDiff is None:
            self.canvas2D.draw()
            self.canvas3D.draw()
            return
        match (_selected):
            case "imgMean":
                self.ax2D.set_axis_on()
                self.imshow2D = self.ax2D.imshow(imgObj.imgView(ImageView.SPATIAL).Mean, cmap="Greys_r") # type: ignore (imgView() is never None)
            case "imgStd":
                self.ax2D.set_axis_on()
                self.imshow2D = self.ax2D.imshow(imgObj.imgView(ImageView.SPATIAL).Std, cmap="Greys_r") # type: ignore (imgView() is never None)
            case "diffMax":
                self.ax2D.set_axis_on()
                self.imshow2D = self.ax2D.imshow(imgObj.imgDiffView(ImageView.SPATIAL).Max, cmap="inferno") # type: ignore (imgView() is never None)
            case "diffStd":
                self.ax2D.set_axis_on()
                self.imshow2D = self.ax2D.imshow(imgObj.imgDiffView(ImageView.SPATIAL).Std, cmap="inferno") # type: ignore (imgView() is never None)
            case "diffMaxWithoutSignal":
                if imgObj.signal_obj.imgObj_sliced and imgObj.signal_obj.imgObj_sliced.imgDiff is not None:
                    self.ax2D.set_axis_on()
                    self.imshow2D = self.ax2D.imshow(signalObj.imgObj_sliced.imgDiffView(ImageView.SPATIAL).Max, cmap="inferno") # type: ignore (imgView() is never None)
                else:
                    self.ax2D.set_axis_off()
            case _:
                self.ax2D.set_axis_off()
        if (self.notebookPlots.tab(self.notebookPlots.select(), "text") == "2D"):
            if self.imshow2D is not None:
                self.colorbar = self.figure2D.colorbar(self.imshow2D, ax=self.ax2D)
            self.canvas2D.draw()
            return
        if self.notebookPlots.tab(self.notebookPlots.select(), "text") != "3D":
            print("Assertion Error: The tabMain value is not 2D or 3D")

        X = np.arange(0,imgObj.imgDiff.shape[2])
        Y = np.arange(0,imgObj.imgDiff.shape[1])
        X, Y = np.meshgrid(X, Y)
        match (_selected):
            case "imgMean":
                self.imshow3D = self.ax3D.plot_surface(X,Y, imgObj.imgView(ImageView.SPATIAL).Mean, cmap="Greys_r" ) # type: ignore (imgView() is never None)
            case "imgStd":
                self.imshow3D = self.ax3D.plot_surface(X,Y, imgObj.imgView(ImageView.SPATIAL).Std, cmap="Greys_r") # type: ignore (imgView() is never None)
            case "diffMax":
                self.imshow3D = self.ax3D.plot_surface(X,Y, imgObj.imgDiffView(ImageView.SPATIAL).Max, cmap="inferno") # type: ignore (imgView() is never None)
            case "diffStd":
                self.imshow3D = self.ax3D.plot_surface(X,Y, imgObj.imgDiffView(ImageView.SPATIAL).Std, cmap="inferno") # type: ignore (imgView() is never None)
            case "diffMaxWithoutSignal":
                if imgObj.signal_obj.imgObj_sliced and imgObj.signal_obj.imgObj_sliced.imgDiff is not None:
                    self.imshow3D = self.ax3D.plot_surface(X,Y, signalObj.imgObj_sliced.imgDiffView(ImageView.SPATIAL).Max, cmap="inferno") # type: ignore (imgView() is never None)
            case _:
                pass
        if self.imshow3D is not None:
            self.colorbar = self.figure3D.colorbar(self.imshow3D, ax=self.ax3D)
        self.canvas3D.draw()

    def _insert_dict_into_tree(self, parent_node: str, d: dict, max_level_open:int, level:int=0):
        """ Insert a dictionary with strings and (sub-)dictionary as values recursively into the treeView """
        for k, v in d.items():
            iid = str(uuid.uuid4())
            if isinstance(v, dict):
                self.treeMetadata.insert(parent=parent_node, index='end', iid=iid, text=k, values=([""]), open=(level <= max_level_open))
                self._insert_dict_into_tree(parent_node=iid, d=v, max_level_open=max_level_open, level=(level+1))
            else:
                self.treeMetadata.insert(parent=parent_node, index='end', iid=iid, text=k, values=([str(v)]), open=(level <= max_level_open))
