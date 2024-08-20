import numpy as np
from scipy.ndimage import convolve
import threading
from enum import Enum

class IMG_TYPE(Enum):
    IMG = 1
    IMG_DIFF = 2
    IMG_DIFF_MAX_TIME = 3
    IMG_DIFF_MAX_SPATIAL = 4

class Img:

    #Convention: Img (time, y (top to bottom), x)

    def __init__(self, img: np.ndarray, imgType: IMG_TYPE):
        self.img = None
        self.imgDiff = None
        self.imgDiffMaxTime = None
        self.imgDiffMaxSpatial = None
        self.imgConv = None

        match imgType:
            case IMG_TYPE.IMG:
                self.img = img
                self.ImgProvided()
            case IMG_TYPE.IMG_DIFF:
                self.imgDiff = img
                self.ImgDiffProvided()
            case IMG_TYPE.IMG_DIFF_MAX_TIME:
                self.imgDiffMaxTime = img
            case IMG_TYPE.IMG_DIFF_MAX_SPATIAL:
                self.imgDiffMaxSpatial = img
            case _:
                pass

    def __init__(self):
        self.img = None
        self.imgDiff = None
        self.imgDiffMaxTime = None
        self.imgDiffMaxSpatial = None
        self.imgConv = None

    def CheckImg(self):
        if (self.img is None or not isinstance(self.img, np.ndarray)):
            return False
        if (len(self.img.shape) != 3):
            return False
        return True
    
    def CheckImgDiff(self):
        if (self.imgDiff is None or not isinstance(self.imgDiff, np.ndarray)):
            return False
        if (len(self.imgDiff.shape) != 3):
            return False
        return True
        
    def ImgProvided(self):
        if self.CheckImg() == False: return
        self.CalcDiff()
        self.CalcDiffMax()
    
    def ImgDiffProvided(self):
        if self.CheckImgDiff() == False: return
        self.CalcDiffMax()
    
    def CalcDiff(self):
        if not self.CheckImg(): return
        self.imgDiff = np.diff(self.img, axis=0)
    
    def CalcDiffMax(self):
        if not self.CheckImgDiff(): return
        self.imgDiffMaxTime = np.max(self.imgDiff, axis=0)
        self.imgDiffMaxSpatial = np.max(self.imgDiff, axis=(1,2))

    # Point (X, Y)
    def GetImgConv_At(self, point, radius: int) -> (np.ndarray, int):
        mask, n = self._Circle_FullMask(point, radius)
        _ret = np.empty(shape=self.img.shape)
        for t in range(self.img.shape[0]):
            _ret[t] = np.multiply(self.img[t], mask)
        return (_ret, n)

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