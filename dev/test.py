import sys, os
import tkinter as tk
import psutil
import threading
import pickle
import matplotlib
from tkinter import ttk, messagebox, filedialog
from enum import Enum
from typing import Literal
import logging
import collections
from typing import Callable, Literal
import numpy as np
from scipy.ndimage import convolve, gaussian_filter
from io import StringIO
import time
import pims
"""
import threading
import pickle
import matplotlib
from tkinter import ttk, messagebox, filedialog
from enum import Enum
from typing import Literal
import logging
import tkinter as tk
import psutil
import collections
from typing import Callable, Literal
import numpy as np
from scipy.ndimage import convolve, gaussian_filter
import threading
from enum import Enum
import time
import pims
import os, sys
import tkinter as tk
from tkinter import ttk
from io import StringIO
import time
from enum import Enum
"""

process = psutil.Process()
_size = round(process.memory_info().rss/(1024**2),2)

root = tk.Tk()
tk.Label(root, text=_size).pack()
root.mainloop()