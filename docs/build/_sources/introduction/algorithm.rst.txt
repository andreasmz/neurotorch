Algorithm and core concepts
###############################

Delta video
=================================

The main idea of Neurotorch is to use the differences between frames to find peaks of
brightness. Therefore Neurotorch calculates the so called delta video.

.. figure:: /../media/nt/algorithm/diffImage_overview.jpg
  :alt: Overview of delta video frames around a stimulation

  Example for a delta video around an external stimulation (frame 100).
  In the microscopic video (first row) you can see the increase in brightness in frame 100
  and 101, which result in bright spots in the delta video (row 2 and 3). For detection,
  values in the delta video below 0 are clipped to 0 (row 3)


Denoising the delta video
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. figure:: /../media/nt/algorithm/diffImage_convolution_compare.png
  :alt: Different levels of denoising for the delta video compared

  Different levels of denoising for the delta video compared. In general, a Gaussian kernel with σ=2px is good a compromise.


The performance of the algorithms can be enchanced by denoising the delta video frames. This is done by applying a Gaussian kernel
on each frame of the video. The idea is that an increase in brightness is only significant,
if neighbouring pixels show the same trend. You can choose different σ parameters or use the default of σ=2px.

Note that this does not alter any image data, as only the delta video used for the Neurotorch`s algorithms is altered.

Image views
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

As an microscopic video is threedimensional, for displaying it must be reduced
to an 2D image. Neurotorch knows four types of reducing it to 2D

- Mean
- Median
- Standard deviation (*Std*)
- Maximum

Each of this functions is applied pixelwise.