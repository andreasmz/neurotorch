import json
import os

from neurotorch.gui.settings import Neurotorch_Settings as Settings

class _ResourceManager():

    def __init__(self):
        self.resourceFolderPath = os.path.join(*[Settings.ParentPath, "resources", "strings.json"])
        if not os.path.exists(self.resourceFolderPath):
            return
        with open(self.resourceFolderPath) as f:
            self.json = json.load(f)
         
class JSON_Obj():
    def __init__(self, json: list):
        self.json = json

    def Get(self, key: str):
        if self.json is None:
            return JSON_Obj(None)
        if not key in self.json.keys():
            return JSON_Obj(None)
        return JSON_Obj(self.json[key])
        
    def __str__(self):
        if self.json is None:
            return ""
        return str(self.json)


ResourceManager = _ResourceManager() 

def Get(key: str) -> JSON_Obj:
    return JSON_Obj(ResourceManager.json).Get(key)