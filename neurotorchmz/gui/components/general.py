import tkinter as tk
from tkinter import ttk
from typing import Literal
from tktooltip import ToolTip
import psutil

from ...core.settings import logger, log_exception_debug
from ...core.task_system import Task, TaskState

class Statusbar:
    """
        Implements the Status Bar into the GUI displaying the currently running jobs, system usage and the custom status text
    """
    timerLowSpeed = 1000 # ms
    timerHighSpeed = 100 # ms
    lowerTimerSpeed = 1000 #ms
    def __init__(self, root, frame):
        self._statusTxt = ""
        self._progTxt = ""
        self._finishedTxt = ""
        self._timerSpeed = Statusbar.timerLowSpeed #ms

        self.root = root
        self.frame = frame

        # self.statusFrame = tk.Frame(self.frame)
        # self.statusFrame.pack(side=tk.BOTTOM, fill="x", expand=False)
        # self.varProgMain = tk.DoubleVar()
        # self.progMain = ttk.Progressbar(self.statusFrame,orient="horizontal", length=200, variable=self.varProgMain, maximum=100)
        # self.progMain.pack(side=tk.LEFT)
        # self.lblProg = tk.Label(self.statusFrame, text="", relief=tk.SUNKEN,borderwidth=1)
        # self.lblProg.pack(side=tk.LEFT, padx=(10,10))
        # self.lblStatus = tk.Label(self.statusFrame, text="", borderwidth=1, relief=tk.SUNKEN)
        # self.lblStatus.pack(side=tk.LEFT, padx=(10, 10))
        # self.lblSystemUsage = tk.Label(self.statusFrame, text="")
        # self.lblSystemUsage2 = tk.Label(self.statusFrame, text="")
        # self.lblSystemUsage3 = tk.Label(self.statusFrame, text="")
        # self.lblSystemUsage3.pack(side=tk.RIGHT, padx=(0, 10))
        # self.lblSystemUsage2.pack(side=tk.RIGHT, padx=(0, 0))
        # self.lblSystemUsage.pack(side=tk.RIGHT, padx=(10, 0))

        self.statusbarFrame = tk.Frame(self.frame)
        self.statusbarFrame.pack(side=tk.BOTTOM, fill="x", expand=False)
        self.varProgMain = tk.DoubleVar()
        self.finishedTaskFrame = tk.Frame(self.statusbarFrame)
        self.finishedTaskFrame.grid(row=0, column=0, sticky="w")
        self.runningTaskFrame = tk.Frame(self.statusbarFrame)
        self.runningTaskFrame.grid(row=0, column=1, sticky="w")
        self.statusFrame = tk.Frame(self.statusbarFrame)
        self.statusFrame.grid(row=0, column=2)
        self.systemInfoFrame = tk.Frame(self.statusbarFrame)
        self.systemInfoFrame.grid(row=0, column=3, columnspan=2, sticky="e")
        self.statusbarFrame.grid_columnconfigure([2], weight=1)
        self.statusbarFrame.grid_columnconfigure([0], minsize=150)

        self.lblTasksFinished = tk.Label(self.finishedTaskFrame, text="")
        self.lblTasksFinished.pack()
        self.progMain = ttk.Progressbar(self.runningTaskFrame, orient="horizontal", length=100, variable=self.varProgMain, maximum=100)
        self.progMain.pack(side=tk.LEFT)
        self.lblProg = tk.Label(self.runningTaskFrame, text="")
        self.lblProg.pack(side=tk.LEFT, padx=(7,0))
        self.lblStatus = tk.Label(self.statusFrame, text="")
        self.lblStatus.pack(padx=(5, 5))
        self.lblSystemUsage = tk.Label(self.systemInfoFrame, text="")
        self.lblSystemUsage2 = tk.Label(self.systemInfoFrame, text="")
        self.lblSystemUsage3 = tk.Label(self.systemInfoFrame, text="")
        self.lblSystemUsage3.pack(side=tk.RIGHT, padx=(0, 5))
        self.lblSystemUsage2.pack(side=tk.RIGHT, padx=(0, 0))
        self.lblSystemUsage.pack(side=tk.RIGHT, padx=(5, 0))


        self.root.after(0, self._TimerTick)
        self.root.after(1000, self._LowerTimerTick)

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
    def ProgressText(self, val):
        if val != self._progTxt:
            self._progTxt = val
            self.lblProg["text"] = self._progTxt

    @property
    def TaskFinishedText(self):
        return self._finishedTxt
    
    @TaskFinishedText.setter
    def TaskFinishedText(self, val):
        if val != self._finishedTxt:
            self._finishedTxt = val
            self.lblTasksFinished["text"] = self._finishedTxt

    def _TimerTick(self):
        self._timerSpeed = Statusbar.timerHighSpeed
        def _Tick():
            active_tasks = [t for t in Task.get_tasks() if t.state == TaskState.RUNNING and t.time_since_start >= 0.5]
            finished_task = [t for t in Task.get_tasks() if t.tend is not None and t.time_since_end <= 5 and t.runtime >= 0.5]

            sorted(active_tasks, key=lambda t: t.time_since_start, reverse=True) # Oldest tasks first
            sorted(finished_task, key=lambda t: (t.state.value, t.time_since_end)) # Newest finish first

            if len(active_tasks) == 0:
                self._timerSpeed = Statusbar.timerLowSpeed

            if len(finished_task) == 0:
                self.TaskFinishedText = ""
            else:
                t: Task = finished_task[0]
                if t.error is not None and self.lblTasksFinished["fg"] != "red":
                    self.lblTasksFinished.config(fg="red")
                elif self.lblTasksFinished["fg"] != "SystemButtonText":
                    self.lblTasksFinished.config(fg="SystemButtonText")
                self.TaskFinishedText = str(t)

            if len(active_tasks) == 0:
                self.ProgressText = ""
                if str(self.progMain["mode"]) != "determinate":
                    self.progMain.configure(mode="determinate")
                if self.varProgMain.get() != 0:
                    self.varProgMain.set(0)
            else:
                t: Task = active_tasks[0]
                # Those both if querys create a flashing effect
                if t.error is not None and self.lblProg["fg"] != "red":
                    self.lblProg.config(fg="red")
                elif self.lblProg["fg"] != "SystemButtonText":
                    self.lblProg.config(fg="SystemButtonText")
                self.ProgressText = str(t) + (f" and {len(active_tasks)-1} more task{'s' if len(active_tasks) >= 3 else ''}" if len(active_tasks) >= 2 else "")
                if t.is_determinate():
                    if str(self.progMain["mode"]) != "determinate":
                        self.progMain.configure(mode="determinate")
                    if self.varProgMain.get() != t.progress:
                        self.varProgMain.set(100*t.progress)
                else:
                    if str(self.progMain["mode"]) != "indeterminate":
                        self.progMain.configure(mode="indeterminate")
                    self.progMain.step(10)
        try:
            _Tick()
        except Exception as ex:
            logger.debug(f"An error happened processing the task loop: {str(ex)}")
        finally:
            self.root.after(self._timerSpeed, self._TimerTick)

    def _LowerTimerTick(self):
        process = psutil.Process()
        _size = round(process.memory_info().rss/(1024**2),2)
        _availableRAM = round(psutil.virtual_memory().available/(1024**3), 2)
        _totalRAM = round(psutil.virtual_memory().total/(1024**3), 2)
        self.lblSystemUsage["text"] = f"CPU: {psutil.cpu_percent(interval=None)}%, RAM: {_size} MB ("
        self.lblSystemUsage2["text"] = f"{_availableRAM} GB free"
        if _availableRAM < 3:
            self.lblSystemUsage2.config(fg="red")
        else:
            self.lblSystemUsage2.config(fg="SystemButtonText")
        self.lblSystemUsage3["text"] = f" / {_totalRAM} GB)"
        self.root.after(Statusbar.lowerTimerSpeed, self._LowerTimerTick)


