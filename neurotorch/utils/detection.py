import numpy as np
import skimage as ski
import math


class ROIImage:

    # Convention: self.rois (X, Y)

    def __init__(self):
        self.imgThresholded = None
        self.imgLabeled = None
        self.imgRegProps = None
        self.rois = None

    def EstimateParameters(self, img: np.ndarray):
        median = np.median(img.flatten())
        std = np.std(img.flatten())
        max = np.max(img)
        threshold = math.ceil(median+2*std)
        if (std <= 2*median):
            threshold = math.ceil(0.3*max)
        return {"Threshold": threshold}

    def SetImg(self, img: np.ndarray, threshold):
        if (img is None or len(img.shape) != 2): return
        self.imgThresholded = (img >= threshold).astype(int)


    def LabelImg(self, radius: int, minROISize: float):
        self.imgLabeled = ski.measure.label(self.imgThresholded, connectivity=2)
        self.imgRegProps = ski.measure.regionprops(self.imgLabeled)
        self.rois = []
        for i in range(len(self.imgRegProps)):
            if(self.imgRegProps[i].area >= math.pi*(radius**2)*minROISize):
                self.rois.append((int(round(self.imgRegProps[i].centroid[1],0)), int(round(self.imgRegProps[i].centroid[0],0))))
