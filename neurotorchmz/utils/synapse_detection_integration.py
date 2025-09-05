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
        self.image_prop: ImageProperties = ImageProperties(None)
        """ The ImageProperties object should contain a 2D image and is used as input for the algorithm """

    def get_options_frame(self, master) -> tk.LabelFrame:
        """
            Creates an tkinter widget for the algorithms settings in the provided master.
        """
        self.master = master
        self.optionsFrame = tk.LabelFrame(self.master, text="Settings")
        return self.optionsFrame
    
    def update(self, image_prop: ImageProperties|None):
        """
            This function is called by the GUI to notify the detection algorithm integration object about a change in either the image object or the
            image input
        """
        self.image_obj = self.session.active_image_object
        if image_prop is None:
            self.image_prop = ImageProperties(None)
        else:
            self.image_prop = image_prop

    def detect_auto_params(self) -> list[ISynapseROI]:
        """
            This function must be overwritten by subclasses and should implement calling the underlying IDetectionAlgorithm with parameters
            choosen in the settings frame. 
        """
        raise NotImplementedError()
    

    def get_rawdata_overlay(self) -> tuple[tuple[np.ndarray, ...]|None, list[patches.Patch]|None]:
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
        """
        Filter the rois and add adds the signal strength to the ROI

        :param sort: If not None, sort the ROIs based on theire location (top to down first)
        :param min_signal: If not None, return only peaks exceeding the given signal strength
        :param max_peaks: If not None, return only the n strongest peaks
        """
        if self.image_obj is not None and self.image_obj.img_diff is not None:
            for roi in rois:
                roi.signal_strength = np.max(np.mean(roi.get_signal_from_image(self.image_obj.img_diff), axis=1))
        if min_signal is not None:
            rois = [r for r in rois if r.signal_strength is not None and r.signal_strength > min_signal] 
        if sort == "Strength" or max_peaks is not None:
            rois.sort(key=lambda x: (x.signal_strength if x.signal_strength is not None else 0), reverse=True)
        if max_peaks is not None:
            rois = rois[:max_peaks]
        if sort == "Location":
            rois.sort(key=lambda x: (x.location_x, x.location_y))
        return rois