class EntryPopup(ttk.Entry):
    """
        Implements editabled ttk Treeview entries
    """
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
        self.bind("<Escape>", lambda *val1: self.destroy())


    def on_return(self, event):
        val = self.get()
        if self.oldval != val:
            try:
                self.callback({"RowID": self.rowid, "Column": self.column, "OldValue" : self.oldval, "NewVal": val})
            except:
                pass
        self.destroy()


    def select_all(self, *val1):
        self.selection_range(0, 'end')
        return 'break'

class GridSetting:
    """
        Implements a helper class to quickly add a label, a spinner and a spinbox for numbers in a grid layout
    """
    
    def __init__(self, 
                 parent, 
                 row: int,
                 text:str, 
                 default:int = 0, 
                 min_:int = 0, 
                 max_:int = 1000, 
                 scaleMin:int = 0, 
                 scaleMax:int = 100,
                 tooltip: str = "",
                 unit:str = "",
                 type_: Literal["Int", "Checkbox"] = "Int"):
        self._visible = False
        self.parent = parent
        self.row = row
        self.unit = unit
        self.var = IntStringVar(default)
        self.type: Literal["Int", "Checkbox"] = type_

        self.label = ttk.Label(self.parent, text=text)
        if tooltip is not None and tooltip != "":
            self.toolTip = ToolTip(self.label, msg=tooltip, follow=True, delay=0.1)
        match self.type:
            case "Int":
                self.scale = ttk.Scale(self.parent, from_=scaleMin, to=scaleMax, variable=self.var.IntVar)
                self.spinbox = tk.Spinbox(self.parent, from_=min_, to=max_, textvariable=self.var.StringVar, width=6)
                self.lblUnit = tk.Label(self.parent, text=unit)
            case "Checkbox":
                self.check = ttk.Checkbutton(self.parent, variable=self.var.IntVar)
            case _:
                raise ValueError(f"Invalid type {self.type}")

        self.SetVisibility(True)

    def Get(self) -> int:
        return self.var.IntVar.get()
    
    def Set(self, val:int):
        self.var.IntVar.set(val)
    
    def SetRange(self, 
                 min_:int = None, 
                 max_:int = None, 
                 scaleMin:int = None, 
                 scaleMax:int = None,
                 syncScale:bool = False):
        min_ = self.spinbox.cget("from") if min_ is None else min_
        max_ = self.spinbox.cget("to") if max_ is None else max_
        self.spinbox.configure(from_=min_, to=max_)

        if syncScale:
            self.scale.configure(from_=min_, to=max_)
        elif scaleMin is not None or scaleMax is not None:
            scaleMin = self.spinbox.cget("from") if scaleMin is None else scaleMin
            scaleMax = self.spinbox.cget("to") if scaleMax is None else scaleMax
            self.scale.configure(from_=min_, to=max_)
        
        if min_ > max_:
            self.Set(0)
        
        if self.Get() < min_:
            self.Set(min_)
        elif self.Get() > max_:
            self.Set(max_)
        
    
    def SetVisibility(self, visibility:bool):
        if visibility == self._visible:
            return
        if visibility:
            self.label.grid(row=self.row, column=0, sticky="ne")
            match self.type:
                case "Int":
                    self.scale.grid(row=self.row, column=1, sticky="news")
                    self.spinbox.grid(row=self.row, column=2, sticky="news")
                    if self.unit is not None and self.unit != "":
                        self.lblUnit.grid(row=self.row, column=3, sticky="nw")
                case "Checkbox":
                    self.check.grid(row=self.row, column=1, sticky="nw")
                case _:
                    raise ValueError(f"Invalid type {self.type}")
        else:
            self.label.grid_forget()
            match self.type:
                case "Int":
                    self.scale.grid_forget()
                    self.spinbox.grid_forget()
                    if self.unit is not None and self.unit != "":
                        self.lblUnit.grid_forget()
                case "Checkbox":
                    self.check.grid_forget()
                case _:
                    raise ValueError(f"Invalid type {self.type}")
        self._visible = visibility


