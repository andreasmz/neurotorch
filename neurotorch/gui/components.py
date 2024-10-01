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
