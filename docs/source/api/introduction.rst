Introduction to the Neurotorch API
######################################

Neurotorch is shipped with an API and plugin system. Popular use cases may be:

- Automate the image analysis
- Add custom filters
- Interact with the UI and add custom features (e.g. as the shipped plugins for Fiji/ImageJ and TraceSelector)

Here you find the documentation for those interfaces.

Interact with Neurotorch
==========================

Besides the common approach to start Neurotorch via a shortcut or importing the module like
you can also import Neurotorch from any Python script

.. code-block:: python

   import neurotorchmz
   session = neurotorchmz.start_background(headless=False)

The `start_background()` function returns a :class:`Session <neurotorchmz.core.session.Session>` object which holds references to all objects associated with Neurotorch.
It is your main connection point to the API. If you do not need the GUI, launch with `headless=False`. Please note that the session is returned immediately while you need to wait for the GUI
to be ready before you should interact with the API. 


Important classes
==========================

If you want to use the Neurotorch API, you should have a look at the following classes first

* :class:`neurotorchmz.core.session.Session`: An object of this class is returned when starting Neurotorch. It allows you to interact with the API and GUI
* :class:`neurotorchmz.utils.image.ImageObject`: This class is used to efficiently work with videos (called images for history reasons) by caching views (e.g. the spatial) or the delta video.
* :mod:`neurotorchmz.utils.synapse_detection`: This module contains code to detect ROIs and Synapses in an ImageObject. It includes the algorithms and classes to describe Synapses and ROIs
* :mod:`neurotorchmz.utils.signal_detection`: This module contains the code to detect signals (a generic term for stimulation) in ImageObjects.
* :class:`neurotorchmz.core.events.Event`: If you want to develop a plugin, the event library may be helpful. For example, the GUI fires a :class:`WindowLoadedEvent <neurotorchmz.gui.events.WindowLoadedEvent>` as well as a :class:`ImageObjectChangedEvent <neurotorchmz.gui.events.ImageObjectChangedEvent>`