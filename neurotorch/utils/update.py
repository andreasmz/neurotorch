import neurotorch.gui.settings as settings
import fsspec
import requests
from pathlib import Path

class _Updater:
    def __init__(self):
        self.fs = fsspec.filesystem("github", org="andreasmz", repo="neurotorch")
        self.version_github = None

    def CheckForUpdate(self):
        try:
            response = requests.get("https://raw.githubusercontent.com/andreasmz/neurotorch/main/version.txt")
            if (response.status_code != 200):
                return
            self.version_github = response.text
        except Exception as ex:
            print(ex)
            return False

    def DownloadUpdate(self):
        #destination = Path.home() / "test_recursive_folder_copy"
        #destination.mkdir(exist_ok=True, parents=True)
        fs.get(fs.ls("src/"), destination.as_posix(), recursive=True)

Updater = _Updater()