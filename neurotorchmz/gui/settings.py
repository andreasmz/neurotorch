import os, sys
import json
import platformdirs
import pathlib
import configparser


class Neurotorch_Settings:

    defaultSettings = {"ImageJ_Path": ""}
    ParentPath = None
    SuperParentPath = None
    UserPath = None
    MediaPath = None
    ResourcesPath = None
    DataPath = None
    ConfigPath = None
    config : configparser.ConfigParser = None

    def _CreateStatic():
        Neurotorch_Settings.ParentPath = os.path.abspath(os.path.join(os.path.join(__file__, os.pardir), os.pardir))
        Neurotorch_Settings.SuperParentPath = os.path.abspath(os.path.join(Neurotorch_Settings.ParentPath, os.pardir))
        Neurotorch_Settings.UserPath = os.path.join(Neurotorch_Settings.ParentPath, "user")
        Neurotorch_Settings.MediaPath = os.path.join(Neurotorch_Settings.ParentPath, "media")
        Neurotorch_Settings.ResourcesPath = os.path.join(Neurotorch_Settings.ParentPath, "resources")
        Neurotorch_Settings.DataPath = platformdirs.user_data_path("Neurotorch", "AndreasB")
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

Neurotorch_Settings._CreateStatic()