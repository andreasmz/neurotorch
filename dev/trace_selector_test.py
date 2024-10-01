import multiprocessing
from tkinter import messagebox

from trace_selector.gui.gui import MainWindow
from trace_selector.utils.configuration import gui_settings
from trace_selector.detection.model_zoo import ModelZoo
from PyQt6.QtWidgets import QApplication
import os, sys

def Test():
    modelzoo_folder = os.path.join(*["d:\\Eigene Datein\\Programmieren\\Git\\abrilka\\neurotorch\\neurotorch", "external", "synapse_selector_modelzoo"])
    modelzoo = ModelZoo(modelzoo_folder)
    settings = gui_settings(modelzoo)
    app = QApplication(sys.argv)
    main = MainWindow(settings)
    main.show()
    app.exec()

if __name__ == '__main__':
    proc = multiprocessing.Process(target=Test, args=()) 
    proc.start()
    print("Running")