import tkinter as tk
from tkinter import messagebox, filedialog
import subprocess
import pathlib
import threading
import importlib.util

from neurotorchmz.core.session import *

class TraceSelectorBridge:

    proc: subprocess.Popen|None = None
    pipe_thread: threading.Thread|None = None
    
    def __init__(self, session: Session) -> None:
        self.session = session
        window_events.WindowLoadedEvent.register(self.on_window_loaded)
        window_events.SynapseTreeviewContextMenuEvent.register(self.on_tv_context_menu_created)

    def on_window_loaded(self, e: "window_events.WindowLoadedEvent") -> None:
        assert e.session.window is not None
        self.menu_settings = tk.Menu(e.session.window.menu_settings, tearoff=0)
        self.menu_plugin = e.menu_plugins(plugin_manager.get_module())
        #e.session.window.menu_settings.add_cascade(label="TraceSelector", menu=self.menu_settings)

        e.session.window.menu_run.add_command(label="Start TraceSelector", command=self.ask_for_start)
        self.menu_plugin.add_command(label="Install dependencies", command=self.ask_for_installation)
        self.menu_plugin.add_command(label="Terminate TraceSelector", command=self.kill_trace_selector)

    def on_tv_context_menu_created(self, e: "window_events.SynapseTreeviewContextMenuEvent") -> None:
        e.export_context_menu.add_command(label="Open in TraceSelector", command=lambda:self.export_roifinder_traces(e.detection_result))

    def test_installation(self) -> bool:
        """ Returns True if TraceSelector is installed in the current environment """
        return importlib.util.find_spec("trace_selector") is not None
    
    def is_trace_selector_running(self) -> bool:
        """ Returns True if TraceSelector is running and ready. Garbage collects the proc variable """
        if TraceSelectorBridge.proc is None:
            return False
        if TraceSelectorBridge.proc.poll() is not None:
            TraceSelectorBridge.proc = None
            return False
        return True


    def start_trace_selector(self):
        """ Attempts to start TraceSelector """
        if self.is_trace_selector_running():
            logger.warning(f"Failed to start TraceSelector: An instance is already running")
            if self.session.root is not None:
                if messagebox.askyesno("TraceSelector bridge", f"TraceSelector is already running. Do you want to restart it?", icon="question", default="no"):
                    self.kill_trace_selector()
                else:
                    return
            else:
                return
            
        if self.is_trace_selector_running():
            return

        args = [sys.executable, "-m", "trace_selector"]
        TraceSelectorBridge.proc = subprocess.Popen(args, stdout=subprocess.PIPE, stdin=subprocess.PIPE, text=True)
        TraceSelectorBridge.pipe_thread = threading.Thread(target=self._pipe_thread)
        TraceSelectorBridge.pipe_thread.start()
        logger.info(f"Started TraceSelector")

    def kill_trace_selector(self):
        if TraceSelectorBridge.proc is None or not self.is_trace_selector_running():
            return
        TraceSelectorBridge.proc.terminate()
        TraceSelectorBridge.proc = None

    def _pipe_thread(self):
        """ Internal function as target for the pipe thread, which is handling the communication with TraceSelector via stdout """
        if TraceSelectorBridge.proc is None or TraceSelectorBridge.proc.stdout is None:
            return
        while (line := TraceSelectorBridge.proc.stdout.readline().strip("\n")) != "":
            logger.debug(f"[TraceSelector]: {line}")
        logger.debug(f"TraceSelector terminated")
        TraceSelectorBridge.pipe_thread = None

    def install_trace_selector(self) -> None:
        """ Tries to install TraceSelector via pip and subprocess """
        subprocess.check_call([sys.executable, "-m", "pip", "install", "trace_selector", "--dry-run"])

    def ask_for_installation(self) -> bool:
        """ Asks the user to install TraceSelector. Returns True if it is already installed and False otherwise """
        def _callback():
            if self.test_installation():
                logger.info(f"Installed TraceSelector via pip into the current environment")
                messagebox.showinfo(f"Neurotorch TraceSelector bridge", "Successfully installed TraceSelector")
            else:
                logger.warning(f"Failed to install TraceSelector via pip: The module can not be found. Try to restart TraceSelector")
                messagebox.showwarning(f"Neurotorch TraceSelector bridge", "TraceSelector was installed, but it can not be found. Try to restart Neurotorch. If the error persists, try to install TraceSelector manually via pip (see documentation)")
        
        def _error_callback(e: Exception):
            logger.warning(f"Failed to install TraceSelector via pip", exc_info=True)
            messagebox.showwarning(f"Neurotorch TraceSelector bridge", "Failed to install TraceSelector. See the logs for more details and try to install it manually via pip (see documentation)")
            
        if self.test_installation():
            return True
        if messagebox.askyesno(f"Neurotorch TraceSelector bridge", f"TraceSelector must be installed first. Do you want to install it now?"):
            Task(self.install_trace_selector, name="Installing TraceSelector", run_async=True).set_indeterminate().add_callback(_callback).set_error_callback(_error_callback).start()
        return False

    def ask_for_start(self) -> bool:
        """ Asks the user to start TraceSelector and returns True if it is already running """
        def _error_callback(e: Exception):
            logger.warning(f"Failed to start TraceSelector", exc_info=True)
            messagebox.showwarning(f"Neurotorch TraceSelector bridge", "Failed to start TraceSelector. See the logs for more details")
            
        if self.session.root is None:
            return False
        if self.is_trace_selector_running():
            return True
        if not self.ask_for_installation():
            return False
        
        if messagebox.askyesno(f"Neurotorch TraceSelector bridge", f"You must first start TraceSelector. Do you want to start it now?"):
            Task(self.start_trace_selector, name="Starting TraceSelector", run_async=True).set_indeterminate().set_error_callback(_error_callback).start()
        return False

    def export_roifinder_traces(self, detection_result: DetectionResult):
        """ Exports the traces in the tab ROIFinder to TraceSelector """
        if not self.ask_for_start():
            return
        assert TraceSelectorBridge.proc is not None and TraceSelectorBridge.proc.stdin is not None
        if (imgObj := self.session.active_image_object) is None:
            if self.session.root is not None:
                self.session.root.bell()
            return
        
        name = imgObj.name if imgObj.name != "" else "Neurotorch_Export" 
        path = pathlib.Path(settings.tmp_path) / f"{name}.csv"

        if not detection_result.export_traces(path, imgObj):
            logger.warning(f"Failed to export the traces to TraceSelector")
            messagebox.showwarning(f"Neurotorch", "Failed to export the traces to TraceSelector")
            return

        TraceSelectorBridge.proc.stdin.write(f"open\t{str(path)}\n")
        TraceSelectorBridge.proc.stdin.flush()

@SessionCreateEvent.hook
def on_session_created(e: SessionCreateEvent):
    TraceSelectorBridge(e.session)