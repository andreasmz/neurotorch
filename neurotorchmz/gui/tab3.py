""" Implements the ROI Finder Tab in Neurotorch"""
from .window import *
from .components.treeview import SynapseTreeview
from .components.general import ScrolledFrame, GridSetting
from ..utils import synapse_detection_integration as detection

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends._backend_tk import NavigationToolbar2Tk
from matplotlib.ticker import MaxNLocator
import numpy as np

# class TabROIFinder_InvalidateROIsEvent(TabUpdateEvent):
#     pass

class TabROIFinder_InvalidateEvent(TabUpdateEvent):
    """ Internal event to invalidate different parts of the tab """
    def __init__(self, algorithm:bool = False, image:bool = False, rois:bool = False, selectedROI: bool = False, selectedROI_tuple: tuple[ISynapse|None, ISynapseROI|None]|None = None):
        super().__init__()
        self.algorithm = algorithm
        self.image = image
        self.rois = rois
        self.selectedROIS = selectedROI
        self.selectedROI_tuple = selectedROI_tuple

class TabROIFinder(Tab):

    def __init__(self, session: Session, root:tk.Tk, notebook: ttk.Notebook):
        super().__init__(session, root, notebook, _tab_name="Tab ROI Finder")
        self.detectionAlgorithm = detection.IDetectionAlgorithmIntegration(self.session)
        self.roiPatches = {}
        self.roiPatches2 = {}
        self.treeROIs_entryPopup = None
        self.ax1Image = None
        self.ax2Image = None
        self.ax1_colorbar = None
        self.ax2_colorbar = None
        self.frameAlgoOptions: tk.LabelFrame|None = None

    def init(self):
        self.notebook.add(self.tab, text="Synapse ROI Finder")

        self.frameToolsContainer = ScrolledFrame(self.tab)
        self.frameToolsContainer.pack(side=tk.LEFT, fill="y", anchor=tk.NW)
        self.frameTools = self.frameToolsContainer.frame

        self.frameOptions = ttk.LabelFrame(self.frameTools, text="Algorithm and image")
        self.frameOptions.grid(row=0, column=0, sticky="news")
        self.lblAlgorithm = tk.Label(self.frameOptions, text="Algorithm")
        self.lblAlgorithm.grid(row=0, column=0, columnspan=2, sticky="nw")
        self.radioAlgoVar = tk.StringVar(value="local_max")
        self.radioAlgo1 = tk.Radiobutton(self.frameOptions, variable=self.radioAlgoVar, indicatoron=True, text="Threshold (Deprecated)", value="threshold", command=lambda:self.invoke_update(TabROIFinder_InvalidateEvent(algorithm=True, image=True)))
        self.radioAlgo2 = tk.Radiobutton(self.frameOptions, variable=self.radioAlgoVar, indicatoron=True, text="Hysteresis thresholding", value="hysteresis", command=lambda:self.invoke_update(TabROIFinder_InvalidateEvent(algorithm=True, image=True)))
        self.radioAlgo3 = tk.Radiobutton(self.frameOptions, variable=self.radioAlgoVar, indicatoron=True, text="Local Max", value="local_max", command=lambda:self.invoke_update(TabROIFinder_InvalidateEvent(algorithm=True, image=True)))
        ToolTip(self.radioAlgo1, msg=resources.get_string("algorithms/threshold/description"), follow=True, delay=0.1)
        ToolTip(self.radioAlgo2, msg=resources.get_string("algorithms/hysteresisTh/description"), follow=True, delay=0.1)
        ToolTip(self.radioAlgo3, msg=resources.get_string("algorithms/localMax/description"), follow=True, delay=0.1)
        self.radioAlgo1.grid(row=1, column=0, sticky="nw", columnspan=3)
        self.radioAlgo2.grid(row=2, column=0, sticky="nw", columnspan=3)
        self.radioAlgo3.grid(row=3, column=0, sticky="nw", columnspan=3)

        self.lblFrameOptions = tk.Label(self.frameOptions, text="Image Source")
        self.lblFrameOptions.grid(row=10, column=0, sticky="ne")
        ToolTip(self.lblFrameOptions, msg=resources.get_string("tab3/imageSource"), follow=True, delay=0.1)
        self.varImage = tk.StringVar(value="Delta (maximum)")
        self.varImage.trace_add("write", lambda _1,_2,_3: self.comboImage_changed())
        self.comboImage = ttk.Combobox(self.frameOptions, textvariable=self.varImage, state="readonly")
        self.comboImage['values'] = ["Delta", "Delta (maximum)", "Delta (std.)", "Delta (max.), signal removed"]
        self.comboImage.grid(row=10, column=1, sticky="news")
        self.varImageFrame = tk.StringVar()
        self.varImageFrame.trace_add("write", lambda _1,_2,_3: self.comboImage_changed())
        self.comboFrame = ttk.Combobox(self.frameOptions, textvariable=self.varImageFrame, state="disabled", width=5)
        self.comboFrame.grid(row=10, column=2, sticky="news")
        tk.Label(self.frameOptions, text="Delta images overlay").grid(row=11, column=0)
        self.setting_plotOverlay = GridSetting(self.frameOptions, row=11, type_="Checkbox", text="Plot raw algorithm output", default=0, tooltip=resources.get_string("tab3/rawAlgorithmOutput"))
        self.setting_plotOverlay.var.int_var.trace_add("write", lambda _1,_2,_3: self.invoke_update(TabROIFinder_InvalidateEvent(rois=True)))
        self.setting_plotPixels = GridSetting(self.frameOptions, row=12, type_="Checkbox", text="Plot ROI pixels", default=0, tooltip=resources.get_string("tab3/plotROIPixels"))
        self.setting_plotPixels.var.int_var.trace_add("write", lambda _1,_2,_3: self.invoke_update(TabROIFinder_InvalidateEvent(rois=True)))

        self.btnDetect = tk.Button(self.frameOptions, text="Detect", command=self.detect)
        self.btnDetect.grid(row=15, column=0)

        self.figure1 = Figure(figsize=(20,10), dpi=100)
        self.ax1 = self.figure1.add_subplot(221)  
        self.ax2 = self.figure1.add_subplot(222, sharex=self.ax1, sharey=self.ax1)  
        self.ax3 = self.figure1.add_subplot(223)  
        self.ax4 = self.figure1.add_subplot(224, sharex=self.ax3)  
        self.clear_image_plot()
        self.canvas1 = FigureCanvasTkAgg(self.figure1, self.tab)
        self.canvtoolbar1 = NavigationToolbar2Tk(self.canvas1,self.tab)
        self.canvtoolbar1.update()
        self.canvas1.get_tk_widget().pack(expand=True, fill="both", side=tk.LEFT)
        self.canvas1.mpl_connect('resize_event', self._canvas1_resize)
        self.canvas1.mpl_connect('button_press_event', self.canvas1_click)
        self.canvas1.draw()

        self.frameROIS = tk.LabelFrame(self.frameTools, text="ROIs")
        self.frameROIS.grid(row=2, column=0, sticky="news")

        self.tvSynapses = SynapseTreeview(master=self.frameROIS, 
                                          session=self.session, 
                                          detection_result=self.session.roifinder_detection_result, 
                                          select_callback=lambda synapse, roi:self.invoke_update(TabROIFinder_InvalidateEvent(selectedROI=True, selectedROI_tuple=(synapse, roi))), 
                                          allow_singleframe=True)
        self.tvSynapses.pack(fill="both")
        self.detection_result.register_callback(lambda _1, _2, _3: self.invoke_update(TabROIFinder_InvalidateEvent(rois=True)))

        #tk.Grid.rowconfigure(self.frameTools, 3, weight=1)

        self.update_tab(TabROIFinder_InvalidateEvent(algorithm=True, image=True, rois=True))


    # Convience functions

    @property
    def detection_result(self) -> DetectionResult:
        """ Convience property for self.session.roifinder_detection_result """
        return self.session.roifinder_detection_result

    # Update and Invalidation functions

    def update_tab(self, event: TabUpdateEvent):
        """ The main function to update this tab. """
        if isinstance(event, ImageChangedEvent):
            self.detection_result.clear_where(lambda s: not s.staged)
            self.clear_image_plot()
            self.comboImage_changed()
        elif isinstance(event, TabROIFinder_InvalidateEvent):
            if event.algorithm: self.invalidate_algorithm()
            if event.image: self.invalidate_image()
            if event.rois: self.invalidate_ROIs()
            if event.selectedROIS and event.selectedROI_tuple is not None: self.invalidate_selected_ROI(*event.selectedROI_tuple)

    def comboImage_changed(self):
        if self.active_image_object is None:
            return # TODO: Check
        signalObj = self.active_image_object.signal_obj
        
        if signalObj is None or self.varImage.get() != "Delta" or signalObj.peaks is None:
            self.comboFrame['values'] = []
            self.comboFrame["state"] = "disabled"
            self.varImageFrame.set("")
        else:
            self.comboFrame['values'] = [str(f+1) for f in list(signalObj.peaks)]
            self.comboFrame["state"] = "normal"
        
        self.invalidate_algorithm()
        self.invalidate_image()
        

    def invalidate_algorithm(self):
        match self.radioAlgoVar.get():
            case "threshold":
                if isinstance(self.detectionAlgorithm, detection.Thresholding_Integration):
                    return
                self.detectionAlgorithm = detection.Thresholding_Integration(self.session)
            case "hysteresis":
                if type(self.detectionAlgorithm) == detection.HysteresisTh_Integration:
                    return
                self.detectionAlgorithm = detection.HysteresisTh_Integration(self.session)
            case "local_max":
                if type(self.detectionAlgorithm) == detection.LocalMax_Integration:
                    return
                self.detectionAlgorithm = detection.LocalMax_Integration(self.session)
            case _:
                raise RuntimeError(f"Invalid algorithm '{self.radioAlgoVar.get()}'")
        if (self.frameAlgoOptions is not None):
            self.frameAlgoOptions.grid_forget()
        self.frameAlgoOptions = self.detectionAlgorithm.get_options_frame(self.frameTools)
        self.detectionAlgorithm.update(image_prop=self.current_input_image)
        self.frameAlgoOptions.grid(row=1, column=0, sticky="news")

    def clear_image_plot(self):
        if self.ax1_colorbar is not None:
            self.ax1_colorbar.remove()
            self.ax1_colorbar = None
        if self.ax2_colorbar is not None:
            self.ax2_colorbar.remove()
            self.ax2_colorbar = None
        for ax in [self.ax1, self.ax2, self.ax3, self.ax4]: 
            ax.clear()
            ax.set_axis_off()
            ax.xaxis.set_major_locator(MaxNLocator(integer=True))
            if ax == self.ax1 or ax == self.ax2:
                ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        self.ax1.set_title("Original (Mean)")
        self.ax2.set_title("Delta Video")

    def invalidate_image(self):
        imgObj = self.active_image_object

        if self.detectionAlgorithm is None:
            return

        self.detectionAlgorithm.update(image_prop=self.current_input_image)

        self.ax2.set_title("Delta Video")
        self.ax1Image = None
        self.ax2Image = None    
        if self.ax1_colorbar is not None:
            self.ax1_colorbar.remove()
            self.ax1_colorbar = None
        if self.ax2_colorbar is not None:
            self.ax2_colorbar.remove()
            self.ax2_colorbar = None
        for ax in [self.ax1, self.ax2]: 
            for axImg in ax.get_images(): 
                axImg.remove()
            ax.set_axis_off()
        
        if imgObj is None or imgObj.img is None or imgObj.img_diff is None or (_img := imgObj.img_view(ImageView.SPATIAL).mean_image) is None:
            self.invalidate_ROIs()
            return
        
        self.ax1Image = self.ax1.imshow(_img, cmap="Greys_r") 
        self.ax1.set_axis_on()
        self.ax1_colorbar = self.figure1.colorbar(self.ax1Image, ax=self.ax1)

        ax2_ImgProp, _ax2Title = self.current_input_image, self.current_input_description
        self.ax2.set_title(_ax2Title)
        if ax2_ImgProp.img is not None:
            self.ax2Image = self.ax2.imshow(ax2_ImgProp.img, cmap="inferno")
            self.ax2_colorbar = self.figure1.colorbar(self.ax2Image, ax=self.ax2)
            self.ax2.set_axis_on()

        self.invalidate_ROIs()


    def invalidate_ROIs(self):
        for axImg in self.ax1.get_images():
            if axImg != self.ax1Image: axImg.remove()
        for axImg in self.ax2.get_images():
            if axImg != self.ax2Image: axImg.remove()
        for p in reversed(self.ax1.patches): p.remove()
        for p in reversed(self.ax2.patches): p.remove()
        self.roiPatches = {}
        self.roiPatches2 = {}

        if self.tvSynapses.modified:
            self.frameROIS["text"] = "ROIs*"
        else:
            self.frameROIS["text"] = "ROIs"

        _ax1HasImage = len(self.ax1.get_images()) > 0
        _ax2HasImage = len(self.ax2.get_images()) > 0
        
        # Plotting the ROIs
        for synapse in self.detection_result:
            for roi in synapse.rois:
                if isinstance(roi, detection.CircularSynapseROI) and roi.location is not None and roi.radius is not None:
                    c = patches.Circle((cast(float, roi.location_x), cast(float, roi.location_y)), roi.radius+0.5, color="red", fill=False)
                    c2 = patches.Circle((cast(float, roi.location_x), cast(float, roi.location_y)), roi.radius+0.5, color="green", fill=False)
                elif isinstance(roi, detection.PolygonalSynapseROI) and roi.polygon is not None:
                    c = patches.Polygon(roi.polygon[:, ::-1], color="red", fill=False)
                    c2 = patches.Polygon(roi.polygon[:, ::-1], color="green", fill=False)
                else:
                    continue
                if _ax1HasImage:
                    self.ax1.add_patch(c)
                    self.roiPatches[roi.uuid] = c
                if _ax2HasImage:
                    self.ax2.add_patch(c2)
                    self.roiPatches2[roi.uuid] = c2

        # Plotting the overlays
        if self.current_input_image.img is not None:
            _currentSource = self.current_input_image.img
            if self.setting_plotPixels.get() == 1 and _ax1HasImage:
                _overlay = np.zeros(shape=_currentSource.shape, dtype=_currentSource.dtype)
                for synapse in self.detection_result:
                    for roi in synapse.rois:
                        _overlay[roi.get_coordinates(_currentSource.shape)] = 1
                self.ax1.imshow(_overlay, alpha=_overlay*0.5, cmap="viridis")

            if self.setting_plotOverlay.get() == 1 and _ax2HasImage:
                _overlays, _patches = self.detectionAlgorithm.get_rawdata_overlay()
                if _overlays is not None:
                    for _overlay in _overlays:
                        self.ax2.imshow(_overlay!=0, alpha=(_overlay != 0).astype(int)*0.5, cmap="gist_gray")
                if _patches is not None:
                    for p in _patches:
                        self.ax2.add_patch(p)

        self.figure1.tight_layout()
        self.canvas1.draw()

        self.tvSynapses.selection_clear()

    def invalidate_selected_ROI(self, synapse: ISynapse|None=None, roi: ISynapseROI|None=None):
        """ Called by self.tvSynapses when a item is selected. If root item is selected, synapse and roi are None. If a ISynapse is selected, roi is None """
        imgObj = self.session.active_image_object
        self.ax3.clear()
        self.ax3.set_title("Image Signal")
        self.ax3.set_ylabel("mean brightness")
        self.ax3.set_xlabel("frame")
        self.ax3.set_axis_off()
        self.ax4.clear()
        self.ax4.set_title("Detection Signal (from delta video)")
        self.ax4.set_ylabel("mean brightness increase")
        self.ax4.set_xlabel("delta video frame")
        self.ax4.set_axis_off()

        if synapse is not None and roi is None:
            roi_uuids = [r.uuid for r in synapse.rois]
        elif synapse is not None and roi is not None:
            roi_uuids = [roi.uuid]
        else:
            roi_uuids = []
        for patch_name, patch in self.roiPatches.items():
            if patch_name in roi_uuids:
                patch.set_color("yellow")
            else:
                patch.set_color("red")
        for patch_name, patch in self.roiPatches2.items():
            if patch_name in roi_uuids:
                patch.set_color("yellow")
            else:
                patch.set_color("green")
    
        if synapse is not None and len(synapse.rois) == 1 and imgObj is not None and imgObj.img is not None and imgObj.img_diff is not None:
            self.ax3.set_axis_on()
            self.ax4.set_axis_on()

            roi = synapse.rois[0]
            signal = roi.get_signal_from_image(imgObj.img)
            signalDiff = roi.get_signal_from_image(imgObj.img_diff)
            if signal.shape[0] > 0:
                self.ax3.plot(np.mean(signal, axis=1))
            if signalDiff.shape[0] > 0:
                self.ax4.plot(range(1, signalDiff.shape[0]+1), np.max(signalDiff, axis=1), label="Max", c="blue")
                self.ax4.plot(range(1, signalDiff.shape[0]+1), np.mean(signalDiff, axis=1), label="Mean", c="red")
                self.ax4.plot(range(1, signalDiff.shape[0]+1), np.min(signalDiff, axis=1), label="Min", c="darkorchid")
                self.ax4.legend()
        self.figure1.tight_layout()
        self.canvas1.draw()

    # Detection

    @property
    def current_input_image(self) -> ImageProperties:
        """ Return the current input image as a ImageProperties object which caches statistics about the image """
        imgObj = self.session.active_image_object
        self._current_input_description_str = "NO IMAGE" # Stores a string describing the current input image 
        if imgObj is None or imgObj.img_diff is None:
            return ImageProperties(None)
        
        match(self.varImage.get()):
            case "Delta":
                if self.varImageFrame.get() == "":
                    self._current_input_description_str = "INVALID FRAME"
                    return ImageProperties(None)
                _frame = int(v) - 1 if (v := self.varImageFrame.get()).isdigit() else -1
                if _frame < 0 or _frame >= imgObj.img_diff.shape[0]:
                    self._current_input_description_str = "INVALID FRAME"
                    return ImageProperties(None)
                self._current_input_description_str = f"Delta (Frame {_frame + 1})"
                return imgObj.img_diff_frame_props(_frame)
            case "Delta (maximum)":
                self._current_input_description_str = "Delta (maximum)"
                return imgObj.img_diff_view(ImageView.SPATIAL).max_props
            case "Delta (std.)":
                self._current_input_description_str = "Delta (std.)"
                return imgObj.img_diff_view(ImageView.SPATIAL).std_normed_props
            case "Delta (max.), signal removed":
                if imgObj.signal_obj.signal is None:
                    self._current_input_description_str = "SIGNAL MISSING"
                    return ImageProperties(None)
                elif imgObj.signal_obj.img_diff_without_signal_view(ImageView.SPATIAL).image is False:
                    self._current_input_description_str = "NO IMAGE"
                    return ImageProperties(None)
                self._current_input_description_str = "Delta (max.), signal removed"
                return imgObj.signal_obj.img_diff_without_signal_view(ImageView.SPATIAL).max_props
            case _:
                return ImageProperties(None)
        
    @property
    def current_input_description(self) -> str:
        """ Returns a string describing the current input image """
        self.current_input_image
        return self._current_input_description_str
        
    def detect(self) -> Task|None:
        if self.detectionAlgorithm is None or self.session.active_image_object is None:
            self.root.bell()
            return
        if self.current_input_image is None:
            self.root.bell()
            return 

        def _detect(task: Task):
            if self.detectionAlgorithm is None or self.current_input_image.img is None:
                return
            self.detection_result.clear_where(lambda s: not s.staged)
            task.set_step_progress(0, "")
            rois = self.detectionAlgorithm.detect_auto_params()
            synapes = [SingleframeSynapse(roi=r) for r in rois]
            self.detection_result.extend(synapes)

        return Task(_detect, "Detecting ROIs", run_async=True).set_step_mode(1).start()


    # GUI events
    
    def canvas1_click(self, event):
        if not event.dblclick or event.inaxes is None:
            return
        if (event.inaxes != self.ax1 and event.inaxes != self.ax2):
            return
        x, y = event.xdata, event.ydata
        rois = [(s, r, ISynapseROI.get_distance(r.location, (y, x))) for s in self.detection_result for r in s.rois]
        rois.sort(key=lambda v: v[2])
        if len(rois) == 0: return
        synapse, roi, d = rois[0]
        if d <= 40:
            self.tvSynapses.select(synapse=synapse, roi=roi)

    def _canvas1_resize(self, event):
        if self.tab.winfo_width() > 300:
            self.figure1.tight_layout()
            self.canvas1.draw()