""" Common convolution functions for denoising an image """

from ..image import *

import numpy as np
from scipy.ndimage import gaussian_filter as _gaussian_filter, convolve

def cumsum_denoise(imgObj: ImageObject) -> np.ndarray:
    if imgObj.imgView(ImageView.SPATIAL).Median is None or imgObj.img_diff_raw is None:
        raise RuntimeError("Can not denoise an ImageObject without image")
    return imgObj.imgView(ImageView.SPATIAL).Median + np.cumsum(imgObj.img_diff_raw, axis=0)

def gaussian_xy(imgObj: ImageObject, sigma: float) -> np.ndarray:
    return _gaussian_filter(imgObj.img_diff_raw, sigma=sigma, axes=(1,2))

# def mean_diff(self, img:np.ndarray, img_mean: np.ndarray, img_signed: np.ndarray) -> np.ndarray:
#     return (img_signed - img_mean).astype(img_signed.dtype)

def gaussian_xy_kernel(sigma: float) -> np.ndarray:
    ax = np.arange(-(3*sigma) // 2, (3*sigma) // 2 + 1)
    xx, yy = np.meshgrid(ax, ax)
    kernel = np.exp(-(xx**2 + yy**2) / (2 * sigma**2))
    return kernel / kernel.sum()

def gaussian_t_kernel(sigma: float, negate: bool = False) -> np.ndarray:
    ax = np.arange(-(3*sigma) // 2, (3*sigma) // 2 + 1)
    kernel = np.exp(-(ax**2) / (2 * sigma**2))
    if negate:
        kernel = -kernel
    return kernel / kernel.sum()


def leap_gaussian_t_kernel(sigma: float) -> np.ndarray:
    ax = np.arange(-(3*sigma) // 2, (3*sigma) // 2 + 1)
    kernel = (ax > 0)*np.exp(-(ax**2) / (2 * sigma**2))
    return kernel / kernel.sum()

def drop_t_kernel() -> np.ndarray:
    return np.array([-1])

def combined_diff_convolution(img_obj: ImageObject, xy_kernel_fn: Callable|None, t_kernel_fn: Callable|None, xn_kernel_args: dict = {}, t_kernel_args: dict = {}) -> np.ndarray|None:
    if img_obj.img_diff_raw is None:
        return None
    if xy_kernel_fn is None and t_kernel_fn is None:
        return img_obj.img_diff_raw
    
    if xy_kernel_fn is None:
        xy_kernel = np.array([1])
    else:
        xy_kernel = xy_kernel_fn(**xn_kernel_args)

    if t_kernel_fn is None:
        t_kernel = np.array([1])
    else:
        t_kernel = t_kernel_fn(**t_kernel_args)

    kernel = t_kernel[:, None, None] * xy_kernel[None, :, :]
    return convolve(img_obj.img_diff_raw, kernel, mode="reflect")