class Thresholding_Integration(Thresholding, IDetectionAlgorithmIntegration):

    def __init__(self, session: Session):
        super().__init__()
        IDetectionAlgorithmIntegration.__init__(self, session=session)

    def get_options_frame(self, master) -> tk.LabelFrame:
        super().get_options_frame(master=master)

        self.setting_threshold = GridSetting(self.optionsFrame, row=5, text="Threshold", unit="", default=50, min_=0, max_=2**15-1, scale_min=1, scale_max=200, tooltip=resources.get_string("algorithms/threshold/params/threshold"))
        self.setting_radius = GridSetting(self.optionsFrame, row=6, text="Radius", unit="px", default=6, min_=0, max_=1000, scale_min=-1, scale_max=30, tooltip=resources.get_string("algorithms/threshold/params/radius"))
        self.setting_minArea = GridSetting(self.optionsFrame, row=7, text="Minimal area", unit="px", default=40, min_=0, max_=1000, scale_min=0, scale_max=200, tooltip=resources.get_string("algorithms/threshold/params/minArea"))
        self.setting_minArea.var.int_var.trace_add("write", lambda _1,_2,_3: self._update_lbl_minarea())
        self.lblMinAreaInfo = tk.Label(self.optionsFrame, text="")
        self.lblMinAreaInfo.grid(row=8, column=0, columnspan=3)
        self._update_lbl_minarea()
        
        return self.optionsFrame
    
    def detect_auto_params(self, **kwargs) -> list[ISynapseROI]:
        if self.image_prop.img is None:
            raise RuntimeError(f"The detection functions requires the update() function to be called first")
        threshold = self.setting_threshold.get()
        radius = self.setting_radius.get()
        minArea = self.setting_minArea.get()
        minArea = None if minArea < 0 else minArea 
        return self.detect(img=self.image_prop.img, threshold=threshold, radius=radius, minArea=minArea)

    def get_rawdata_overlay(self) -> tuple[tuple[np.ndarray]|None, list[patches.Patch]|None]:
        if self.imgThresholded is None:
            return (None, None)
        return ((self.imgThresholded,), None)
    
    def _update_lbl_minarea(self):
        """ Internal function. Called to print in a label the equivalent radius of the min_area parameter"""
        A = self.setting_minArea.get()
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

        self.setting_lowerTh = GridSetting(self.optionsFrame, row=10, text="Lower threshold", unit="", default=50, min_=0, max_=2**15-1, scale_min=1, scale_max=200, tooltip=resources.get_string("algorithms/hysteresisTh/params/lowerThreshold"))
        self.setting_upperTh = GridSetting(self.optionsFrame, row=11, text="Upper threshold", unit="", default=70, min_=0, max_=2**15-1, scale_min=1, scale_max=200, tooltip=resources.get_string("algorithms/hysteresisTh/params/upperThreshold"))
        self.lblPolygonalROIs = tk.Label(self.optionsFrame, text="Polygonal ROIs")
        self.lblPolygonalROIs.grid(row=12, column=0, sticky="ne")
        ToolTip(self.lblPolygonalROIs, msg=resources.get_string("algorithms/hysteresisTh/params/polygonalROIs"), follow=True, delay=0.1)
        self.varCircularApprox = tk.IntVar(value=1)
        self.checkCircularApprox = ttk.Checkbutton(self.optionsFrame, variable=self.varCircularApprox)
        self.checkCircularApprox.grid(row=12, column=1, sticky="nw")
        self.setting_radius = GridSetting(self.optionsFrame, row=13, text="Radius", unit="px", default=6, min_=0, max_=1000, scale_min=1, scale_max=30, tooltip=resources.get_string("algorithms/hysteresisTh/params/radius"))
        self.setting_radius.set_visibility(not self.varCircularApprox.get())
        self.varCircularApprox.trace_add("write", lambda _1,_2,_3:self.setting_radius.set_visibility(not self.varCircularApprox.get()))
        
        self.setting_minArea = GridSetting(self.optionsFrame, row=14, text="Min. Area", unit="px", default=50, min_=1, max_=10000, scale_min=0, scale_max=200, tooltip=resources.get_string("algorithms/hysteresisTh/params/minArea"))
        self.setting_minArea.var.int_var.trace_add("write", lambda _1,_2,_3: self._update_lbl_minarea())
        self.lblMinAreaInfo = tk.Label(self.optionsFrame, text="")
        self.lblMinAreaInfo.grid(row=15, column=0, columnspan=3)
        self._update_lbl_minarea()

        self.update(None)
        
        return self.optionsFrame
    
    def update(self, image_prop: ImageProperties|None):
        super().update(image_prop=image_prop)
        if self.image_prop.img is None:
            self.lblImgStats["text"] = ""
            return
        
        _t = f"Image Stats: range = [{self.image_prop.min:.5g}, {self.image_prop.max:.5g}], "
        _t = _t + f"{self.image_prop.mean:.5g} ± {self.image_prop.std:.5g}, "
        _t = _t + f"median = {self.image_prop.median:.5g}"

        self.lblImgStats["text"] = _t
        self.estimate_params()

    def estimate_params(self):
        """
            Estimate some parameters based on the provided image.
        """
        if self.varAutoParams.get() != 1 or self.image_prop.img is None:
            return
        assert self.image_prop.mean is not None and self.image_prop.std is not None and self.image_prop.max is not None
        lowerThreshold = int(self.image_prop.mean + 2.5*self.image_prop.std)
        upperThreshold = int(max(lowerThreshold, min(float(self.image_prop.max)/2, float(self.image_prop.mean + 5*self.image_prop.std))))
        self.setting_lowerTh.set(lowerThreshold)
        self.setting_upperTh.set(upperThreshold)

    def _update_lbl_minarea(self):
        A = self.setting_minArea.get()
        r = round(np.sqrt(A/np.pi),2)
        self.lblMinAreaInfo["text"] = f"A circle with radius {r} px has the same area" 

    def detect_auto_params(self) -> list[ISynapseROI]:
        if self.image_prop.img is None:
            raise RuntimeError(f"The detection functions requires the update() function to be called first")
        polygon = self.varCircularApprox.get()
        radius = self.setting_radius.get()
        lowerThreshold = self.setting_lowerTh.get()
        upperThreshold = self.setting_upperTh.get()
        minArea = self.setting_minArea.get() if polygon else 0

        rois = self.detect(img=self.image_prop.img, 
                             lowerThreshold=lowerThreshold, 
                             upperThreshold=upperThreshold, 
                             minArea=minArea)
        
        rois: list[ISynapseROI] = self.filter_rois(rois, sort="Location")

        if not polygon:
            rois = [CircularSynapseROI().set_location(location=r.location).set_radius(radius) for r in rois]
        rois = self.filter_rois(rois, sort="Location")
        return rois
            
    def Img_DetectionOverlay(self) -> tuple[tuple[np.ndarray]|None, list[patches.Patch]|None]:
        if self.thresholdFiltered_img is None:
            return (None, None)
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
        self.setting_polygonal_ROIS.var.int_var.trace_add("write", lambda _1,_2,_3:self.setting_radius.set_visibility(not self.setting_polygonal_ROIS.get()))
        self.setting_polygonal_ROIS.var.set_callback(lambda: self.setting_radius.set_visibility(not self.setting_polygonal_ROIS.get()))

        self.setting_radius = GridSetting(self.optionsFrame, row=11, text="Radius", unit="px", default=6, min_=1, max_=1000, scale_min=1, scale_max=30, tooltip=resources.get_string("algorithms/localMax/params/radius"))
        self.setting_radius.set_visibility(not self.setting_polygonal_ROIS.get())
        self.setting_lowerTh = GridSetting(self.optionsFrame, row=12, text="Lower threshold", unit="", default=50, min_=0, max_=2**15-1, scale_min=1, scale_max=400, tooltip=resources.get_string("algorithms/localMax/params/lowerThreshold"))
        self.setting_upperTh = GridSetting(self.optionsFrame, row=13, text="Upper threshold", unit="", default=70, min_=0, max_=2**15-1, scale_min=1, scale_max=400, tooltip=resources.get_string("algorithms/localMax/params/upperThreshold"))
        
        tk.Label(self.optionsFrame, text="Advanced settings").grid(row=20, column=0, columnspan=4, sticky="nw")
        self.setting_maxPeakCount = GridSetting(self.optionsFrame, row=21, text="Max. Peak Count", unit="", default=100, min_=0, max_=200, scale_min=0, scale_max=100, tooltip=resources.get_string("algorithms/localMax/params/maxPeakCount"))
        self.setting_minDistance = GridSetting(self.optionsFrame, row=22, text="Min. Distance", unit="px", default=20, min_=1, max_=1000, scale_min=1, scale_max=100, tooltip=resources.get_string("algorithms/localMax/params/minDistance"))
        self.setting_expandSize = GridSetting(self.optionsFrame, row=23, text="Expand size", unit="px", default=6, min_=0, max_=200, scale_min=0, scale_max=50, tooltip=resources.get_string("algorithms/localMax/params/expandSize"))
        self.setting_minSignal = GridSetting(self.optionsFrame, row=24, text="Minimum Signal", unit="", default=0, min_=0, max_=2**15-1, scale_min=0, scale_max=400, tooltip=resources.get_string("algorithms/localMax/params/minSignal"))
        self.setting_minArea = GridSetting(self.optionsFrame, row=25, text="Min. Area", unit="px", default=50, min_=1, max_=10000, scale_min=0, scale_max=200, tooltip=resources.get_string("algorithms/localMax/params/minArea"))
        self.setting_minArea.var.int_var.trace_add("write", lambda _1,_2,_3: self._update_lbl_minarea())
        self.lblMinAreaInfo = tk.Label(self.optionsFrame, text="")
        self.lblMinAreaInfo.grid(row=26, column=1, columnspan=2)
        self._update_lbl_minarea()

        self.update(None)

        return self.optionsFrame
    
    def update(self, image_prop: ImageProperties|None):
        super().update(image_prop=image_prop)
        if self.image_prop.img is None:
            self.lblImgStats["text"] = ""
            return
        
        _t = f"Image Stats: range = [{self.image_prop.min:.5g}, {self.image_prop.max:.5g}], "
        _t = _t + f"{self.image_prop.mean:.5g} ± {self.image_prop.std:.5g}, "
        _t = _t + f"median = {self.image_prop.median:.5g}"
        self.lblImgStats["text"] = _t
        self.estimate_params()

    def estimate_params(self):
        """
            Estimate some parameters based on the provided image.
        """
        if self.varAutoParams.get() != 1 or self.image_prop.img is None:
            return
        assert self.image_prop.mean is not None and self.image_prop.std is not None and self.image_prop.max is not None
        lowerThreshold = int(self.image_prop.mean + 2.5*self.image_prop.std)
        upperThreshold = int(max(lowerThreshold, min(float(self.image_prop.max)/2, float(self.image_prop.mean + 5*self.image_prop.std))))
        self.setting_lowerTh.set(lowerThreshold)
        self.setting_upperTh.set(upperThreshold)

    def _update_lbl_minarea(self):
        A = self.setting_minArea.get()
        r = round(np.sqrt(A/np.pi),2)
        self.lblMinAreaInfo["text"] = f"A circle with radius {r} px\n has the same area" 

    
    def detect_auto_params(self) -> list[ISynapseROI]:
        if self.image_prop.img is None:
            return []
        lowerThreshold = self.setting_lowerTh.get()
        upperThreshold = self.setting_upperTh.get()
        expandSize = self.setting_expandSize.get()
        maxPeakCount = self.setting_maxPeakCount.get()
        maxPeakCount = maxPeakCount if maxPeakCount != 0 else None
        minArea = self.setting_minArea.get()
        minDistance = self.setting_minDistance.get()
        minSignal = self.setting_minSignal.get()
        minSignal = minSignal if minSignal != 0 else None
        radius = None if self.setting_polygonal_ROIS.get() == 1 else self.setting_radius.get()
        rois = self.detect(img=self.image_prop.img,
                           lowerThreshold=lowerThreshold, 
                           upperThreshold=upperThreshold, 
                           expandSize=expandSize,
                           minArea=minArea,
                           minDistance=minDistance, 
                           radius=radius)
        return self.filter_rois(rois=rois, sort="Location", min_signal=minSignal, max_peaks=maxPeakCount)
            
    def get_rawdata_overlay(self) -> tuple[tuple[np.ndarray, np.ndarray]|None, list[patches.Patch]|None]:
        if self.maxima is None or self.labeledImage is None or self.region_props is None or self.maxima_labeled_expanded is None:
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