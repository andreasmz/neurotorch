from neurotorch.gui.settings import Neurotorch_Settings as Settings
import fsspec
from tkinter import messagebox
import requests
import os
from pathlib import Path

class _Updater:
    def __init__(self):
        _versiontxtPath = os.path.join(Settings.ParentPath, "VERSION.txt")
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
                return False
            self.version_github = response.text
        except Exception as ex:
            print(ex)
            return False
        return True

    def DownloadUpdate(self):
        if not self.CheckForUpdate():
            messagebox.showerror("Neurotorch", "The update server is not available")
            return
        try:
            self.fs = fsspec.filesystem("github", org="andreasmz", repo="neurotorch", branch="main")
            if (len(Settings.SuperParentPath) < 10):
                # Never download to toplevel or any wrong path like '' or 'C:\'
                # Yeah, it's a dump solution...
                messagebox.showerror("There was an error downloading the update (Home Path is unsafe)")
                return
            destination = Path(Settings.SuperParentPath) / "neurotorch_update"
            print(f"Download Update to {destination}")
            destination.mkdir(exist_ok=True)
            self.fs.get("neurotorch", destination.as_posix(), recursive=True)
            print("Update finished")
        except Exception as ex:
            print(ex)
            messagebox.showerror("Neurotorch", "The updater failed for unkown reason")
            return
        messagebox.showwarning("Neurotorch", f"Neurotorch version {self.version_github} was installed into {destination}.\n\n1. Close the application\n2. Rename 'neurotorch/neurotorch' to 'neurotorch/neurotorch_old'\n3. Rename 'neurotorch_update' to 'neurotorch'\nto install the update\n4. If all works, delete 'neurotorch/neurotorch_old'")
        if (not messagebox.askyesno("Neurotorch", "Did you followed all steps?")):
            messagebox.showwarning("Neurotorch", f"Neurotorch version {self.version_github} was installed into {destination}.\n\n1. Close the application\n2. Rename 'neurotorch/neurotorch' to 'neurotorch/neurotorch_old'\n3. Rename 'neurotorch_update' to 'neurotorch'\nto install the update\n4. If all works, delete 'neurotorch/neurotorch_old'")

Updater = _Updater()