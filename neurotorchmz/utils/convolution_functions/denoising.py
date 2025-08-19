""" Common convolution functions for denoising an image """

from ..image import *

import numpy as np
from scipy.ndimage import gaussian_filter as _gaussian_filter, convolve


# def cumsum_denoise(imgObj: ImageObject) -> np.ndarray:
#     if imgObj.img_view(ImageView.SPATIAL).median_image is None or imgObj.img_diff_raw is None:
#         raise RuntimeError("Can not denoise an ImageObject without image")
#     return imgObj.img_view(ImageView.SPATIAL).median_image + np.cumsum(imgObj.img_diff_raw, axis=0)

# def mean_diff(self, img:np.ndarray, img_mean: np.ndarray, img_signed: np.ndarray) -> np.ndarray:
#     return (img_signed - img_mean).astype(img_signed.dtype)

def gaussian_xy_kernel(img: np.ndarray, sigma: float) -> np.ndarray:
    t0 = time.perf_counter()
    _img_max, _img_min, _img_dtype = np.max(img), np.min(img), img.dtype
    r = _gaussian_filter(img, sigma=sigma, axes=(1,2), output="float32")
    r = (r*(_img_max/r.max()).astype(r.dtype)).astype(_img_dtype)
    #r = (_img_min.astype(r.dtype) + (r + r.min()) / (r.max() - r.min())*(_img_max-_img_min).astype(r.dtype)).astype(_img_dtype)
    logger.debug(f"Calculated gaussian xy kernel in {(time.perf_counter()-t0):1.3f} s")
    return r

def gaussian_t_kernel(img: np.ndarray, sigma: float, negate: bool = False) -> np.ndarray:
    t0 = time.perf_counter()
    if negate:
        img = -img
    r = -_gaussian_filter(img, sigma=sigma, axes=(0), output=img.dtype)
    logger.debug(f"Calculated gaussian t kernel in {(time.perf_counter()-t0):1.3f} s")
    return r


def leap_gaussian_t_kernel(img: np.ndarray, sigma: float, negate: bool = False) -> np.ndarray:
    ax = np.arange(-(3*sigma) // 2, (3*sigma) // 2 + 1)
    kernel = int(ax > 0)*np.exp(-(ax**2) / (2 * sigma**2))
    kernel /= kernel.sum()
    if negate:
        kernel = -kernel
    return kernel


def reverse_t_kernel(img: np.ndarray) -> np.ndarray:
    return -img

def sliding_cumsum(img: np.ndarray, frames: int, negate: bool = False) -> np.ndarray:
    norm = 1/(frames + 1)
    a1 = np.full(shape=(frames), fill_value=((-norm) if negate else norm))
    a2 = np.full(shape=(frames), fill_value=0)
    c = np.concatenate([a2, np.array([norm]), a1])
    c = c[:, None, None]

    if negate:
        img = -img

    return convolve(img, c, output="float32").astype(img.dtype)

def cumsum(img: np.ndarray, negate: bool = False) -> np.ndarray:
    if negate:
        img = -img
    return np.cumsum(img, axis=0, dtype=img.dtype)

def combined_diff_convolution(img_obj: ImageObject, norm: bool, xy_kernel_fn: Callable[..., np.ndarray]|None, t_kernel_fn: Callable[..., np.ndarray]|None, xy_kernel_args: dict = {}, t_kernel_args: dict = {}) -> np.ndarray|None:
    if img_obj.img_diff_raw is None:
        return None
    if xy_kernel_fn is None and t_kernel_fn is None:
        return img_obj.img_diff_raw
    
    img = img_obj.img_diff_raw
    
    if xy_kernel_fn is not None:
        img = xy_kernel_fn(img, **xy_kernel_args)

    gc.collect()

    if t_kernel_fn is not None:
        img = t_kernel_fn(img, **t_kernel_args)

    gc.collect()

    return img