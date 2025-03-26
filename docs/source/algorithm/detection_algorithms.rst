Detection Algorithms
========================

Neurotorch currently offers three detection algorithms used to find areas of synaptic activity.


Threshold
--------------------------

.. note::

    This algorithm is deprecated and should not be used anymore

The threshold algorithm has quite a simple approach: Select connected areas above the given
threshold (diagonal jumps are considered connected). If the given area exceeds a given size,
take the center (not weighted by signal strength) and use it as base for a circular ROI of radius r.
The minium area is calculated by multiplying the circles area (given by the supplied radius) times the
"Min. converage" factor. 

Example:

Radius r = 6px and minimum coverage of 60%. Therefore the area must exceed π*6²*0.6 ~ 68 px.

Hysteresis thresholding
--------------------------


Local Max
--------------------------

The local maximum algorithm is in general the best algorithm to choose. It tries to find local maxima and extends
them into their neighborhood if certain criteria are met. In contrast to hysteresis thresholding it can work with 
images with ares of high and local signal strength. Like hysteresis thresholding it provides an auto parameter option
to set the most common parameters depending on the image properties.

=========================== =========================== ==========================================================
Parameter                   Type                        Description
=========================== =========================== ==========================================================
lower threshold             integer or float            Defines the noise level, as all values greater or equal
                                                        this threshold are considered 
=========================== =========================== ==========================================================