""" Common convolution functions for denoising an image """

from .image import *

import numpy as np
from scipy.ndimage import gaussian_filter as _gaussian_filter, convolve


# def leap_gaussian_t_kernel(axis_image: AxisImage, sigma: float, negate: bool = False) -> AxisImage:
#     ax = np.arange(-(3*sigma) // 2, (3*sigma) // 2 + 1)
#     kernel = int(ax > 0)*np.exp(-(ax**2) / (2 * sigma**2))
#     kernel /= kernel.sum()
#     if negate:
#         kernel = -kernel
#     return kernel


class PRE_FUNCTIONS:

    FUNCTION_CLASS = FunctionType.PRE_FUNCTION

    @staticmethod
    def invert(axis_img: AxisImage, axis_img_diff: AxisImage) -> AxisImage:
        return AxisImage(((-axis_img_diff.image) if axis_img_diff.image is not None else None), axis_img_diff.axis, axis_img_diff.name)


class XY_DIFF_FUNCTIONS:

    FUNCTION_CLASS = FunctionType.XY

    @staticmethod
    def gaussian_xy_kernel(img: np.ndarray, sigma: float) -> np.ndarray:
        _img_max, _img_min, _img_dtype = np.max(img), np.min(img), img.dtype
        r = _gaussian_filter(img, sigma=sigma, axes=(1,2), output="float32") # Peak 1 float32
        r: np.ndarray = (r*(_img_max/r.max()).astype(r.dtype)).astype(_img_dtype) # Peak 2 float32
        #r = (_img_min.astype(r.dtype) + (r + r.min()) / (r.max() - r.min())*(_img_max-_img_min).astype(r.dtype)).astype(_img_dtype)
        return r
    
    @staticmethod
    def get_gaussian_xy_kernel(sigma: float) -> Callable[[AxisImage, AxisImage], AxisImage]:
        def _wrapper(axis_img: AxisImage, axis_img_diff: AxisImage, sigma=sigma) -> AxisImage:
            img = axis_img_diff.image
            if img is None:
                return axis_img_diff.copy()
            t0 = time.perf_counter()
            r = XY_DIFF_FUNCTIONS.gaussian_xy_kernel(img, sigma=sigma)
            logger.debug(f"Calculated gaussian xy kernel in {(time.perf_counter()-t0):1.3f} s")
            return AxisImage(r, axis=axis_img_diff.axis, name=axis_img_diff.name)
        return _wrapper


class TRIGGER_FUNCTIONS:

    FUNCTION_CLASS = FunctionType.T

    
    @staticmethod
    def gaussian_t_kernel(img: np.ndarray, sigma: float) -> np.ndarray:
        return -_gaussian_filter(img, sigma=sigma, axes=(0), output=img.dtype)
    
    @staticmethod
    def get_gaussian_t_kernel(sigma: float) -> Callable[[AxisImage, AxisImage], AxisImage]:
        def _wrapper(axis_img: AxisImage, axis_img_diff: AxisImage, sigma=sigma) -> AxisImage:
            img = axis_img_diff.image
            if img is None:
                return axis_img_diff.copy()
            t0 = time.perf_counter()
            r = TRIGGER_FUNCTIONS.gaussian_t_kernel(img, sigma=sigma)
            logger.debug(f"Calculated gaussian t kernel in {(time.perf_counter()-t0):1.3f} s")
            return AxisImage(r, axis=axis_img_diff.axis, name=axis_img_diff.name)
        return _wrapper

    @staticmethod
    def baseline_delta(img_spatial_mean: np.ndarray, img: np.ndarray, invert: bool) -> np.ndarray:
        if invert:
            return img_spatial_mean[None, :, :] - img[1:, :, :]
        return img[1:, :, :] - img_spatial_mean[None, :, :]
    
    @staticmethod
    def get_baseline_delta(invert: bool = False) -> Callable[[AxisImage, AxisImage], AxisImage]:
        def _wrapper(axis_img: AxisImage, axis_img_diff: AxisImage) -> AxisImage:
            if axis_img.image is None:
                return axis_img_diff.copy()
            t0 = time.perf_counter()
            img_mean = AxisImage(axis_img.image, ImageView.SPATIAL.value, (axis_img.name if axis_img.name is not None else "")+"_tmp").mean_image
            if img_mean is None:
                return axis_img_diff.copy()
            r = TRIGGER_FUNCTIONS.baseline_delta(img_mean, axis_img.image, invert=invert)
            logger.debug(f"Calculated baseline delta in {(time.perf_counter()-t0):1.3f} s")
            return AxisImage(r, axis=axis_img_diff.axis, name=axis_img_diff.name)
        return _wrapper
    

    @staticmethod
    def sliding_cumsum(img: np.ndarray, n: int) -> np.ndarray:
        a1 = np.full(shape=(n), fill_value=1)
        a2 = np.full(shape=(n), fill_value=0)
        c = np.concatenate([a2, np.array([1]), a1])
        c = c[:, None, None]

        return np.floor_divide(convolve(img, c, output=img.dtype), n+1, dtype=img.dtype)
    
    @staticmethod
    def get_sliding_cumsum(n: int) -> Callable[[AxisImage, AxisImage], AxisImage]:
        def _wrapper(axis_img: AxisImage, axis_img_diff: AxisImage, n = n) -> AxisImage:
            img = axis_img_diff.image
            if img is None:
                return axis_img_diff.copy()
            t0 = time.perf_counter()
            r = TRIGGER_FUNCTIONS.sliding_cumsum(img, n=n)
            logger.debug(f"Calculated sliding cumsum kernel in {(time.perf_counter()-t0):1.3f} s")
            return AxisImage(r, axis=axis_img_diff.axis, name=axis_img_diff.name)
        return _wrapper