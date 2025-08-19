import tkinter as tk
from tkinter import messagebox, filedialog
import subprocess
import pathlib
import threading
import importlib.util

from neurotorchmz.core.session import *

class TraceSelector:

    proc: subprocess.Popen|None = None
    pipeThread: threading.Thread|None = None
    
    def __init__(self, session: Session) -> None:
        self.session = session
        window_events.WindowLoadedEvent.register(self.on_window_loaded)

    def on_window_loaded(self, e: window_events.WindowLoadedEvent) -> None:
        assert e.session.window is not None
        self.menu_settings = tk.Menu(e.session.window.menu_settings, tearoff=0)
        self.menu_plugin = e.menu_plugins(plugin_manager.get_module())
        e.session.window.menu_settings.add_cascade(label="TraceSelector", menu=self.menu_settings)

        e.session.window.menu_run.add_command(label="Start TraceSelector")
        self.menu_plugin.add_command(label="Terminate TraceSelector")


    @window_events.SynapseTreeviewContextMenuEvent.hook
    def on_tv_context_menu_created(e: window_events.SynapseTreeviewContextMenuEvent) -> None:
        e.export_context_menu.add_command(label="Open in TraceSelector", command=open)

    def test_installation() -> bool:
        """ Returns True if TraceSelector is installed in the current environment """
        return importlib.util.find_spec("trace_selector") is not None

    def menu_run_click() -> None:
        if 


    def StartTrace_Selector(self):
        if TraceSelector.proc is not None:
            self.gui.root.bell()
            if messagebox.askyesnocancel("Neurotorch", "Trace Selector is already running. Do you want to terminate it?"):
                TraceSelector.proc.terminate()
            else:
                return
        if TraceSelector.pipe_thread is not None and TraceSelector.pipe_thread.is_alive():
            self.gui.root.bell()
            messagebox.showerror("Neurotorch", "Trace Selector is still running and can't be terminated")

        pythonpath = Settings.GetSettings("traceselectorPythonPath")
        if not pythonpath:
            self.gui.root.bell()
            messagebox.showerror("Neurotorch", "You didn't specified the path to Trace Selector in the AppData config file (on Windows: AppData/Local/AndreasB/Neurotorch/neurtorch_config.ini you must set traceselectorPythonPath and traceselectorScriptPath)")

        args = [pythonpath, "-m", "trace_selector"]
        TraceSelector.proc = subprocess.Popen(args, stdout=subprocess.PIPE, stdin=subprocess.PIPE, text=True)
        TraceSelector.pipe_thread = threading.Thread(target=self.PipeThread)
        TraceSelector.pipe_thread.start()
        print("Started Trace Selector")

    def TerminateTrace_Selector(self):
        if TraceSelector.proc is None:
            self.gui.root.bell()
            messagebox.showwarning("Neurotorch", "Trace Selector is not running")
            return
        TraceSelector.proc.terminate()
        TraceSelector.proc = None
        messagebox.showinfo("Neurotorch", "Terminated Trace Selector")

    def PipeThread(self):
        if TraceSelector.proc is None or TraceSelector.proc.stdout is None:
            return
        while (line := TraceSelector.proc.stdout.readline().strip("\n")) != "":
            print("[Trace Selector]", line)
        print("Trace Selector stopped")

    def start_trace_selector(self):
        """ Attempts to start TraceSelector """
        if TraceSelector.proc is None:
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

        TraceSelector.proc.stdin.write(f"open\t{str(path)}\n")
        TraceSelector.proc.stdin.flush()

@SessionCreateEvent.hook
def on_session_created(e: SessionCreateEvent):
    TraceSelector(e.session)