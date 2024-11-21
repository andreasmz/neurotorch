from .window import Neurotorch_GUI, Tab
from .settings import Neurotorch_Settings as Settings

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import ImageTk, Image, ImageOps
import os, sys
import subprocess

class TabWelcome(Tab):
    def __init__(self, gui: Neurotorch_GUI):
        super().__init__(gui)
        self.tab_name = "Tab Welcome"
        self._gui = gui
        self.root = gui.root
        self.Init()

    def Init(self):
        self.tab = ttk.Frame(self._gui.tabMain)
        self._gui.tabMain.add(self.tab, text="Welcome to Neurotorch")

        self.frame = tk.Frame(self.tab, background="white")
        self.frame.bind("<Configure>", self._FrameResizeEvent)
        self.frame.pack(expand=True, fill="both")

        self.coverimg = Image.open(os.path.join(Settings.MediaPath, "neurotorch_coverimage_4.webp"))
        self.canvas = tk.Canvas(self.frame, background="black")
        self.canvas.pack(expand=True, fill="both")
        self.frameBottom_L = tk.Frame(self.frame)
        self.frameBottom_L.pack(anchor="nw")
        self.frameBottom_R = tk.Frame(self.frame)
        self.frameBottom_R.pack(anchor="ne")

        self.lblWelcome = tk.Label(self.frame, text="Welcome to Neurotorch", font=("Arial", 25), background="black", foreground="white")
        self.lblWelcome.place(x=50, y=30)

        self.btnOpenDocs = tk.Button(self.frame, text="Read the Docs", font=("Arial", 15), background="#347ed9", foreground="white", command=self.BtnOpenDocs)
        self.btnOpenDocs.place(in_=self.frameBottom_L, x=30, y=-50)

        self.btnGithub = tk.Button(self.frame, text="View on GitHub", font=("Arial", 15), background="#2ad460", foreground="white", command=self.BtnGithub)
        self.btnGithub.place(in_=self.frameBottom_R, x=-30, y=-50, anchor="ne")

    def _FrameResizeEvent(self, event):
        self._FrameResize(event.height, event.width)

    def _FrameResize(self, height, width):

        ratio = 1.75
        _ratioheight = int(width/ratio)
        _ratiowidth = int(height*ratio)
        xOffset = 0
        yOffset = 0
        if _ratiowidth >= width:
            xOffset = int((width-_ratiowidth)/2)
            self.coverimg_display = self.coverimg.resize(size=(_ratiowidth, height))
        else:
            yOffset = int((height-_ratioheight)/2)
            self.coverimg_display = self.coverimg.resize(size=(width, _ratioheight))

        #if _ratioheight:
        #    xOffset = int((frameheight-height)/2)
        #    self.coverimg_display = self.coverimg.resize(size=(width, height))
        #else:
        self.image = ImageTk.PhotoImage(self.coverimg_display)
        self.canvas.delete("IMG")
        self.canvas.create_image(xOffset, yOffset, image=self.image, anchor="nw", tags="IMG")

    def BtnOpenDocs(self):
        _path = os.path.join(*[Settings.ParentPath, "neurotorch_documentation.pdf"])
        print("Opening Documentation at", _path)
        subprocess.Popen([_path],shell=True)

    def BtnGithub(self):
        url = "https://github.com/andreasmz/neurotorch/"
        if sys.platform=='win32':
            os.startfile(url)
        elif sys.platform=='darwin':
            subprocess.Popen(['open', url])
        else:
            try:
                subprocess.Popen(['xdg-open', url])
            except OSError:
                self.root.bell()