"""
    While synapse_detection.py provides detection algorithms, this file contains the actual implementation into Neurotorch GUI
"""

import tkinter as tk
from tkinter import ttk
from matplotlib import patches

from ..core.session import *
from ..gui.components.general import *

class IDetectionAlgorithmIntegration:
    """ 
        GUI integration of a synapse detection algorithm. Provides an option frame for setting information about an image
    """
    
    def __init__(self, session: Session):
        # The algorithm is choosing on its own what data to use. For this, an IMGObject is provided
        self.session = session
        self.provides_rawPlot: bool = False
        """ If set to true, the GUI knows that this algorithms provides raw information from the detection """

        self.image_obj: ImageObject|None = None
        """ The current image object. Is for example used by some integrations to calculate the signal """
        self.image_prop: ImageProperties|None = None
        """ The ImageProperties object should contain a 2D image and is used as input for the algorithm """

    def get_options_frame(self, master) -> tk.LabelFrame:
        """
            Creates an tkinter widget for the algorithms settings in the provided master.
        """
        self.master = master
        self.optionsFrame = tk.LabelFrame(self.master, text="Setting")
        return self.optionsFrame
    
    def update(self, image_prop: ImageProperties|None):
        """
            This function is called by the GUI to notify the detection algorithm integration object about a change in either the image object or the
            image input
        """
        self.image_obj = self.session.active_image_object
        self.image_prop = image_prop

    def detect_auto_params(self) -> list[ISynapseROI]:
        """
            This function must be overwritten by subclasses and should implement calling the underlying IDetectionAlgorithm with parameters
            choosen in the settings frame. 
        """
        raise NotImplementedError()
    

    def get_rawdata_overlay(self) -> tuple[tuple[np.ndarray]|None, list[patches.Patch]|None]:
        """
            An Integration may choose to provide an custom overlay image, usually the raw data obtained in one of the first steps. 
            Also it may provide a list of matplotlib patches for this overlay

            Return None to not plot anything
        """
        return (None, None)
    
    def filter_rois(self, rois: list[ISynapseROI], 
               sort:None|Literal['Strength', 'Location'] = None, 
               min_signal: float|None = None, 
               max_peaks: int|None = None) -> list[ISynapseROI]:
        """ Add the measured signal strength to a given a list of ROI. If sort is set to true, sort the list accordingly """
        if self.image_obj is not None and self.image_obj.imgDiff is not None:
            for roi in rois:
                roi.signal_strength = np.max(np.mean(roi.get_signal_from_image(self.image_obj.imgDiff), axis=1))
        if max_peaks is not None: 
            signal_strengths = sorted([r.signal_strength if r.signal_strength is not None else 0 for r in rois], reverse=False)
            count_cutoff = signal_strengths[min(len(signal_strengths) - 1)]
            min_signal = max(count_cutoff, min_signal) if min_signal is not None else count_cutoff
        if min_signal is not None:
            rois = [r for r in rois if r.signal_strength > min_signal] 
        if sort == "Strength":
            rois.sort(key=lambda x: x.strength, reverse=True)
        elif sort == "Location":
            rois.sort(key=lambda x: (x.location[0], x.location[1]))
        
        return rois

class Thresholding_Integration(Thresholding, IDetectionAlgorithmIntegration):

    def __init__(self, session: Session):
        super().__init__()
        IDetectionAlgorithmIntegration.__init__(self, session=session)

    def get_options_frame(self, master) -> tk.LabelFrame:
        super().get_options_frame(master=master)

        self.setting_threshold = GridSetting(self.optionsFrame, row=5, text="Threshold", unit="", default=50, min_=0, max_=2**15-1, scaleMin=1, scaleMax=200, tooltip=resources.get_string("algorithms/threshold/params/threshold"))
        self.setting_radius = GridSetting(self.optionsFrame, row=6, text="Radius", unit="px", default=6, min_=0, max_=1000, scaleMin=-1, scaleMax=30, tooltip=resources.get_string("algorithms/threshold/params/radius"))
        self.setting_minArea = GridSetting(self.optionsFrame, row=7, text="Minimal area", unit="px", default=40, min_=0, max_=1000, scaleMin=0, scaleMax=200, tooltip=resources.get_string("algorithms/threshold/params/minArea"))
        self.setting_minArea.var.IntVar.trace_add("write", lambda _1,_2,_3: self._update_lbl_minarea())
        self.lblMinAreaInfo = tk.Label(self.optionsFrame, text="")
        self.lblMinAreaInfo.grid(row=8, column=0, columnspan=3)
        self._update_lbl_minarea()
        
        return self.optionsFrame
    
    def detect_auto_params(self, **kwargs) -> list[ISynapseROI]:
        if self.image_prop is None:
            raise RuntimeError(f"The detection functions requires the update() function to be called first")
        threshold = self.setting_threshold.Get()
        radius = self.setting_radius.Get()
        minArea = self.setting_minArea.Get()
        minArea = None if minArea < 0 else minArea 
        return self.detect(img=self.image_prop.img, threshold=threshold, radius=radius, minArea=minArea)

    def get_rawdata_overlay(self) -> tuple[tuple[np.ndarray]|None, list[patches.Patch]|None]:
        return ((self.imgThresholded,), None)
    
    def _update_lbl_minarea(self):
        """ Internal function. Called to print in a label the equivalent radius of the min_area parameter"""
        A = self.setting_minArea.Get()
        r = round(np.sqrt(A/np.pi),2)
        self.lblMinAreaInfo["text"] = f"A circle with radius {r} px has the same area" 
    

