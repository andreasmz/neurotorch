""" Common convolution functions for denoising an image """

from ..image import *

import numpy as np
from scipy.ndimage import gaussian_filter as _gaussian_filter

def cumsum_denoise(imgObj: ImageObject) -> np.ndarray:
    if imgObj.imgView(ImageView.SPATIAL).Median is None or imgObj.imgDiff is None:
         raise RuntimeError("Can not denoise an ImageObject without image")
    return imgObj.imgView(ImageView.SPATIAL).Median + np.cumsum(imgObj.imgDiff, axis=0)

def gaussian_blur(imgObj: ImageObject, sigma: float) -> np.ndarray:
    return _gaussian_filter(imgObj._img_diff, sigma=sigma, axes=(1,2))

def mean_diff(self, img:np.ndarray, img_mean: np.ndarray, img_signed: np.ndarray) -> np.ndarray:
        return (img_signed - img_mean).astype(img_signed.dtype)