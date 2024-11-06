from .window import Neurotorch_GUI, Tab, TabUpdateEvent
from ..utils.synapse_detection_integration import *

class TabAnalysis(Tab):
    def __init__(self, gui: Neurotorch_GUI):
        super().__init__(gui)
        self.tab_name = "Tab Synapse Analysis"
        self.gui = gui
        self.root = gui.root
        self.detectionResult = DetectionResult()

    def Init(self):
        self.tab = ttk.Frame(self.gui.tabMain)
        self.gui.tabMain.add(self.tab, text="Synapse Analysis (Multiframe ROI Finder)")

        self.frame = tk.Frame(self.tab)
        self.frame.pack(side=tk.LEFT, fill="y", expand=True, anchor=tk.W)
        self.frameOptions = ttk.LabelFrame(self.frame, text="Options")
        self.frameOptions.grid(row=0, column=0, sticky="news")
        self.lblSignalReady = tk.Label(self.frameOptions, text="")
        self.lblSignalReady.grid(row=2, column=0, columnspan=3)
        self.varMultiAlgos = tk.StringVar(value="Single")
        self.varMultiAlgos.trace_add("write", lambda _1,_2,_3: self.RadioMultiAlgos_Changed())
        self.radioMultiAlgos_Single = ttk.Radiobutton(self.frameOptions, value="Single", text="Single algorithm and parameters", variable=self.varMultiAlgos)
        self.radioMultiAlgos_MultiParams = ttk.Radiobutton(self.frameOptions, value="MultiParams", text="Single algorithm, parameters per frame", variable=self.varMultiAlgos)
        self.radioMultiAlgos_Multi = ttk.Radiobutton(self.frameOptions, value="Multi", text="Different algorithm and paramaters per frame", state="disabled", variable=self.varMultiAlgos)
        self.radioMultiAlgos_Single.grid(row=3, column=0, columnspan=3, sticky="nw")
        self.radioMultiAlgos_MultiParams.grid(row=4, column=0, columnspan=3, sticky="nw")
        self.radioMultiAlgos_Multi.grid(row=5, column=0, columnspan=3, sticky="nw")
        self.varFrame = tk.StringVar()
        self.comboFrame = ttk.Combobox(self.frameOptions, textvariable=self.varFrame, state="readonly")
        self.comboFrame.grid(row=6, column=1)
        tk.Label(self.frameOptions, text="Frame").grid(row=6, column=0, sticky="news")

        self.InvalidateSignal()

    def Update(self, events: list[TabUpdateEvent|str]):
        if TabUpdateEvent.NEWIMAGE in events:
            pass
        if TabUpdateEvent.NEWSIGNAL in events:
            self.InvalidateSignal()
    
    def InvalidateSignal(self):
        self.comboFrame['values'] = []
        self.varFrame.set("")
        signalPeaks = self.gui.signal.peaks
        if signalPeaks is None or len(signalPeaks) == 0:
            self.lblSignalReady["text"] = "Signal not ready"
            self.lblSignalReady["fg"] = "red"
            return
        self.lblSignalReady["text"] = "Signal available"
        self.lblSignalReady["fg"] = "green"
        self.comboFrame['values'] = list(signalPeaks.astype(str))
        

    def RadioMultiAlgos_Changed(self):
        match self.varMultiAlgos.get():
            case "Single":
                self.comboFrame["state"] = "disabled"
            case "MultiParams":
                self.comboFrame["state"] = "readonly"
            case "Multi":
                self.comboFrame["state"] = "readonly"
            case _:
                raise RuntimeError("Unexpected value for varMultiAlgos")
