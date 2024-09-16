import neurotorch.gui.settings as settings
import fsspec
import requests
import os

class _Updater:
    def __init__(self):
        _versiontxtPath = os.path.join(settings.UserSettings.ParentPath, "VERSION.txt")
        if not os.path.exists(_versiontxtPath):
            self.version = "?"
        else:
            with open(_versiontxtPath, 'r') as f:
                self.version = f.readline()

        #self.fs = fsspec.filesystem("github", org="andreasmz", repo="neurotorch")
        self.version_github = None

    def CheckForUpdate(self):
        self.version_github = None
        try:
            response = requests.get("https://raw.githubusercontent.com/andreasmz/neurotorch/main/neurotorch/neurotorch/VERSION.txt")
            if (response.status_code != 200):
                return
            self.version_github = response.text
        except Exception as ex:
            print(ex)
            return False

    def DownloadUpdate(self):
        #destination = Path.home() / "test_recursive_folder_copy"
        #destination.mkdir(exist_ok=True, parents=True)
        #fs.get(fs.ls("src/"), destination.as_posix(), recursive=True)
        pass

Updater = _Updater()