import multiprocessing
import threading
from tkinter import messagebox
from io import StringIO
import os, sys
import contextlib
import pathlib
from neurotorchmz.gui.settings import Neurotorch_Settings

ts_modelzoo, ts_settings, ts_app, ts_mainWindow = None, None, None, None

class VirtualFile(StringIO):
    def endswith(self, value, start=None, end=None):
        return "_virtualFile.csv".endswith(value, start, end)

def _StartTraceSelector():
    #global MainWindow, gui_settings, ModelZoo, QApplication
    global ts_modelzoo, ts_settings, ts_app, ts_mainWindow
    from trace_selector.gui.gui import MainWindow
    from trace_selector.utils.configuration import gui_settings
    from trace_selector.detection.model_zoo import ModelZoo
    from PyQt6.QtWidgets import QApplication
    if ts_modelzoo is None or ts_settings is None:
        modelzoo_folder = pathlib.Path(Neurotorch_Settings.DataPath / "external" / "synapse_selector_modelzoo")
        modelzoo_folder.mkdir(exist_ok=True, parents=True) 
        ts_modelzoo = ModelZoo(modelzoo_folder)
        ts_settings = gui_settings(ts_modelzoo)
    if ts_app or ts_mainWindow is None:
        ts_app = QApplication(sys.argv)
        ts_mainWindow = MainWindow(ts_settings)
    ts_mainWindow.show()
    ts_app.exec()

def OpenStream(stream: StringIO):
    global ts_mainWindow
    with contextlib.suppress(TypeError):
        ts_mainWindow.synapse_response.open_file(VirtualFile(stream), "Neurotorch Export", 
                ts_mainWindow.get_setting("meta_columns"),
                ts_mainWindow.get_setting("normalization_use_median"),
                ts_mainWindow.get_setting("normalization_sliding_window_size")
        )
    ts_mainWindow.labels = []
    ts_mainWindow.switch_to_main_layout()
    ts_mainWindow.plot()


def StartTraceSelector():
    global MainWindow, gui_settings, ModelZoo, QApplication
    try:
        from trace_selector.gui.gui import MainWindow
        from trace_selector.utils.configuration import gui_settings
        from trace_selector.detection.model_zoo import ModelZoo
        from PyQt6.QtWidgets import QApplication
    except ModuleNotFoundError as ex:
        messagebox.showerror("Neurotorch", "Trace Selector seems to be not installed. Try to run the following commands in the Anaconda prompt (replace the conda enviorenment name if necessary)\n\tconda activate pyimagej\n\tpip install trace_selector --ignore-requires-python")
    try:
        ts_thread = multiprocessing.Process(target=_StartTraceSelector)
        #ts_thread = threading.Thread(target=_StartTraceSelector)
        ts_thread.start()
    except Exception as ex:
        print("An error happended running Trace Selector:", repr(ex))
        messagebox.showerror("Neurotorch", "Trace Selector crashed due to unkown resone. Try to restart Neurotorch")