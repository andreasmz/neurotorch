""" Provides a module to load and update settings. Provides also the paths of resources and the temp folder for other modules """
from ..core import logs
from ..core.logs import logger

import platformdirs
import configparser
from pathlib import Path
import atexit
from typing import Any
import os
import shutil

# Initialize paths
app_data_path = platformdirs.user_data_path(appname="NeurotorchMZ", appauthor="andreasmz", roaming=True, ensure_exists=True)
app_data_local_path = platformdirs.user_data_path(appname="NeurotorchMZ", appauthor="andreasmz", roaming=False, ensure_exists=True)
log_path = app_data_path / "logs.txt"
tmp_path = app_data_local_path / "tmp"
environ_path = app_data_local_path / "environment"
user_plugin_path = app_data_path / "plugins"
preinstalled_plugin_path = Path(__file__).parent.parent / "plugins"
resource_path = Path(__file__).parent.parent / "resources"

# Create the appdata folder if not exist
app_data_path.mkdir(parents=True, exist_ok=True)
tmp_path.mkdir(exist_ok=True, parents=False)
environ_path.mkdir(exist_ok=True, parents=False)
user_plugin_path.mkdir(exist_ok=True, parents=False)

# Logging
logs.init_file_handler(log_path)

# Search for library folders inside the environ path and add them to the environ variable
for p in environ_path.iterdir():
    if not p.is_dir():
        continue
    if ("jdk" in p.name) and (p / "bin").exists():
        if shutil.which("javac") is None:
            os.environ["JAVA_HOME"] = str(p)
            os.environ["PATH"] += os.pathsep + str(p / "bin")
            logger.debug(f"Found '{p.name}' in the AppData folder, created JAVA_HOME and added '{p / 'bin'}' temporarily to PATH")
        else:
            logger.debug(f"Found '{p.name}' in the AppData folder, but javac seems already to be installed.")
    if ("maven" in p.name) and (p / "bin").exists():
        os.environ["PATH"] += os.pathsep + str(p / "bin")
        logger.debug(f"Found '{p.name}' in the AppData folder and added '{p / 'bin'}' temporarily to PATH")

# Link definitions
documentation_url = "https://andreasmz.github.io/neurotorch/"

# Config
class Config:

    config_parser: configparser.ConfigParser
    config_path: Path

    def __init_subclass__(cls) -> None:
        cls.config_parser = configparser.ConfigParser()
        d = {}
        for section_name, section_obj in vars(cls).items():
            if not isinstance(section_obj, type) or not issubclass(section_obj, Section):
                continue
            section_obj.config = cls
            d[section_name] = {}
            for option_name, option_obj in vars(section_obj).items():
                if not isinstance(option_obj, Option):
                    continue
                d[section_name][option_name] = option_obj.default_value
        cls.config_parser.read_dict(d)
        cls.load_config()
        atexit.register(cls.save_config)
    
    @classmethod
    def load_config(cls):
        """ Initializes the config parser """
        cls.config_parser.read(cls.config_path)
        if not (cls.config_path).exists():
            cls.save_config()
    
    @classmethod
    def save_config(cls) -> None:
        try:
            with open(cls.config_path, 'w') as configfile:
                cls.config_parser.write(configfile)
            logger.debug(f"Saved config '{cls.config_path.name}'")
        except Exception:
            logger.warning(f"Failed to save config '{cls.config_path.name}':", exc_info=True)


class Section:

    config: type[Config]

    def __init_subclass__(cls) -> None:
        for attr_name, attr_value in cls.__dict__.items():
            if isinstance(attr_value, Option):
                attr_value.section = cls
                attr_value.name = attr_name
    

class Option:
    
    def __init__(self, default_value) -> None:
        self.default_value = default_value
        self.name: str
        self.section: type[Section]
    
    @property
    def config_parser(self) -> configparser.ConfigParser:
        return self.section.config.config_parser
    
    def save(self) -> None:
        self.section.config.save_config()

    def get(self):
        raise NotImplementedError()    
    
    def set(self, val: Any, save: bool = False) -> None:
        self.config_parser.set(self.section.__name__, self.name, str(val))
        logger.debug(f"Changed setting '{self.section.__name__}.{self.name}' from '{str(self.get())}' to '{str(val)}'")
        if save:
            self.save()
    
class StringOption(Option):
    def get(self) -> str:
        return self.config_parser.get(self.section.__name__, self.name, fallback=self.default_value)

class IntOption(Option):
    def get(self) -> int:
        return self.config_parser.getint(self.section.__name__, self.name, fallback=self.default_value)

class FloatOption(Option):
    def get(self) -> float:
        return self.config_parser.getfloat(self.section.__name__, self.name, fallback=self.default_value)
    
class BoolOption(Option):
    def get(self) -> bool:
        return self.config_parser.getboolean(self.section.__name__, self.name, fallback=self.default_value)
    
class PathOption(Option):
    def get(self) -> Path|None:
        p = self.config_parser.get(self.section.__name__, self.name, fallback=self.default_value)
        if p is not None and p != "":
            return Path(p).resolve()
        return None


# Default settings
class UserSettings(Config):
    config_path = Path(app_data_path / "settings.ini")
    class IMAGEJ(Section):
        imagej_path = PathOption("")
        
    class SIGNAL_DETECTION(Section):
        peak_width_left = IntOption(1)
        peak_width_right = IntOption(6)

# Temp files
def clear_temp_files():
    """ Clears the temporary files and folders """
    for f in tmp_path.iterdir():
        if f.is_file():
            try:
                f.unlink()
            except Exception:
                logger.warning(f"Failed to remove temporary file {f.name}:", exc_info=True)
            else:
                logger.debug(f"Cleared file {f.name} from the tmp folder")
        elif f.is_dir():
            try:
                f.rmdir()
            except Exception:
                logger.warning(f"Failed to remove temporary folder {f.name}:", exc_info=True)
            else:
                logger.debug(f"Cleared folder {f.name} from the tmp folder")

clear_temp_files()
atexit.register(clear_temp_files)