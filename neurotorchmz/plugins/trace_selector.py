import tkinter as tk
from tkinter import messagebox, filedialog
import subprocess
import pathlib
import threading

from ..gui.window import Neurotorch_GUI
from ..gui.components.treeview import SynapseTreeview
from ..gui.settings import Neurotorch_Settings as Settings
from ..gui.tab3 import TabROIFinder

class TraceSelector:
    def __init__(self, gui: Neurotorch_GUI):
        self.gui = gui

        self.proc: subprocess.Popen = None
        self.pipeThread: threading.Thread = None

        self.menuTC = tk.Menu(self.gui.root, tearoff=0)
        self.gui.menuPlugins.add_cascade(label="Trace Selector", menu=self.menuTC)
        self.menuTC.add_command(label="Locate Environment", command=self.Locate)
        self.menuTC.add_command(label="Start", command=self.StartTrace_Selector)
        self.menuTC.add_command(label="Terminate", command=self.TerminateTrace_Selector)
        self.menuTC.add_separator()
        self.menuTC.add_command(label="Open CSV in Trace Selector", command=self.Open)

        self.tab3: TabROIFinder = self.gui.tabs[TabROIFinder]

        SynapseTreeview.API_rightClickHooks.append(self.AddExportCommandSynapseTreeview)

    def AddExportCommandSynapseTreeview(self, contextMenu: tk.Menu, importMenu: tk.Menu, exportMenu: tk.Menu):
        exportMenu.add_command(label="Open in Trace Selector", command=self.Open)

    def Locate(self):
        path = filedialog.askopenfilename(parent=self.gui.root, title="Neurotorch - Please select the python interpeter installed with Trace Selector", 
                filetypes=(("Python EXE with Trace Selector installed", "*.*"),) )
        if path is not None and path != "":
            Settings.SetSetting("traceselectorPythonPath", path)

    def StartTrace_Selector(self):
        if self.proc is not None:
            self.gui.root.bell()
            if messagebox.askyesnocancel("Neurotorch", "Trace Selector is already running. Do you want to terminate it?"):
                self.proc.terminate()
            else:
                return
        if self.pipeThread is not None and self.pipeThread.is_alive():
            self.gui.root.bell()
            messagebox.showerror("Neurotorch", "Trace Selector is still running and can't be terminated")

        pythonpath = Settings.GetSettings("traceselectorPythonPath")
        if not pythonpath:
            self.gui.root.bell()
            messagebox.showerror("Neurotorch", "You didn't specified the path to Trace Selector in the AppData config file (on Windows: AppData/Local/AndreasB/Neurotorch/neurtorch_config.ini you must set traceselectorPythonPath and traceselectorScriptPath)")

        args = [pythonpath, "-m", "trace_selector"]
        self.proc = subprocess.Popen(args, stdout=subprocess.PIPE, stdin=subprocess.PIPE, text=True)
        self.pipeThread = threading.Thread(target=self.PipeThread)
        self.pipeThread.start()
        print("Started Trace Selector")

    def TerminateTrace_Selector(self):
        if self.proc is None:
            self.gui.root.bell()
            messagebox.showwarning("Neurotorch", "Trace Selector is not running")
            return
        self.proc.terminate()
        self.proc = None
        messagebox.showinfo("Neurotorch", "Terminated Trace Selector")

    def PipeThread(self):
        if self.proc is None or self.proc.stdout is None:
            return
        while (line := self.proc.stdout.readline().strip("\n")) != "":
            print("[Trace Selector]", line)
        print("Trace Selector stopped")

    def Open(self):
        if self.proc is None:
            self.gui.root.bell()
            messagebox.showwarning("Neurotorch", "Trace Selector is not running")
            return
        
        if self.gui.ImageObject is None:
            self.gui.root.bell()
            return
        
        name = self.gui.ImageObject.name if self.gui.ImageObject.name != "" else "Neurotorch_Export" 
        path = pathlib.Path(Settings.TempPath) / f"{name}.csv"

        if self.tab3.tvSynapses.ExportCSVMultiM(path=path, dropFrame=True) != True:
            messagebox.showerror("Neurotorch", "With this command you export the multi measure data from the tab 'Synapse ROI Finder'. Please first create data there")

        self.proc.stdin.write(f"open\t{str(path)}\n")
        self.proc.stdin.flush()