import os
import json

class _UserSettings():
    def __init__(self) -> None:
        self.ParentPath = os.path.abspath(os.path.join(os.path.join(__file__, os.pardir), os.pardir))
        self.UserPath = os.path.join(self.ParentPath, "user")
        self.Settings = None
        self.ParseSettings()

    def ReadSettings(self):
        self.Settings = None
        _settingsFile = os.path.join(self.UserPath, "settings.json")
        if not os.path.isfile(_settingsFile):
            print("settings.json not found")
            return
        try:
            with open(_settingsFile) as f:
                self.Settings = {}
                d = json.load(f)
                for k,v in d.items():
                    self.Settings[k] = v
        except Exception:
            print("Can't open settings.json")
            return
        self.ParseSettings()
        
    def ParseSettings(self):
        self.imageJPath = None
        if self.Settings is None:
            return
        if "ImageJPath" in self.Settings.keys(): self.imageJPath = self.Settings["ImageJPath"]


UserSettings = _UserSettings()