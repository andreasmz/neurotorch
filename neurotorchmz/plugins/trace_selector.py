import tkinter as tk
from tkinter import messagebox
import subprocess
import pathlib
import threading

from ..gui.window import Neurotorch_GUI
from ..gui.settings import Neurotorch_Settings as Settings
from ..gui.tab3 import Tab3

class TraceSelector:
    def __init__(self, gui: Neurotorch_GUI):
        self.gui = gui

        self.proc: subprocess.Popen = None
        self.pipeThread: threading.Thread = None

        self.menuTC = tk.Menu(self.gui.root, tearoff=0)
        self.gui.menuPlugins.add_cascade(label="Trace Selector", menu=self.menuTC)
        self.menuTC.add_command(label="Start", command=self.StartTrace_Selector)
        self.menuTC.add_command(label="Terminate", command=self.TerminateTrace_Selector)
        self.menuTC.add_separator()
        self.menuTC.add_command(label="Open CSV in Trace Selector", command=self.Open)

        self.tab3: Tab3 = self.gui.tabs["Tab3"]

        self.btnOpenInTraceSelector = tk.Button(self.tab3.frameBtnsExport, text="Open in Trace Selector", command=self.Open)
        self.btnOpenInTraceSelector.grid(row=1, column=0)


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
        modulepath = Settings.GetSettings("traceselectorScriptPath")
        if not pythonpath or not modulepath:
            self.gui.root.bell()
            messagebox.showerror("Neurotorch", "You didn't specified the path to Trace Selector in the AppData config file (on Windows: AppData/Local/AndreasB/Neurotorch/neurtorch_config.ini you must set traceselectorPythonPath and traceselectorScriptPath)")

        args = [pythonpath, modulepath]
        self.proc = subprocess.Popen(args, stdout=subprocess.PIPE, stdin=subprocess.PIPE, text=True)
        self.pipeThread = threading.Thread(target=self.PipeThread)
        self.pipeThread.start()

    def TerminateTrace_Selector(self):
        if self.proc is None:
            self.gui.root.bell()
            messagebox.showwarning("Neurotorch", "Trace Selector is not running")
            return
        self.proc.terminate()
        self.proc = None
        messagebox.showinfo("Neurotorch", "Terminated Trace Selector")

    def PipeThread(self):
        return True
        # Currently not necessary
        if self.proc is None or self.proc.stdout is None:
            return
        i = 0
        while (line := self.proc.stdout.readline().strip("\n")) != "":
            print(i, line)
            i += 1

    def Open(self):
        if self.proc is None:
            self.gui.root.bell()
            messagebox.showwarning("Neurotorch", "Trace Selector is not running")
            return
        
        _buffer = self.tab3.ExportCSVMultiM(toStream=True, dropFrame=True)
        if (_buffer is None):
            self.gui.root.bell()
            messagebox.showerror("Neurotorch", "With this command you export the multi measure data from the tab 'Synapse ROI Finder'. Please first create data there")
            return
        path = pathlib.Path(Settings.DataPath) / "temp_TraceSelectorExport.csv"
        with open(path, "w") as f:
            f.write(_buffer)

        self.proc.stdin.write(f"open\t{str(path)}\n")
        self.proc.stdin.flush()