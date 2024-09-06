# Neurotorch
Neurotorch is a simple program to analyze microscopic images containing various neurons. It provides various tools containing the following
* Signal finding: Detect frames in a video, where neurons fire
* ROI finding: Auto-detect ROIs (Regions of Interest)
* Synapse analysing: Use the detected ROIs and analyze each signal frame independently <br>
Neurotorch can be run as a standalone program with an conda enviorenment having PyImageJ installed. If ImageJ connectivity is not needed, Neurotorch Light can be used lacking support for ImageJ but
beeing compiled in a stand alone File (currently Windows only). It also can be used as an API (for example in Jupyter Notebooks) by simply import the module