class IntStringVar:
    def __init__(self, default):
        self.IntVar = tk.IntVar(value=default)
        self.StringVar = tk.StringVar(value=default)
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


class ScrolledFrame(ttk.Frame):
    """
        Implements a scrollable frame
    """

    def __init__(self, parent, *args, **kw):
        ttk.Frame.__init__(self, parent, *args, **kw)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical")
        self.canvas = tk.Canvas(self, yscrollcommand=self.scrollbar.set)
        self.frame = ttk.Frame(self.canvas)
        self.scrollbar.config(command=self.canvas.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill="y", expand=False)
        self.canvas.create_window(0, 0, window=self.frame, anchor="nw")
        self.canvas.pack(side=tk.LEFT, fill="y")
        
        def _configure_frame(e):
            # The scrollview is initially not set. Therefore, the user can scroll without limits to the left or right. Also, the canvas does not fit to content width """
            size = (self.frame.winfo_reqwidth(), self.frame.winfo_reqheight()) # Size of frame content
            if self.canvas["scrollregion"] != ("0 0 %s %s" % size): # Change scroll region if necessary
                self.canvas.config(scrollregion="0 0 %s %s" % size)
            if self.canvas.winfo_width() != self.frame.winfo_reqwidth(): # Change canvas width if necessary (height is autoset by fill=y)
                self.canvas.config(width=self.frame.winfo_reqwidth())
        self.frame.bind("<Configure>", _configure_frame)