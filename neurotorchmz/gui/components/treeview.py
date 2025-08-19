""" This module defines the SynapseTreeviee, a class to display detection results and provide an interface to modify them"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Literal
import re
import pandas as pd

from ..window import *
from ...utils.synapse_detection import *

class SynapseTreeview(ttk.Treeview):
    """
        A treeview component to display Synapses. Provides GUI components to edit them.
    """

    editableFiels = [
        "CircularSynapseROI.Frame",
        "CircularSynapseROI.Center",
        "CircularSynapseROI.Radius",
    ]

    def __init__(self, 
                 master: tk.Widget, 
                 session: Session, 
                 detection_result: DetectionResult,
                 select_callback: Callable[[ISynapse|None, ISynapseROI|None], None]|None = None, 
                 allow_singleframe: bool = False,
                 allow_multiframe: bool = False,
                 **kwargs):
        """
            :param tk.Widget master: The reference to the master widget is used to create the tree view as sub widget inside of master
            :param Session session: A reference to the current session
            :param Detection_Result detection_result: A result to the DetectionResult object the treeview will be synced
            :param Callable[[ISynapse|None, ISynapseROI|None], None] select_callback: If not None, the widget will call this function when the user selects an item in the tree view
            :param bool allow_singleframe: If set to True, SingleFrame synapses are allowed
            :param bool allow_singleframe: If set to True, MultiFrame synapses are allowed
        """
        self.master = master
        self.session = session
        self.option_allowAddingSingleframeSynapses = allow_singleframe
        self.option_allowAddingMultiframeSynapses = allow_multiframe
        self.frame = ttk.Frame(self.master)
        self.frametv = ttk.Frame(self.frame)
        self.frametv.pack(fill="both")

        super().__init__(master=self.frametv, columns=("Val"), **kwargs)
        self.heading("#0", text="Property")
        self.heading("#1", text="Value")
        self.column("#0", minwidth=0, width=100, stretch=False)
        self.column("#1", minwidth=0, width=150, stretch=False)
        self.tag_configure("staged_synapse", foreground="#9416a6")

        self.scrollbar = ttk.Scrollbar(self.frametv, orient="vertical", command=self.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill="y")
        super().pack(fill="both", padx=10)
        self.scrollbarx = ttk.Scrollbar(self.frametv, orient="horizontal", command=self.xview)
        self.scrollbarx.pack(side=tk.BOTTOM, fill="x")

        self.frameButtons = tk.Frame(self.frame)
        self.frameButtons.pack()
        _btn_padx = 5
        if self.option_allowAddingSingleframeSynapses:
            self.btnAdd = tk.Button(self.frameButtons, text="+ Add", command = lambda: self._on_context_menu_add("Singleframe_CircularROI"))
            self.btnAdd.pack(side=tk.LEFT, padx=_btn_padx)
        if self.option_allowAddingMultiframeSynapses:
            self.btnAdd_Multiframe = tk.Button(self.frameButtons, text="+ Add Synapse", command= lambda: self._on_context_menu_add("MultiframeSynapse"))
            self.btnAdd_Multiframe.pack(side=tk.LEFT, padx=_btn_padx)

        self.btnRemove = tk.Button(self.frameButtons, text="🗑 Remove", state="disabled", command=self._btn_remove_cick)
        self.btnRemove.pack(side=tk.LEFT, padx=_btn_padx)
        self.btnStage = tk.Button(self.frameButtons, text="🔒 Stage", state="disabled", command=self._btn_stage_click)
        self.btnStage.pack(side=tk.LEFT, padx=_btn_padx)

        tk.Label(self.frame, text="Use Right-Click to edit").pack(fill="x")
        tk.Label(self.frame, text="Double click on values to modify them").pack(fill="x")

        self.configure(yscrollcommand = self.scrollbar.set)
        self.configure(xscrollcommand = self.scrollbarx.set)
        self.bind("<<TreeviewSelect>>", self._on_select)
        self.bind("<Double-1>", self._on_double_click)
        self.bind("<Button-3>", self._on_right_click)

        self.modified = False
        self._select_callback = select_callback
        self.detection_result = detection_result # Returns dict of UUID -> ISynapse
        self.detection_result.register_callback(lambda _1, _2, _3: self.sync_synapses())

        self._entryPopup = None
        self._sync_task = Task(function=self._sync_synapses_task, name="syncing synapse treeview", run_async=True, keep_alive=True)
        self.sync_synapses()

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)

    def sync_synapses(self):
        """ Display the given list of ISynapse in the treeview. Updates existing values to keep the scrolling position. """
        self._sync_task.start()

    def _sync_synapses_task(self, task:Task):
        task.set_indeterminate()
        if self._entryPopup is not None:
            self._entryPopup.destroy()   
            self._entryPopup = None
        synapses = dict(sorted(self.detection_result.as_dict().items(), key=lambda v: (not v[1].staged, v[1].location_y if v[1].location_y is not None else 0, v[1].location_x if v[1].location_x is not None else 0)))

        for _uuid in ((uuidsOld := set(self.get_children(''))) - (uuidsNew := set(synapses.keys()))):
            self.delete(_uuid) # Delete removed entries
        for _uuid in (uuidsNew - uuidsOld):
            isSingleframe = isinstance(synapses[_uuid], SingleframeSynapse)
            self.insert('', 'end', iid=_uuid, text='', open=(not isSingleframe)) # Create template node for newly added entries
        synapse_index = 1 # Index to label synapses without a name
        for i, (_uuid, s) in enumerate(synapses.items()):
            if self.index(_uuid) != i: # Keep the order the same as in the list
                self.move(_uuid, '', i)
            name = s.name
            if name is None:
                name = f"Synapse {synapse_index}"
                synapse_index += 1
            isSingleframe = isinstance(s, SingleframeSynapse)
            self.item(_uuid, text=name)
            self.item(_uuid, values=[s.get_roi_description()])
            self.item(_uuid, tags=(("staged_synapse",) if s.staged else ()))

            # Now the same procedure for the ISynapseROIs
            rois = dict(sorted(s.rois.as_dict().items(), key=lambda item: item[1].frame if item[1].frame is not None else -1))
            for _ruuid in ((uuidsOld := set(self.get_children(_uuid))) - (uuidsNew := set(rois.keys()))):
                self.delete(_ruuid)
            for _ruuid in (uuidsNew - uuidsOld):
                self.insert(_uuid, 'end', iid=_ruuid, text='', open=isSingleframe)

            for si, (_ruuid, r) in enumerate(rois.items()):
                if self.index(_ruuid) != si:
                    self.move(_ruuid, _uuid, si)
                self._update_ISynapseROI(r)
        if len(self.get_children('')) == 0:
            self.btnRemove.config(state="disabled")
            self.btnStage.config(state="disabled")

    def get_synapse_by_row_id(self, rowid: str) -> tuple[ISynapse|None, ISynapseROI|None]:
        """ 
            Given a rowid, return the corrosponding ISynapse and ISynapseROI as tuple (ISynapse, ISynapseROI).
            If provided with a ISynapse row, return (ISynapse, None). If provided with a root node, return (None, None).
        """
        if rowid is None: return (None, None)
        parents = [rowid]
        while parents[-1] != '':
            parents.append(self.parent(parents[-1]))
        if len(parents) < 2:
            return (None, None)
        synapse_uuid = parents[-2]
        if synapse_uuid not in self.detection_result:
            logger.warning(f"SynapseTreeview: Can't find synapse {synapse_uuid} in the callback")
            return (None, None)
        synapse = self.detection_result[synapse_uuid]
        if len(parents) < 3:
            return (synapse, None)
        roi_uuid = parents[-3]
        if roi_uuid not in synapse.rois:
            logger.warning(f"SynapseTreeview: Can't find ROI {roi_uuid} in synapse {synapse_uuid}")
            return (synapse, None)
        roi = synapse.rois[roi_uuid]
        return (synapse, roi)
    
    def get_selected_synapse(self) -> tuple[ISynapse|None, ISynapseROI|None]:
        """
            Identifies the currently selected rowid and returns the result of get_synapse_by_row_id
        """
        selection = self.selection()
        if len(selection) != 1:
            return (None, None)
        rowid = selection[0]
        synapse, roi = self.get_synapse_by_row_id(rowid)
        return synapse, roi
    
    def select(self, synapse: ISynapse|None = None, roi:ISynapseROI|None = None):
        """
            Selects an entry based on synapse or roi ID and scrolls to it. As a convenience feature, if both synapse and ROI are given,
            it will select the synapse if the node is collapsed and the ROI in the other case.
        """
        if synapse is None and roi is None:
            raise ValueError("Selecting a row in a synapse entry requires at least a synapse or ROI uuid")
        if synapse is not None and not isinstance(synapse, ISynapse):
            raise ValueError(f"The provided synapse is of type {type(synapse)}")
        if roi is not None and not isinstance(roi, ISynapseROI):
            raise ValueError(f"The provided ROI is of type {type(roi)}")
        if roi is not None and (synapse is None or self.item(synapse.uuid, "open") or len(synapse.rois) >= 2):
            self.selection_set(roi.uuid)
            self.see(roi.uuid)
        elif synapse is not None:
            self.selection_set(synapse.uuid)
            self.see(synapse.uuid)
        
    def _on_select(self, event):
        """ Triggered on selecting a row in the Treeview. Determines the corrosponding ISynapse and passes it back to the callback. """
        selection = self.selection()
        if len(selection) != 1:
            if self._select_callback is not None:
                self._select_callback(None, None)
            return
        rowid = selection[0]
        synapse, roi = self.get_synapse_by_row_id(rowid)
        if synapse is not None or roi is not None:
            self.btnRemove.config(state="active")
            self.btnStage.config(state="active")
        else:
            self.btnRemove.config(state="disabled")
            self.btnStage.config(state="disabled")
        if self._select_callback is not None:
            self._select_callback(synapse, roi)

    def _on_double_click(self, event):
        """ Triggered on double clicking and creates a editable field if the clicked field is editable """
        try: 
            if self._entryPopup is not None:
                self._entryPopup.destroy()
        except AttributeError:
            pass    
        rowid = self.identify_row(event.y)
        column = self.identify_column(event.x)
        if rowid is None: return
        rowid_fiels = rowid.split("_")
        synapse, roi = self.get_synapse_by_row_id(rowid)

        if column == "#0": # Catches editable Synapse Name
            if synapse is None or roi is not None: 
                return
        elif column == "#1": # Catches editable fields
            if len(rowid_fiels) < 2: return # Editable rows have form {roi.uuid}_{modifiable_field_name}
            if rowid_fiels[1] not in SynapseTreeview.editableFiels: return
            if synapse is None or roi is None: return
        else:
            return

        self._entryPopup = EntryPopup(self, self._on_entry_changed, rowid, column)
        self._entryPopup.place_auto()
        return "break"

    def _on_right_click(self, event):
        """ Triggered on right clicking in the Treeview. Opens a context menu. """
        rowid = self.identify_row(event.y)
        synapse, roi = self.get_synapse_by_row_id(rowid)

        contextMenu = tk.Menu(self.master, tearoff=0)
        addMenu = tk.Menu(contextMenu, tearoff=0)
        if self.option_allowAddingSingleframeSynapses or self.option_allowAddingMultiframeSynapses:
            if self.option_allowAddingSingleframeSynapses:
                addMenu.add_command(label="Circular ROI Synapse", command = lambda: self._on_context_menu_add("Singleframe_CircularROI"))
            if self.option_allowAddingMultiframeSynapses:
                addMenu.add_command(label="Multiframe Synapse", command = lambda: self._on_context_menu_add("MultiframeSynapse"))  
            contextMenu.add_cascade(menu=addMenu, label="Add")

        stageMenu = tk.Menu(contextMenu, tearoff=0)
        stageMenu.add_command(label="All to stage", command = self._on_context_menu_all_to_stage)    
        stageMenu.add_command(label="All from stage", command = self._on_context_menu_all_from_stage)  
        contextMenu.add_cascade(menu=stageMenu, label="Stage")  

        clearMenu = tk.Menu(contextMenu, tearoff=0)
        clearMenu.add_command(label="Clear", command= lambda: self.clear_synapses('non_staged'))
        clearMenu.add_command(label="Clear staged", command= lambda: self.clear_synapses('staged'))
        clearMenu.add_command(label="Clear all", command= lambda: self.clear_synapses('all'))
        contextMenu.add_cascade(menu=clearMenu, label="Clear/Remove")

        importMenu = tk.Menu(contextMenu, tearoff=0)
        contextMenu.add_cascade(menu=importMenu, label="Import")

        exportMenu = tk.Menu(contextMenu, tearoff=0)
        self.detection_result
        exportMenu.add_command(label="Export as file", command=self._on_context_menu_export)
        contextMenu.add_cascade(menu=exportMenu, label="Export")

        if synapse is not None or roi is not None:
            clearMenu.insert_separator(index=0)
            stageMenu.insert_separator(index=0)

        if synapse is not None:
            if synapse.name is not None:
                clearMenu.insert_command(index=0, label="Reset name", command = lambda: self._on_context_menu_reset_name(synapse=synapse))
            clearMenu.insert_command(index=0, label="Remove Synapse", command = lambda: self._on_context_menu_remove(synapse=synapse))
            stageMenu.insert_command(index=0, label="Toggle Stage", command = lambda: self._on_context_menu_toggle_stage(synapse=synapse))

            if isinstance(synapse, MultiframeSynapse):
                addMenu.add_separator()
                addMenu.add_command(label="Circular ROI",  command = lambda: self._on_context_menu_add("CircularROI", synapse=synapse))

        if roi is not None and isinstance(synapse, MultiframeSynapse):
            clearMenu.insert_command(index=0, label="Remove ROI", command = lambda: self._on_context_menu_remove(synapse=synapse, roi=roi))

        window_events.SynapseTreeviewContextMenuEvent(import_context_menu=importMenu, export_context_menu=exportMenu, detection_result=self.detection_result)

        contextMenu.post(event.x_root, event.y_root)  
        

    def _on_entry_changed(self, rowid: str, column: str, oldval: str, val: str):
        """ Called after a EntryPopup closes with a changed value. Determines the corresponding ISynapse and modifies it"""

        rowid_fiels = rowid.split("_")
        synapse, roi = self.get_synapse_by_row_id(rowid)

        if column == "#0": # Catches editable Synapse Name
            if synapse is None or roi is not None: 
                return
            synapse.name = val
            logger.debug(f"Renamed synapse {synapse.uuid} to '{val}'")
        elif column == "#1": # Catches editable fields
            if len(rowid_fiels) < 2: return # Editable rows have form {roi.uuid}_{modifiable_field_name}
            if rowid_fiels[1] not in SynapseTreeview.editableFiels: return
            if synapse is None or roi is None: return

            match (rowid_fiels[1]):
                case "CircularSynapseROI.Frame":
                    if not val.isdigit() or int(val) < 1:
                        logger.debug(f"Invalid input for edtiable field '{rowid_fiels[1]}': {val}")
                        self.master.bell()
                        return
                    roi.set_frame(int(val) - 1)
                    logger.debug(f"Modified frame of CircularSynapseROI to {roi.frame}")
                case "CircularSynapseROI.Center":
                    if (_match := re.match(r"^(\d+),(\d+)$", val.replace(" ", "").replace("(", "").replace(")", ""))) is None or len(_match.groups()) != 2:
                        logger.debug(f"Invalid input for edtiable field '{rowid_fiels[1]}': {val}")
                        self.master.bell()
                        return
                    roi.set_location(x=int(_match.groups()[0]), y=int(_match.groups()[1]))
                    logger.debug(f"Modified location of CircularSynapseROI to {roi.location_string}")
                case "CircularSynapseROI.Radius":
                    roi = cast(CircularSynapseROI, roi)
                    if not val.isdigit():
                        logger.debug(f"Invalid input for edtiable field '{rowid_fiels[1]}': {val}")
                        self.master.bell()
                        return
                    roi.set_radius(int(val))
                    logger.debug(f"Modified radius of CircularSynapseROI to {roi.radius}")
                case _:
                    logger.warning(f"SynapseTreeview: Unexpected invalid editable field {rowid_fiels[1]}")
                    return
        else:
            return
        
        self.modified = True
        self.sync_synapses()

    def _update_ISynapseROI(self, roi: ISynapseROI):
        """ Updates the values in the treeview for a given ISynapseROI """
        _ruuid = roi.uuid
        self.delete(*self.get_children(_ruuid))
        if roi.frame is not None:
            self.insert(_ruuid, 'end', iid=f"{_ruuid}_CircularSynapseROI.Frame", text="Frame", values=[roi.frame + 1])

        if roi.signal_strength is not None:
            self.insert(_ruuid, 'end', iid=f"{_ruuid}_CircularSynapseROI.SignalStrength", text="Signal Strength", values=[f"{roi.signal_strength:1.3f}"])
        
        if type(roi) == CircularSynapseROI:
            type_ = "Circular ROI"
            self.insert(_ruuid, 'end', iid=f"{_ruuid}_CircularSynapseROI.Radius", text="Radius", values=[roi.radius if roi.radius is not None else ''])
            self.insert(_ruuid, 'end', iid=f"{_ruuid}_CircularSynapseROI.Center", text="Center(X,Y)",  values=[roi.location_string])
        elif type(roi) == PolygonalSynapseROI:
            type_ = "Polygonal ROI"
        else:
            type_ = "Undefined ROI"

        if roi.region_props is not None:
            rp = roi.region_props
            rp_id = f"{_ruuid}_RegionProperties"
            self.insert(_ruuid, 'end', iid=f"{_ruuid}_RegionProperties", text="Properties", values=[])
            self.insert(rp_id, 'end', iid=f"{_ruuid}_RegionProperties.Area", text="Area [px]", values=[rp.area])
            self.insert(rp_id, 'end', iid=f"{_ruuid}_RegionProperties.CircleRadius", text=f"Radius of circle with same size [px]", values=([f"{round(rp.equivalent_diameter_area/2, 2)}"]))
            self.insert(rp_id, 'end', iid=f"{_ruuid}_RegionProperties.Eccentricity", text=f"Eccentricity [0,1)", values=([f"{round(rp.eccentricity, 3)}"]))
            self.insert(rp_id, 'end', iid=f"{_ruuid}_RegionProperties.SignalMax", text=f"Signal Maximum", values=([f"{round(rp.intensity_max, 2)}"]))
            self.insert(rp_id, 'end', iid=f"{_ruuid}_RegionProperties.SignalMin", text=f"Signal Minimum", values=([f"{round(rp.intensity_min, 2)}"]))
            self.insert(rp_id, 'end', iid=f"{_ruuid}_RegionProperties.SignalMean", text=f"Signal Mean", values=([f"{round(rp.intensity_mean, 2)}"]))
            self.insert(rp_id, 'end', iid=f"{_ruuid}_RegionProperties.SignalStd", text=f"Signal Std.", values=([f"{round(rp.intensity_std, 2)}"]))
            self.insert(rp_id, 'end', iid=f"{_ruuid}_RegionProperties.InertiaX", text=f"Inertia X", values=([f"{round(rp.inertia_tensor[0,0], 2)}"]))
            self.insert(rp_id, 'end', iid=f"{_ruuid}_RegionProperties.InertiaY", text=f"Inertia Y", values=([f"{round(rp.inertia_tensor[1,1], 2)}"]))
            self.insert(rp_id, 'end', iid=f"{_ruuid}_RegionProperties.InertiaRatio", text=f"Inertia Ratio", values=([f"{round(rp.inertia_tensor[0,0]/rp.inertia_tensor[1,1], 2)}"]))
        self.item(_ruuid, text=type_, values=[f"Frame {roi.frame + 1}" if roi.frame is not None else ''])

    # Button Clicks

    def _btn_remove_cick(self):
        """ Triggered when clicking the Remove button """
        synapse, roi = self.get_selected_synapse()
        if synapse is not None and roi is not None and self.option_allowAddingMultiframeSynapses:
            self._on_context_menu_remove(synapse, roi)
        elif synapse is not None:
            self._on_context_menu_remove(synapse)
        else:
            self.master.bell()
            
    def _btn_stage_click(self):
        """ Triggered when clicking the Stage button """
        synapse, roi = self.get_selected_synapse()
        if synapse is not None:
            self._on_context_menu_toggle_stage(synapse)
        else:
            self.master.bell()

    # Context Menu Clicks

    def _on_context_menu_add(self, class_: Literal["CircularROI", "PolyonalROI", "MultiframeSynapse", "Singleframe_CircularROI", "Singleframe_PolyonalROI"], synapse: ISynapse|None = None):
        if isinstance(synapse, MultiframeSynapse):
            match class_:
                case "CircularROI":
                    r = CircularSynapseROI().set_radius(6).set_location(x=0,y=0).set_frame(0)
                case "PolyonalROI":
                    r = PolygonalSynapseROI().set_frame(0)
                case _:
                    return
            s = cast(MultiframeSynapse, self.detection_result[synapse.uuid])
            s.rois.append(r)
        else:
            match class_:
                case "Singleframe_CircularROI":
                    s = SingleframeSynapse(CircularSynapseROI().set_radius(6).set_location(x=0,y=0))
                case "Singleframe_PolyonalROI":
                    s = SingleframeSynapse(PolygonalSynapseROI())
                case "MultiframeSynapse":
                    s = MultiframeSynapse()
                case _:
                    return
            self.detection_result.append(s)
        self.modified = True
        self.sync_synapses()

    def _on_context_menu_all_to_stage(self):
        for s in self.detection_result:
            s.staged = True
        self.sync_synapses()

    def _on_context_menu_all_from_stage(self):
        for s in self.detection_result:
            s.staged = False
        self.sync_synapses()

    def _on_context_menu_toggle_stage(self, synapse: ISynapse):
        synapse.staged = not synapse.staged
        self.sync_synapses()
    
    def _on_context_menu_remove(self, synapse: ISynapse|None = None, roi: ISynapseROI|None = None):
        if synapse is not None and roi is not None:
            synapse.rois.remove(roi)
        elif synapse is not None:
            self.detection_result.remove(synapse)
        self.modified = True
        self.sync_synapses()

    def _on_context_menu_reset_name(self, synapse: ISynapse):
        synapse.name = None
        self.sync_synapses()

    def _on_context_menu_export(self) -> None:
        assert self.session.root is not None
        imgObj = self.session.active_image_object
        if imgObj is None or imgObj.img is None:
            self.session.root.bell()
            return
        path = filedialog.asksaveasfilename(title=f"Neurotorch: Select a path to export the multi measure", filetypes=(("CSV", "*.csv"), ("All files", "*.*")), defaultextension="*.csv")
        if path is None or path == "" or not (path := Path(path)).exists():
            self.session.root.bell()
            return
        if not self.detection_result.export_traces(path, imgObj):
            logger.warning(f"Failed to export the traces to TraceSelector")
            messagebox.showwarning(f"Neurotorch", "Failed to export the traces to TraceSelector")

    def clear_synapses(self, target: Literal['staged', 'non_staged', 'all']):
        match(target):
            case 'staged':
                self.detection_result.clear_where(lambda s: s.staged)
            case 'non_staged':
                self.detection_result.clear_where(lambda s: not s.staged)
            case 'all':
                self.detection_result.clear()
            case _:
                return
        self.modified = False
        self.sync_synapses()


class EntryPopup(ttk.Entry):
    """
        Implements editabled ttk Treeview entries
    """

    def __init__(self, tv: ttk.Treeview, callback: Callable[[str, str, str, str], None], rowid: str, column: str, **kw):
        ttk.Style().configure('pad.TEntry', padding='1 1 1 1')
        super().__init__(tv, style='pad.TEntry', **kw)
        self.tv = tv
        self.callback = callback
        self.rowid = rowid
        self.column = column
        if self.column == "#0":
            self.oldval = self.tv.item(self.rowid, 'text')
        else:
            self.oldval = self.tv.item(self.rowid, 'values')[int(self.column[1:]) - 1]

        self.insert(0, self.oldval) 

        self.focus_force()
        self.select_all()
        self.bind("<Return>", self.on_return)
        self.bind("<Escape>", lambda *val1: self.destroy())
        self.bind("<FocusOut>", lambda *val1: self.destroy())

    def place_auto(self):
        bbox = self.tv.bbox(self.rowid, self.column)
        if bbox == "":
            return
        x,y,width,height = bbox
        pady = height // 2
        self.place(x=x, y=y+pady, width=width, height=height, anchor=tk.W)

    def on_return(self, event):
        val = self.get()
        try:
            if self.oldval != val:
                self.callback(self.rowid, self.column, self.oldval, val)
        finally:
            self.destroy()

    def select_all(self, *val1):
        self.selection_range(0, 'end')
        return 'break'