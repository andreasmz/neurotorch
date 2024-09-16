import neurotorch.gui.settings as settings
import fsspec
from tkinter import messagebox
import requests
import os
from pathlib import Path

class _Updater:
    def __init__(self):
        _versiontxtPath = os.path.join(settings.UserSettings.ParentPath, "VERSION.txt")
        if not os.path.exists(_versiontxtPath):
            self.version = "?"
        else:
            with open(_versiontxtPath, 'r') as f:
                self.version = f.readline()

        self.version_github = None

    def CheckForUpdate(self):
        self.version_github = None
        try:
            response = requests.get("https://raw.githubusercontent.com/andreasmz/neurotorch/main/neurotorch/VERSION.txt")
            if (response.status_code != 200):
                return
            self.version_github = response.text
        except Exception as ex:
            print(ex)
            return False

    def DownloadUpdate(self):
        try:
            self.fs = fsspec.filesystem("github", org="andreasmz", repo="neurotorch", branch="main")
            if (len(settings.UserSettings.SuperParentPath) < 10):
                # Never download to toplevel or any wrong path like '' or 'C:\'
                # Yeah, it's a dump solution...
                messagebox.showerror("There was an error downloading the update (Home Path is unsafe)")
                return
            destination = Path(settings.UserSettings.SuperParentPath) / "neurotorch_update"
            print(f"Download Update to {destination}")
            destination.mkdir(exist_ok=True)
            self.fs.get(self.fs.ls("neurotorch"), destination.as_posix(), recursive=True)
            print("Update finished")
        except Exception as ex:
            print(ex)
            messagebox.showerror("Neurotorch", "The updater failed for unkown reason")

Updater = _Updater()