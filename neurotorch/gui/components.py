import tkinter as tk
from tkinter import ttk
from io import StringIO
import time
from enum import Enum
import psutil

class Statusbar:
    timerLowSpeed = 1000 # ms
    timerHighSpeed = 100 # ms
    lowerTimerSpeed = 2000 #ms
    def __init__(self, root, frame):
        self._statusTxt = ""
        self._progTxt = ""
        self._timerSpeed = Statusbar.timerLowSpeed #ms
        self._jobs : list[Job] = []

        self.root = root
        self.frame = frame

        self.statusFrame = tk.Frame(self.frame)
        self.statusFrame.pack(side=tk.BOTTOM, fill="x", expand=False)
        self.varProgMain = tk.DoubleVar()
        self.progMain = ttk.Progressbar(self.statusFrame,orient="horizontal", length=200, variable=self.varProgMain, maximum=100)
        self.progMain.pack(side=tk.LEFT)
        self.lblProg = tk.Label(self.statusFrame, text="", relief=tk.SUNKEN,borderwidth=1)
        self.lblProg.pack(side=tk.LEFT, padx=(10,10))
        self.lblStatus = tk.Label(self.statusFrame, text="", borderwidth=1, relief=tk.SUNKEN)
        self.lblStatus.pack(side=tk.LEFT, padx=(10, 10))
        self.lblSystemUsage = tk.Label(self.statusFrame, text="")
        self.lblSystemUsage.pack(anchor=tk.E, padx=(10, 10))

        self.root.after(0, self._TimerTick)
        self.root.after(1000, self._LowerTimerTick)

    def AddJob(self, job):
        self._jobs.append(job)

    @property
    def StatusText(self):
        return self._statusTxt
    
    @StatusText.setter
    def StatusText(self, val):
        if val != self._statusTxt:
            self._statusTxt = val
            self.lblStatus["text"] = self._statusTxt

    @property
    def ProgressText(self):
        return self._progTxt
    
    @ProgressText.setter
    def progressText(self, val):
        if val != self._progTxt:
            self._progTxt = val
            self.lblProg["text"] = self._progTxt

    def _TimerTick(self):
        if len(self._jobs) == 0:
            self._timerSpeed = Statusbar.timerLowSpeed
        else:
            self._timerSpeed = Statusbar.timerHighSpeed
        
        for j in self._jobs:
            if ((j.State == JobState.STOPPED) | (j.State == JobState.TIMEOUT)) and (j.Time <= -3 or j.Runtime <= 3):
                self._jobs.remove(j)
        self._jobs.sort(key=lambda j: j.Runtime)
        
        if len(self._jobs) == 0:
            self.progressText = ""
            if self.varProgMain.get() != 0:
                self.varProgMain.set(0)
        elif len(self._jobs) > 0:
            j = self._jobs[-1]
            self.progressText = f"{j.Text} ({round(j.Time, 0)} s)" if len(self._jobs) == 1 else f"{j.Text} ({round(j.Time, 0)} s) and {len(self._jobs)-1} more job running"
            if j.steps == 0:
                if str(self.progMain["mode"]) != "indeterminate":
                    self.progMain.configure(mode="indeterminate")
                self.progMain.step(100)
            else:
                if str(self.progMain["mode"]) != "determinate":
                    self.progMain.configure(mode="determinate")
                if self.varProgMain.get() != j.Percentage:
                    self.varProgMain.set(j.Percentage)
        self.root.after(self._timerSpeed, self._TimerTick)

    def _LowerTimerTick(self):
        process = psutil.Process()
        _size = round(process.memory_info().rss/(1024**2),2)
        self.lblSystemUsage["text"] = f"RAM: {_size} MB"
        self.root.after(Statusbar.lowerTimerSpeed, self._LowerTimerTick)
    
class JobState(Enum):
    RUNNING = 1
    STOPPED = 2
    TIMEOUT = 3
