import logging
import sys

logger = logging.getLogger("NeurotorchMZ")
formatter = logging.Formatter(fmt="[%(asctime)s|%(module)s|%(levelname)s] %(message)s")
streamHandler = logging.StreamHandler(sys.stdout)
streamHandler.setFormatter(formatter)
streamHandler.setLevel(logging.DEBUG)
logger.addHandler(streamHandler)