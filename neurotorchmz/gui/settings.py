import os
import platformdirs
import pathlib
import configparser
import json
from PIL import Image

class Neurotorch_Settings:

    defaultSettings = {"ImageJ_Path": ""}
    ParentPath = None
    SuperParentPath = None
    UserPath = None
    MediaPath = None
    ResourcesPath = None
    DataPath = None
    ConfigPath = None
    TempPath = None
    config : configparser.ConfigParser = None

    def _CreateStatic():
        Neurotorch_Settings.ParentPath = os.path.abspath(os.path.join(os.path.join(__file__, os.pardir), os.pardir))
        Neurotorch_Settings.SuperParentPath = os.path.abspath(os.path.join(Neurotorch_Settings.ParentPath, os.pardir))
        Neurotorch_Settings.UserPath = os.path.join(Neurotorch_Settings.ParentPath, "user")
        Neurotorch_Settings.MediaPath = os.path.join(Neurotorch_Settings.ParentPath, "media")
        Neurotorch_Settings.ResourcesPath = os.path.join(Neurotorch_Settings.ParentPath, "resources")
        Neurotorch_Settings.PluginPath = os.path.join(Neurotorch_Settings.ParentPath, "plugins")
        Neurotorch_Settings.DataPath = platformdirs.user_data_path("Neurotorch", "AndreasB")
        pathlib.Path(Neurotorch_Settings.DataPath).mkdir(exist_ok=True, parents=True)
        Neurotorch_Settings.TempPath = os.path.join(Neurotorch_Settings.DataPath, "temp")
        pathlib.Path(Neurotorch_Settings.TempPath).mkdir(exist_ok=True, parents=True)
        for f in [os.path.join(Neurotorch_Settings.TempPath, f) for f in os.listdir(Neurotorch_Settings.TempPath)]:
            if os.path.isfile(f):
                os.remove(f)

        Neurotorch_Settings.ConfigPath = os.path.join(Neurotorch_Settings.DataPath, 'neurtorch_config.ini')
        Neurotorch_Settings.config = configparser.ConfigParser()
        Neurotorch_Settings.ReadConfig()

    def ReadConfig():
        Neurotorch_Settings.config.read(Neurotorch_Settings.ConfigPath)
        if "SETTINGS" not in Neurotorch_Settings.config.sections():
            Neurotorch_Settings.config.add_section("SETTINGS")
        for k,v in Neurotorch_Settings.defaultSettings.items():
            if not Neurotorch_Settings.config.has_option("SETTINGS", k):
                Neurotorch_Settings.config.set("SETTINGS", k, v)

        if not os.path.exists(Neurotorch_Settings.ConfigPath):
            Neurotorch_Settings.SaveConfig()

    def GetSettings(key: str) -> str|None:
        if not Neurotorch_Settings.config.has_option("SETTINGS", key):
            return None
        return Neurotorch_Settings.config.get("SETTINGS", key)
    
    def SetSetting(key: str, value: str):
        Neurotorch_Settings.config.set("SETTINGS", key, value)
        Neurotorch_Settings.SaveConfig()

    def SaveConfig():
        pathlib.Path(os.path.dirname(Neurotorch_Settings.ConfigPath)).mkdir(parents=True, exist_ok=True)
        with open(Neurotorch_Settings.ConfigPath, 'w') as configfile:
            Neurotorch_Settings.config.write(configfile)

class Neurotorch_Resources:

    _path_stringsJSON = None
    _json: dict = None

    def _CreateStatic():
        Neurotorch_Resources._path_stringsJSON = os.path.join(*[Neurotorch_Settings.ResourcesPath, "strings.json"])
        if not os.path.exists(Neurotorch_Resources._path_stringsJSON):
            return
        with open(Neurotorch_Resources._path_stringsJSON) as f:
            Neurotorch_Resources._json = json.load(f)

    def GetString(path:str) -> str:
        if Neurotorch_Resources._json is None:
            return ""
        _folder = Neurotorch_Resources._json
        for key in path.split("/"):
            if key not in _folder.keys():
                return ""
            _folder = _folder[key]
        if type(_folder) == str:
            return _folder
        return path
    
    def GetImage(relativepath: str):
        _path = os.path.abspath(os.path.join(Neurotorch_Settings.MediaPath, *relativepath.split("/")))
        if not os.path.exists(_path):
            return None
        return Image.open(_path)

Neurotorch_Settings._CreateStatic()
Neurotorch_Resources._CreateStatic()