class HysteresisTh_Integration(HysteresisTh, IDetectionAlgorithmIntegration):

    def __init__(self, session: Session):
        super().__init__()
        IDetectionAlgorithmIntegration.__init__(self, session=session)
        
    def get_options_frame(self, master) -> tk.LabelFrame:
        super().get_options_frame(master=master)

        self.lblImgStats = tk.Label(self.optionsFrame)
        self.lblImgStats.grid(row=1, column=0, columnspan=3)

        tk.Label(self.optionsFrame, text="Auto paramters").grid(row=5, column=0, sticky="ne")
        self.varAutoParams = tk.IntVar(value=1)
        self.checkAutoParams = ttk.Checkbutton(self.optionsFrame, variable=self.varAutoParams)
        self.checkAutoParams.grid(row=5, column=1, sticky="nw")

        self.setting_lowerTh = GridSetting(self.optionsFrame, row=10, text="Lower threshold", unit="", default=50, min_=0, max_=2**15-1, scaleMin=1, scaleMax=200, tooltip=resources.get_string("algorithms/hysteresisTh/params/lowerThreshold"))
        self.setting_upperTh = GridSetting(self.optionsFrame, row=11, text="Upper threshold", unit="", default=70, min_=0, max_=2**15-1, scaleMin=1, scaleMax=200, tooltip=resources.get_string("algorithms/hysteresisTh/params/upperThreshold"))
        self.lblPolygonalROIs = tk.Label(self.optionsFrame, text="Polygonal ROIs")
        self.lblPolygonalROIs.grid(row=12, column=0, sticky="ne")
        ToolTip(self.lblPolygonalROIs, msg=resources.get_string("algorithms/hysteresisTh/params/polygonalROIs"), follow=True, delay=0.1)
        self.varCircularApprox = tk.IntVar(value=1)
        self.checkCircularApprox = ttk.Checkbutton(self.optionsFrame, variable=self.varCircularApprox)
        self.checkCircularApprox.grid(row=12, column=1, sticky="nw")
        self.setting_radius = GridSetting(self.optionsFrame, row=13, text="Radius", unit="px", default=6, min_=0, max_=1000, scaleMin=1, scaleMax=30, tooltip=resources.get_string("algorithms/hysteresisTh/params/radius"))
        self.setting_radius.SetVisibility(not self.varCircularApprox.get())
        self.varCircularApprox.trace_add("write", lambda _1,_2,_3:self.setting_radius.SetVisibility(not self.varCircularApprox.get()))
        
        self.setting_minArea = GridSetting(self.optionsFrame, row=14, text="Min. Area", unit="px", default=50, min_=1, max_=10000, scaleMin=0, scaleMax=200, tooltip=resources.get_string("algorithms/hysteresisTh/params/minArea"))
        self.setting_minArea.var.IntVar.trace_add("write", lambda _1,_2,_3: self._update_lbl_minarea())
        self.lblMinAreaInfo = tk.Label(self.optionsFrame, text="")
        self.lblMinAreaInfo.grid(row=15, column=0, columnspan=3)
        self._update_lbl_minarea()

        self.update(None)
        
        return self.optionsFrame
    
    def update(self, image_prop: ImageProperties|None):
        super().update(image_prop=image_prop)
        if self.image_prop is None:
            self.lblImgStats["text"] = ""
            return
        
        _t = f"Image Stats: range = [{int(self.image_prop.min)}, {int(self.image_prop.max)}], "
        _t = _t + f"{np.round(self.image_prop.mean, 2)} ± {np.round(self.image_prop.std, 2)}, "
        _t = _t + f"median = {np.round(self.image_prop.median, 2)}"
        self.lblImgStats["text"] = _t
        self.estimate_params()

    def estimate_params(self):
        """
            Estimate some parameters based on the provided image.
        """
        if self.varAutoParams.get() != 1 or self.image_prop is None:
            return
        lowerThreshold = int(self.image_prop.mean + 2.5*self.image_prop.std)
        upperThreshold = max(lowerThreshold, min(self.image_prop.max/2, self.image_prop.mean + 5*self.image_prop.std))
        self.setting_lowerTh.Set(lowerThreshold)
        self.setting_upperTh.Set(upperThreshold)

    def _update_lbl_minarea(self):
        A = self.setting_minArea.Get()
        r = round(np.sqrt(A/np.pi),2)
        self.lblMinAreaInfo["text"] = f"A circle with radius {r} px has the same area" 

    def detect_auto_params(self) -> list[ISynapseROI]:
        if self.image_prop is None:
            raise RuntimeError(f"The detection functions requires the update() function to be called first")
        polygon = self.varCircularApprox.get()
        radius = self.setting_radius.Get()
        lowerThreshold = self.setting_lowerTh.Get()
        upperThreshold = self.setting_upperTh.Get()
        minArea = self.setting_minArea.Get() if polygon else 0

        result = self.detect(img=self.image_prop.img, 
                             lowerThreshold=lowerThreshold, 
                             upperThreshold=upperThreshold, 
                             minArea=minArea)

        if polygon:
            return result
        else:
            synapses_return = []
            if result is None:
                return None
            for s in result:
                if isinstance(s, CircularSynapseROI):
                    synapses_return.append(s)
                    continue
                synapses_return.append(CircularSynapseROI().set_location(x=s.location[0], y=s.location[1]).set_radius(radius))
            return synapses_return
            
    def Img_DetectionOverlay(self) -> tuple[tuple[np.ndarray]|None, list[patches.Patch]|None]:
        return ((self.thresholdFiltered_img, ), None)
    

