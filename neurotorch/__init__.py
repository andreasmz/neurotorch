import sys, os
if __name__ == "__main__":
    neurotorch_path = os.path.join(os.path.join(__file__, os.pardir), os.pardir)
    neurotorch_path = os.path.abspath(neurotorch_path)
    sys.path.insert(1, neurotorch_path)


import neurotorch.gui.window as window
import neurotorch.gui.settings as settings
import threading

def Start():
    settings.UserSettings.ReadSettings()
    window.GUI.GUI()

def Start_Background():
    task = threading.Thread(target=Start)
    task.start()

def API_GUI():
    return window.GUI

def API_IJ():
    return window.GUI.ij

def API_IMG():
    return window.GUI.IMG

def API_ROI_IMG():
    return window.GUI.ROI_IMG

class API:
    def Peaks():
        if window.GUI.signal is None or window.GUI.signal.peaks is None:
            return []
        return window.GUI.signal.peaks
    
    def DetectedSynapses():
        if window.GUI.tab3.detection is None or window.GUI.tab3.detection.synapses is None:
            return {}
        return window.GUI.tab3.detection.synapses
    
    def Img():
        return window.GUI.IMG.img
    
    def ImgDiff():
        return window.GUI.IMG.imgDiff
    
if __name__ == "__main__":
    Start()

