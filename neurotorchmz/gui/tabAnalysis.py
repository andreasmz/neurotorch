from .window import *
from .components.treeview import SynapseTreeview
from .components.general import ScrolledFrame, GridSetting
from ..utils import synapse_detection_integration as detection

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.widgets as PltWidget
import matplotlib.patches as patches
from matplotlib.ticker import MaxNLocator
import numpy as np
from scipy.stats import multivariate_normal


class TabAnalysis_InvalidateEvent(TabUpdateEvent):
    """ Internal event to invalidate different parts of the tab """

    def __init__(self, algorithm:bool = False, image:bool = False, rois:bool = False, selectedROI: bool = False, selectedROI_tuple: tuple = None):
        super().__init__()
        self.algorithm = algorithm
        self.image = image
        self.rois = rois
        self.selectedROIS = selectedROI
        self.selectedROI_tuple = selectedROI_tuple

class TabAnalysis(Tab):

    def __init__(self, session: Session, root:ttk.Frame, frame: ttk.Frame):
        super().__init__(session=session, root=root, frame=frame)
        self.tab_name = "Tab Analysis"
        self.detectionAlgorithm: detection.IDetectionAlgorithmIntegration = None
        self.roiPatches = {}
        self.roiPatches2 = {}
        self.treeROIs_entryPopup = None
        self.ax1Image = None
        self.ax2Image = None
        self.ax1_colorbar = None
        self.ax2_colorbar = None

    def init(self):
        self.tab = ttk.Frame(self.frame)
        self.frame.add(self.tab, text="Synapse Analyzer (Beta version)")
        self.frameToolsContainer = ScrolledFrame(self.tab)
        self.frameToolsContainer.pack(side=tk.LEFT, fill="y", anchor=tk.NW)
        self.frameTools = self.frameToolsContainer.frame

        self.frameDetection = ttk.LabelFrame(self.frameTools, text="Detection Algorithm")
        self.frameDetection.grid(row=0, column=0, sticky="news")
        self.lblAlgorithm = tk.Label(self.frameDetection, text="Algorithm")
        self.lblAlgorithm.grid(row=0, column=0, columnspan=2, sticky="nw")
        self.radioAlgoVar = tk.StringVar(value="local_max")
        self.radioAlgo1 = tk.Radiobutton(self.frameDetection, variable=self.radioAlgoVar, indicatoron=True, text="Threshold (Deprecated)", value="threshold", command=lambda:self.invoke_update(TabAnalysis_InvalidateEvent(algorithm=True, image=True)))
        self.radioAlgo2 = tk.Radiobutton(self.frameDetection, variable=self.radioAlgoVar, indicatoron=True, text="Hysteresis thresholding", value="hysteresis", command=lambda:self.invoke_update(TabAnalysis_InvalidateEvent(algorithm=True, image=True)))
        self.radioAlgo3 = tk.Radiobutton(self.frameDetection, variable=self.radioAlgoVar, indicatoron=True, text="Local Max", value="local_max", command=lambda:self.invoke_update(TabAnalysis_InvalidateEvent(algorithm=True, image=True)))
        ToolTip(self.radioAlgo1, msg=Resources.GetString("algorithms/threshold/description"), follow=True, delay=0.1)
        ToolTip(self.radioAlgo2, msg=Resources.GetString("algorithms/hysteresisTh/description"), follow=True, delay=0.1)
        ToolTip(self.radioAlgo3, msg=Resources.GetString("algorithms/localMax/description"), follow=True, delay=0.1)
        self.radioAlgo1.grid(row=1, column=0, sticky="nw", columnspan=3)
        self.radioAlgo2.grid(row=2, column=0, sticky="nw", columnspan=3)
        self.radioAlgo3.grid(row=3, column=0, sticky="nw", columnspan=3)

        tk.Label(self.frameDetection, text="Delta images overlay").grid(row=10, column=0)
        self.setting_plotOverlay = GridSetting(self.frameDetection, row=11, type_="Checkbox", text="Plot raw algorithm output", default=0, tooltip=Resources.GetString("tab3/rawAlgorithmOutput"))
        self.setting_plotOverlay.var.IntVar.trace_add("write", lambda _1,_2,_3: self.invalidate_ROIs())
        self.setting_plotPixels = GridSetting(self.frameDetection, row=12, type_="Checkbox", text="Plot ROIs pixels", default=0, tooltip=Resources.GetString("tab3/plotROIPixels"))
        self.setting_plotPixels.var.IntVar.trace_add("write", lambda _1,_2,_3: self.invalidate_ROIs())
        self.btnDetect = tk.Button(self.frameDetection, text="Detect", command=self.detect)
        self.btnDetect.grid(row=20, column=0)

        self.frameDisplay= ttk.LabelFrame(self.frameTools, text="Display Options")
        self.frameDisplay.grid(row=1, column=0, sticky="news")

        self.sliderFrame = GridSetting(self.frameDisplay, row=5, type_="Int", text="Frame", min_=0, max_=0, scaleMin=0, scaleMax=0)
        self.sliderFrame.var.SetCallback(self.sliderFrame_changed)
        self.sliderPeak = GridSetting(self.frameDisplay, row=6, type_="Int", text="Peak", min_=0, max_=0, scaleMin=0, scaleMax=0)
        self.sliderPeak.var.SetCallback(self.sliderPeak_changed)
        self.btn3DPlot = tk.Button(self.frameDisplay, text="3D Multiframe Plot", command=lambda:self.show_external_plot("3D Multiframe Plot", self.plot_3D_multiframe))
        self.btn3DPlot.grid(row=10, column=1)
        
        self.frameAlgoOptions = self.detectionAlgorithm.get_options_frame(self.frameTools, lambda: self.session.active_image_object)
        self.frameAlgoOptions.grid(row=2, column=0, sticky="news")

        self.frameROIS = tk.LabelFrame(self.frameTools, text="ROIs")
        self.frameROIS.grid(row=3, column=0, sticky="news")

        self.tvSynapses = SynapseTreeview(self.frameROIS, self.session, 
                                          detection_result=self.session.synapse_analysis_detection_result, 
                                          selectCallback=lambda synapse, 
                                          roi:self.invoke_update(TabAnalysis_InvalidateEvent(selectedROI=True, selectedROI_tuple=(synapse, roi))), 
                                          updateCallback=lambda:self.invoke_update(TabAnalysis_InvalidateEvent(rois=True)), 
                                          allowMultiframe=True)
        self.tvSynapses.pack(fill="both", padx=10)

        self.figure1 = plt.Figure(figsize=(20,10), dpi=100)
        self.ax1 = self.figure1.add_subplot(221)  
        self.ax2 = self.figure1.add_subplot(222, sharex=self.ax1, sharey=self.ax1)  
        self.ax3 = self.figure1.add_subplot(223)  
        self.ax4 = self.figure1.add_subplot(224)  

        self.clear_image_plot()
        self.canvas1 = FigureCanvasTkAgg(self.figure1, self.tab)
        self.canvtoolbar1 = NavigationToolbar2Tk(self.canvas1,self.tab)
        self.canvtoolbar1.update()
        self.canvas1.get_tk_widget().pack(expand=True, fill="both", side=tk.LEFT)
        self.canvas1.mpl_connect('resize_event', self._canvas1_resize)
        self.canvas1.mpl_connect('button_press_event', self.canvas1_click)
        self.canvas1.draw()

        #tk.Grid.rowconfigure(self.frameTools, 3, weight=1)

        self.tvSynapses.SyncSynapses()
        self.Update(TabAnalysis_InvalidateEvent(algorithm=True, image=True))

    # Update and Invalidation functions

    def update_tab(self, event: TabUpdateEvent):
        """ The main function to update this tab. """
        if isinstance(event, ImageChangedEvent):
            self.tvSynapses.ClearSynapses(target='non_staged')
            self.tvSynapses.SyncSynapses()
            self.clear_image_plot()
            self.invalidate_algorithm()
            self.invalidate_image()
        elif isinstance(event, SignalChangedEvent):
            self.invalidate_stimulation()
        elif isinstance(event, TabAnalysis_InvalidateEvent):
            if event.algorithm: self.invalidate_algorithm()
            if event.image: self.invalidate_image()
            if event.rois: self.invalidate_ROIs()
            if event.selectedROIS: self.invalidate_selected_ROI(*event.selectedROI_tuple)

    @property
    def detection_result(self) -> DetectionResult:
        """ Convience property for self.session.synapse_analysis_detection_result """
        return self.session.synapse_analysis_detection_result

    def invalidate_algorithm(self):
        match self.radioAlgoVar.get():
            case "threshold":
                if isinstance(self.detectionAlgorithm, detection.Thresholding_Integration):
                    return
                self.detectionAlgorithm = detection.Thresholding_Integration()
            case "hysteresis":
                if type(self.detectionAlgorithm) == detection.HysteresisTh_Integration:
                    return
                self.detectionAlgorithm = detection.HysteresisTh_Integration()
            case "local_max":
                if type(self.detectionAlgorithm) == detection.LocalMax_Integration:
                    return
                self.detectionAlgorithm = detection.LocalMax_Integration()
            case _:
                self.detectionAlgorithm = None
                return
        if (self.frameAlgoOptions is not None):
            self.frameAlgoOptions.grid_forget()
        self.frameAlgoOptions = self.detectionAlgorithm.get_options_frame(self.frameTools)
        self.detectionAlgorithm.update(image_obj=self.session.active_image_object, image_prop=self.current_input_image)
        self.frameAlgoOptions.grid(row=2, column=0, sticky="news")

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
            ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        self.ax1.set_title("Image (Mean)")
        self.ax2.set_title("Diff Image")

    def invalidate_stimulation(self):
        signalObj = self.session.active_image_signal
        if signalObj is not None and signalObj.peaks is not None and len(signalObj.peaks) >= 1:
            self.sliderPeak.SetRange(min_=1, max_=len(signalObj.peaks), syncScale=True)
        else:
            self.sliderPeak.SetRange(0,0, syncScale=True)
        

    def invalidate_image(self):
        imgObj = self.session.active_image_object

        self.ax1Image = None
        if self.ax1_colorbar is not None:
            self.ax1_colorbar.remove()
            self.ax1_colorbar = None
        for axImg in self.ax1.get_images(): 
            axImg.remove()
        self.ax1.set_axis_off()

        self.invalidate_stimulation()
        
        if imgObj is None or imgObj.img is None or imgObj.imgDiff is None:
            self.sliderFrame.SetRange(0,0, syncScale=True)
            self.invalidate_delta_plot()
            return
        
        self.ax1Image = self.ax1.imshow(imgObj.imgView(ImageView.SPATIAL).Mean, cmap="Greys_r") 
        self.ax1.set_axis_on()
        self.ax1_colorbar = self.figure1.colorbar(self.ax1Image, ax=self.ax1)
        
        self.sliderFrame.SetRange(min_=1, max_=imgObj.imgDiff.shape[0], syncScale=True)
        self.invalidate_delta_plot()


    def invalidate_delta_plot(self):
        imgObj = self.session.active_image_object
        self.ax2Image = None    

        if self.ax2_colorbar is not None:
            self.ax2_colorbar.remove()
            self.ax2_colorbar = None
        for axImg in self.ax2.get_images(): 
            axImg.remove()
        self.ax2.set_axis_off()
            
        if imgObj is None or imgObj.img is None or imgObj.imgDiff is None:
            self.invalidate_ROIs()
            return
        frame = self.sliderFrame.Get() - 1
        if frame < 0 or frame >= imgObj.imgDiff.shape[0]:
            self.invalidate_ROIs()
            return
        
        vmin, vmax = 0, imgObj.imgDiffProps.max
        self.ax2Image = self.ax2.imshow(imgObj.imgDiff[frame], cmap="inferno", vmin=vmin, vmax=vmax)
        self.ax2_colorbar = self.figure1.colorbar(self.ax2Image, ax=self.ax2)
        self.ax2.set_axis_on()

        self.ax2.set_title(f"Diff. Image (Frame {frame + 1})")

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

        frame = self.sliderFrame.Get() - 1
        
        # Plotting the ROIs

        for synapse in self.detection_result.synapses:
            for roi in synapse.rois:
                if roi.location is None:
                    continue
                if isinstance(roi, detection.CircularSynapseROI):
                    c = patches.Circle(roi.location, roi.radius+0.5, color="red", fill=False)
                    c2 = patches.Circle(roi.location, roi.radius+0.5, color="green", fill=False)
                elif isinstance(roi, detection.PolygonalSynapseROI):
                    c = patches.Polygon(roi.polygon, color="red", fill=False)
                    c2 = patches.Polygon(roi.polygon, color="green", fill=False)
                else:
                    continue
                if _ax1HasImage:
                    self.ax1.add_patch(c)
                    self.roiPatches[roi.uuid] = c
                if _ax2HasImage and (roi.frame is None or roi.frame == frame):
                    self.ax2.add_patch(c2)
                    self.roiPatches2[roi.uuid] = c2
                    
        self.tvSynapses._OnSelect(None)

    def invalidate_selected_ROI(self, synapse: ISynapse|None=None, roi: ISynapseROI|None=None):
        """ Called by self.tvSynapses when a item is selected. If root item is selected, synapse and roi are None. If a ISynapse is selected, roi is None """
        if synapse is not None and roi is None:
            roi_uuids = list(synapse.rois_dict.keys())
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

        self.figure1.tight_layout()
        self.canvas1.draw()    
        
    def detect(self) -> Task:
        imgObj = self.session.active_image_object
        signalObj = self.session.active_image_signal
        if self.detectionAlgorithm is None or imgObj is None or imgObj.img is None or imgObj.imgDiff is None:
            self.root.bell()
            return

        def _detect(task: Task):
            self.tvSynapses.ClearSynapses('non_staged')
            self.tvSynapses.SyncSynapses()
            rois: list[ISynapseROI] = []
            for i, p in enumerate(signalObj.peaks):
                task.set_step_progress(i, f"detecting ROIs in frame {p}")
                rois.extend([r.set_frame(p) for r in self.detectionAlgorithm.DetectAutoParams(imgObj.imgDiff_FrameProps(p))])
            synapses = SimpleCusteringcluster(rois)
            self.detection_result.synapses = synapses
            self.tvSynapses.SyncSynapses()
            self.invoke_update(TabAnalysis_InvalidateEvent(rois=True))

        if signalObj is None or signalObj.peaks is None or len(signalObj.peaks) == 0:
            messagebox.showwarning("Neurotorch", "You must first get at least one signal frame in the Signal Finder Tab before you can detect Multiframe Synapses")
            return
        return Task(_detect, "Detecting ROIs", run_async=True).set_step_mode(len(signalObj.peaks)).start()

    # Helper function

    @property
    def current_input_image(self) -> ImageProperties|None:
        imgObj = self.session.active_image_object
        if imgObj is None or imgObj.img is None or imgObj.imgDiff is None:
            return None
        return imgObj.imgDiffView(ImageView.SPATIAL).MaxProps
    
    def sliderFrame_changed(self):
        frame = self.sliderFrame.Get() - 1
        signalObj = self.session.active_image_signal
        if signalObj is not None and signalObj.peaks is not None and len(peaks_index := (np.where(np.array(signalObj.peaks) == frame)[0])) == 1:
            peak = signalObj.peaks[peaks_index[0]]
            self.sliderPeak.Set(peaks_index[0] + 1)
            
        self.invalidate_delta_plot()

    def sliderPeak_changed(self):
        peak = self.sliderPeak.Get() - 1
        signalObj = self.session.active_image_signal
        if peak != -1 and signalObj.peaks is not None and len(signalObj.peaks) > peak:
            self.sliderFrame.Set(signalObj.peaks[peak] + 1)
        


    def show_external_plot(self, name:str,  plotFunction):
        dialog_figure = plt.Figure(figsize=(20,10), dpi=100)
        if plotFunction(dialog_figure) != True:
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.wm_title(f"Neurotorch: {name}")

        dialog_canvas = FigureCanvasTkAgg(dialog_figure, dialog)
        dialog_canvtoolbar = NavigationToolbar2Tk(dialog_canvas, dialog)
        dialog_canvtoolbar.update()
        dialog_canvas.get_tk_widget().pack(expand=True, fill="both", side=tk.LEFT)
        dialog_canvas.draw()

    def plot_3D_multiframe(self, figure):
        ax = figure.add_subplot(111, projection="3d")  
        imgObj = self.session.active_image_object

        if imgObj is None or imgObj.img is None or len(self.ax2.get_images()) == 0:
            messagebox.showerror("Neurotorch", f"You first need to load an image to plot the 3D Multifram synapse plot")
            return False

        img = np.full(shape=self.ax2.get_images()[0].get_size(), fill_value=0.0)
        mesh_X, mesh_Y = np.mgrid[0:img.shape[0], 0:img.shape[1]]
        pos = np.dstack((mesh_X, mesh_Y))
        for synapse in self.detection_result.synapses:
            for roi in synapse.rois:
                if roi.location is None: continue
                if isinstance(roi, CircularSynapseROI):
                    cov = roi.radius
                else:
                    cov = roi.region_props.equivalent_diameter_area/2 if roi.region_props is not None else 6
                img += multivariate_normal.pdf(x=pos, mean=roi.location, cov=cov)

        #overlay_img_props = self._gui.ImageObject.imgView(ImgObj.SPATIAL).MeanProps
        #norm = cm_colors.Normalize(vmin=overlay_img_props.min, vmax=overlay_img_props.max)
        #cmap = cm.get_cmap("Greys_r")
        #img_plot = ax.plot_surface(mesh_X, mesh_Y, img, rcount=100, ccount=100, facecolors = cmap(norm(overlay_img_props.img)))
        img_plot = ax.plot_surface(mesh_X, mesh_Y, img, rcount=150, ccount=150,  cmap="inferno")
        figure.colorbar(img_plot, ax=ax)
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.set_title("Surface plot of detected synapses per signal frame merged to a single image by multiplying each ROI location\nwith a normal probability distribution with covariance set to radius (or equivalent radius for non circular ROIs)")
        return True
    
    def canvas1_click(self, event):
        if not event.dblclick or event.inaxes is None:
            return
        x, y = event.xdata, event.ydata
        if event.inaxes == self.ax1:
            rois = [(s, r) for s in self.detection_result.synapses for r in s.rois]
        elif event.inaxes == self.ax2:
            rois = [(s, r) for s in self.detection_result.synapses for r in s.rois if r.uuid in self.roiPatches2.keys()]
        else:
            return
        if len(rois) == 0: return
        rois.sort(key=lambda v: (v[1].location[0]-x)**2+(v[1].location[1]-y)**2 if v[1].location is not None else np.inf)
        synapse, roi = rois[0]
        d = ((roi.location[0]-x)**2+(roi.location[1]-y)**2)**0.5 if roi.location is not None else np.inf
        if d <= 40:
            self.tvSynapses.Select(synapse=synapse, roi=roi)

    def _canvas1_resize(self, event):
        if self.tab.winfo_width() > 300:
            self.figure1.tight_layout()
            self.canvas1.draw()