class LocalMax_Integration(LocalMax, IDetectionAlgorithmIntegration):

    def __init__(self, session: Session):
        super().__init__()
        IDetectionAlgorithmIntegration.__init__(self, session=session)

    def get_options_frame(self, master) -> tk.LabelFrame:
        super().get_options_frame(master=master)

        self.lblImgStats = tk.Label(self.optionsFrame)
        self.lblImgStats.grid(row=1, column=0, columnspan=3)

        tk.Label(self.optionsFrame, text="Auto paramters").grid(row=5, column=0, sticky="ne")
        self.varAutoParams = tk.IntVar(value=1)
        self.checkAutoParams = ttk.Checkbutton(self.optionsFrame, variable=self.varAutoParams)
        self.checkAutoParams.grid(row=5, column=1, sticky="nw")

        self.setting_polygonal_ROIS = GridSetting(self.optionsFrame, row=10, text="Polygonal ROIs", type_="Checkbox", default=1)
        self.setting_polygonal_ROIS.var.IntVar.trace_add("write", lambda _1,_2,_3:self.setting_radius.SetVisibility(not self.setting_polygonal_ROIS.Get()))
        self.setting_polygonal_ROIS.var.SetCallback(lambda: self.setting_radius.SetVisibility(not self.setting_polygonal_ROIS.Get()))

        self.setting_radius = GridSetting(self.optionsFrame, row=11, text="Radius", unit="px", default=6, min_=1, max_=1000, scaleMin=-1, scaleMax=30, tooltip=resources.get_string("algorithms/localMax/params/radius"))
        self.setting_radius.SetVisibility(not self.setting_polygonal_ROIS.Get())
        self.setting_lowerTh = GridSetting(self.optionsFrame, row=12, text="Lower threshold", unit="", default=50, min_=0, max_=2**15-1, scaleMin=1, scaleMax=400, tooltip=resources.get_string("algorithms/localMax/params/lowerThreshold"))
        self.setting_upperTh = GridSetting(self.optionsFrame, row=13, text="Upper threshold", unit="", default=70, min_=0, max_=2**15-1, scaleMin=1, scaleMax=400, tooltip=resources.get_string("algorithms/localMax/params/upperThreshold"))
        self.setting_sortBySignal = GridSetting(self.optionsFrame, row=14, text="Sort by signal strength", type_="Checkbox", default=1, min_=0, tooltip=resources.get_string("algorithms/localMax/params/sortBySignal"))
        
        tk.Label(self.optionsFrame, text="Advanced settings").grid(row=20, column=0, columnspan=4, sticky="nw")
        self.setting_maxPeakCount = GridSetting(self.optionsFrame, row=21, text="Max. Peak Count", unit="", default=0, min_=0, max_=200, scaleMin=0, scaleMax=100, tooltip=resources.get_string("algorithms/localMax/params/maxPeakCount"))
        self.setting_minDistance = GridSetting(self.optionsFrame, row=22, text="Min. Distance", unit="px", default=20, min_=1, max_=1000, scaleMin=1, scaleMax=100, tooltip=resources.get_string("algorithms/localMax/params/minDistance"))
        self.setting_expandSize = GridSetting(self.optionsFrame, row=23, text="Expand size", unit="px", default=6, min_=0, max_=200, scaleMin=0, scaleMax=50, tooltip=resources.get_string("algorithms/localMax/params/expandSize"))
        self.setting_minSignal = GridSetting(self.optionsFrame, row=24, text="Minimum Signal", unit="", default=0, min_=0, max_=2**15-1, scaleMin=0, scaleMax=400, tooltip=resources.get_string("algorithms/localMax/params/minSignal"))
        self.setting_minArea = GridSetting(self.optionsFrame, row=25, text="Min. Area", unit="px", default=50, min_=1, max_=10000, scaleMin=0, scaleMax=200, tooltip=resources.get_string("algorithms/localMax/params/minArea"))
        self.setting_minArea.var.IntVar.trace_add("write", lambda _1,_2,_3: self._update_lbl_minarea())
        self.lblMinAreaInfo = tk.Label(self.optionsFrame, text="")
        self.lblMinAreaInfo.grid(row=26, column=1, columnspan=2)
        self._update_lbl_minarea()

        self.update(None)

        return self.optionsFrame
    
    def update(self, image_prop: ImageProperties|None):
        super().update(image_prop=image_prop)
        if self.image_prop is None:
            self.lblImgStats["text"] = ""
            return
        
        _t = f"Image Stats: range = [{int(self.image_prop.min)}, {int(self.image_prop.max)}], "
        _t = _t + f"{np.round(self.image_prop.mean, 2)} ± {np.round(self.image_prop.std, 2)}, "
        _t = _t + f"median = {np.round(self.image_prop.median, 2)}"
        self.lblImgStats["text"] = _t
        self.estimate_params()

    def estimate_params(self):
        """
            Estimate some parameters based on the provided image.
        """
        if self.varAutoParams.get() != 1 or self.image_prop is None:
            return
        lowerThreshold = int(self.image_prop.mean + 2.5*self.image_prop.std)
        upperThreshold = max(lowerThreshold, min(self.image_prop.max/2, self.image_prop.mean + 5*self.image_prop.std))
        self.setting_lowerTh.Set(lowerThreshold)
        self.setting_upperTh.Set(upperThreshold)

    def _update_lbl_minarea(self):
        A = self.setting_minArea.Get()
        r = round(np.sqrt(A/np.pi),2)
        self.lblMinAreaInfo["text"] = f"A circle with radius {r} px\n has the same area" 

    
    def detect_auto_params(self) -> list[ISynapseROI]:
        lowerThreshold = self.setting_lowerTh.Get()
        upperThreshold = self.setting_upperTh.Get()
        expandSize = self.setting_expandSize.Get()
        maxPeakCount = self.setting_maxPeakCount.Get()
        minArea = self.setting_minArea.Get()
        minDistance = self.setting_minDistance.Get()
        minSignal = self.setting_minSignal.Get()
        radius = None if self.setting_polygonal_ROIS.Get() == 1 else self.setting_radius.Get()
        rois = self.detect(img=self.image_prop.img,
                           lowerThreshold=lowerThreshold, 
                           upperThreshold=upperThreshold, 
                           expandSize=expandSize,
                           minArea=minArea,
                           minDistance=minDistance, 
                           radius=radius)
        return self.add_signal_to_result(rois=rois, sort=False)
            
    def get_rawdata_overlay(self) -> tuple[tuple[np.ndarray]|None, list[patches.Patch]|None]:
        if self.maxima is None:
            return (None, None)
        _patches = []
        for i in range(self.maxima.shape[0]):
            x, y = self.maxima[i, 1], self.maxima[i, 0]
            label = self.labeledImage[y,x]
            for region in self.region_props:
                if region.label == label:
                    y2, x2 = region.centroid_weighted
                    p = patches.Arrow(x,y, (x2-x), (y2-y))
                    _patches.append(p)
                    break
        return ((self.maxima_labeled_expanded, self.labeledImage), _patches)