""" Implements a simple test plugin """

__version__ = "1.0.0"
__author__ = "Andreas Brilka"
__plugin_name__ = "Test Plugin"
__plugin_desc__ = """ A demo plugin to test Neurotorch's plugin system """

from neurotorchmz.core.session import *


@events.SessionCreateEvent.hook
def on_session_start(e: events.SessionCreateEvent):
    logger.debug(f"Testplugin noticed that the session started")