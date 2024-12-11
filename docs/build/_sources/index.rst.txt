Neurotorch documentation
========================

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Getting started

   installation
   tabs/tab_image
   tabs/tab_signal
   tabs/tab_roifinder
   imagej

.. toctree::
   :hidden:
   :caption: Algorithms

   algorithm/detection_algorithms
   algorithm/signal_algorithms

.. warning::
   You find here an early alpha version of the documentation currently beeing written

Neurotorch is a tool designed to extract regions of synaptic activity in neurons tagges with iGluSnFR, 
but is in general capable to find any kind of local brightness increase due to synaptic activity. 
It works with microscopic image series / videos and is able to open an variety of formats (for details see below)

- **Fiji/ImageJ**: Full connectivity provided. Open files in ImageJ and send them to Neurotorch and vice versa.
- **Stimulation extraction**: Find the frames where stimulation was applied
- **ROI finding**: Auto detect regions with high synaptic activity. Export data directly or send the ROIs back to ImageJ
- **Image analysis**: Analyze each frame of the image and get a visual impression where signal of synapse activity was detected
- **API**: You can access the core functions of Neurotorch also by importing it as an python module

.. image:: media/neurotorch_overview.png
  :alt: Overview of Neurotorchs GUI
