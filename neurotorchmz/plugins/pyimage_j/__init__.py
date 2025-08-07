""" The pyImageJ module provides a connection layer between Fiji/ImageJ and Neurotorch """

__version__ = "1.0.0"
__author__ = "Andreas Brilka"
__plugin_name__ = "Fiji/ImageJ bridge"
__plugin_desc__ = """ Provides a bridge to a local Fiji/ImageJ installation via pyimagej. Requires open-jdk and apache-maven to be installed """

from . import pyimagej