""" Utilities for logging in Neurotorch """
import logging
import sys
import threading
import types
from pathlib import Path
from logging.handlers import RotatingFileHandler

logger = logging.getLogger("NeurotorchMZ")
""" The root logger for NeurotorchMZ. The level defaults to DEBUG to allow derived Handlers (e.g. StreamHandler, RotatingFileHandler) to set custom (higher) levels """

debugging = False

_fmt = logging.Formatter('[%(asctime)s %(levelname)s]: %(message)s')
_fmtFile = logging.Formatter('[%(asctime)s|%(levelname)s|%(module)s]: %(message)s')

stream_logging_handler = logging.StreamHandler()
""" The default logging handler to the user console """
stream_logging_handler.setFormatter(_fmt)
stream_logging_handler.setLevel(logging.ERROR)

file_logging_handler: RotatingFileHandler
""" The default file logging handler """

logger.setLevel(logging.DEBUG)
logger.addHandler(stream_logging_handler) 
_exception_logger = logging.getLogger("NeurotorchMZ_Errors")   
_exception_logger.setLevel(logging.DEBUG)

def _ini_file_handler(app_data_path: Path) -> None:
    """ Should be called from the settings handler when the AppData Path is set to initialize the file handler for logging """
    global file_logging_handler, _fmtFile, logger
    file_logging_handler = RotatingFileHandler(app_data_path / "log.txt", mode="a", maxBytes=(1024**2), backupCount=10)
    file_logging_handler.setFormatter(_fmtFile)
    file_logging_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_logging_handler)

def log_exceptions_hook(exc_type: type[BaseException], exc_value: BaseException, exc_traceback: types.TracebackType | None = None) -> None:
    global logger
    logger.exception(f"An {repr(exc_type)} happened: {exc_value}", exc_info=(exc_type, exc_value, exc_traceback))
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

def thread_exceptions_hook(exc_type: type[BaseException], exc_value: BaseException, exc_traceback: types.TracebackType | None = None, thread = None) -> None:
    global logger
    logger.debug(type(thread))
    logger.exception(f"An {repr(exc_type)} happened in thread: {exc_value}", exc_info=(exc_type, exc_value, exc_traceback))
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

def start_debugging():
    """ Starts the debugging of not started yet """
    global debugging
    if debugging:
        return
    debugging = True
    stream_logging_handler.setLevel(logging.DEBUG)
    logger.debug(f"Started debugging")

sys.excepthook = log_exceptions_hook
threading.excepthook = thread_exceptions_hook