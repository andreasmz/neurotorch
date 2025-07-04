""" Provides a module to load and update settings. Provides also the paths of resources and the temp folder for other modules """
import platformdirs
import configparser
from pathlib import Path
import atexit

from .logger import logger

# Initialize paths
app_data_path = platformdirs.user_data_path(appname="NeurotorchMZ", appauthor=False, roaming=True, ensure_exists=True)
tmp_path: Path = app_data_path / "tmp"
user_plugin_path = app_data_path / "plugins"
preinstalled_plugin_path = Path(__file__).parent.parent / "plugins"
resource_path = Path(__file__).parent.parent / "resources"

# Create the appdata folder if not exist
app_data_path.mkdir(parents=True, exist_ok=True)
tmp_path.mkdir(exist_ok=True, parents=False)
user_plugin_path.mkdir(exist_ok=True, parents=False)

# Clear temp files
for f in tmp_path.iterdir():
    if f.is_file():
        f.unlink()
        logger.debug(f"Cleared file {f.name} from the tmp folder")
    elif f.is_dir():
        f.rmdir()
        logger.debug(f"Cleared folder {f.name} from the tmp folder")

config = configparser.ConfigParser()

def _ReadConfig():
    """ Initializes the config parser """
    config.read(app_data_path / "settings.ini")
    if "SETTINGS" not in config.sections():
        config.add_section("SETTINGS")
    if not (app_data_path / "settings.ini").exists():
        SaveConfig()

_ReadConfig()

def ClearTempFiles():
    """ Clears the temporary files and folders """
    for f in tmp_path.iterdir():
        if f.is_file():
            try:
                f.unlink()
            except Exception as ex:
                logger.warning(f"Failed to remove temporary file {f.name} ({repr(ex)})")
            else:
                logger.debug(f"Cleared file {f.name} from the tmp folder")
        elif f.is_dir():
            try:
                f.rmdir()
            except Exception as ex:
                logger.warning(f"Failed to remove temporary folder {f.name} ({repr(ex)})")
            else:
                logger.debug(f"Cleared folder {f.name} from the tmp folder")

ClearTempFiles()

def GetSettings(key: str) -> str|None:
    """ Retrieve a setting. If the key does not exist, return None """
    if not config.has_option("SETTINGS", key):
        return None
    return config.get("SETTINGS", key)

def SetSetting(key: str, value: str, save: bool = False):
    """ Set a setting. If save=True, the file is saved to disk """
    config.set("SETTINGS", key, value)
    if save:
        SaveConfig()

def SaveConfig():
    """ Writes the config file to disk"""
    try:
        with open(app_data_path / "settings.ini", 'w') as configfile:
            config.write(configfile)
        logger.debug("Saved the config")
    except Exception as ex:
        logger.warning(f"Failed to save the config. The error message was: \n---\n%s\n---" % str(ex))

def _LoadPlugins():
    """ This function loads plugins from a) the shipped plugin folder contained in the package itself and b) the AppData folder """
    user_plugin_path = (app_data_path / "plugins").mkdir(parents=True, exist_ok=True)

atexit.register(SaveConfig)
atexit.register(ClearTempFiles)