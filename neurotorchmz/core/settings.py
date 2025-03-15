import platformdirs
import configparser
import json
from PIL import Image
from pathlib import Path
import sys
import threading
import logging
from logging.handlers import RotatingFileHandler
logger = logging.getLogger("NeurotorchMZ")


class Neurotorch_Settings:
    """ Static class to access user configurations and data """

    app_data_path: Path = platformdirs.user_data_path(appname="NeurotorchMZ", appauthor=False, roaming=True, ensure_exists=True)
    tmp_path: Path = app_data_path / "tmp"
    config: configparser.ConfigParser = None


    def _CreateStatic():
        Neurotorch_Settings.app_data_path.mkdir(parents=True, exist_ok=True)
        Neurotorch_Settings.tmp_path.mkdir(exist_ok=True, parents=False)
        for f in Neurotorch_Settings.tmp_path.iterdir():
            if f.is_file():
                f.unlink()
                logger.debug(f"Cleared file {f.name} from the tmp folder")
            elif f.is_dir():
                f.rmdir()
                logger.debug(f"Cleared folder {f.name} from the tmp folder")
        Neurotorch_Settings.config = configparser.ConfigParser()
        Neurotorch_Settings.ReadConfig()

    def ReadConfig():
        """ Initializes the config parser """
        Neurotorch_Settings.config.read(Neurotorch_Settings.app_data_path / "settings.ini")
        if "SETTINGS" not in Neurotorch_Settings.config.sections():
            Neurotorch_Settings.config.add_section("SETTINGS")

        if not (Neurotorch_Settings.app_data_path / "settings.ini").exists():
            Neurotorch_Settings.SaveConfig()

    def GetSettings(key: str) -> str|None:
        """ Retrieve a setting. If the key does not exist, return None """
        if not Neurotorch_Settings.config.has_option("SETTINGS", key):
            return None
        return Neurotorch_Settings.config.get("SETTINGS", key)
    
    def SetSetting(key: str, value: str, save: bool = False):
        """ Set a setting. If save=True, the file is saved to disk """
        Neurotorch_Settings.config.set("SETTINGS", key, value)
        if save:
            Neurotorch_Settings.SaveConfig()

    def SaveConfig():
        """ Writes the config file to disk"""
        try:
            with open(Neurotorch_Settings.app_data_path / "settings.ini", 'w') as configfile:
                Neurotorch_Settings.config.write(configfile)
        except Exception as ex:
            logger.warning(f"Failed to save the config. The error message was: \n---\n%s\n---" % str(ex))

    def LoadPlugins():
        """ This function loads plugins from a) the shipped plugin folder contained in the package itself and b) the AppData folder """
        user_plugin_path = (Neurotorch_Settings.app_data_path / "plugins").mkdir(parents=True, exist_ok=True)


class Neurotorch_Resources:
    """ Static class to access resources """

    path = Path(__file__).parent.parent / "resources"

    _json: dict = None

    def _CreateStatic():
        path = Path(__file__).parent.parent / "resources" / "strings.json"
        with open(path) as f:
            Neurotorch_Resources._json = json.load(f)

    def GetString(path:str) -> str:
        """ Retreive a key by supplying the adress with slashes (example: tab2/algorithms/diffMax). Returns '' if the key is not found and the path itself if it does not point to a end node """
        if Neurotorch_Resources._json is None:
            return ""
        _folder = Neurotorch_Resources._json
        paths = path.split("/")
        for i, key in enumerate(paths):
            if key not in _folder.keys():
                logger.debug(f"Can't find key {path}. It stops at '{'/'.join(paths[0:i])}'")
                return ""
            _folder = _folder[key]
        if type(_folder) == str:
            return _folder
        return path
    
    def GetImage(filename: str) -> Image.Image:
        """ Open a image. Raises FileNotFoundError if the file can't be opened """
        path = Neurotorch_Resources.path / filename
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Can't find the resource file {filename}")
        return Image.open(path)
    
_fmt = logging.Formatter('[%(asctime)s %(levelname)s]: %(message)s')
_fmtFile = logging.Formatter('[%(asctime)s|%(levelname)s|%(module)s]: %(message)s')
file_logging_handler = RotatingFileHandler(Neurotorch_Settings.app_data_path / "log.txt", mode="a", maxBytes=(1024**2), backupCount=10)
file_logging_handler.setFormatter(_fmtFile)
file_logging_handler.setLevel(logging.DEBUG)
stream_logging_handler = logging.StreamHandler()
stream_logging_handler.setFormatter(_fmt)
stream_logging_handler.setLevel(logging.ERROR)
logger.setLevel(logging.DEBUG)
logger.addHandler(file_logging_handler)
logger.addHandler(stream_logging_handler)    

def log_exceptions_hook(exc_type, exc_value=None, exc_traceback=None, thread=None):
    logger.error(f"An {repr(exc_type)} happened: {exc_value}", exc_info=(exc_type, exc_value, exc_traceback))
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

def thread_exceptions_hook(args):
    log_exceptions_hook(*args)

sys.excepthook = log_exceptions_hook
threading.excepthook = thread_exceptions_hook

Neurotorch_Settings._CreateStatic()
Neurotorch_Resources._CreateStatic()

def log_exception_debug(ex: Exception, msg:str = None):
    logger.debug("%s:\n---\n%s\n---" % (msg if msg is not None else f"An exception happened", str(ex)))