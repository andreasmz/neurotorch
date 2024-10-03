import tkinter as tk
from tkinter import ttk
from io import StringIO

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