class Job:

    def __init__(self, steps, timeout=60*5, showSteps=True):
        """
            steps: Number of steps or 0 for continuous jobs
        """
        if steps < 0:
            raise ValueError("Steps must be a positive integer or zero")
        self.startTime = time.time()
        self.steps = steps
        self.timeout = timeout
        self.showSteps = showSteps if steps != 0 else False
        self._progress = 0
        self._text = ""
        self._state : JobState = JobState.RUNNING
        self._finishedTime = None
    
    @property
    def Text(self):
        if self.State == JobState.STOPPED:
            return f"Finished: {self._text}"
        if self.State == JobState.TIMEOUT:
            return f"Timeout: {self._text}"
        if self.showSteps:
            if self.Progress == self.steps:
                return f"Completing: {self._text}"
            return f"{self.Progress+1}/{self.steps} {self._text}"
        return self._text

    @property
    def Progress(self):
        return self._progress

    def SetProgress(self, val, text=False, noError=False):
        if val > self.steps or val < 0:
            if noError:
                return False
            raise ValueError("The progress value must be smaller than step size and greater or equal to zero")
        self._progress = val
        if text != False:
            self._text = text

    def SetStopped(self, text=False):
        self._finishedTime = time.time()
        self._state = JobState.STOPPED
        self._progress = self.steps
        if text != False:
            self._text = text
    
    @property
    def State(self):
        if self._state == JobState.RUNNING:
            if (time.time() - self.startTime) >= self.timeout:
                self._state = JobState.TIMEOUT
                self._finishedTime = time.time()
        return self._state

    @property
    def Percentage(self):
        if (self.State == JobState.STOPPED) | (self.State == JobState.TIMEOUT):
            return 0
        if self.steps == 0:
            return 100
        return int(95*self._progress/self.steps + 5)
    
    @property
    def Runtime(self):
        """
            The runtime of the job
        """
        match (self.State):
            case JobState.RUNNING:
                return time.time() - self.startTime
            case JobState.STOPPED | JobState.TIMEOUT:
                if self._finishedTime is None:
                    raise RuntimeError("The finish time of the job wasn't set")
                return self._finishedTime - self.startTime
            case _:
                raise RuntimeError(f"The job was in an unkown JobState {self._state}")
    
    @property
    def Time(self):
        """
            The runtime of the job (postive) or the time since stopped (negative)
        """
        match (self.State): #using the property will update to possible timeout
            case JobState.RUNNING:
                return time.time() - self.startTime
            case JobState.STOPPED | JobState.TIMEOUT:
                if self._finishedTime is None:
                    raise RuntimeError("The finish time of the job wasn't set")
                return self._finishedTime - time.time()
            case _:
                raise RuntimeError(f"The job was in an unkown JobState {self._state}")


class EntryPopup(ttk.Entry):
    def __init__(self, tv, callback, rowid, column, val, **kw):
        ttk.Style().configure('pad.TEntry', padding='1 1 1 1')
        super().__init__(tv, style='pad.TEntry', **kw)
        self.tv = tv
        self.callback = callback
        self.rowid = rowid
        self.column = column
        self.oldval = val

        self.insert(0, val) 

        self.focus_force()
        self.select_all()
        self.bind("<Return>", self.on_return)
        #self.bind("<Control-a>", self.select_all)
        self.bind("<Escape>", lambda *ignore: self.destroy())


    def on_return(self, event):
        val = self.get()
        if self.oldval != val:
            try:
                self.callback({"RowID": self.rowid, "Column": self.column, "OldValue" : self.oldval, "NewVal": val})
            except:
                pass
        self.destroy()


    def select_all(self, *ignore):
        self.selection_range(0, 'end')
        return 'break'


class VirtualFile(StringIO):
    def endswith(self, value, start=None, end=None):
        return "_virtualFile.csv".endswith(value, start, end)


class IntStringVar:
    def __init__(self, root, IntVar: tk.IntVar):
        self.IntVar = IntVar
        self.StringVar = tk.StringVar(root, value=self.IntVar.get())
        self.IntVar.trace_add("write", self._IntVarUpdate)
        self.StringVar.trace_add("write", self._StringVarUpdate)
        self.callback = None
        self.min = None
        self.max = None

    def SetCallback(self, callback):
        self.callback = callback

    def SetStringVarBounds(self, min: int, max: int):
        self.min = min
        self.max = max
        return self

    def _IntVarUpdate(self, val1, val2, val3):
        if (self.StringVar.get() != str(self.IntVar.get())):
            self.StringVar.set(str(int(self.IntVar.get())))
            if self.callback is not None:
                self.callback()
    
    def _StringVarUpdate(self, val1, val2, val3):
        strval = self.StringVar.get()
        intval = str(self.IntVar.get())
        if (strval != intval):
            if not strval.lstrip("-").isdigit():
                return
            if self.min is not None and int(strval) < self.min:
                return
            if self.max is not None and int(strval) > self.max:
                return
            self.IntVar.set(strval)
            if self.callback is not None:
                self.callback()