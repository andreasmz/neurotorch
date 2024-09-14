# Neurotorch
![Neurotorch Logo](https://github.com/andreasmz/neurotorch/blob/main/doc/neurotorch_logo.jpg)

Neurotorch is a simple program to analyze microscopic images containing tagged neuron images, for example with bind to Glutamate release. It provides various tools containing the following
* Signal finding: Detect the frames where neurons fire
* ROI finding: Auto-detect ROIs (Regions of Interest)
* Synapse analysing: Use the detected ROIs and analyze each signal frame independently

Neurotorch is able to connect to a local ImageJ installation, but can also be run as standalone program. Image Files can be accessed from ImageJ or opened directly in Neurotorch. ROIs and the Diff Image can be back exported to ImageJ, while the measurement of the ROIs can be saved as CSV directly in Neurotorch. Also, Neurotorch can be imported as an regular module giving access to it's API for example from Jupyter Notebooks.