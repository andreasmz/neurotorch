""" Common convolution functions for denoising an image """

from ..image import *

import numpy as np
from scipy.ndimage import gaussian_filter

def cumsum_denoise(img: np.ndarray, img_diff: np.ndarray, img_median: np.ndarray) -> np.ndarray:
    return img_median + np.cumsum(img_diff, axis=0)

def gaussian_blur(img: np.ndarray, sigma: float) -> np.ndarray:
    return gaussian_filter(img, sigma=sigma, axes=(1,2))

def mean_diff(self, img:np.ndarray, img_mean: np.ndarray, img_signed: np.ndarray) -> np.ndarray:
        return (img_signed - img_mean).astype(img_signed.dtype)