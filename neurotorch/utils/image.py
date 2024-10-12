import numpy as np
from scipy.ndimage import convolve, gaussian_filter
import threading
from enum import Enum

class Img:

    #Convention: Img (time, y (top to bottom), x)

    def __init__(self):
        self.img = None
        self.imgMean = None
        self.imgStd = None
        self.imgMedian = None
        self.img_Stats = None

        self.imgDiff = None
        self.imgDiff_Stats = None
        self.imgDiffMaxTime = None
        self.imgDiffMaxTime_Stats = None
        self.imgDiffMaxSpatial = None
        self.imgDiffStdTime = None

        #self.imgDiff2 = None
        #self.imgDiff2_Stats = None
        #self.imgDiff2MaxTime = None
        #self.imgDiff2StdTime = None

        self.name = None

    def SetIMG(self, img:np.ndarray, name:str="", denoise=False):
        if (len(img.shape) != 3):
            return False
        match (img.dtype):
            case "uint8":
                self.img = img.astype("int8")
            case "uint16":
                self.img = img.astype("int16")
            case "uint32":
                self.img = img.astype("int32")   
            case _:
                self.img = img
        
        self.imgMean = np.mean(self.img, axis=0)
        self.imgStd = np.std(self.img, axis=0)
        self.imgMedian = np.mean(self.img, axis=0)
        self.name = name
        _imgMin = np.min(self.img)
        self.img_Stats = {"Max": np.max(self.img), "Min": _imgMin, "ClipMin": max(0, _imgMin)}
        self.CalcDiff(denoise=denoise)
        self.CalcDiffMax()
        return True
    
    def CalcDiff(self, denoise=False):
        if self.img is None: return
        if self.img.shape[0] <= 1:
            return
        
        self.imgDiff = np.diff(self.img, axis=0)
        #self.imgDiff2 = np.diff(self.img, axis=0, n=2)
        if denoise:
            self.imgDiff = gaussian_filter(self.imgDiff, sigma=2, axes=(1,2))
            #self.imgDiff2 = gaussian_filter(self.imgDiff2, sigma=2, axes=(1,2))  
        self.imgDiff_Stats = {"ClipMin": max(0, np.min(self.imgDiff)), "Max": np.max(self.imgDiff)}
        #self.imgDiff2_Stats = {"ClipMin": max(0, np.min(self.imgDiff2)), "Max": np.max(self.imgDiff2)}
    
    def CalcDiffMax(self):
        if self.imgDiff is None: return
        self.imgDiffMaxTime = np.max(self.imgDiff, axis=0)
        self.imgDiffMaxSpatial = np.max(self.imgDiff, axis=(1,2))
        self.imgDiffStdTime = np.std(self.imgDiff, axis=0)

        self.imgDiffMaxTime_Stats = {"Min": np.min(self.imgDiffMaxTime), 
                                     "Max": np.max(self.imgDiffMaxTime),
                                     "Std": np.std(self.imgDiffMaxTime),
                                     "Median": np.median(self.imgDiffMaxTime),
                                     "Mean": np.mean(self.imgDiffMaxTime)}
        
        self.imgDiffStdTime_Stats = {"Min": np.min(self.imgDiffStdTime), 
                                     "Max": np.max(self.imgDiffStdTime),
                                     "Std": np.std(self.imgDiffStdTime),
                                     "Median": np.median(self.imgDiffStdTime),
                                     "Mean": np.mean(self.imgDiffStdTime)}

        #self.imgDiff2MaxTime = np.max(-self.imgDiff2, axis=0)
        #self.imgDiff2StdTime = np.std(self.imgDiff2, axis=0)

"""
    # Point (X, Y)
    def GetImgROIAt(self, point, radius) -> np.ndarray:
        xmax = self.img.shape[2]
        ymax = self.img.shape[1]
        return np.array([self.img[:,y,x] for x in range(point[0]-radius,point[0]+2*radius+1) for y in range(point[1]-radius,point[1]+2*radius+1)
                     if ((x-point[0])**2+(y-point[1])**2)<radius**2+2**(1/2) and x >= 0 and y >= 0 and x < xmax and y < ymax])

        #mask, n = self._Circle_FullMask(point, radius)
        #_ret = np.empty(shape=self.img.shape)
        #for t in range(self.img.shape[0]):
        #    _ret[t] = np.multiply(self.img[t], mask)
        #return (_ret, n)

    def _CircleMask(self, radius: int) -> (np.ndarray, int):
        x = np.arange(-radius, +radius+1)
        y = np.arange(-radius, +radius+1)
        mask = np.array((x[np.newaxis,:])**2 + (y[:,np.newaxis])**2 <= radius**2, dtype="int32")
        n = np.count_nonzero(mask==1)
        return (mask,n)
    
    def _Circle_FullMask(self, point, radius: int) -> np.ndarray:
        x = np.arange(0, self.imgDiff.shape[2])
        y = np.arange(0, self.imgDiff.shape[1])
        mask = np.array((x[np.newaxis,:] - point[0])**2 + (y[:,np.newaxis] - point[1])**2 <= radius**2, dtype="int32")
        n = np.count_nonzero(mask==1)
        return (mask, n)
    
    def _ConvTask(self, radius: int):
        mask, n = self._CircleMask(radius)
        mask3 = mask[np.newaxis, :]
        self.imgConv = convolve(self.img,mask3)/n

    def ConvCorr(self, radius: int):
        if not self.ImgProvided(): return
        t1 = threading.Thread(target=self._ConvTask, args=(radius))
        t1.start()

"""